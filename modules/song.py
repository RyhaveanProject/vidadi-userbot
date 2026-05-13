import asyncio
import os
import tempfile
import time

from pyrogram import filters
from pyrogram.types import Message

from app import app, log
from config import COMMAND_PREFIXES, SONG_BOT, ARTIST_TAG
from utils.metadata import rewrite_mp3_metadata


_LOCK = asyncio.Lock()  # serialize interactions with @SongFastBot


async def _baseline_last_id(client, bot_username: str) -> int:
    """Return the id of the most recent message currently in the chat with the bot."""
    try:
        async for m in client.get_chat_history(bot_username, limit=1):
            return m.id
    except Exception:  # noqa: BLE001
        pass
    return 0


async def _wait_for_results(client, bot_username: str, baseline_id: int, timeout: float = 15.0):
    """
    Poll the chat with SongFastBot for a NEW message (id > baseline_id) that
    has inline buttons (= the search results message). The baseline ensures we
    don't accidentally click the /start welcome keyboard or any older message.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            async for m in client.get_chat_history(bot_username, limit=10):
                if m.id <= baseline_id:
                    # older than our baseline -> stop scanning this iteration
                    break
                if m.from_user and m.from_user.is_self:
                    # our own outgoing query message
                    continue
                if m.reply_markup and getattr(m.reply_markup, "inline_keyboard", None):
                    return m
        except Exception as e:  # noqa: BLE001
            log.warning("get_chat_history failed: %s", e)
        await asyncio.sleep(0.6)
    return None


async def _wait_for_audio(client, bot_username: str, baseline_id: int, timeout: float = 30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            async for m in client.get_chat_history(bot_username, limit=10):
                if m.id <= baseline_id:
                    break
                if m.audio:
                    return m
        except Exception as e:  # noqa: BLE001
            log.warning("get_chat_history failed: %s", e)
        await asyncio.sleep(0.6)
    return None


@app.on_message(
    filters.command("song", prefixes=COMMAND_PREFIXES)
    & (filters.group | filters.private)
)
async def song_cmd(client, message: Message):
    log.info(".song triggered in chat=%s by user=%s", message.chat.id,
             message.from_user.id if message.from_user else "?")

    if len(message.command) < 2:
        await message.reply("🥷 İstifadə: `.song mahnı adı`", quote=True)
        return

    query = message.text.split(maxsplit=1)[1].strip()
    status = await message.reply(f"🔎 `{query}` Arıyorum bebegim 🫦...", quote=True)

    async with _LOCK:
        try:
            # 1. /start the bot once (idempotent). Ignore the welcome message.
            try:
                await client.send_message(SONG_BOT, "/start")
                await asyncio.sleep(1.2)
            except Exception as e:  # noqa: BLE001
                log.warning("/start to %s failed (continuing): %s", SONG_BOT, e)

            # 2. Snapshot the baseline AFTER /start so we ignore the welcome keyboard.
            baseline_id = await _baseline_last_id(client, SONG_BOT)
            log.info("song: baseline_id=%s", baseline_id)

            # 3. Send the search query
            await client.send_message(SONG_BOT, query)

            # 4. Wait for a NEW message with inline buttons (search results).
            results_msg = await _wait_for_results(client, SONG_BOT, baseline_id, timeout=15.0)
            if not results_msg:
                await status.edit("Gaga məzələnisən? elə mahnı tapılmadı 🤬")
                return

            # 5. Click the first button
            try:
                await results_msg.click(0)
            except Exception as e:  # noqa: BLE001
                log.warning("click(0) failed: %s — falling back to raw callback", e)
                try:
                    btn = results_msg.reply_markup.inline_keyboard[0][0]
                    if getattr(btn, "callback_data", None):
                        await client.request_callback_answer(
                            chat_id=results_msg.chat.id,
                            message_id=results_msg.id,
                            callback_data=btn.callback_data,
                        )
                    else:
                        raise RuntimeError("First button has no callback_data")
                except Exception as e2:  # noqa: BLE001
                    log.exception("song click fallback failed")
                    await status.edit(f"Bir deşiyi tutturanmadım {e2}")
                    return

            # 6. After clicking, the audio comes as a NEW message. New baseline = current latest.
            audio_baseline = await _baseline_last_id(client, SONG_BOT)
            audio_msg = await _wait_for_audio(client, SONG_BOT, audio_baseline, timeout=30.0)
            if not audio_msg:
                await status.edit("❌ Mahnı gəlmədi qaçdı (timeout).")
                return

            # 7. Download
            tmp_dir = tempfile.mkdtemp(prefix="rv_song_")
            path = await audio_msg.download(file_name=os.path.join(tmp_dir, "track.mp3"))

            # 8. Rewrite metadata (artist + cover)
            title = (audio_msg.audio.title if audio_msg.audio else None) or query
            try:
                rewrite_mp3_metadata(path, artist=ARTIST_TAG, title=title)
            except Exception as e:  # noqa: BLE001
                log.warning("Metadata rewrite failed: %s", e)

            duration = audio_msg.audio.duration if audio_msg.audio else 0

            # 9. Send as reply to the original .song message
            await client.send_audio(
                chat_id=message.chat.id,
                audio=path,
                caption=f"🎵 {title}\n👤 {ARTIST_TAG}",
                title=title,
                performer=ARTIST_TAG,
                duration=duration,
                reply_to_message_id=message.id,
            )

            try:
                await status.delete()
            except Exception:  # noqa: BLE001
                pass

            # cleanup
            try:
                os.remove(path)
                os.rmdir(tmp_dir)
            except Exception:  # noqa: BLE001
                pass

        except Exception as e:  # noqa: BLE001
            log.exception("song_cmd error")
            try:
                await status.edit(f"Medyanı açın blet {e}")
            except Exception:  # noqa: BLE001
                pass
