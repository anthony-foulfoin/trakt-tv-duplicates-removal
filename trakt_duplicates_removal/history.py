import json
from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from .prompts import prompt_yes_no
from .settings import BACKUP_DIR, REQUEST_TIMEOUT, TRAKT_API, session


class HistoryError(RuntimeError):
    """Raised when a history-related Trakt operation fails."""


@lru_cache(maxsize=None)
def get_timezone_info(timezone_name):
    """Resolve an IANA timezone once and fall back to UTC when local tz data is missing."""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        print(f"Warning: Timezone data for '{timezone_name}' is not available locally, using UTC.")
        return timezone.utc


def get_trakt_user_timezone():
    """Fetch the user's Trakt timezone, falling back to UTC when unavailable."""
    try:
        response = session.get(f'{TRAKT_API}/users/settings', timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return 'UTC'

        data = response.json() or {}
        timezone_name = (data.get('account', {}) or {}).get('timezone')
        if not isinstance(timezone_name, str) or not timezone_name:
            return 'UTC'

        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            print(
                f"Warning: Timezone data for '{timezone_name}' is not available locally, "
                "falling back to UTC."
            )
            return 'UTC'

        return timezone_name
    except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
        print(f'Warning: Could not determine user timezone, falling back to UTC. Error: {exc}')
        return 'UTC'


def watched_date_in_tz(watched_at, timezone_name):
    """Convert a Trakt watched_at value to YYYY-MM-DD in the target timezone."""
    value = watched_at.strip()

    if 'T' not in value:
        date_time = datetime.fromisoformat(value + 'T00:00:00+00:00')
    else:
        # Trakt usually sends UTC timestamps with a trailing Z, which fromisoformat cannot parse directly.
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        date_time = datetime.fromisoformat(value)

        if date_time.tzinfo is None:
            date_time = date_time.replace(tzinfo=timezone.utc)

    return date_time.astimezone(get_timezone_info(timezone_name)).date().isoformat()


def get_history(history_type, username):
    """Download all history items for the requested Trakt type."""
    results = []
    url_params = {
        'page': 1,
        'limit': 1000,
        'history_type': history_type
    }

    print(f'   ... retrieving history for {history_type}')
    history_url = f'{TRAKT_API}/users/{username}/history/{{history_type}}?page={{page}}&limit={{limit}}'

    while True:
        request_url = history_url.format(**url_params)
        print(f'\t{request_url}')

        try:
            response = session.get(request_url, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            raise HistoryError(f'Unable to retrieve {history_type} history: {exc}') from exc

        if response.status_code != 200:
            raise HistoryError(
                f'Unable to retrieve {history_type} history: HTTP {response.status_code} - {response.text}'
            )

        page_items = response.json()
        if not isinstance(page_items, list):
            raise HistoryError(f'Unexpected response while retrieving {history_type} history.')

        results.extend(page_items)

        try:
            page_count = int(response.headers.get('X-Pagination-Page-Count', '1'))
        except ValueError:
            page_count = 1

        if url_params['page'] >= page_count:
            break

        url_params['page'] += 1

    print(f'   Done retrieving {history_type} history')
    return results


def save_history_backup(history_type, history):
    """Write a local JSON backup before any destructive API call."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f'{history_type}.json'
    with backup_path.open('w', encoding='utf-8') as output:
        json.dump(history, output, indent=4)
    print(f'   History saved in file {backup_path.relative_to(backup_path.parent.parent)}')


def build_movie_history_entry(movie):
    """Return a new movie history entry using the release date or a safe year fallback."""
    trakt_id = movie['ids']['trakt']
    title = movie['title']
    year = movie.get('year')

    try:
        response = session.get(f'{TRAKT_API}/movies/{trakt_id}', timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        response = None
        print(f'   Warning: Error fetching details for "{title}" ({exc}).')

    if response is not None and response.status_code == 200:
        movie_details = response.json() or {}
        release_date = movie_details.get('released')
        if release_date:
            return {
                'watched_at': release_date,
                'ids': movie['ids']
            }

        print(f'   Warning: No release date found for "{title}" in the API response.')
    elif response is not None:
        print(f'   Warning: Could not fetch details for "{title}" (HTTP {response.status_code}).')

    if year:
        fallback_date = f'{year}-01-01'
        print(f'   Warning: Using fallback date {fallback_date} for "{title}".')
        return {
            'watched_at': fallback_date,
            'ids': movie['ids']
        }

    print(f'   Warning: Skipping "{title}" because neither a release date nor a year is available.')
    return None


def correct_movie_history(history):
    """Replace movie history with one entry per movie using the release date as watched_at."""
    if not history:
        print('   No movie history entries found.')
        return

    print('   Preparing to correct movie history...')

    unique_movies = {}
    titles_by_trakt_id = {}
    for item in history:
        movie = item['movie']
        trakt_id = movie['ids']['trakt']
        titles_by_trakt_id.setdefault(trakt_id, movie['title'])
        unique_movies.setdefault(trakt_id, movie)

    ids_to_remove = [item['id'] for item in history]
    movies_to_add = []
    print('   Fetching release dates from the Trakt API...')

    for movie in unique_movies.values():
        new_entry = build_movie_history_entry(movie)
        if new_entry:
            movies_to_add.append(new_entry)

    if not movies_to_add:
        print('   No movies with usable release dates were found. Aborting.')
        return

    print('\n   PREVIEW OF HISTORY CORRECTION:')
    print('   ------------------------------')
    print(f'   Movies to be removed: {len(ids_to_remove)}')
    print(f'   Unique movies to be re-added: {len(movies_to_add)}')
    for movie in movies_to_add:
        title = titles_by_trakt_id.get(movie['ids']['trakt'], 'Unknown movie')
        print(f"   - {title} -> Watched at: {movie['watched_at']}")

    if not prompt_yes_no('Proceed with this movie history rewrite?', default='no'):
        print('   History correction cancelled.')
        return

    # This is a destructive flow: remove all movie history first, then add back one entry per movie.
    remove_response = session.post(
        f'{TRAKT_API}/sync/history/remove',
        json={'ids': ids_to_remove},
        timeout=REQUEST_TIMEOUT
    )
    if remove_response.status_code != 200:
        raise HistoryError(
            f'Unable to remove movie history: HTTP {remove_response.status_code} - {remove_response.text}'
        )

    print('   All movie history successfully removed.')

    add_response = session.post(
        f'{TRAKT_API}/sync/history',
        json={'movies': movies_to_add},
        timeout=REQUEST_TIMEOUT
    )
    if add_response.status_code not in {200, 201}:
        raise HistoryError(
            f'Unable to add corrected movie history: HTTP {add_response.status_code} - {add_response.text}'
        )

    print('   Movies successfully added back to history.')


def format_history_entry_title(item, entry_type):
    """Build a readable label for preview output."""
    if entry_type == 'movie':
        return item['movie']['title']

    show_title = item['show']['title']
    episode_title = item['episode'].get('title') or 'Unknown episode title'
    season = item['episode'].get('season', 0)
    number = item['episode'].get('number', 0)
    return f'{show_title} - S{season:02d}E{number:02d} - {episode_title}'


def remove_duplicates(history, history_type, keep_per_day, keep_strategy, user_timezone):
    """Remove duplicate movie or episode plays based on the selected strategy."""
    if not history:
        print(f'   No {history_type} history entries found.')
        return

    print(f'   Finding duplicate {history_type} plays')
    entry_type = 'movie' if history_type == 'movies' else 'episode'

    duplicates = []
    duplicate_details = []

    # Trakt returns history from newest to oldest. Reverse it only when we want to keep the oldest play.
    process_order = history if keep_strategy == 'newest' else list(reversed(history))

    seen_any = set()
    seen_dates = {}

    for item in process_order:
        trakt_id = item[entry_type]['ids']['trakt']
        watched_date = watched_date_in_tz(item['watched_at'], user_timezone)

        is_duplicate = False
        if keep_per_day:
            # Same-day duplicate mode uses the account timezone so local calendar days match what the user expects.
            dates = seen_dates.setdefault(trakt_id, set())
            if watched_date in dates:
                is_duplicate = True
            else:
                dates.add(watched_date)
        else:
            if trakt_id in seen_any:
                is_duplicate = True
            else:
                seen_any.add(trakt_id)

        if is_duplicate:
            duplicates.append(item['id'])
            duplicate_details.append({
                'id': item['id'],
                'title': format_history_entry_title(item, entry_type),
                'watched_at': item['watched_at']
            })

    if not duplicates:
        print(f'   No {history_type} duplicates found')
        return

    print(f'   {len(duplicates)} {history_type} duplicate plays found')
    print('\n   PREVIEW OF ENTRIES TO BE DELETED:')
    print('   --------------------------------')

    duplicate_details.sort(key=lambda item: (item['title'], item['watched_at']))
    for index, item in enumerate(duplicate_details, 1):
        print(f"   {index}. {item['title']} - Watched on: {item['watched_at']}")

    print(f'\n   Total: {len(duplicates)} {history_type} duplicates')
    if not prompt_yes_no('Proceed with deletion?', default='no'):
        print('   Deletion cancelled.')
        return

    response = session.post(
        f'{TRAKT_API}/sync/history/remove',
        json={'ids': duplicates},
        timeout=REQUEST_TIMEOUT
    )
    if response.status_code != 200:
        raise HistoryError(f'Unable to remove duplicates: HTTP {response.status_code} - {response.text}')

    print(f'   {len(duplicates)} {history_type} duplicate plays successfully removed!')

