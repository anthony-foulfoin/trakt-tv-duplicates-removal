from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / 'auth_config.json'
BACKUP_DIR = PROJECT_ROOT / 'backup'
TRAKT_API = 'https://api.trakt.tv'
USER_AGENT = 'Trakt duplicates removal'
REQUEST_TIMEOUT = 30

session = requests.Session()

