Trakt.tv duplicate / additional plays bulk removal  
===========  
This script allows you to remove all duplicate or additional plays for your trakt.tv movies or episodes, and just keep one play per movie/episode (either the oldest or newest one, based on your preference). It also includes advanced features for movie history correction and flexible duplicate removal options.

## Features

### Duplicate Removal
Remove duplicate plays from your Trakt.tv history with flexible options:

- **Keep oldest or newest**: Choose whether to keep the first or last play of each movie/episode
- **Daily filtering**: Option to only remove duplicates that occur on the same day
- **Preview before deletion**: See exactly what will be removed before confirming

### Movie History Correction
A special feature that corrects movie history by:
- Removing all existing movie plays
- Re-adding each unique movie with the watched date set to the movie's release date
- Useful for cleaning up imported data or correcting inaccurate watch dates

### Data Safety
- **Backup creation**: Automatically saves your complete history to local JSON files before making changes
- **Confirmation prompts**: Always asks for confirmation before making any changes
- **Detailed previews**: Shows exactly what entries will be modified or deleted

## Example

For instance, if you have 3 plays for the movie **Guardians of the Galaxy** at these dates:

- 2014-08-01T20:00:00.000Z
- 2017-05-05T22:00:00.000Z  
- 2018-02-05T21:00:00.000Z

**Standard duplicate removal:**
- If you choose to keep the oldest play, the script will keep the 2014-08-01T20:00:00.000Z entry and remove the others
- If you choose to keep the newest play, the script will keep the 2018-02-05T21:00:00.000Z entry and remove the others

**Movie history correction:**
- If the movie was released on 2014-08-01, all three entries will be removed and replaced with a single entry dated 2014-08-01

## Getting Started

### Prerequisites
You will need Python 3 and pip installed and in your path.

### Installation
1. Install dependencies:
```shell
pip install -r requirements.txt
```

2. Launch the script:
```shell
python trakt-duplicates-removal.py
```

### Setup Process
When you run the script, you'll be guided through the following steps:

1. **Trakt.tv API Setup**:
   - Register a new API app at: https://trakt.tv/oauth/applications/new
   - Use these settings:
     - Name: `trakt-duplicates-removal`
     - Redirect URI: `urn:ietf:wg:oauth:2.0:oob`
   - Enter your Client ID and Client Secret when prompted

2. **Authentication**:
   - The script will open your browser for OAuth authorization
   - Copy and paste the PIN code when prompted

3. **Configuration Options**:
   - Choose whether to include movies and/or episodes
   - For movies: Option to correct history using release dates
   - For standard duplicate removal:
     - Choose whether to only remove duplicates on the same day
     - Choose whether to keep oldest or newest plays

4. **Review and Confirm**:
   - The script will show a detailed preview of what will be changed
   - Confirm before any modifications are made to your Trakt.tv account

### Output Files
The script creates backup files in the current directory:
- `movies.json` - Complete movie history backup
- `episodes.json` - Complete episode history backup

## Usage Examples

### Remove All Movie Duplicates (Keep Oldest)
```
- Include movies? (yes/no): yes
- Correct movie history by setting watched date to release date? (yes/no): no
- Include episodes? (yes/no): no
- Remove repeated only on distinct days? (yes/no): no
- Keep oldest or newest plays? (oldest/newest): oldest
```

### Correct Movie History to Release Dates
```
- Include movies? (yes/no): yes
- Correct movie history by setting watched date to release date? (yes/no): yes
- Include episodes? (yes/no): no
```

### Remove Episode Duplicates Only on Same Day (Keep Newest)
```
- Include movies? (yes/no): no
- Include episodes? (yes/no): yes
- Remove repeated only on distinct days? (yes/no): yes
- Keep oldest or newest plays? (oldest/newest): newest
```

## Safety Notes

- **Always review the preview** before confirming any changes
- **Backup files** are automatically created but consider exporting your data from Trakt.tv before running
- **Test with a small subset** if you're unsure about the results
- The script uses the official Trakt.tv API and respects rate limits

### Contributors

Thanks to:
- [@lsoares](https://www.github.com/lsoares)
- [@luigidotmoe](https://www.github.com/luigidotmoe)

For their contributions

### Credits

Based on https://gist.github.com/blaulan/50d462696bce5da9225b8d596a8c6fb4
