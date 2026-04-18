import json
import time
import webbrowser

import requests

from .prompts import prompt_choice, prompt_non_empty, prompt_yes_no
from .settings import CONFIG_FILE, REQUEST_TIMEOUT, TRAKT_API, USER_AGENT, session


BASE_HEADERS = {
    'Accept': 'application/json',
    'User-Agent': USER_AGENT,
    'Connection': 'Keep-Alive'
}

TOKEN_EXPIRY_SKEW_SECONDS = 60


def load_config():
    """Load the saved configuration if the file exists and contains JSON."""
    if not CONFIG_FILE.exists():
        return {}

    try:
        with CONFIG_FILE.open('r', encoding='utf-8') as file_handle:
            data = json.load(file_handle)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f'Error loading config file: {exc}')
        return {}


def save_config(config):
    """Persist the configuration to disk."""
    try:
        with CONFIG_FILE.open('w', encoding='utf-8') as file_handle:
            json.dump(config, file_handle, indent=4)
        print(f'Configuration saved to {CONFIG_FILE.name}')
    except OSError as exc:
        print(f'Error saving config file: {exc}')


def get_token_expiry(token_payload):
    """Return the absolute access-token expiry timestamp when it can be derived."""
    expires_at = token_payload.get('expires_at')
    if expires_at is not None:
        try:
            return int(expires_at)
        except (TypeError, ValueError):
            return None

    expires_in = token_payload.get('expires_in')
    if expires_in is None:
        return None

    try:
        expires_in = int(expires_in)
    except (TypeError, ValueError):
        return None

    created_at = token_payload.get('created_at')
    try:
        base_time = int(created_at) if created_at is not None else int(time.time())
    except (TypeError, ValueError):
        base_time = int(time.time())

    return base_time + expires_in


def is_token_expired(config):
    """Return True when a saved token has a known expiry that is due or already passed."""
    expires_at = get_token_expiry(config)
    if expires_at is None:
        return False

    return expires_at <= int(time.time()) + TOKEN_EXPIRY_SKEW_SECONDS


def build_saved_token_config(client_id, client_secret, username, token_payload):
    """Build the persisted auth config using the latest OAuth token payload."""
    config = {
        'client_id': client_id,
        'client_secret': client_secret,
        'username': username,
        'access_token': token_payload['access_token']
    }

    refresh_token = token_payload.get('refresh_token')
    if refresh_token:
        config['refresh_token'] = refresh_token

    expires_at = get_token_expiry(token_payload)
    if expires_at is not None:
        config['expires_at'] = expires_at

    return config


def request_token(post_data, error_prefix):
    """Request a Trakt OAuth token and return the parsed JSON payload."""
    try:
        response = session.post(f'{TRAKT_API}/oauth/token', data=post_data, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f'{error_prefix}: {exc}') from exc

    try:
        token_payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f'{error_prefix}: Trakt returned a non-JSON response.') from exc

    access_token = token_payload.get('access_token')
    if response.status_code != 200 or not access_token:
        error_message = token_payload.get('error_description') or token_payload.get('error') or response.text
        raise RuntimeError(f'{error_prefix}: HTTP {response.status_code} - {error_message}')

    return token_payload


def refresh_access_token(client_id, client_secret, username, config):
    """Try to exchange a saved refresh token for a new access token."""
    refresh_token = config.get('refresh_token')
    if not refresh_token:
        return False

    print('Saved access token expired or is invalid, trying to refresh it...')
    set_api_headers(client_id)

    try:
        token_payload = request_token({
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'refresh_token'
        }, 'Token refresh failed')
    except RuntimeError as exc:
        print(f'Warning: {exc}')
        print('Saved refresh token is not usable, requesting a new token...')
        return False

    save_config(build_saved_token_config(client_id, client_secret, username, token_payload))
    print('Authentication token refreshed and saved for future use.')
    set_api_headers(client_id, token_payload['access_token'])
    return True


def set_api_headers(client_id, access_token=None):
    """Apply the headers required by the Trakt API to the shared session."""
    session.headers.clear()
    session.headers.update(BASE_HEADERS)

    if access_token:
        session.headers.update({
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': client_id,
            'Authorization': f'Bearer {access_token}'
        })


def get_user_credentials():
    """Collect Trakt API credentials, reusing saved values when possible."""
    config = load_config()

    if config.get('client_id') and config.get('client_secret') and config.get('username'):
        print('Found saved credentials:')
        print(f"  Client ID: {config['client_id'][:10]}...")
        print(f"  Username: {config['username']}")
        print()
        print('Options:')
        print('  1. Use saved credentials')
        print('  2. Enter new credentials')
        print('  3. Delete saved configuration and exit')

        choice = prompt_choice('Choose an option', {'1', '2', '3'})
        if choice == '1':
            return config['client_id'], config['client_secret'], config['username']
        if choice == '3':
            CONFIG_FILE.unlink(missing_ok=True)
            print(f'Configuration file {CONFIG_FILE.name} deleted.')
            print('Restart the script if you want to enter new credentials now.')
            raise SystemExit(0)

        print()

    print('Register a new API app at https://trakt.tv/oauth/applications/new if needed.')
    print('Use these values:')
    print('  Name: trakt-duplicates-removal')
    print('  Redirect URI: urn:ietf:wg:oauth:2.0:oob')
    print('Other fields can be left empty for this script.')
    print()

    client_id = prompt_non_empty('Enter your client ID')
    client_secret = prompt_non_empty('Enter your client secret')
    username = prompt_non_empty('Enter your Trakt username')

    if prompt_yes_no('Save these credentials for future runs?', default='yes'):
        save_config({
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username
        })

    return client_id, client_secret, username


def login_to_trakt(client_id, client_secret, username):
    """Authenticate the session, reusing a compatible saved access token when possible."""
    config = load_config()
    saved_access_token = config.get('access_token')
    matching_credentials = config.get('client_id') == client_id and config.get('username') == username

    if matching_credentials and saved_access_token:
        if is_token_expired(config):
            if refresh_access_token(client_id, client_secret, username, config):
                return
        else:
            print('Found a saved access token, testing authentication...')
            set_api_headers(client_id, saved_access_token)

            try:
                test_response = session.get(f'{TRAKT_API}/users/me', timeout=REQUEST_TIMEOUT)
            except requests.exceptions.RequestException as exc:
                print(f'Warning: Could not verify the saved token, requesting a new one. Error: {exc}')
            else:
                if test_response.status_code == 200:
                    print('Existing token is valid, skipping OAuth.')
                    return

                if test_response.status_code == 401 and refresh_access_token(client_id, client_secret, username, config):
                    return

                print('Saved token is no longer valid, requesting a new one...')
    elif matching_credentials and config.get('refresh_token'):
        if refresh_access_token(client_id, client_secret, username, config):
            return
    elif saved_access_token:
        print('Saved token does not match the selected credentials, so it will be ignored.')

    auth_url = (
        'https://trakt.tv/oauth/authorize'
        f'?response_type=code&client_id={client_id}&redirect_uri=urn:ietf:wg:oauth:2.0:oob'
    )
    webbrowser.open(auth_url)
    set_api_headers(client_id)

    post_data = {
        'code': prompt_non_empty('Paste the PIN returned by Trakt'),
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'grant_type': 'authorization_code'
    }

    token_payload = request_token(post_data, 'Authentication request failed')

    save_config(build_saved_token_config(client_id, client_secret, username, token_payload))
    print('Authentication token saved for future use.')

    set_api_headers(client_id, token_payload['access_token'])

