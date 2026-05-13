import os

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# Optional environment overrides
SONG_BOT = os.environ.get("SONG_BOT", "SongFastBot")
ARTIST_TAG = os.environ.get("ARTIST_TAG", "@Ryhavean")
COMMAND_PREFIXES = list(os.environ.get("COMMAND_PREFIXES", "."))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
