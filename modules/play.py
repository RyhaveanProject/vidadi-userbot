import asyncio
import os
import tempfile
import time

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from pytgcalls.types import MediaStream, AudioQuality
from pytgcalls.exceptions import NoActiveGroupCall

from app import app, call_py, log
from config import COMMAND_PREFIXES
from utils.youtube import search_audio


# --- helpers ---------------------------------------------------------------

# ffmpeg parameters are a SINGLE STRING in py-tgcalls 2.2.x (NOT a dict).
_FFMPEG_NETWORK_FLAGS = (
    "-reconnect 1 "
    "-reconnect_at_eof 1 "
    "-reconnect_streamed 1 "
    "-reconnect_delay_max 5 "
    "-rw_timeout 15000000"
)


def _build_stream(source: str, *, is_file: bool) -> MediaStream:
    return MediaStream(
        source,
        audio_parameters=AudioQuality.HIGH,
        video_flags=MediaStream.Flags.IGNORE,
        ffmpeg_parameters=None if is_file else _FFMPEG_NETWORK_FLAGS,
    )


async def _stream(chat_id: int, source: str, *, is_file: bool):
    media = _build_stream(source, is_file=is_file)
    await call_py.play(chat_id, media)


# --- handlers --------------------------------------------------------------

@app.on_message(
    filters.command("play", prefixes=COMMAND_PREFIXES)
    & filters.group
)
async def play_cmd(_, message: Message):
    log.info(".play triggered in chat=%s by user=%s", message.chat.id,
             message.from_user.id if message.from_user else "?")
    chat_id = message.chat.id
    started_at = time.monotonic()

    # 1. Mənbə təyini
    replied = message.reply_to_message
    source_path: str | None = None
    is_file = False
    title = ""
    status = None

    if replied and (replied.audio or replied.voice or replied.video or replied.document):
        status = await message.reply("Yüklənir ürəyim...", quote=True)
        try:
            source_path = await replied.download(
                file_name=os.path.join(tempfile.gettempdir(), f"rv_{message.id}_")
            )
            is_file = True
            media = replied.audio or replied.voice or replied.video
            title = getattr(media, "title", None) or getattr(media, "file_name", None) or "Audio"
        except Exception as e:  # noqa: BLE001
            log.exception(".play download failed")
            await status.edit(f"Şansını bir daha sına gaga : {e}")
            return
    else:
        if len(message.command) < 2:
            await message.reply(
                "🥷 İstifadə:\n"
                "• `.play Auye jizin varam`\n"
                "• Audio/səs faylına reply edib `.play` yaz ürəg",
                quote=True,
            )
            return
        query = message.text.split(maxsplit=1)[1]
        status = await message.reply(f"Axtarılır xəyatım 🫦: `{query}`", quote=True)
        try:
            info = await search_audio(query)
        except Exception as e:  # noqa: BLE001
            log.exception(".play yt-dlp search failed")
            await status.edit(f"içnə paks tapılmadı: {e}")
            return
        if not info:
            await status.edit("pay içnə yenə tapılmadı 🍑.")
            return
        source_path = info["url"]
        title = info["title"]

    # 2. Çal. Aktiv VC yoxdursa — userbot ilə YARATMA (Telegram session-ı revoke edir).
    try:
        await _stream(chat_id, source_path, is_file=is_file)
    except NoActiveGroupCall:
        # Userbot-un CreateGroupCall raw API çağırması Telegram anti-abuse-ı
        # işə salır və hesabı deauthorize edir. İstifadəçi VC-ni özü açmalıdır.
        await status.edit(
            "Ayga türkün məsəli səsli söhbət bağlıdıye qadan alım\n"
            "yetkimdə yoxdu brad özün aç səslini 😝"
        )
        return
    except FloodWait as fw:
        log.warning(".play FloodWait %s san.", fw.value)
        await status.edit(f"Telegram bizi {fw.value}s gözlədir, sonra yenidən cəhd et.")
        return
    except Exception as e:  # noqa: BLE001
        log.exception(".play stream failed")
        await status.edit(f"Xarabdı gağa başqaısnı yoxla {e}")
        return

    took = time.monotonic() - started_at
    await status.edit(
        f"🫦 **İndi ÇALIRAM (Musiqini) - Can cigər** `{title}`\n"
        f"⚡️ {took:.1f}s\n"
        f" `.end` yaz və soxum içimə 🥹"
    )


@app.on_message(
    filters.command(["end", "stop", "leave"], prefixes=COMMAND_PREFIXES)
    & filters.group
)
async def end_cmd(_, message: Message):
    chat_id = message.chat.id
    try:
        await call_py.leave_call(chat_id)
        await message.reply("Bəsdi bu qədər qulağ asdığıvız FLY 😏", quote=True)
    except Exception as e:  # noqa: BLE001
        log.exception(".end failed")
        await message.reply(f"⚠️ {e}", quote=True)


@app.on_message(
    filters.command(["pause"], prefixes=COMMAND_PREFIXES) & filters.group
)
async def pause_cmd(_, message: Message):
    try:
        await call_py.pause_stream(message.chat.id)
        await message.reply("Sənə 1", quote=True)
    except Exception as e:  # noqa: BLE001
        log.exception(".pause failed")
        await message.reply(f"⚠️ {e}", quote=True)


@app.on_message(
    filters.command(["resume"], prefixes=COMMAND_PREFIXES) & filters.group
)
async def resume_cmd(_, message: Message):
    try:
        await call_py.resume_stream(message.chat.id)
        await message.reply("Day sənsəndə balam 🫦", quote=True)
    except Exception as e:  # noqa: BLE001
        log.exception(".resume failed")
        await message.reply(f"⚠️ {e}", quote=True)
