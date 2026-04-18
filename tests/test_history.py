import tempfile
import unittest
from datetime import timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from trakt_duplicates_removal import history
from trakt_duplicates_removal.history import HistoryError
from tests.helpers import FakeResponse, QuietTestCase


class HistoryTests(QuietTestCase):
    def tearDown(self):
        history.get_timezone_info.cache_clear()
        super().tearDown()

    def test_watched_date_in_tz_handles_z_suffix_with_mocked_timezone(self):
        fake_timezone = timezone(timedelta(hours=2))
        with patch('trakt_duplicates_removal.history.get_timezone_info', return_value=fake_timezone):
            result = history.watched_date_in_tz('2024-01-01T23:30:00Z', 'Europe/Paris')

        self.assertEqual(result, '2024-01-02')

    def test_format_history_entry_title_formats_episode_entries(self):
        item = {
            'show': {'title': 'My Show'},
            'episode': {'season': 2, 'number': 3, 'title': 'Episode Title'}
        }

        title = history.format_history_entry_title(item, 'episode')

        self.assertEqual(title, 'My Show - S02E03 - Episode Title')

    def test_save_history_backup_writes_json_in_backup_directory(self):
        sample_history = [{'id': 1, 'movie': {'title': 'Movie'}}]
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / 'backup'
            with patch('trakt_duplicates_removal.history.BACKUP_DIR', backup_dir), patch(
                'trakt_duplicates_removal.history.get_backup_date_string',
                return_value='2026-04-18'
            ):
                history.save_history_backup('movies', sample_history)

                output_path = backup_dir / 'movies-2026-04-18.json'
                self.assertTrue(backup_dir.exists())
                self.assertTrue(output_path.exists())
                self.assertIn('Movie', output_path.read_text(encoding='utf-8'))

    def test_build_movie_history_entry_uses_release_date_when_available(self):
        movie = {'title': 'Movie A', 'year': 2022, 'ids': {'trakt': 10}}
        with patch.object(history.session, 'get', return_value=FakeResponse(payload={'released': '2022-04-05'})):
            entry = history.build_movie_history_entry(movie)

        self.assertEqual(entry, {'watched_at': '2022-04-05', 'ids': {'trakt': 10}})

    def test_build_movie_history_entry_falls_back_to_first_day_of_year(self):
        movie = {'title': 'Movie B', 'year': 2020, 'ids': {'trakt': 20}}
        with patch.object(history.session, 'get', return_value=FakeResponse(payload={'released': None})):
            entry = history.build_movie_history_entry(movie)

        self.assertEqual(entry, {'watched_at': '2020-01-01', 'ids': {'trakt': 20}})

    def test_get_history_combines_paginated_results(self):
        page_one = FakeResponse(payload=[{'id': 1}], text='ok', headers={'X-Pagination-Page-Count': '2'})
        page_two = FakeResponse(payload=[{'id': 2}], text='ok', headers={'X-Pagination-Page-Count': '2'})

        with patch.object(history.session, 'get', side_effect=[page_one, page_two]):
            result = history.get_history('movies', 'alice')

        self.assertEqual(result, [{'id': 1}, {'id': 2}])

    def test_get_history_raises_for_non_list_payload(self):
        response = FakeResponse(payload={'unexpected': True}, text='bad payload', headers={'X-Pagination-Page-Count': '1'})

        with patch.object(history.session, 'get', return_value=response):
            with self.assertRaises(HistoryError):
                history.get_history('movies', 'alice')

    def test_remove_duplicates_removes_older_duplicate_when_keeping_newest(self):
        entries = [
            {'id': 30, 'movie': {'ids': {'trakt': 100}, 'title': 'Movie A'}, 'watched_at': '2024-01-03T10:00:00Z'},
            {'id': 20, 'movie': {'ids': {'trakt': 100}, 'title': 'Movie A'}, 'watched_at': '2024-01-02T10:00:00Z'},
            {'id': 10, 'movie': {'ids': {'trakt': 200}, 'title': 'Movie B'}, 'watched_at': '2024-01-01T10:00:00Z'}
        ]
        post_response = FakeResponse(status_code=200, payload={'deleted': 1})

        with patch('trakt_duplicates_removal.history.prompt_yes_no', return_value=True), patch.object(
            history.session,
            'post',
            return_value=post_response
        ) as post_mock:
            history.remove_duplicates(entries, 'movies', keep_per_day=False, keep_strategy='newest', user_timezone='UTC')

        post_mock.assert_called_once()
        self.assertEqual(post_mock.call_args.kwargs['json'], {'ids': [20]})

    def test_remove_duplicates_uses_same_day_mode(self):
        entries = [
            {'id': 3, 'episode': {'ids': {'trakt': 42}, 'season': 1, 'number': 2, 'title': 'Ep 2'}, 'show': {'title': 'Show'}, 'watched_at': 'a'},
            {'id': 2, 'episode': {'ids': {'trakt': 42}, 'season': 1, 'number': 2, 'title': 'Ep 2'}, 'show': {'title': 'Show'}, 'watched_at': 'b'},
            {'id': 1, 'episode': {'ids': {'trakt': 42}, 'season': 1, 'number': 2, 'title': 'Ep 2'}, 'show': {'title': 'Show'}, 'watched_at': 'c'}
        ]
        post_response = FakeResponse(status_code=200, payload={'deleted': 1})

        with patch('trakt_duplicates_removal.history.watched_date_in_tz', side_effect=['2024-01-02', '2024-01-02', '2024-01-01']), patch(
            'trakt_duplicates_removal.history.prompt_yes_no',
            return_value=True
        ), patch.object(history.session, 'post', return_value=post_response) as post_mock:
            history.remove_duplicates(entries, 'episodes', keep_per_day=True, keep_strategy='newest', user_timezone='UTC')

        self.assertEqual(post_mock.call_args.kwargs['json'], {'ids': [2]})

    def test_remove_duplicates_does_not_call_api_when_user_cancels(self):
        entries = [
            {'id': 2, 'movie': {'ids': {'trakt': 100}, 'title': 'Movie A'}, 'watched_at': '2024-01-02T10:00:00Z'},
            {'id': 1, 'movie': {'ids': {'trakt': 100}, 'title': 'Movie A'}, 'watched_at': '2024-01-01T10:00:00Z'}
        ]

        with patch('trakt_duplicates_removal.history.prompt_yes_no', return_value=False), patch.object(
            history.session,
            'post'
        ) as post_mock:
            history.remove_duplicates(entries, 'movies', keep_per_day=False, keep_strategy='newest', user_timezone='UTC')

        post_mock.assert_not_called()

    def test_correct_movie_history_posts_remove_then_add(self):
        entries = [
            {'id': 10, 'movie': {'ids': {'trakt': 100}, 'title': 'Movie A', 'year': 2020}},
            {'id': 11, 'movie': {'ids': {'trakt': 100}, 'title': 'Movie A', 'year': 2020}},
            {'id': 12, 'movie': {'ids': {'trakt': 200}, 'title': 'Movie B', 'year': 2021}}
        ]
        with patch('trakt_duplicates_removal.history.build_movie_history_entry', side_effect=[
            {'watched_at': '2020-01-01', 'ids': {'trakt': 100}},
            {'watched_at': '2021-01-01', 'ids': {'trakt': 200}}
        ]), patch('trakt_duplicates_removal.history.prompt_yes_no', return_value=True), patch.object(
            history.session,
            'post',
            side_effect=[FakeResponse(status_code=200), FakeResponse(status_code=201)]
        ) as post_mock:
            history.correct_movie_history(entries)

        self.assertEqual(post_mock.call_count, 2)
        self.assertEqual(post_mock.call_args_list[0].kwargs['json'], {'ids': [10, 11, 12]})
        self.assertEqual(post_mock.call_args_list[1].kwargs['json'], {
            'movies': [
                {'watched_at': '2020-01-01', 'ids': {'trakt': 100}},
                {'watched_at': '2021-01-01', 'ids': {'trakt': 200}}
            ]
        })

    def test_correct_movie_history_raises_when_remove_fails(self):
        entries = [{'id': 10, 'movie': {'ids': {'trakt': 100}, 'title': 'Movie A', 'year': 2020}}]
        with patch('trakt_duplicates_removal.history.build_movie_history_entry', return_value={
            'watched_at': '2020-01-01',
            'ids': {'trakt': 100}
        }), patch('trakt_duplicates_removal.history.prompt_yes_no', return_value=True), patch.object(
            history.session,
            'post',
            return_value=FakeResponse(status_code=500, text='boom')
        ):
            with self.assertRaises(HistoryError):
                history.correct_movie_history(entries)


if __name__ == '__main__':
    unittest.main()

