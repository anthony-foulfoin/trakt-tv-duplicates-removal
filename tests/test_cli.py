import unittest
from unittest.mock import patch

from trakt_duplicates_removal.cli import get_run_configuration
from tests.helpers import QuietTestCase


class RunConfigurationTests(QuietTestCase):
    def test_configuration_for_movie_correction_and_episode_deduplication(self):
        with patch('trakt_duplicates_removal.cli.prompt_yes_no', side_effect=[True, True, True, True]), patch(
            'trakt_duplicates_removal.cli.prompt_choice',
            return_value='newest'
        ):
            config = get_run_configuration()

        self.assertEqual(config['types'], ['movies', 'episodes'])
        self.assertTrue(config['correct_movie_history'])
        self.assertEqual(config['duplicate_removal_types'], ['episodes'])
        self.assertTrue(config['keep_per_day'])
        self.assertEqual(config['keep_strategy'], 'newest')

    def test_configuration_for_movies_only_uses_duplicate_settings(self):
        with patch('trakt_duplicates_removal.cli.prompt_yes_no', side_effect=[True, False, False, False]), patch(
            'trakt_duplicates_removal.cli.prompt_choice',
            return_value='oldest'
        ):
            config = get_run_configuration()

        self.assertEqual(config['types'], ['movies'])
        self.assertFalse(config['correct_movie_history'])
        self.assertEqual(config['duplicate_removal_types'], ['movies'])
        self.assertFalse(config['keep_per_day'])
        self.assertEqual(config['keep_strategy'], 'oldest')

    def test_configuration_exits_when_nothing_is_selected(self):
        with patch('trakt_duplicates_removal.cli.prompt_yes_no', side_effect=[False, False]):
            with self.assertRaises(SystemExit) as exc:
                get_run_configuration()

        self.assertEqual(exc.exception.code, 0)


if __name__ == '__main__':
    unittest.main()

