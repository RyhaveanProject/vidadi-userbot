import os

from mutagen.id3 import ID3, APIC, TPE1, TPE2, TCOM, TCON, TIT2, error as ID3Error
from mutagen.mp3 import MP3

from .cover import ensure_cover


def rewrite_mp3_metadata(
    path: str,
    artist: str = "@Ryhavean",
    title: str | None = None,
    cover_path: str | None = None,
) -> str:
    """
    Replace artist/composer/album-artist tags with `artist` and embed cover image.
    Returns the same path.
    """
    cover_path = cover_path or ensure_cover()

    try:
        audio = MP3(path, ID3=ID3)
    except Exception:  # noqa: BLE001
        # Not a real mp3 - just return it untouched
        return path

    try:
        audio.add_tags()
    except ID3Error:
        pass

    tags = audio.tags
    if tags is None:
        audio.tags = ID3()
        tags = audio.tags

    # Remove any existing artwork / artist fields
    for key in ("APIC", "APIC:", "TPE1", "TPE2", "TCOM"):
        try:
            tags.delall(key)
        except Exception:  # noqa: BLE001
            pass

    tags.add(TPE1(encoding=3, text=[artist]))     # Lead artist
    tags.add(TPE2(encoding=3, text=[artist]))     # Album artist
    tags.add(TCOM(encoding=3, text=[artist]))     # Composer
    tags.add(TCON(encoding=3, text=["Music"]))

    if title:
        try:
            tags.delall("TIT2")
        except Exception:  # noqa: BLE001
            pass
        tags.add(TIT2(encoding=3, text=[title]))

    if os.path.isfile(cover_path):
        with open(cover_path, "rb") as f:
            cover = f.read()
        tags.add(
            APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=cover,
            )
        )

    audio.save(v2_version=3)
    return path
