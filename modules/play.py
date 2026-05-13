import asyncio
import os
import random
import tempfile
import time

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.raw.functions.phone import CreateGroupCall
from pyrogram.errors import RPCError

from pytgcalls.types import MediaStream, AudioQuality
from pytgcalls.exceptions import NoActiveGroupCall

from app import app, call_py, log
from config import COMMAND_PREFIXES
from utils.youtube import search_audio


# --- helpers ---------------------------------------------------------------

_FFMPEG_NETWORK_FLAGS = (
    "-reconnect 1 "
    "-reconnect_at_eof 1 "
    "-reconnect_streamed 1 "
    "-reconnect_delay_max 5 "
    "-rw_timeout 15000000"
)


async def _try_create_group_call(chat_id: int) -> bool:
    """Try to start a voice chat if user has admin rights. Returns True on success."""
    try:
        peer = await app.resolve_peer(chat_id)
        await app.invoke(
            CreateGroupCall(
                peer=peer,
                random_id=random.randint(10_000_000, 999_999_999),
            )
        )
        # Give Telegram a moment to register the call
        await asyncio.sleep(1.2)
        return True
    except RPCError as e:
        log.warning("CreateGroupCall failed for %s: %s", chat_id, e)
        return False
    except Exception as e:  # noqa: BLE001
        log.warning("CreateGroupCall error for %s: %s", chat_id, e)
        return False


async def _stream(chat_id: int, source: str, *, is_file: bool):
    """Start or replace the active stream in the given chat."""
    ffmpeg_params = {} if is_file else {"before": _FFMPEG_NETWORK_FLAGS}

    media = MediaStream(
        source,
        audio_parameters=AudioQuality.HIGH,
        video_flags=MediaStream.Flags.IGNORE,
        ffmpeg_parameters=ffmpeg_params if ffmpeg_params else None,
    )
    await call_py.play(chat_id, media)


# --- handlers --------------------------------------------------------------

@app.on_message(
    filters.command("play", prefixes=COMMAND_PREFIXES)
    & filters.group
)
async def play_cmd(_, message: Message):
    chat_id = message.chat.id
    started_at = time.monotonic()

    # 1. Determine source
    replied = message.reply_to_message
    source_path: str | None = None
    is_file = False
    title = ""

    if replied and (replied.audio or replied.voice or replied.video or replied.document):
        status = await message.reply("⏬ Endirilir...", quote=True)
        try:
            source_path = await replied.download(
                file_name=os.path.join(tempfile.gettempdir(), f"rv_{message.id}_")
            )
            is_file = True
            media = replied.audio or replied.voice or replied.video
            title = getattr(media, "title", None) or getattr(media, "file_name", None) or "Audio"
        except Exception as e:  # noqa: BLE001
            await status.edit(f"❌ Endirilmədi: {e}")
            return
    else:
        if len(message.command) < 2:
            await message.reply(
                "ℹ️ İstifadə:\n"
                "• `.play mahnı adı`\n"
                "• Audio/səs faylına reply edib `.play` yaz",
                quote=True,
            )
            return
        query = message.text.split(maxsplit=1)[1]
        status = await message.reply(f"🔎 Axtarılır: `{query}`", quote=True)
        try:
            info = await search_audio(query)
        except Exception as e:  # noqa: BLE001
            await status.edit(f"❌ Axtarış xətası: {e}")
            return
        if not info:
            await status.edit("❌ Heç nə tapılmadı.")
            return
        source_path = info["url"]
        title = info["title"]

    # 2. Try to play. If no active call -> attempt to create one.
    async def _do_play():
        await _stream(chat_id, source_path, is_file=is_file)

    try:
        await _do_play()
    except NoActiveGroupCall:
        log.info("No active voice chat in %s — attempting to start one", chat_id)
        if not await _try_create_group_call(chat_id):
            await status.edit(
                "❌ Səsli söhbət aktiv deyil və mən onu aça bilmirəm.\n"
                "Admin rütbəsi və 'Manage Voice Chats' icazəsi lazımdır."
            )
            return
        try:
            await _do_play()
        except Exception as e:  # noqa: BLE001
            await status.edit(f"❌ Səsli chata qoşula bilmədim: {e}")
            return
    except Exception as e:  # noqa: BLE001
        await status.edit(f"❌ Oxutma alınmadı: {e}")
        return

    took = time.monotonic() - started_at
    await status.edit(
        f"🎶 **İndi oxunur:** `{title}`\n"
        f"⚡️ {took:.1f}s\n"
        f"⏹ Dayandırmaq üçün: `.end`"
    )


@app.on_message(
    filters.command(["end", "stop", "leave"], prefixes=COMMAND_PREFIXES)
    & filters.group
)
async def end_cmd(_, message: Message):
    chat_id = message.chat.id
    try:
        await call_py.leave_call(chat_id)
        await message.reply("👋 Səsli söhbətdən çıxdım.", quote=True)
    except Exception as e:  # noqa: BLE001
        await message.reply(f"⚠️ {e}", quote=True)


@app.on_message(
    filters.command(["pause"], prefixes=COMMAND_PREFIXES) & filters.group
)
async def pause_cmd(_, message: Message):
    try:
        await call_py.pause_stream(message.chat.id)
        await message.reply("⏸ Pauza", quote=True)
    except Exception as e:  # noqa: BLE001
        await message.reply(f"⚠️ {e}", quote=True)


@app.on_message(
    filters.command(["resume"], prefixes=COMMAND_PREFIXES) & filters.group
)
async def resume_cmd(_, message: Message):
    try:
        await call_py.resume_stream(message.chat.id)
        await message.reply("▶️ Davam", quote=True)
    except Exception as e:  # noqa: BLE001
        await message.reply(f"⚠️ {e}", quote=True)
