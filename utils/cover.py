import os

from PIL import Image, ImageDraw, ImageFont

COVER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cover.jpg")

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def _load_font(size: int) -> ImageFont.ImageFont:
    for p in _FONT_CANDIDATES:
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def generate_cover(path: str = COVER_PATH, size: int = 640, letter: str = "R") -> str:
    img = Image.new("RGB", (size, size), "black")
    draw = ImageDraw.Draw(img)
    font = _load_font(int(size * 0.75))
    bbox = draw.textbbox((0, 0), letter, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - w) // 2 - bbox[0]
    y = (size - h) // 2 - bbox[1]
    draw.text((x, y), letter, fill="white", font=font)
    img.save(path, format="JPEG", quality=92)
    return path


def ensure_cover(path: str = COVER_PATH) -> str:
    if not os.path.isfile(path):
        generate_cover(path)
    return path
