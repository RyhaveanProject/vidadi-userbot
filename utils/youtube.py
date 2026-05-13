import asyncio
import functools
from typing import Optional

import yt_dlp


_YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "geo_bypass": True,
    "default_search": "ytsearch1",
    "source_address": "0.0.0.0",
    "extract_flat": False,
    "skip_download": True,
}


def _extract(query: str) -> dict:
    with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
        info = ydl.extract_info(query, download=False)
    if "entries" in info:
        entries = [e for e in info["entries"] if e]
        if not entries:
            raise RuntimeError("No results")
        info = entries[0]
    return info


async def search_audio(query: str) -> Optional[dict]:
    """
    Search YouTube and return dict with keys: url, title, duration, webpage_url.
    The 'url' is a direct streamable URL that ffmpeg can consume.
    """
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(None, functools.partial(_extract, query))

    stream_url = info.get("url")
    # When format gives 'requested_formats' (e.g. dash), pick the audio one
    if not stream_url and info.get("requested_formats"):
        for f in info["requested_formats"]:
            if f.get("acodec") and f["acodec"] != "none":
                stream_url = f.get("url")
                break

    if not stream_url:
        return None

    return {
        "url": stream_url,
        "title": info.get("title") or "Unknown",
        "duration": int(info.get("duration") or 0),
        "webpage_url": info.get("webpage_url") or info.get("original_url") or "",
        "uploader": info.get("uploader") or "",
    }
