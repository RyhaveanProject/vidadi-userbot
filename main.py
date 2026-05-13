import asyncio
import os

from pyrogram import idle

from app import app, call_py, log
from utils.cover import ensure_cover

# Register handlers
from modules import play, song  # noqa: F401


async def _startup():
    # Ensure cover image exists before any .song request
    ensure_cover()

    await app.start()
    await call_py.start()

    me = await app.get_me()
    log.info("Userbot started as @%s (id=%s)", me.username, me.id)


async def _main():
    await _startup()
    try:
        await idle()
    finally:
        try:
            await app.stop()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    # Make sure working dir is the script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    asyncio.run(_main())
