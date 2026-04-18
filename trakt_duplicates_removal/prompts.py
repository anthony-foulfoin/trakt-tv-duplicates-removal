def prompt_non_empty(prompt_text):
    """Keep asking until the user enters a non-empty value."""
    while True:
        value = input(f"{prompt_text}: ").strip()
        if value:
            return value
        print('Please enter a value.')


def prompt_yes_no(prompt_text, default=None):
    """Prompt for a yes/no answer and keep asking until the answer is valid."""
    yes_values = {'y', 'yes'}
    no_values = {'n', 'no'}
    suffix = ' [yes/no]'
    if default in {'yes', 'no'}:
        suffix = f" [yes/no, default: {default}]"

    while True:
        answer = input(f"{prompt_text}{suffix}: ").strip().lower()
        if not answer and default in {'yes', 'no'}:
            answer = default

        if answer in yes_values:
            return True
        if answer in no_values:
            return False

        print("Please answer 'yes' or 'no'.")


def prompt_choice(prompt_text, choices, default=None):
    """Prompt for a choice among a fixed set of values."""
    normalized_choices = {choice.lower() for choice in choices}
    display_choices = '/'.join(sorted(normalized_choices))
    suffix = f" [{display_choices}]"
    if default:
        suffix = f" [{display_choices}, default: {default}]"

    while True:
        answer = input(f"{prompt_text}{suffix}: ").strip().lower()
        if not answer and default:
            return default
        if answer in normalized_choices:
            return answer

        print(f'Please choose one of: {display_choices}.')

