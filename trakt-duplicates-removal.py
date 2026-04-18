import json
import webbrowser
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

CONFIG_FILE = 'auth_config.json'


def load_config():
    """Load authentication configuration from file if it exists."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")
    return {}


def save_config(config):
    """Save authentication configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"Error saving config file: {e}")


def get_user_input():
    """Get user input for authentication, using saved values as defaults."""
    config = load_config()

    # Check if we have saved credentials first
    if config.get('client_id') and config.get('client_secret') and config.get('username'):
        print("Found saved credentials:")
        print(f"  Client ID: {config['client_id'][:10]}...")
        print(f"  Username: {config['username']}")
        print()
        print("Options:")
        print("  1. Use saved credentials")
        print("  2. Enter new credentials")
        print("  3. Delete saved configuration")

        choice = input("Choose option (1/2/3): ").strip()

        if choice == '1':
            return config['client_id'], config['client_secret'], config['username']
        elif choice == '3':
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
                print(f"Configuration file {CONFIG_FILE} deleted.")
            else:
                print("No configuration file found.")
            print("Please restart the script to enter new credentials.")
            exit(0)
        # If choice == '2' or invalid choice, continue to get new credentials
        print()

    # Only show API registration instructions when entering new credentials
    print("- Register a new API app at: https://trakt.tv/oauth/applications/new or skip if you already have one (https://trakt.tv/oauth/applications)")
    print("- Fill the form with these details:")
    print("\tName: trakt-duplicates-removal")
    print("\tRedirect URI: urn:ietf:wg:oauth:2.0:oob")
    print("\tYou don't need to fill the other fields.")
    print("  Leave the app's page open.")
    print()

    # Get new credentials
    client_id = input("- Enter your client ID: ").strip()
    client_secret = input("- Enter your client secret: ").strip()
    username = input("- Enter your username: ").strip()

    # Save credentials
    save_credentials = input("Save these credentials for future use? (yes/no): ").strip().lower()
    if save_credentials == 'yes':
        new_config = {
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username
        }
        save_config(new_config)

    return client_id, client_secret, username


client_id, client_secret, username = get_user_input()

types = []
correct_movie_history = False
if input("- Include movies? (yes/no): ").strip().lower() == 'yes':
    types.append('movies')
    if input("- Correct movie history by setting watched date to release date? (yes/no): ").strip().lower() == 'yes':
        correct_movie_history = True
if input("- Include episodes? (yes/no): ").strip().lower() == 'yes':
    types.append('episodes')

if not correct_movie_history:
    keep_per_day = input("- Remove repeated only on distinct days? (yes/no): ").strip().lower() == 'yes'
    keep_strategy = input("- Keep oldest or newest plays? (oldest/newest): ").strip().lower()
    if keep_strategy != 'oldest' and keep_strategy != 'newest':
        print("Invalid option. Defaulting to 'oldest'.")
        keep_strategy = 'oldest'
else:
    keep_per_day = False
    keep_strategy = 'oldest'

trakt_api = 'https://api.trakt.tv'

session = requests.Session()

# Will be populated after login
USER_TIMEZONE = "UTC"


def login_to_trakt():
    # Check if we have a saved access token
    config = load_config()

    if config.get('access_token'):
        print("Found saved access token, testing authentication...")

        # Test the saved token
        session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Betaseries to Trakt',
            'Connection': 'Keep-Alive',
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': client_id,
            'Authorization': 'Bearer ' + config['access_token']
        })

        # Test token by making a simple API call
        test_url = f'{trakt_api}/users/me'
        test_response = session.get(test_url)

        if test_response.status_code == 200:
            print("Existing token is valid, skipping authentication.")
            return
        else:
            print("Saved token is invalid, proceeding with new authentication...")

    # Proceed with OAuth authentication
    webbrowser.open(f'https://trakt.tv/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri=urn:ietf:wg:oauth:2.0:oob')

    session.headers.update({
        'Accept': 'application/json',
        'User-Agent': 'Betaseries to Trakt',
        'Connection': 'Keep-Alive'
    })

    pin = str(input('- Paste the PIN: '))
    post_data = {
        'code': pin,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'grant_type': 'authorization_code'
    }

    auth_get_token_url = '%s/oauth/token' % trakt_api
    request = session.post(auth_get_token_url, data=post_data)
    response = request.json()

    print(response)
    print()

    # Save the new access token
    if 'access_token' in response:
        config = load_config()
        config.update({
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username,
            'access_token': response['access_token']
        })

        # Also save refresh token if available
        if 'refresh_token' in response:
            config['refresh_token'] = response['refresh_token']

        save_config(config)
        print("Authentication tokens saved for future use.")

    session.headers.update({
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': client_id,
        'Authorization': 'Bearer ' + response["access_token"]
    })


