import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import QuietTestCase


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WRAPPER_PATH = PROJECT_ROOT / 'trakt-duplicates-removal.py'


class WrapperTests(QuietTestCase):
    def test_wrapper_script_calls_run_cli_and_exits_with_its_code(self):
        with patch('trakt_duplicates_removal.app.run_cli', return_value=7) as run_cli_mock:
            with self.assertRaises(SystemExit) as exc:
                runpy.run_path(str(WRAPPER_PATH), run_name='__main__')

        self.assertEqual(exc.exception.code, 7)
        run_cli_mock.assert_called_once_with()

    def test_package_entry_point_calls_run_cli_and_exits_with_its_code(self):
        with patch('trakt_duplicates_removal.app.run_cli', return_value=3) as run_cli_mock:
            with self.assertRaises(SystemExit) as exc:
                runpy.run_module('trakt_duplicates_removal', run_name='__main__')

        self.assertEqual(exc.exception.code, 3)
        run_cli_mock.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()

