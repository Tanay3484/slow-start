"""Write the Android launcher icons and splash screens from Slumbrock (original art), replacing the
Capacitor defaults.

    python scripts/android_assets.py

Run after `npx cap add android`. It deletes the adaptive-icon XML so the PNG icons are used as drawn
(adaptive icons would crop a pixel-art sprite), and fills every density of icon and splash.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

RES = Path("app/android/app/src/main/res")
BG = "#1a1c2c"
ICON_SIZES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
SPLASH = {
    "mdpi": (320, 480),
    "hdpi": (480, 800),
    "xhdpi": (720, 1280),
    "xxhdpi": (960, 1600),
    "xxxhdpi": (1280, 1920),
}


def sprite(name: str) -> Image.Image:
    data = json.loads(Path("app/src/art/sprites.json").read_text(encoding="utf-8"))
    rows, pal = data["sprites"][name], data["palette"]
    img = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                h = pal[ch]
                img.putpixel((x, y), (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255))
    return img


def on_canvas(base: Image.Image, w: int, h: int, fill: float) -> Image.Image:
    """The sprite at an integer multiple of its size (crisp pixels), centred on the app background."""
    canvas = Image.new("RGBA", (w, h), BG)
    k = max(1, int(min(w, h) * fill) // max(base.size))
    s = base.resize((base.width * k, base.height * k), Image.NEAREST)
    canvas.alpha_composite(s, ((w - s.width) // 2, (h - s.height) // 2))
    return canvas


def main() -> None:
    giant = sprite("slumbrock_2")
    shutil.rmtree(RES / "mipmap-anydpi-v26", ignore_errors=True)
    for density, size in ICON_SIZES.items():
        icon = on_canvas(giant, size, size, 0.86).convert("RGB")
        for name in ("ic_launcher", "ic_launcher_round", "ic_launcher_foreground"):
            icon.save(RES / f"mipmap-{density}" / f"{name}.png")
    for density, (w, h) in SPLASH.items():
        for orient, size in (("port", (w, h)), ("land", (h, w))):
            on_canvas(giant, *size, 0.4).convert("RGB").save(
                RES / f"drawable-{orient}-{density}" / "splash.png"
            )
    on_canvas(giant, 480, 320, 0.5).convert("RGB").save(RES / "drawable" / "splash.png")
    print("Android icons and splash screens written")


if __name__ == "__main__":
    main()
