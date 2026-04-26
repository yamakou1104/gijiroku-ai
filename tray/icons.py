from PIL import Image, ImageDraw

ICON_SIZE = 64

COLORS = {
    "idle": "#607D8B",
    "recording": "#E53935",
    "processing": "#FDD835",
}

def create_icon(state):
    color = COLORS.get(state, COLORS["idle"])
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = 4
    draw.ellipse(
        [margin, margin, ICON_SIZE - margin, ICON_SIZE - margin],
        fill=color,
    )
    draw.text(
        (ICON_SIZE // 2 - 6, ICON_SIZE // 2 - 8),
        "録",
        fill="white",
    )
    return image
