import logging

from pyrogram import Client
from pytgcalls import PyTgCalls

from config import API_ID, API_HASH, SESSION_STRING, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
# Pyrogram-ı WARNING-də saxla (flood-wait, disconnect logları görünsün, normal trafik səs salmasın)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.WARNING)

log = logging.getLogger("ryhavean")

# IMPORTANT:
# - workers=1 və max_concurrent_transmissions=1: userbotlarda yüksək paralellik
#   Telegram tərəfindən "spam/automation" kimi qəbul edilir və session
#   deauthorize olunmasına gətirib çıxarır. Userbot üçün təvazökar dəyərlər.
# - in_memory=True saxlanılır (Railway disk persistent deyil), AMMA artıq
#   .song polling və .play CreateGroupCall kimi session-revoke triggerlərini
#   kodu yenidən yazmaqla aradan qaldırdıq.
# - sleep_threshold=60: FloodWait < 60 san. avtomatik gözlənilir (crash yox).
app = Client(
    name="ryhavean_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True,
    workers=1,
    max_concurrent_transmissions=1,
    sleep_threshold=60,
)

call_py = PyTgCalls(app)
