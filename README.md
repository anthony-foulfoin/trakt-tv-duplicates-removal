Trakt.tv duplicate / additionnal plays bulk removal  
===========  
This script allows you to remove all the duplicate or additionnal plays for your trakt.tv movies or episodes, and just keep one play per movie / episode (the oldest one).

For instance if you have 3 plays for the movie **Guardians of the Galaxy** at these dates:

- 2014-08-01T20:00:00.000Z
- 2017-05-05T22:00:00.000Z
- 2018-02-05T21:00:00.000Z

The script will keep the oldest play (2014-08-01T20:00:00.000Z) and remove all the others.
If there are no duplicates the script do nothing.
The script backup your data in local json files (movies.json and episodes.json) before doing anything.

## Getting Started

You will need python3 and pip installed and in your path

1. Start by doing a `pip3 install -r requirements.txt` at the root of the project
2. Launch the script:

```shell
python3 trakt-duplicates-removal.py
```

Follow the script instructions

### Contributors

Thanks to 
- [@lsoares](https://www.github.com/lsoares)

For his contributions

### Credits

Based on https://gist.github.com/blaulan/50d462696bce5da9225b8d596a8c6fb4