def get_trakt_user_timezone():
    """
    Fetch the user's Trakt timezone (IANA tz name) from /users/settings.
    Falls back to 'UTC' if unavailable or request fails.
    """
    try:
        resp = session.get(f"{trakt_api}/users/settings")
        if resp.status_code != 200:
            return "UTC"

        data = resp.json() or {}
        tz = (data.get("account", {}) or {}).get("timezone")
        if not tz:
            return "UTC"

        # Validate it
        ZoneInfo(tz)
        return tz
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        print(f"Warning: Could not determine user timezone, falling back to UTC. Error: {e}")
        return "UTC"


def watched_date_in_tz(watched_at: str, tz_name: str) -> str:
    """
    Convert Trakt watched_at (ISO8601) into a YYYY-MM-DD in the given timezone.
    Handles 'Z' suffix and date-only strings.
    """
    s = watched_at.strip()

    # Date-only: treat as midnight UTC
    if "T" not in s:
        dt = datetime.fromisoformat(s + "T00:00:00+00:00")
    else:
        # Python's fromisoformat doesn't accept trailing Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)

        # If naive, assume UTC (shouldn't normally happen, but safe)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(ZoneInfo(tz_name)).date().isoformat()


def get_history(type):
    results = []

    url_params = {
        'page': 1,
        'limit': 1000,
        'type': type
    }

    print('   ... retrieving history for %s' % type)

    get_history_url = '%s/users/%s/history/{type}?page={page}&limit={limit}' % (trakt_api, username)
    while True:
        print("\t" + get_history_url.format(**url_params))
        resp = session.get(get_history_url.format(**url_params))

        if resp.status_code != 200:
            print(resp)
            continue

        results += resp.json()

        if int(resp.headers['X-Pagination-Page-Count']) != url_params['page']:
            url_params['page'] += 1
        else:
            break

    print('   Done retrieving %s history' % type)
    return results


def correct_movie_history_func(history):
    print('   Preparing to correct movie history...')

    unique_movies = {}
    for item in history:
        movie = item['movie']
        trakt_id = movie['ids']['trakt']
        if trakt_id not in unique_movies:
            unique_movies[trakt_id] = movie

    ids_to_remove = [item['id'] for item in history]

    movies_to_add = []
    print('   Fetching release dates from Trakt.tv API...')

    for trakt_id, movie in unique_movies.items():
        # Get detailed movie information from Trakt.tv API to fetch release date
        movie_url = f'{trakt_api}/movies/{trakt_id}'
        try:
            movie_response = session.get(movie_url)
            if movie_response.status_code == 200:
                movie_details = movie_response.json()
                release_date = movie_details.get('released')

                if release_date:
                    # Use the exact release date from API
                    movies_to_add.append({
                        'watched_at': release_date,
                        'ids': movie['ids']
                    })
                else:
                    # Fallback: Use January 1st of the release year if no precise date available
                    year = movie.get('year')
                    if year:
                        fallback_date = f'{year}-01-01'
                        movies_to_add.append({
                            'watched_at': fallback_date,
                            'ids': movie['ids']
                        })
                        print(f'   Warning: No release date found for "{movie["title"]}" ({year}), using {fallback_date}')
            else:
                # If API call fails, use January 1st of the release year as fallback
                year = movie.get('year')
                if year:
                    fallback_date = f'{year}-01-01'
                    movies_to_add.append({
                        'watched_at': fallback_date,
                        'ids': movie['ids']
                    })
                    print(f'   Warning: Could not fetch details for "{movie["title"]}" (API error), using {fallback_date}')
        except Exception as e:
            # If any error occurs, use January 1st of the release year as fallback
            year = movie.get('year')
            if year:
                fallback_date = f'{year}-01-01'
                movies_to_add.append({
                    'watched_at': fallback_date,
                    'ids': movie['ids']
                })
                print(f'   Warning: Error fetching details for "{movie["title"]}" ({e}), using {fallback_date}')

    if not movies_to_add:
        print('   No movies with release dates found. Aborting.')
        return

    print("\n   PREVIEW OF HISTORY CORRECTION:")
    print("   ------------------------------")
    print(f"   Movies to be removed: {len(ids_to_remove)}")
    print(f"   Unique movies to be re-added: {len(movies_to_add)}")
    for movie in movies_to_add:
        title = [m['movie']['title'] for m in history if m['movie']['ids']['trakt'] == movie['ids']['trakt']][0]
        print(f"   - {title} -> Watched at: {movie['watched_at']}")

    confirm = input("\n   Proceed with history correction? (yes/no): ").strip().lower()
    if confirm == 'yes':
        # Remove all movie history
        remove_url = '%s/sync/history/remove' % trakt_api
        remove_payload = {'ids': ids_to_remove}
        remove_response = session.post(remove_url, json=remove_payload)

        if remove_response.status_code == 200:
            print('   All movie history successfully removed.')

            # Add movies back with release date as watched date
            add_url = '%s/sync/history' % trakt_api
            add_payload = {'movies': movies_to_add}
            add_response = session.post(add_url, json=add_payload)

            if add_response.status_code == 201:
                print('   Movies successfully added back to history.')
            else:
                print('   Error adding movies back to history. Status code:', add_response.status_code)
                print('   Response:', add_response.text)
        else:
            print('   Error removing movie history. Status code:', remove_response.status_code)
            print('   Response:', remove_response.text)
    else:
        print('   History correction cancelled.')


