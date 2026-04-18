from .auth import get_user_credentials, login_to_trakt
from .cli import get_run_configuration
from .history import correct_movie_history, get_history, get_trakt_user_timezone, remove_duplicates, save_history_backup


def main():
    """Run the interactive Trakt history cleanup flow."""
    client_id, client_secret, username = get_user_credentials()
    run_configuration = get_run_configuration()

    # Keeping all prompts and network side effects inside main() makes the modules safe to import for tests.
    login_to_trakt(client_id, client_secret, username)

    user_timezone = 'UTC'
    if run_configuration['duplicate_removal_types']:
        user_timezone = get_trakt_user_timezone()
        print(f'Using timezone for same-day duplicate detection: {user_timezone}')

    for history_type in run_configuration['types']:
        history = get_history(history_type, username)
        save_history_backup(history_type, history)

        if history_type == 'movies' and run_configuration['correct_movie_history']:
            correct_movie_history(history)
        else:
            remove_duplicates(
                history,
                history_type,
                run_configuration['keep_per_day'],
                run_configuration['keep_strategy'],
                user_timezone
            )
        print()

    return 0


def run_cli():
    """Run the CLI entry point with user-friendly error handling."""
    try:
        return main()
    except KeyboardInterrupt:
        print('\nOperation cancelled by user.')
        return 1
    except RuntimeError as exc:
        print(f'\nError: {exc}')
        return 1

