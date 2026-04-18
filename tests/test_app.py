import unittest
from unittest.mock import patch

from trakt_duplicates_removal import app
from tests.helpers import QuietTestCase


class AppTests(QuietTestCase):
    def test_main_orchestrates_selected_history_types(self):
        run_configuration = {
            'types': ['movies', 'episodes'],
            'correct_movie_history': True,
            'duplicate_removal_types': ['episodes'],
            'keep_per_day': True,
            'keep_strategy': 'newest'
        }

        with patch('trakt_duplicates_removal.app.get_user_credentials', return_value=('cid', 'secret', 'alice')), patch(
            'trakt_duplicates_removal.app.get_run_configuration',
            return_value=run_configuration
        ), patch('trakt_duplicates_removal.app.login_to_trakt') as login_mock, patch(
            'trakt_duplicates_removal.app.get_trakt_user_timezone',
            return_value='UTC'
        ), patch('trakt_duplicates_removal.app.get_history', side_effect=[[{'id': 1}], [{'id': 2}]]) as get_history_mock, patch(
            'trakt_duplicates_removal.app.save_history_backup'
        ) as backup_mock, patch('trakt_duplicates_removal.app.correct_movie_history') as correct_mock, patch(
            'trakt_duplicates_removal.app.remove_duplicates'
        ) as remove_mock:
            result = app.main()

        self.assertEqual(result, 0)
        login_mock.assert_called_once_with('cid', 'secret', 'alice')
        self.assertEqual(get_history_mock.call_args_list[0].args, ('movies', 'alice'))
        self.assertEqual(get_history_mock.call_args_list[1].args, ('episodes', 'alice'))
        self.assertEqual(backup_mock.call_count, 2)
        correct_mock.assert_called_once_with([{'id': 1}])
        remove_mock.assert_called_once_with([{'id': 2}], 'episodes', True, 'newest', 'UTC')

    def test_run_cli_returns_one_on_runtime_error(self):
        with patch('trakt_duplicates_removal.app.main', side_effect=RuntimeError('boom')):
            result = app.run_cli()

        self.assertEqual(result, 1)


if __name__ == '__main__':
    unittest.main()