def remove_duplicate(history, type):
    print('   Finding %s duplicates' % type)

    entry_type = 'movie' if type == 'movies' else 'episode'

    duplicates = []
    duplicate_details = []

    # If keeping newest, we need to process the history in chronological order
    # (The history array is already sorted from newest to oldest)
    process_order = history if keep_strategy == 'newest' else history[::-1]

    # Track what we have decided to keep
    seen_any = set()              # trakt_id seen at least once (when keep_per_day=False)
    seen_dates = {}               # trakt_id -> set({YYYY-MM-DD,...}) (when keep_per_day=True)

    for i in process_order:
        trakt_id = i[entry_type]['ids']['trakt']
        watched_date = watched_date_in_tz(i['watched_at'], USER_TIMEZONE)

        is_dup = False
        if keep_per_day:
            dates = seen_dates.setdefault(trakt_id, set())
            if watched_date in dates:
                is_dup = True
            else:
                dates.add(watched_date)
        else:
            if trakt_id in seen_any:
                is_dup = True
            else:
                seen_any.add(trakt_id)

        if is_dup:
            duplicates.append(i['id'])

            if entry_type == 'movie':
                title = i['movie']['title']
            else:
                show_title = i['show']['title']
                episode_title = i['episode']['title']
                season = i['episode']['season']
                number = i['episode']['number']
                title = f"{show_title} - S{season:02d}E{number:02d} - {episode_title}"

            duplicate_details.append({
                'id': i['id'],
                'title': title,
                'watched_at': i['watched_at']
            })

    if len(duplicates) > 0:
        print('   %s %s duplicates plays found' % (len(duplicates), type))

        # Preview the duplicates that will be removed
        print("\n   PREVIEW OF ENTRIES TO BE DELETED:")
        print("   --------------------------------")

        # Sort by title for a better display
        duplicate_details.sort(key=lambda x: x['title'])

        for idx, item in enumerate(duplicate_details, 1):
            print(f"   {idx}. {item['title']} - Watched on: {item['watched_at']}")

        print("\n   Total: %s %s duplicates" % (len(duplicates), type))

        # Ask user if they want to proceed
        confirm = input("\n   Proceed with deletion? (yes/no): ").strip().lower()

        if confirm == 'yes':
            sync_history_url = '%s/sync/history/remove' % trakt_api
            response = session.post(sync_history_url, json={'ids': duplicates})

            if response.status_code == 200:
                print('   %s %s duplicates successfully removed!' % (len(duplicates), type))
            else:
                print('   Error removing duplicates. Status code:', response.status_code)
                print('   Response:', response.text)
        else:
            print('   Deletion cancelled.')
    else:
        print('   No %s duplicates found' % type)


if __name__ == '__main__':
    login_to_trakt()

    # Determine timezone for per-day grouping:
    # - Use Trakt user setting if available
    # - Fall back to UTC otherwise
    USER_TIMEZONE = get_trakt_user_timezone()
    print(f"Using timezone for per-day grouping: {USER_TIMEZONE}")

    for type in types:
        history = get_history(type)
        with open('%s.json' % type, 'w') as output:
            json.dump(history, output, indent=4)
            print('   History saved in file %s.json' % type)

        if type == 'movies' and correct_movie_history:
            correct_movie_history_func(history)
        else:
            remove_duplicate(history, type)
        print()
