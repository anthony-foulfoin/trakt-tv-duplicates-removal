import json
import webbrowser

import requests

print("- Register a new API app at: https://trakt.tv/oauth/applications/new or skip if you already have one (https://trakt.tv/oauth/applications)")
print("- Fill the form with these details:")
print("\tName: trakt-duplicates-removal")
print("\tRedirect URI: urn:ietf:wg:oauth:2.0:oob")
print("\tYou don't need to fill the other fields.")
print("  Leave the app's page open.")

client_id = input("- Enter your client ID: ")
client_secret = input("- Enter your client secret: ")
username = input("- Enter your username: ")
types = []
if input("- Include movies? (yes/no): ").strip().lower() == 'yes':
    types.append('movies')
if input("- Include episodes? (yes/no): ").strip().lower() == 'yes':
    types.append('episodes')
keep_per_day = input("- Remove repeated only on distinct days? (yes/no): ").strip().lower() == 'yes'
keep_strategy = input("- Keep oldest or newest plays? (oldest/newest): ").strip().lower()
if keep_strategy != 'oldest' and keep_strategy != 'newest':
    print("Invalid option. Defaulting to 'oldest'.")
    keep_strategy = 'oldest'

trakt_api = 'https://api.trakt.tv'

session = requests.Session()


def login_to_trakt():
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

    session.headers.update({
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': client_id,
        'Authorization': 'Bearer ' + response["access_token"]
    })


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


def remove_duplicate(history, type):
    print('   Removing %s duplicates' % type)

    entry_type = 'movie' if type == 'movies' else 'episode'

    entries = {}
    duplicates = []
    
    # If keeping newest, we need to process the history in chronological order
    # (The history array is already sorted from newest to oldest)
    process_order = history if keep_strategy == 'newest' else history[::-1]
    
    for i in process_order:
        trakt_id = i[entry_type]['ids']['trakt']
        watched_date = i['watched_at'].split('T')[0]
        
        if trakt_id in entries:
            # Check if it's a duplicate on the same day (if keeping per day)
            if not keep_per_day or watched_date == entries[trakt_id][0]:
                duplicates.append(i['id'])
        else:
            entries[trakt_id] = (watched_date, i['id'])

    if len(duplicates) > 0:
        print('   %s %s duplicates plays to be removed' % (len(duplicates), type))

        sync_history_url = '%s/sync/history/remove' % trakt_api
        session.post(sync_history_url, json={'ids': duplicates})
        print('   %s %s duplicates successfully removed!' % (len(duplicates), type))
    else:
        print('   No %s duplicates found' % type)


if __name__ == '__main__':
    login_to_trakt()

    for type in types:
        history = get_history(type)
        with open('%s.json' % type, 'w') as output:
            json.dump(history, output, indent=4)
            print('   History saved in file %s.json' % type)

        remove_duplicate(history, type)
        print()
