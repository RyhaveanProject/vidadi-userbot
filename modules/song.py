import asyncio
import os
import tempfile

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from app import app, log
from config import COMMAND_PREFIXES, SONG_BOT, ARTIST_TAG
from utils.metadata import rewrite_mp3_metadata


# Bütün @SongFastBot qarşılıqlı işləməsini bir-bir et — session-ı qoruyur
_LOCK = asyncio.Lock()

# SongFastBot-dan gələn mesajları gözləyən "future"-lar.
# Polling (get_chat_history) ƏVƏZİNƏ event-driven yanaşma — Telegram-ın
# flood-protection-ini işə salmır. Session-ın revoke olunmasının ƏSAS səbəbi
# bu idi.
_pending_results: asyncio.Future | None = None  # düymələri olan mesaj
_pending_audio: asyncio.Future | None = None    # audio mesaj


@app.on_message(filters.user(SONG_BOT) & filters.private, group=-1)
async def _song_bot_listener(_, message: Message):
    """SongFastBot-dan gələn bütün mesajları lazımi future-lara yönəlt."""
    global _pending_results, _pending_audio

    # Audio gəldisə — audio future-u tamamla (prioritet)
    if message.audio and _pending_audio and not _pending_audio.done():
        _pending_audio.set_result(message)
        return

    # İnline düymələri olan axtarış nəticəsi
    if (
        message.reply_markup
        and getattr(message.reply_markup, "inline_keyboard", None)
        and _pending_results
        and not _pending_results.done()
    ):
        _pending_results.set_result(message)


async def _safe_send(client, *args, **kwargs):
    """FloodWait avtomatik handle olunur."""
    try:
        return await client.send_message(*args, **kwargs)
    except FloodWait as fw:
        log.warning("SPAMDI SPAMM %s Saniyə gözlə ürəg...", fw.value)
        await asyncio.sleep(fw.value + 1)
        return await client.send_message(*args, **kwargs)


@app.on_message(
    filters.command("song", prefixes=COMMAND_PREFIXES)
    & (filters.group | filters.private)
)
async def song_cmd(client, message: Message):
    global _pending_results, _pending_audio

    log.info(".song triggered in chat=%s by user=%s", message.chat.id,
             message.from_user.id if message.from_user else "?")

    if len(message.command) < 2:
        await message.reply("İstifadə: `.song Dolya vor`", quote=True)
        return

    query = message.text.split(maxsplit=1)[1].strip()
    status = await message.reply(f" 🫦", quote=True)

    # Bütün SongFastBot trafikini serializə et (eyni anda 2 .song olmasın)
    async with _LOCK:
        # Bu sorğu üçün təzə future-lar
        loop = asyncio.get_running_loop()
        _pending_results = loop.create_future()
        _pending_audio = loop.create_future()

        try:
            # 1. Axtarışı göndər (artıq /start-a ehtiyac yox — botla əvvəlcədən
            #    açılmış chat varsa, hər .song-da /start spam-a çevrilir).
            await _safe_send(client, SONG_BOT, query)

            # 2. Düymələri olan nəticə mesajı (listener tərəfindən doldurulur)
            try:
                results_msg = await asyncio.wait_for(_pending_results, timeout=15.0)
            except asyncio.TimeoutError:
                # İlk dəfə istifadə olunur? /start ataq və yenidən cəhd
                try:
                    await _safe_send(client, SONG_BOT, "/start")
                    await asyncio.sleep(1.0)
                    _pending_results = loop.create_future()
                    await _safe_send(client, SONG_BOT, query)
                    results_msg = await asyncio.wait_for(_pending_results, timeout=15.0)
                except asyncio.TimeoutError:
                    await status.edit("Gaga məzələnisn?🤬 belə mahnı yoxdu!")
                    return

            # 3. İlk düyməni klik et
            try:
                await results_msg.click(0)
            except Exception as e:  # noqa: BLE001
                log.warning("click(0) failed: %s", e)
                await status.edit(f"Deşiyi tutturanmadıme 🥺 {e}")
                return

            # 4. Audio mesajını gözlə (listener doldurur — POLLING YOXDUR)
            try:
                audio_msg = await asyncio.wait_for(_pending_audio, timeout=45.0)
            except asyncio.TimeoutError:
                await status.edit("Ujey təmiz məzələnirsən Medya Bağlı Sən yarım ağıllı 😏")
                return

            # 5. Yüklə
            tmp_dir = tempfile.mkdtemp(prefix="rv_song_")
            path = await audio_msg.download(file_name=os.path.join(tmp_dir, "track.mp3"))

            # 6. Metadata düzəliş
            title = (audio_msg.audio.title if audio_msg.audio else None) or query
            try:
                rewrite_mp3_metadata(path, artist=ARTIST_TAG, title=title)
            except Exception as e:  # noqa: BLE001
                log.warning("Metadata rewrite failed: %s", e)

            duration = audio_msg.audio.duration if audio_msg.audio else 0

            # 7. Reply olaraq göndər
            try:
                await client.send_audio(
                    chat_id=message.chat.id,
                    audio=path,
                    caption=f"{title}\n{ARTIST_TAG}",
                    title=title,
                    performer=ARTIST_TAG,
                    duration=duration,
                    reply_to_message_id=message.id,
                )
            except FloodWait as fw:
                log.warning("send_audio FloodWait %s san.", fw.value)
                await asyncio.sleep(fw.value + 1)
                await client.send_audio(
                    chat_id=message.chat.id,
                    audio=path,
                    caption=f"{title}\n{ARTIST_TAG}",
                    title=title,
                    performer=ARTIST_TAG,
                    duration=duration,
                    reply_to_message_id=message.id,
                )

            try:
                await status.delete()
            except Exception:  # noqa: BLE001
                pass

            try:
                os.remove(path)
                os.rmdir(tmp_dir)
            except Exception:  # noqa: BLE001
                pass

        except FloodWait as fw:
            log.warning("song_cmd FloodWait %s san.", fw.value)
            try:
                await status.edit(f"Telegram'a da daş qoyanın 🤬 spama saldı oqraş.")
            except Exception:  # noqa: BLE001
                pass
        except Exception as e:  # noqa: BLE001
            log.exception("song_cmd error")
            try:
                await status.edit(f"Xəta: {e}")
            except Exception:  # noqa: BLE001
                pass
        finally:
            # Future-ları təmizlə
            _pending_results = None
            _pending_audio = None
