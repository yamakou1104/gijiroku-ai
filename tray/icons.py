import sys
from PIL import Image, ImageDraw, ImageFont

ICON_SIZE = 44 if sys.platform == "darwin" else 64

COLORS = {
    "idle": "#607D8B",
    "recording": "#E53935",
    "grace_period": "#FF9800",
    "processing": "#FDD835",
}


def _load_cjk_font(size):
    if sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
    else:
        candidates = [
            "C:\\Windows\\Fonts\\meiryo.ttc",
            "C:\\Windows\\Fonts\\msgothic.ttc",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def create_icon(state):
    color = COLORS.get(state, COLORS["idle"])
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = 4
    draw.ellipse(
        [margin, margin, ICON_SIZE - margin, ICON_SIZE - margin],
        fill=color,
    )
    font_size = ICON_SIZE // 4
    font = _load_cjk_font(font_size)
    bbox = draw.textbbox((0, 0), "録", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (ICON_SIZE - tw) // 2
    y = (ICON_SIZE - th) // 2
    draw.text((x, y), "録", fill="white", font=font)
    return image
