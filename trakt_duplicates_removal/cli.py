from typing import TypedDict

from .prompts import prompt_choice, prompt_yes_no


class RunConfiguration(TypedDict):
	types: list[str]
	correct_movie_history: bool
	duplicate_removal_types: list[str]
	keep_per_day: bool
	keep_strategy: str


def get_run_configuration() -> RunConfiguration:
	"""Collect the actions to perform during the current run."""
	selected_types = []
	duplicate_removal_types = []
	correct_movie_history = False

	if prompt_yes_no('Include movies in this run?', default='yes'):
		selected_types.append('movies')
		if prompt_yes_no(
			'For movies, rebuild history so each title is kept once and watched on its release date?',
			default='no'
		):
			correct_movie_history = True
		else:
			duplicate_removal_types.append('movies')

	if prompt_yes_no('Include episodes in this run?', default='yes'):
		selected_types.append('episodes')
		duplicate_removal_types.append('episodes')

	if not selected_types:
		print('Nothing selected. Exiting without authenticating.')
		raise SystemExit(0)

	keep_per_day = False
	keep_strategy = 'oldest'

	if duplicate_removal_types:
		print()
		print('Duplicate-removal settings apply to:', ', '.join(duplicate_removal_types))
		keep_per_day = prompt_yes_no(
			'Only treat plays watched on the same local calendar day as duplicates?',
			default='no'
		)
		keep_strategy = prompt_choice(
			'When duplicates are found, which play should be kept?',
			{'oldest', 'newest'},
			default='oldest'
		)

	return {
		'types': selected_types,
		'correct_movie_history': correct_movie_history,
		'duplicate_removal_types': duplicate_removal_types,
		'keep_per_day': keep_per_day,
		'keep_strategy': keep_strategy
	}

