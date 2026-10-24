"""Draw every sprite in code and write app/src/art/sprites.json (+ a preview PNG sheet).

    python scripts/draw_sprites.py            # writes the JSON the app reads
    python scripts/draw_sprites.py --preview  # also writes results/sprites-preview.png

All art is original, 2D pixel art drawn from rectangles and ellipses here. Nothing is traced from or
modelled on a Nintendo / Pokémon sprite. Each sprite is a list of strings; '.' is transparent and every
other character is a key into PALETTE.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PALETTE = {
    "k": "#1a1c2c",  # outline, deep navy
    "d": "#333c57",  # stone dark
    "s": "#566c86",  # stone mid
    "g": "#94b0c2",  # stone light
    "h": "#c4d4dd",  # stone highlight
    "m": "#38b764",  # moss dark
    "n": "#a7f070",  # moss light
    "y": "#ffcd75",  # glow
    "o": "#ef7d57",  # orange
    "r": "#b13e53",  # red
    "w": "#f4f4f4",  # white
    "b": "#3b5dc9",  # blue
    "c": "#41a6f6",  # cyan
    "t": "#73eff7",  # light teal
    "p": "#5d275d",  # purple
    "v": "#9d6bd3",  # violet
}

OUT_JSON = Path("app/src/art/sprites.json")
OUT_PNG = Path("results/sprites-preview.png")


class Grid:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.p = [["."] * w for _ in range(h)]

    def px(self, x: int, y: int, c: str) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = c

    def rect(self, x0: int, y0: int, x1: int, y1: int, c: str) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, c)

    def block(self, x0, y0, x1, y1, base, light, dark) -> None:
        """A lit block: light from the top left, shadow bottom right."""
        self.rect(x0, y0, x1, y1, base)
        self.rect(x0, y0, x1 - 1, y0, light)
        self.rect(x0, y0, x0, y1 - 1, light)
        self.rect(x0 + 1, y1, x1, y1, dark)
        self.rect(x1, y0 + 1, x1, y1, dark)

    def sym_block(self, x0, y0, x1, y1, base, light, dark) -> None:
        """The same lit block on both sides of the centre line."""
        self.block(x0, y0, x1, y1, base, light, dark)
        self.block(self.w - 1 - x1, y0, self.w - 1 - x0, y1, base, light, dark)

    def sym_rect(self, x0, y0, x1, y1, c) -> None:
        self.rect(x0, y0, x1, y1, c)
        self.rect(self.w - 1 - x1, y0, self.w - 1 - x0, y1, c)

    def sym_px(self, x, y, c) -> None:
        self.px(x, y, c)
        self.px(self.w - 1 - x, y, c)

    def ell(self, cx: float, cy: float, rx: float, ry: float, c: str) -> None:
        for y in range(self.h):
            for x in range(self.w):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.p[y][x] = c

    def outline(self, c: str = "k") -> None:
        src = [row[:] for row in self.p]
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x] != ".":
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and src[ny][nx] != ".":
                        self.p[y][x] = c
                        break

    def rows(self) -> list[str]:
        return ["".join(r) for r in self.p]


# ---------------------------------------------------------------- Slumbrock (32 x 32)


def slumbrock(stage: int) -> list[str]:
    """Stage 0 asleep, 1 drowsy, 2 awake, 3 roaring."""
    g = Grid(34, 34)  # one pixel of margin all round, for the outline
    o = 1  # offset
    dy = {0: 3, 1: 1, 2: 0, 3: 0}[stage]  # the head sinks while asleep

    def P(x, y):  # point in 32x32 space -> grid
        return x + o, y + o

    def B(x0, y0, x1, y1, *c):
        g.block(x0 + o, y0 + o, x1 + o, y1 + o, *c)

    def SB(x0, y0, x1, y1, *c):
        g.sym_block(x0 + o, y0 + o, x1 + o, y1 + o, *c)

    def R(x0, y0, x1, y1, c):
        g.rect(x0 + o, y0 + o, x1 + o, y1 + o, c)

    def SR(x0, y0, x1, y1, c):
        g.sym_rect(x0 + o, y0 + o, x1 + o, y1 + o, c)

    # legs and feet
    SB(9, 26, 14, 30, "s", "g", "d")
    SB(8, 29, 14, 31, "d", "s", "d")
    # torso and shoulders
    B(8, 20, 23, 25, "s", "g", "d")
    B(5, 16, 26, 19, "g", "h", "s")
    # arms
    if stage == 3:  # arms up, roaring
        SB(1, 9, 4, 17, "s", "g", "d")
        SB(0, 5, 5, 9, "g", "h", "s")
    else:
        SB(1, 17, 4, 25, "s", "g", "d")
        SB(0, 25, 5, 29, "g", "h", "s")
    # chest rune
    rune = {0: "d", 1: "o", 2: "y", 3: "y"}[stage]
    R(14, 21, 17, 24, rune)
    R(13, 22, 18, 23, rune)
    if stage == 3:
        R(15, 21, 16, 24, "w")
        g.px(12 + o, 22 + o, "o")
        g.px(19 + o, 22 + o, "o")
    # neck, only visible when the head is up
    if dy < 3:
        R(13, 14 + dy, 18, 15, "d")
    # head
    B(9, 4 + dy, 22, 13 + dy, "g", "h", "s")
    SB(7, 2 + dy, 9, 5 + dy, "s", "g", "d")  # horn stones
    R(14, 2 + dy, 17, 3 + dy, "m")
    for x, y, c in (
        (15, 1, "n"),
        (16, 1, "n"),
        (14, 2, "n"),
        (17, 3, "n"),
        (18, 2, "m"),
    ):
        g.px(x + o, y + dy + o, c)
    R(10, 7 + dy, 21, 8 + dy, "d")  # heavy brow
    # eyes
    if stage == 0:  # closed
        SR(11, 10 + dy, 13, 10 + dy, "k")
    elif stage == 1:  # half open, heavy lids
        SR(11, 9 + dy, 13, 9 + dy, "d")
        SR(11, 10 + dy, 13, 10 + dy, "w")
        g.px(13 + o, 10 + dy + o, "k")
        g.px(18 + o, 10 + dy + o, "k")
    else:  # open
        SR(11, 9 + dy, 13, 10 + dy, "w")
        g.px(13 + o, 9 + dy + o, "k")
        g.px(13 + o, 10 + dy + o, "k")
        g.px(18 + o, 9 + dy + o, "k")
        g.px(18 + o, 10 + dy + o, "k")
    # mouth
    if stage == 3:
        R(13, 11 + dy, 18, 13 + dy, "r")
        for x in (14, 16):
            g.px(x + o, 11 + dy + o, "w")
        g.px(15 + o, 13 + dy + o, "w")
        g.px(17 + o, 13 + dy + o, "w")
    else:
        R(13, 12 + dy, 18, 12 + dy, "d")
    # moss on the shoulders and head; more while asleep
    patches = [(6, 16), (8, 17), (24, 16), (22, 17), (10, 5 + dy), (21, 12 + dy)]
    if stage <= 1:
        patches += [
            (7, 16),
            (25, 17),
            (11, 6 + dy),
            (12, 4 + dy),
            (20, 5 + dy),
            (9, 20),
            (22, 25),
        ]
    for i, (x, y) in enumerate(patches):
        g.px(x + o, y + o, "m" if i % 2 == 0 else "n")
    if stage == 3:  # sparks of rune light around the head
        for x, y in ((3, 8), (28, 8), (7, 2), (24, 1), (1, 4), (30, 3)):
            g.px(x + o, y + o, "y")
    g.outline("k")
    return g.rows()


# ---------------------------------------------------------------- wild creatures (16 x 16)


def mk() -> Grid:
    return Grid(18, 18)  # 16 plus margin


def eyes(g: Grid, y: int, x1: int = 6, x2: int = 10, c: str = "k") -> None:
    g.px(x1 + 1, y, c)
    g.px(x2 + 1, y, c)
    g.px(x1 + 1, y - 1, "w") if c == "k" else None
    g.px(x2 + 1, y - 1, "w") if c == "k" else None


def mossling() -> list[str]:
    g = mk()
    g.ell(9, 10, 6.5, 5.5, "m")
    g.ell(8, 8.5, 4, 2.5, "n")
    g.ell(9, 10, 6.5, 5.5, "m") if False else None
    g.rect(9, 3, 9, 5, "m")
    g.ell(11, 3, 2.5, 1.5, "n")  # leaf sprout
    for x, y in ((6, 11), (12, 10)):
        g.px(x, y, "k")
        g.px(x, y - 1, "k")
    g.rect(8, 13, 10, 13, "d")
    g.outline()
    return g.rows()


def leafwing() -> list[str]:
    g = mk()
    g.ell(9, 9, 3.5, 4.5, "n")
    g.ell(4.5, 8, 3, 2, "m")
    g.ell(13.5, 8, 3, 2, "m")
    g.rect(8, 6, 8, 6, "k")
    g.rect(10, 6, 10, 6, "k")
    g.px(9, 8, "o")
    g.rect(8, 13, 8, 14, "o")
    g.rect(10, 13, 10, 14, "o")
    g.outline()
    return g.rows()


def pebbit() -> list[str]:
    g = mk()
    g.ell(9, 11, 5.5, 4.5, "g")
    g.ell(9, 8, 4, 3.5, "g")
    g.rect(6, 2, 7, 6, "s")  # ears
    g.rect(11, 2, 12, 6, "s")
    g.rect(6, 3, 6, 5, "h")
    g.rect(11, 3, 11, 5, "h")
    g.px(7, 8, "k")
    g.px(11, 8, "k")
    g.px(9, 10, "r")
    g.rect(6, 13, 7, 14, "s")
    g.rect(11, 13, 12, 14, "s")
    g.px(8, 10, "d")
    g.px(10, 10, "d")
    g.outline()
    return g.rows()


def lampwick() -> list[str]:
    g = mk()
    g.rect(8, 8, 9, 15, "d")
    g.rect(6, 15, 11, 16, "s")
    g.ell(8.5, 5, 4, 4, "y")
    g.ell(8.5, 5, 2.5, 2.5, "w")
    g.rect(5, 3, 12, 3, "d") if False else None
    g.px(7, 5, "k")
    g.px(10, 5, "k")
    g.rect(4, 9, 6, 9, "d")  # little arms
    g.rect(11, 9, 13, 9, "d")
    g.outline()
    return g.rows()


def ripplet() -> list[str]:
    g = mk()
    g.ell(9, 11, 5.5, 5, "c")
    g.rect(8, 3, 9, 6, "c")
    g.rect(9, 2, 9, 3, "t")
    g.ell(7.5, 10, 2, 2, "t")
    g.px(7, 12, "k")
    g.px(11, 12, "k")
    g.px(7, 11, "w")
    g.px(11, 11, "w")
    g.rect(8, 14, 10, 14, "b")
    g.outline()
    return g.rows()


def plateling() -> list[str]:
    g = mk()
    g.ell(9, 9, 6.5, 6.5, "d")
    g.ell(9, 9, 5, 5, "s")
    g.ell(8, 7.5, 3, 2, "g")  # a shine on the iron
    g.rect(6, 9, 7, 10, "w")
    g.rect(11, 9, 12, 10, "w")
    g.px(7, 10, "k")
    g.px(11, 10, "k")
    g.rect(8, 12, 10, 12, "d")
    g.rect(1, 8, 2, 11, "g")  # little grip hands
    g.rect(15, 8, 16, 11, "g")
    g.px(9, 3, "k")  # the bolt hole, small and high up
    g.outline()
    return g.rows()


def chalkpuff() -> list[str]:
    g = mk()
    for cx, cy, r in ((6, 10, 3.5), (12, 10, 3.5), (9, 8, 4.5), (9, 12, 4)):
        g.ell(cx, cy, r, r, "w")
    g.ell(9, 8, 3, 2, "h")
    g.px(7, 10, "k")
    g.px(11, 10, "k")
    g.rect(8, 12, 10, 12, "s")
    g.px(5, 14, "h")
    g.px(13, 14, "h")
    g.outline()
    return g.rows()


def wanderwisp() -> list[str]:
    g = mk()
    g.ell(9, 11, 5, 5, "v")
    g.ell(9, 6, 3, 4, "v")
    g.ell(9, 3, 1.5, 2, "v")
    g.rect(9, 1, 9, 2, "y")
    g.ell(9, 11, 3, 3, "p") if False else None
    g.ell(9, 9, 3.5, 3, "p")
    g.rect(7, 9, 8, 9, "y")
    g.rect(10, 9, 11, 9, "y")
    g.rect(6, 14, 7, 16, "v")
    g.rect(10, 14, 12, 16, "v")
    g.outline()
    return g.rows()


def starpebble() -> list[str]:
    g = mk()
    g.rect(7, 2, 10, 15, "y")
    g.rect(2, 7, 15, 10, "y")
    g.ell(9, 9, 5, 5, "y")
    g.ell(8, 8, 3, 3, "w")
    g.rect(6, 4, 7, 5, "o") if False else None
    g.px(7, 10, "k")
    g.px(11, 10, "k")
    g.rect(9, 12, 9, 12, "o")
    g.px(12, 5, "o")
    g.px(5, 13, "o")
    g.outline()
    return g.rows()


SPRITES = {
    **{f"slumbrock_{i}": slumbrock(i) for i in range(4)},
    "mossling": mossling(),
    "leafwing": leafwing(),
    "pebbit": pebbit(),
    "lampwick": lampwick(),
    "ripplet": ripplet(),
    "plateling": plateling(),
    "chalkpuff": chalkpuff(),
    "wanderwisp": wanderwisp(),
    "starpebble": starpebble(),
}


def preview(path: Path, scale: int = 10) -> None:
    from PIL import Image  # pillow ships with the model extra

    def rgb(h: str):
        return tuple(int(h[i : i + 2], 16) for i in (1, 3, 5))

    cell = 36 * scale
    cols = 4
    rows = (len(SPRITES) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), rgb("#566c86"))
    for i, rowsx in enumerate(SPRITES.values()):
        ox, oy = (i % cols) * cell, (i // cols) * cell
        for y, row in enumerate(rowsx):
            for x, ch in enumerate(row):
                if ch != ".":
                    for dy in range(scale):
                        for dx in range(scale):
                            sheet.putpixel(
                                (
                                    ox + x * scale + dx + scale,
                                    oy + y * scale + dy + scale,
                                ),
                                rgb(PALETTE[ch]),
                            )
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    for name, rows in SPRITES.items():
        widths = {len(r) for r in rows}
        assert len(widths) == 1, f"{name}: ragged rows {widths}"
        assert all(ch == "." or ch in PALETTE for r in rows for ch in r), f"{name}: unknown key"
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"palette": PALETTE, "sprites": SPRITES}, indent=1), encoding="utf-8"
    )
    print(f"wrote {len(SPRITES)} sprites to {OUT_JSON}")
    if args.preview:
        preview(OUT_PNG)
        print(f"wrote {OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
