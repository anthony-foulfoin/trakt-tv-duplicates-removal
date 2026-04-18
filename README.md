Trakt.tv duplicate / additional plays bulk removal
===========

[![CI](https://github.com/anthony-foulfoin/trakt-tv-duplicates-removal/actions/workflows/ci.yml/badge.svg)](https://github.com/anthony-foulfoin/trakt-tv-duplicates-removal/actions/workflows/ci.yml)

This Python script helps you clean up your Trakt.tv history by either:

- removing duplicate movie and/or episode plays, or
- rebuilding movie history so each movie is kept once with its watched date set to the movie release date.

It creates local JSON backups before making changes and always shows a preview before deleting or rewriting history.

## Features

### Duplicate removal

- Supports `movies`, `episodes`, or both in the same run
- Lets you keep either the **oldest** or **newest** play
- Can limit duplicate detection to entries watched on the **same local day**
- Shows a detailed preview of entries that will be deleted
- Requires explicit confirmation before deletion

### Movie-only history correction

This feature applies to **movies only**. Episodes are **not** rebuilt or reassigned to release dates, they are just deduplicated according to the selected duplicate-removal settings.

For movies, the script can:

- remove all existing movie history entries
- keep one entry per unique movie
- re-add each movie using its Trakt release date as `watched_at`
- fall back to `YYYY-01-01` when Trakt does not return an exact release date but a year is available

### Saved authentication

The script can persist authentication data in `auth_config.json`:

If saved credentials exist, the script offers these options on startup:

1. use saved credentials
2. enter new credentials
3. delete saved configuration and exit

If the credentials are expired, the script falls back to the normal OAuth PIN flow.

## Requirements

- Python 3.9 or newer
  - the script uses `zoneinfo`, which is included in the standard library starting with Python 3.9
  - on Windows and some minimal Python environments, `tzdata` is also installed so IANA timezone names resolve correctly
- `pip`

## Installation

```shell
pip install -r requirements.txt
```

Current dependency:

- `requests==2.32.5`
- `tzdata>=2024.1`

## Run

```shell
python trakt-duplicates-removal.py
```

You can also run the package entry point directly:

```shell
python -m trakt_duplicates_removal
```

## Tests

The project now includes an offline unit test suite built with the Python standard library's `unittest` module.

It covers:

- prompt validation helpers
- run configuration flow
- history backup and duplicate-detection logic
- movie history rewrite flow with mocked API calls
- authentication flows with mocked HTTP responses
- top-level app orchestration
- the wrapper script and package entry points

Shared test utilities live in `tests/helpers.py` so mocked HTTP responses and quiet test output can be reused across the suite.

From the project root, run the full suite with the same command on Linux, macOS, and Windows:

```shell
python -m tests -v
```

If you prefer a file-based launcher, this wrapper is also cross-platform:

```shell
python run_tests.py -v
```

## Project structure

The code is split into a small internal package to keep responsibilities separate:

- `trakt-duplicates-removal.py`: thin compatibility wrapper for the existing CLI command
- `trakt_duplicates_removal/app.py`: top-level orchestration and CLI error handling
- `trakt_duplicates_removal/auth.py`: saved config handling and Trakt OAuth
- `trakt_duplicates_removal/cli.py`: run configuration prompts and validation
- `trakt_duplicates_removal/prompts.py`: reusable prompt helpers
- `trakt_duplicates_removal/history.py`: history download, backup, duplicate removal, and movie rewrite logic
- `trakt_duplicates_removal/settings.py`: shared constants and HTTP session

## Trakt API setup

If you do not already have a Trakt API application, create one at:

- https://trakt.tv/oauth/applications/new

Recommended values:

- **Name**: `trakt-duplicates-removal`
- **Redirect URI**: `urn:ietf:wg:oauth:2.0:oob`

Other fields can be left empty for this script.

## What the script asks you

### 1. Credentials

On a fresh setup, the script asks for:

- client ID
- client secret
- Trakt username
- whether to save those credentials for future runs

### 2. Content selection

You are then prompted for:

```text
- Include movies in this run? [yes/no]
- For movies, rebuild history so each title is kept once and watched on its release date? [yes/no]
- Include episodes in this run? [yes/no]
```

If at least one selected type uses duplicate removal, the script also asks:

```text
- Only treat plays watched on the same local calendar day as duplicates? [yes/no]
- When duplicates are found, which play should be kept? [oldest/newest]
```

The script validates those answers and keeps asking until a valid value is entered.

If you select **movie history correction** and **episodes** in the same run, the duplicate-removal settings apply to **episodes only**.

If you select neither movies nor episodes, the script exits before authenticating.

### 3. OAuth PIN flow

If there is no valid saved token:

- your browser is opened to the Trakt authorization page
- you authorize the app
- you paste the returned PIN into the terminal

## How duplicate detection works

### Keep oldest vs keep newest

For standard duplicate removal:

- `oldest` keeps the earliest play and removes later duplicates
- `newest` keeps the latest play and removes older duplicates

### Same-day duplicate mode

When you answer `yes` to:

```text
- Only treat plays watched on the same local calendar day as duplicates? [yes/no]
```

the script removes duplicates **only when the same movie or episode appears more than once on the same local calendar day**.

The local day is calculated using:

- your Trakt account timezone from `/users/settings`, or
- `UTC` if the timezone cannot be retrieved

If local IANA timezone data is missing on the machine running the script, the script falls back to `UTC` and prints a warning.

When you answer `no`, the script keeps only one play per movie or episode across the full history.

## Movie history correction details

When movie history correction is enabled, the script processes **movies only**:

1. downloads your selected movie history
2. saves it to `backup/movies.json`
3. builds a unique movie list by Trakt movie ID
4. fetches each movie's release date from the Trakt API
5. shows a preview of the replacement entries
6. removes all movie history entries
7. re-adds one entry per unique movie

If no exact release date is available but the movie year exists, the script uses `January 1st` of that year.

## Output files

For each selected content type, the script writes a local backup in the `backup` directory before making changes:

- `backup/movies.json`
- `backup/episodes.json`

It also stores saved credentials and tokens in:

- `auth_config.json`

## Important implementation notes

- The script is interactive and modifies live Trakt history only after confirmation.
- Backups are created only for the types you selected in the current run.
- The script does not provide a dry-run mode beyond the on-screen preview.
- On startup, choosing option `3` for saved credentials deletes `auth_config.json` and exits; you must restart the script afterward.
- The script ignores a saved access token when it does not match the currently selected `client_id` and `username`.

## Usage examples

### Remove all movie duplicates and keep the oldest play

```text
- Include movies in this run? [yes/no, default: yes]: yes
- For movies, rebuild history so each title is kept once and watched on its release date? [yes/no, default: no]: no
- Include episodes in this run? [yes/no, default: yes]: no
- Only treat plays watched on the same local calendar day as duplicates? [yes/no, default: no]: no
- When duplicates are found, which play should be kept? [newest/oldest, default: oldest]: oldest
```

### Remove only same-day episode duplicates and keep the newest play

```text
- Include movies in this run? [yes/no, default: yes]: no
- Include episodes in this run? [yes/no, default: yes]: yes
- Only treat plays watched on the same local calendar day as duplicates? [yes/no, default: no]: yes
- When duplicates are found, which play should be kept? [newest/oldest, default: oldest]: newest
```

### Rebuild movie history using release dates

```text
- Include movies in this run? [yes/no, default: yes]: yes
- For movies, rebuild history so each title is kept once and watched on its release date? [yes/no, default: no]: yes
- Include episodes in this run? [yes/no, default: yes]: no
```

## Safety recommendations

- Review the preview carefully before confirming any change.
- Keep the generated JSON backup files until you have verified the result in Trakt.
- Consider exporting your history from Trakt before running bulk changes.
- If you want different duplicate-removal rules for episodes, do not combine them with movie history correction in the same run.

## Contributors

Thanks to:

- [@lsoares](https://www.github.com/lsoares)
- [@luigidotmoe](https://www.github.com/luigidotmoe)
- [sidaths](https://www.github.com/sidaths)

## Credits

Based on:

- https://gist.github.com/blaulan/50d462696bce5da9225b8d596a8c6fb4
