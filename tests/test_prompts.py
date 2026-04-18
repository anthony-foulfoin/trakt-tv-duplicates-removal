import unittest
from unittest.mock import patch

from trakt_duplicates_removal import prompts


class PromptTests(unittest.TestCase):
    def test_prompt_non_empty_retries_until_value_is_entered(self):
        with patch('builtins.input', side_effect=['', '  ', ' value ']), patch('builtins.print') as print_mock:
            result = prompts.prompt_non_empty('Enter value')

        self.assertEqual(result, 'value')
        self.assertEqual(print_mock.call_count, 2)

    def test_prompt_yes_no_accepts_default_when_input_is_empty(self):
        with patch('builtins.input', side_effect=['']):
            result = prompts.prompt_yes_no('Continue?', default='yes')

        self.assertTrue(result)

    def test_prompt_yes_no_retries_on_invalid_answer(self):
        with patch('builtins.input', side_effect=['maybe', 'n']), patch('builtins.print') as print_mock:
            result = prompts.prompt_yes_no('Continue?')

        self.assertFalse(result)
        print_mock.assert_called_once_with("Please answer 'yes' or 'no'.")

    def test_prompt_choice_retries_until_choice_matches(self):
        with patch('builtins.input', side_effect=['invalid', 'Newest']), patch('builtins.print') as print_mock:
            result = prompts.prompt_choice('Pick one', {'oldest', 'newest'})

        self.assertEqual(result, 'newest')
        print_mock.assert_called_once()

    def test_prompt_choice_returns_default_on_empty_answer(self):
        with patch('builtins.input', side_effect=['']):
            result = prompts.prompt_choice('Pick one', {'oldest', 'newest'}, default='oldest')

        self.assertEqual(result, 'oldest')


if __name__ == '__main__':
    unittest.main()

