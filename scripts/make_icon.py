"""Generates app.ico for the PortfolioManager .exe.

Draws a simple flat-style icon: a rounded "wallet/chart" motif —
a dark card with a green upward trend line — to represent an
investment portfolio tracker. Run manually when the icon needs
regenerating: python scripts/make_icon.py
"""

from PIL import Image, ImageDraw

SIZE = 256
BG = (15, 23, 42, 255)        # slate-900
CARD = (30, 41, 59, 255)      # slate-800
ACCENT = (34, 197, 94, 255)   # green-500
ACCENT_LIGHT = (74, 222, 128, 255)  # green-400


def build_base() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 14
    draw.rounded_rectangle(
        [margin, margin, SIZE - margin, SIZE - margin],
        radius=48,
        fill=BG,
    )

    inset = 34
    draw.rounded_rectangle(
        [inset, inset + 20, SIZE - inset, SIZE - inset],
        radius=28,
        fill=CARD,
    )

    points = [
        (58, 168),
        (98, 128),
        (128, 152),
        (168, 96),
        (198, 118),
    ]
    draw.line(points, fill=ACCENT_LIGHT, width=14, joint="curve")

    arrow_tip = (198, 118)
    draw.polygon(
        [
            (arrow_tip[0] - 26, arrow_tip[1] - 6),
            (arrow_tip[0] + 6, arrow_tip[1] - 26),
            (arrow_tip[0] + 14, arrow_tip[1] + 14),
        ],
        fill=ACCENT,
    )

    for px, py in points:
        r = 7
        draw.ellipse([px - r, py - r, px + r, py + r], fill=ACCENT_LIGHT)

    return img


def main() -> None:
    base = build_base()
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base.save(
        "app.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print("Wrote app.ico")


if __name__ == "__main__":
    main()
