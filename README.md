Trakt.tv duplicate / additionnal plays bulk removal  
===========  
This script allows you to remove all the duplicate or additionnal plays for your trakt.tv movies or episodes, and just keep one play per movie / episode (either the oldest or newest one, based on your preference).

For instance if you have 3 plays for the movie **Guardians of the Galaxy** at these dates:

- 2014-08-01T20:00:00.000Z
- 2017-05-05T22:00:00.000Z
- 2018-02-05T21:00:00.000Z

If you choose to keep the oldest play, the script will keep the 2014-08-01T20:00:00.000Z entry and remove the others.
If you choose to keep the newest play, the script will keep the 2018-02-05T21:00:00.000Z entry and remove the others.
If there are no duplicates the script does nothing.

The script provides a preview of what will be deleted and asks for confirmation before proceeding, so you can review the changes before they're applied. The script also backs up your data in local json files (movies.json and episodes.json) before doing anything.

## Getting Started

You will need python3 and pip installed and in your path

1. Start by doing a `pip3 install -r requirements.txt` at the root of the project
2. Launch the script:

```shell
python3 trakt-duplicates-removal.py
```

### Contributors

Thanks to 
- [@lsoares](https://www.github.com/lsoares)
- [@luigidotmoe](https://www.github.com/luigidotmoe)

For his contributions

### Credits

Based on https://gist.github.com/blaulan/50d462696bce5da9225b8d596a8c6fb4
