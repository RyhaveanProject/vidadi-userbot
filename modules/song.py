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


async def _wait_for_results(client, bot_username: str, after_ts: float, timeout: float = 8.0):
    """Poll the chat with SongFastBot for the latest message with inline buttons."""
    deadline = time.time() + timeout
    last_id = 0
    while time.time() < deadline:
        async for m in client.get_chat_history(bot_username, limit=5):
            if m.date and m.date.timestamp() < after_ts - 1:
                break
            if m.reply_markup and getattr(m.reply_markup, "inline_keyboard", None):
                return m
            last_id = max(last_id, m.id)
        await asyncio.sleep(0.4)
    return None


async def _wait_for_audio(client, bot_username: str, after_ts: float, timeout: float = 15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        async for m in client.get_chat_history(bot_username, limit=5):
            if m.date and m.date.timestamp() < after_ts - 1:
                break
            if m.audio:
                return m
        await asyncio.sleep(0.4)
    return None


@app.on_message(
    filters.command("song", prefixes=COMMAND_PREFIXES)
    & (filters.group | filters.private)
)
async def song_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("ℹ️ İstifadə: `.song mahnı adı`", quote=True)
        return

    query = message.text.split(maxsplit=1)[1].strip()
    status = await message.reply(f"🔎 `{query}` axtarılır...", quote=True)

    async with _LOCK:
        try:
            # 1. /start the bot (idempotent)
            await client.send_message(SONG_BOT, "/start")
            await asyncio.sleep(1.0)

            # 2. Send search query
            sent_ts = time.time()
            await client.send_message(SONG_BOT, query)
            await asyncio.sleep(2.0)

            # 3. Wait for results message with inline buttons
            results_msg = await _wait_for_results(client, SONG_BOT, sent_ts, timeout=8.0)
            if not results_msg:
                await status.edit("❌ Nəticə tapılmadı.")
                return

            # 4. Click the first button
            try:
                # Some bots use callback, others a URL. Try positional click.
                await results_msg.click(0)
            except Exception as e:  # noqa: BLE001
                log.warning("click(0) failed: %s — falling back", e)
                try:
                    btn = results_msg.reply_markup.inline_keyboard[0][0]
                    if btn.callback_data:
                        await client.request_callback_answer(
                            chat_id=results_msg.chat.id,
                            message_id=results_msg.id,
                            callback_data=btn.callback_data,
                        )
                except Exception as e2:  # noqa: BLE001
                    await status.edit(f"❌ Düyməyə basa bilmədim: {e2}")
                    return

            # 5. Wait for audio
            click_ts = time.time()
            audio_msg = await _wait_for_audio(client, SONG_BOT, click_ts, timeout=20.0)
            if not audio_msg:
                await status.edit("❌ Mahnı gəlmədi (timeout).")
                return

            # 6. Download
            tmp_dir = tempfile.mkdtemp(prefix="rv_song_")
            path = await audio_msg.download(file_name=os.path.join(tmp_dir, "track.mp3"))

            # 7. Rewrite metadata (artist + cover)
            title = (audio_msg.audio.title if audio_msg.audio else None) or query
            try:
                rewrite_mp3_metadata(path, artist=ARTIST_TAG, title=title)
            except Exception as e:  # noqa: BLE001
                log.warning("Metadata rewrite failed: %s", e)

            duration = audio_msg.audio.duration if audio_msg.audio else 0

            # 8. Send as reply to the original .song message
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
                await status.edit(f"❌ Xəta: {e}")
            except Exception:  # noqa: BLE001
                pass
