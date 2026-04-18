from unittest import TestCase
from unittest.mock import patch


class FakeResponse:
    """Minimal HTTP-like response object for offline unit tests."""

    def __init__(self, status_code=200, payload=None, text='', headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class QuietTestCase(TestCase):
    """Mute print() by default so unittest output stays readable."""

    def setUp(self):
        super().setUp()
        self.print_patcher = patch('builtins.print')
        self.print_mock = self.print_patcher.start()
        self.addCleanup(self.print_patcher.stop)

