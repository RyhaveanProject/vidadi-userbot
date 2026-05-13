import logging

from pyrogram import Client
from pytgcalls import PyTgCalls

from config import API_ID, API_HASH, SESSION_STRING, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
# Silence noisy libs
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.WARNING)

log = logging.getLogger("ryhavean")

app = Client(
    name="ryhavean_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True,
    workers=8,
    max_concurrent_transmissions=4,
)

call_py = PyTgCalls(app)
