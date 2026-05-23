from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets"
PNG_PATH = ASSET_DIR / "app_icon.png"
ICO_PATH = ASSET_DIR / "app_icon.ico"


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def draw_icon(size: int = 1024) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    radius = int(size * 0.22)
    margin = int(size * 0.06)
    for y in range(margin, size - margin):
        t = (y - margin) / (size - margin * 2)
        color = (
            lerp(40, 72, t),
            lerp(124, 86, t),
            lerp(210, 190, t),
            255,
        )
        draw.line((margin, y, size - margin, y), fill=color)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((margin, margin, size - margin, size - margin), radius=radius, fill=255)
    image.putalpha(mask)

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        (int(size * 0.18), int(size * 0.12), int(size * 0.82), int(size * 0.76)),
        fill=(255, 255, 255, 34),
    )
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(int(size * 0.035))))

    bubble = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bubble_draw = ImageDraw.Draw(bubble)
    bubble_box = (
        int(size * 0.19),
        int(size * 0.25),
        int(size * 0.81),
        int(size * 0.67),
    )
    bubble_draw.rounded_rectangle(bubble_box, radius=int(size * 0.1), fill=(255, 255, 255, 245))
    tail = [
        (int(size * 0.39), int(size * 0.64)),
        (int(size * 0.31), int(size * 0.79)),
        (int(size * 0.51), int(size * 0.66)),
    ]
    bubble_draw.polygon(tail, fill=(255, 255, 255, 245))
    shadow = bubble.filter(ImageFilter.GaussianBlur(int(size * 0.012)))
    shadow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_layer.alpha_composite(shadow, (0, int(size * 0.02)))
    image.alpha_composite(shadow_layer)
    image.alpha_composite(bubble)

    mark = ImageDraw.Draw(image)
    heart_color = (236, 72, 153, 255)
    cx, cy = int(size * 0.5), int(size * 0.47)
    r = int(size * 0.07)
    mark.ellipse((cx - r * 2, cy - r, cx, cy + r), fill=heart_color)
    mark.ellipse((cx, cy - r, cx + r * 2, cy + r), fill=heart_color)
    mark.polygon(
        [
            (cx - r * 2, cy),
            (cx + r * 2, cy),
            (cx, cy + int(size * 0.19)),
        ],
        fill=heart_color,
    )

    sparkle = (255, 213, 79, 255)
    sx, sy = int(size * 0.68), int(size * 0.34)
    s = int(size * 0.055)
    mark.polygon([(sx, sy - s), (sx + s // 3, sy), (sx, sy + s), (sx - s // 3, sy)], fill=sparkle)
    mark.polygon([(sx - s, sy), (sx, sy + s // 3), (sx + s, sy), (sx, sy - s // 3)], fill=sparkle)

    return image


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    icon = draw_icon()
    icon.save(PNG_PATH)
    icon.save(ICO_PATH, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {ICO_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
