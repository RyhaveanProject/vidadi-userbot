import logging

from pyrogram import Client
from pytgcalls import PyTgCalls

from config import API_ID, API_HASH, SESSION_STRING, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
# Keep pyrogram/pytgcalls at INFO so Railway logs show what's happening
# (handler triggers, call lifecycle, etc.). Bump to WARNING if too noisy.
logging.getLogger("pyrogram").setLevel(logging.INFO)
logging.getLogger("pytgcalls").setLevel(logging.INFO)

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
