import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trakt_duplicates_removal import auth
from tests.helpers import FakeResponse, QuietTestCase


class AuthTests(QuietTestCase):
    def setUp(self):
        super().setUp()
        self.original_headers = dict(auth.session.headers)

    def tearDown(self):
        auth.session.headers.clear()
        auth.session.headers.update(self.original_headers)
        super().tearDown()

    def test_load_config_returns_empty_dict_for_missing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'missing.json'
            with patch('trakt_duplicates_removal.auth.CONFIG_FILE', config_path):
                self.assertEqual(auth.load_config(), {})

    def test_save_and_load_config_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'auth.json'
            with patch('trakt_duplicates_removal.auth.CONFIG_FILE', config_path):
                auth.save_config({'client_id': 'abc', 'username': 'alice'})
                self.assertEqual(auth.load_config(), {'client_id': 'abc', 'username': 'alice'})
                self.assertEqual(json.loads(config_path.read_text(encoding='utf-8'))['client_id'], 'abc')

    def test_set_api_headers_populates_session_headers(self):
        auth.set_api_headers('client-id', 'token-123')

        self.assertEqual(auth.session.headers['trakt-api-key'], 'client-id')
        self.assertEqual(auth.session.headers['Authorization'], 'Bearer token-123')
        self.assertEqual(auth.session.headers['User-Agent'], auth.USER_AGENT)

    def test_get_user_credentials_returns_saved_values_when_requested(self):
        saved_config = {'client_id': 'cid', 'client_secret': 'secret', 'username': 'alice'}
        with patch('trakt_duplicates_removal.auth.load_config', return_value=saved_config), patch(
            'trakt_duplicates_removal.auth.prompt_choice',
            return_value='1'
        ):
            result = auth.get_user_credentials()

        self.assertEqual(result, ('cid', 'secret', 'alice'))

    def test_login_to_trakt_skips_oauth_when_saved_token_is_valid(self):
        with patch('trakt_duplicates_removal.auth.load_config', return_value={
            'client_id': 'cid',
            'username': 'alice',
            'access_token': 'token'
        }), patch.object(auth.session, 'get', return_value=FakeResponse(status_code=200)), patch(
            'trakt_duplicates_removal.auth.webbrowser.open'
        ) as browser_mock, patch.object(auth.session, 'post') as post_mock:
            auth.login_to_trakt('cid', 'secret', 'alice')

        browser_mock.assert_not_called()
        post_mock.assert_not_called()
        self.assertEqual(auth.session.headers['Authorization'], 'Bearer token')

    def test_login_to_trakt_requests_new_token_and_saves_it(self):
        save_patcher = patch('trakt_duplicates_removal.auth.save_config')
        save_mock = save_patcher.start()
        self.addCleanup(save_patcher.stop)

        with patch('trakt_duplicates_removal.auth.load_config', return_value={}), patch(
            'trakt_duplicates_removal.auth.prompt_non_empty',
            return_value='123456'
        ), patch('trakt_duplicates_removal.auth.webbrowser.open') as browser_mock, patch.object(
            auth.session,
            'post',
            return_value=FakeResponse(status_code=200, payload={'access_token': 'fresh-token'})
        ):
            auth.login_to_trakt('cid', 'secret', 'alice')

        browser_mock.assert_called_once()
        save_mock.assert_called_once_with({
            'client_id': 'cid',
            'client_secret': 'secret',
            'username': 'alice',
            'access_token': 'fresh-token'
        })
        self.assertEqual(auth.session.headers['Authorization'], 'Bearer fresh-token')

    def test_login_to_trakt_refreshes_expired_saved_token(self):
        save_patcher = patch('trakt_duplicates_removal.auth.save_config')
        save_mock = save_patcher.start()
        self.addCleanup(save_patcher.stop)

        with patch('trakt_duplicates_removal.auth.load_config', return_value={
            'client_id': 'cid',
            'client_secret': 'secret',
            'username': 'alice',
            'access_token': 'expired-token',
            'refresh_token': 'refresh-me',
            'expires_at': 1
        }), patch.object(
            auth.session,
            'post',
            return_value=FakeResponse(status_code=200, payload={
                'access_token': 'refreshed-token',
                'refresh_token': 'refreshed-refresh-token',
                'created_at': 1000,
                'expires_in': 7200
            })
        ) as post_mock, patch.object(auth.session, 'get') as get_mock, patch(
            'trakt_duplicates_removal.auth.webbrowser.open'
        ) as browser_mock:
            auth.login_to_trakt('cid', 'secret', 'alice')

        get_mock.assert_not_called()
        browser_mock.assert_not_called()
        post_mock.assert_called_once()
        self.assertEqual(post_mock.call_args.kwargs['data']['grant_type'], 'refresh_token')
        save_mock.assert_called_once_with({
            'client_id': 'cid',
            'client_secret': 'secret',
            'username': 'alice',
            'access_token': 'refreshed-token',
            'refresh_token': 'refreshed-refresh-token',
            'expires_at': 8200
        })
        self.assertEqual(auth.session.headers['Authorization'], 'Bearer refreshed-token')

    def test_login_to_trakt_falls_back_to_oauth_when_refresh_token_is_invalid(self):
        save_patcher = patch('trakt_duplicates_removal.auth.save_config')
        save_mock = save_patcher.start()
        self.addCleanup(save_patcher.stop)

        with patch('trakt_duplicates_removal.auth.load_config', return_value={
            'client_id': 'cid',
            'client_secret': 'secret',
            'username': 'alice',
            'access_token': 'expired-token',
            'refresh_token': 'expired-refresh-token',
            'expires_at': 1
        }), patch('trakt_duplicates_removal.auth.prompt_non_empty', return_value='123456'), patch(
            'trakt_duplicates_removal.auth.webbrowser.open'
        ) as browser_mock, patch.object(
            auth.session,
            'post',
            side_effect=[
                FakeResponse(status_code=401, payload={'error': 'invalid_grant'}, text='invalid_grant'),
                FakeResponse(status_code=200, payload={
                    'access_token': 'fresh-token',
                    'refresh_token': 'fresh-refresh-token',
                    'created_at': 2000,
                    'expires_in': 3600
                })
            ]
        ) as post_mock, patch.object(auth.session, 'get') as get_mock:
            auth.login_to_trakt('cid', 'secret', 'alice')

        get_mock.assert_not_called()
        browser_mock.assert_called_once()
        self.assertEqual(post_mock.call_count, 2)
        self.assertEqual(post_mock.call_args_list[0].kwargs['data']['grant_type'], 'refresh_token')
        self.assertEqual(post_mock.call_args_list[1].kwargs['data']['grant_type'], 'authorization_code')
        save_mock.assert_called_once_with({
            'client_id': 'cid',
            'client_secret': 'secret',
            'username': 'alice',
            'access_token': 'fresh-token',
            'refresh_token': 'fresh-refresh-token',
            'expires_at': 5600
        })
        self.assertEqual(auth.session.headers['Authorization'], 'Bearer fresh-token')

    def test_login_to_trakt_raises_on_error_response(self):
        with patch('trakt_duplicates_removal.auth.load_config', return_value={}), patch(
            'trakt_duplicates_removal.auth.prompt_non_empty',
            return_value='123456'
        ), patch('trakt_duplicates_removal.auth.webbrowser.open'), patch.object(
            auth.session,
            'post',
            return_value=FakeResponse(status_code=401, payload={'error_description': 'bad pin'}, text='bad pin')
        ):
            with self.assertRaises(RuntimeError):
                auth.login_to_trakt('cid', 'secret', 'alice')


if __name__ == '__main__':
    unittest.main()

