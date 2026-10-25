"""Draw every sprite in code and write app/src/art/sprites.json (+ a preview sheet).

    python scripts/draw_sprites.py            # writes the JSON the app reads
    python scripts/draw_sprites.py --preview  # also writes results/sprites-preview.png

All art is original 2D pixel art built here from shaded shapes. Nothing is traced from or modelled on a
Nintendo / Pokémon sprite. Each sprite has animation frames:

    idle   a short loop (wings, flames, breathing)
    blink  eyes closed
    hit    eyes squeezed shut, used for a moment when it takes damage

A frame is a list of strings; '.' is transparent and every other character is a key into PALETTE.
Shading: shapes are lit like spheres or bevelled blocks by a light from the top left, quantised to a
four-tone ramp with a little ordered dithering, then outlined in the darkest tone of the neighbouring ramp.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

# ---------------------------------------------------------------- palette and ramps

PALETTE = {
    # stone (Slumbrock, Pebbit, Plateling)
    "a": "#141626", "b": "#262b44", "c": "#3a4466", "d": "#5a6988", "e": "#8b9bb4", "f": "#c0cbdc", "g": "#eef2f8",
    # moss and leaves
    "h": "#12331f", "i": "#1f5f3a", "j": "#2e9a4f", "k": "#63c74d", "l": "#a7f070", "m": "#e3ffb8",
    # water
    "n": "#0b1f4a", "o": "#1f3a8a", "p": "#2c6bd6", "q": "#41a6f6", "r": "#8fe3ff", "s": "#e2fbff",
    # warm light
    "t": "#3e1d12", "u": "#9a4a26", "v": "#ef7d57", "w": "#ffcd75", "x": "#fff1a8", "y": "#ffffff",
    # spirit
    "z": "#24102e", "A": "#5d275d", "B": "#9d4fc9", "C": "#c98bf2", "D": "#f2d6ff",
    # details
    "E": "#0d0d14",  # pupils
    "F": "#ff8fab",  # blush
    "G": "#b13e53",  # mouth
    "H": "#7a2d3c",  # mouth dark
    "I": "#73eff7",  # eye glow
    "J": "#d9fffd",  # eye glow core
    "K": "#ffd84d",  # flower
}  # fmt: skip

RAMPS = {
    "stone": ["b", "c", "d", "e", "f"],
    "moss": ["i", "j", "k", "l", "m"],
    "water": ["o", "p", "q", "r", "s"],
    "warm": ["u", "v", "w", "x", "y"],
    "spirit": ["A", "B", "C", "D", "D"],
    "puff": ["d", "e", "f", "g", "y"],
}
# outline colour for a pixel next to transparency, by the fill it borders
OUTLINE: dict[str, str] = {}
for _ramp, _out in (
    ("stone", "a"),
    ("moss", "h"),
    ("water", "n"),
    ("warm", "t"),
    ("spirit", "z"),
    ("puff", "c"),
):
    for _k in RAMPS[_ramp]:
        OUTLINE.setdefault(_k, _out)
for _k in "EFGHIJKghmsy":
    OUTLINE.setdefault(_k, "a")

_L = (-0.55, -0.7, 0.55)
_n = math.sqrt(sum(c * c for c in _L))
LIGHT = (_L[0] / _n, _L[1] / _n, _L[2] / _n)
BAYER = [[0.0, 0.5], [0.75, 0.25]]

OUT_JSON = Path("app/src/art/sprites.json")
OUT_PNG = Path("results/sprites-preview.png")


class Grid:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.p = [["."] * w for _ in range(h)]

    def px(self, x, y, c) -> None:
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = c

    def rect(self, x0, y0, x1, y1, c) -> None:
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.px(x, y, c)

    def shade(self, ramp: str, intensity: float, x: int, y: int) -> str:
        tones = RAMPS[ramp]
        i = intensity + (BAYER[y % 2][x % 2] - 0.375) * 0.18
        if i > 0.78:
            return tones[4]
        if i > 0.45:
            return tones[3]
        if i > 0.05:
            return tones[2]
        if i > -0.35:
            return tones[1]
        return tones[0]

    def ball(self, cx, cy, rx, ry, ramp) -> None:
        """An ellipse lit like a sphere."""
        for y in range(self.h):
            for x in range(self.w):
                nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                d2 = nx * nx + ny * ny
                if d2 <= 1.0:
                    nz = math.sqrt(max(0.0, 1.0 - d2))
                    it = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]
                    self.p[y][x] = self.shade(ramp, it, x, y)

    def block(self, x0, y0, x1, y1, ramp, bevel: int = 2) -> None:
        """A bevelled stone block: lit top and left faces, shadowed bottom and right."""
        tones = RAMPS[ramp]
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                top, left = y - y0, x - x0
                bottom, right = y1 - y, x1 - x
                if top < bevel and top <= right:
                    c = tones[4] if top == 0 else tones[3]
                elif left < bevel and left <= bottom:
                    c = tones[3]
                elif bottom < bevel:
                    c = tones[0] if bottom == 0 else tones[1]
                elif right < bevel:
                    c = tones[1]
                else:
                    c = tones[2] if (x * 7 + y * 13) % 11 else tones[1]  # a little grit
                self.px(x, y, c)

    def poly(self, pts, ramp) -> None:
        """A filled polygon, lit brighter towards the top left and the centre (gems, flames)."""
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        span = max(math.hypot(px - cx, py - cy) for px, py in pts)
        for y in range(self.h):
            for x in range(self.w):
                if _inside(x + 0.5, y + 0.5, pts):
                    dx, dy = (x + 0.5 - cx) / span, (y + 0.5 - cy) / span
                    it = 0.7 + (dx * LIGHT[0] + dy * LIGHT[1]) * 0.8 - 0.45 * math.hypot(dx, dy)
                    self.p[y][x] = self.shade(ramp, it, x, y)

    def outline(self) -> None:
        src = [row[:] for row in self.p]
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x] != ".":
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and src[ny][nx] != ".":
                        self.p[y][x] = OUTLINE.get(src[ny][nx], "a")
                        break

    def rows(self) -> list[str]:
        return ["".join(r) for r in self.p]


def _inside(x, y, pts) -> bool:
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            inside = not inside
        j = i
    return inside


# ---------------------------------------------------------------- faces


def eyes(g: Grid, xl: int, xr: int, y: int, state: str, size: int = 3) -> None:
    """Two eyes. state: idle (open), blink, hit."""
    for x0 in (xl, xr):
        if state == "blink":
            g.rect(x0, y + size - 2, x0 + size - 1, y + size - 2, "E")
        elif state == "hit":
            g.px(x0, y, "E")
            g.px(x0 + size - 1, y, "E")
            g.rect(x0, y + 1, x0 + size - 1, y + 1, "E")
        else:
            g.rect(x0, y, x0 + size - 1, y + size - 1, "E")
            g.px(x0, y, "y")
            if size >= 3:
                g.px(x0 + 1, y, "y")


def blush(g: Grid, xl: int, xr: int, y: int) -> None:
    for x0 in (xl, xr):
        g.rect(x0, y, x0 + 1, y, "F")


def smile(g: Grid, x0: int, y: int, w: int = 3, open_: bool = False) -> None:
    if open_:
        g.rect(x0, y, x0 + w - 1, y + 1, "G")
        g.rect(x0 + 1, y + 1, x0 + w - 2, y + 1, "H")
    else:
        g.px(x0, y, "E")
        g.rect(x0 + 1, y + 1, x0 + w - 2, y + 1, "E")
        g.px(x0 + w - 1, y, "E")


# ---------------------------------------------------------------- Slumbrock (48 x 48, plus margin)


def slumbrock(stage: int, frame: int = 0, face: str = "idle") -> list[str]:
    """Stage 0 asleep, 1 drowsy, 2 awake, 3 roaring. frame 0/1 is the breath; face idle/blink/hit/yawn."""
    g = Grid(50, 50)
    o = 1
    up = frame % 2  # the upper body sinks a pixel on the out-breath
    sink = {0: 5, 1: 2, 2: 0, 3: -1}[stage]  # how far the head hangs

    def B(x0, y0, x1, y1, bevel=2, dy=0):
        g.block(x0 + o, y0 + o + dy, x1 + o, y1 + o + dy, "stone", bevel)

    def R(x0, y0, x1, y1, c, dy=0):
        g.rect(x0 + o, y0 + o + dy, x1 + o, y1 + o + dy, c)

    def P(x, y, c, dy=0):
        g.px(x + o, y + o + dy, c)

    # legs and feet stay planted
    B(12, 37, 21, 45)
    B(26, 37, 35, 45)
    R(11, 45, 22, 47, "b")
    R(25, 45, 36, 47, "b")
    R(12, 45, 21, 45, "c")
    R(26, 45, 35, 45, "c")
    # torso
    B(11, 26, 36, 38, dy=up)
    # arms
    if stage == 3 and face != "hit":
        lift = frame % 2
        B(0, 8 - lift, 7, 24)
        B(40, 8 - lift, 47, 24)
        B(-1, 2 - lift, 8, 9)
        B(39, 2 - lift, 48, 9)
    else:
        B(1, 21, 8, 35, dy=up)
        B(39, 21, 46, 35, dy=up)
        B(0, 34, 9, 41, dy=up)
        B(38, 34, 47, 41, dy=up)
    # shoulders
    B(5, 19, 42, 27, bevel=3, dy=up)
    # the rune in the chest: dark asleep, ember drowsy, bright awake, white-hot roaring
    rune = {0: ("c", "d"), 1: ("u", "v"), 2: ("v", "w"), 3: ("w", "y")}[stage]
    for yy, (a, b_) in enumerate(((22, 25), (21, 26), (21, 26), (22, 25))):
        R(a, 29 + yy, b_, 29 + yy, rune[0], dy=up)
    R(23, 30, 24, 31, rune[1], dy=up)
    # cracks
    for x, y in ((15, 29), (16, 30), (16, 31), (31, 33), (32, 34), (9, 23), (10, 24), (37, 22)):
        P(x, y, "b", dy=up)
    # head
    hy = sink + up
    B(13, 4, 34, 18, bevel=3, dy=hy)
    B(10, 1, 15, 7, dy=hy)  # horn stones
    B(32, 1, 37, 7, dy=hy)
    R(14, 9, 33, 10, "b", dy=hy)  # the heavy brow
    R(14, 8, 33, 8, "c", dy=hy)
    # eyes
    if stage == 0 or face == "blink":
        R(17, 13, 20, 13, "a", dy=hy)
        R(27, 13, 30, 13, "a", dy=hy)
    elif face == "hit":
        for x0 in (17, 27):
            P(x0, 12, "a", dy=hy)
            P(x0 + 1, 13, "a", dy=hy)
            P(x0 + 2, 13, "a", dy=hy)
            P(x0 + 3, 12, "a", dy=hy)
    elif stage == 1:
        R(17, 12, 20, 12, "b", dy=hy)
        R(27, 12, 30, 12, "b", dy=hy)
        R(17, 13, 20, 13, "I", dy=hy)
        R(27, 13, 30, 13, "I", dy=hy)
    else:
        R(17, 12, 20, 13, "I", dy=hy)
        R(27, 12, 30, 13, "I", dy=hy)
        R(18, 12, 19, 12, "J", dy=hy)
        R(28, 12, 29, 12, "J", dy=hy)
    # mouth
    if stage == 3 or face == "yawn":
        R(19, 15, 28, 17, "H", dy=hy)
        R(20, 15, 27, 16, "G", dy=hy)
        for x in (20, 23, 26):
            P(x, 15, "g", dy=hy)
    else:
        R(20, 16, 27, 16, "b", dy=hy)
    # moss on the head and shoulders; it thins as he wakes, and flowers open once he is awake
    for x, y in ((21, 0), (22, -1), (23, 0), (24, -2), (25, 0), (26, -1), (20, 1), (27, 1)):
        P(x, y + 3, "k", dy=hy)
        P(x, y + 4, "j", dy=hy)
    R(18, 3, 29, 4, "j", dy=hy)
    R(19, 3, 28, 3, "k", dy=hy)
    moss = [(6, 19, 12), (31, 19, 9), (16, 19, 5)]
    if stage <= 1:
        moss += [(14, 26, 6), (27, 26, 5), (2, 21, 4), (40, 21, 4), (13, 4, 6)]
    for x0, y0, n in moss:
        for i in range(n):
            P(x0 + i, y0, "k" if i % 3 else "l", dy=up)
            if i % 2 == 0:
                P(x0 + i, y0 + 1, "j", dy=up)
    if stage >= 2:
        for x, y in ((8, 18), (34, 18), (24, 1)):
            dy = hy if y < 5 else up
            P(x, y, "K", dy=dy)
            P(x - 1, y + 1, "K", dy=dy)
            P(x + 1, y + 1, "K", dy=dy)
            P(x, y + 1, "v", dy=dy)
    g.outline()
    return g.rows()


# ---------------------------------------------------------------- wild creatures (32 x 32, plus margin)


def canvas() -> Grid:
    return Grid(34, 34)


def mossling(frame: int, face: str) -> list[str]:
    g = canvas()
    tilt = [-1, 0, 1, 0][frame % 4]
    g.rect(16, 6, 17, 10, "i")  # stem
    g.ball(12 + tilt, 6, 5, 3, "moss")  # leaves
    g.ball(22 + tilt, 5, 4, 2.5, "moss")
    g.ball(17, 20, 13, 11, "moss")
    for x, y in ((10, 24), (23, 26), (14, 28), (25, 18)):
        g.px(x, y, "i")
    g.ball(11, 31, 3, 1.6, "moss")
    g.ball(23, 31, 3, 1.6, "moss")
    g.outline()
    eyes(g, 11, 20, 17, face, 3)
    blush(g, 9, 24, 21)
    smile(g, 15, 22, 4, open_=face == "hit")
    return g.rows()


def leafwing(frame: int, face: str) -> list[str]:
    g = canvas()
    flap = [0, -3, -5, -3][frame % 4]
    g.ball(6, 16 + flap, 6, 3, "moss")
    g.ball(28, 16 + flap, 6, 3, "moss")
    g.ball(17, 28, 3, 2, "moss")  # tail leaf
    g.ball(17, 18, 8, 9, "moss")
    g.ball(17, 21, 5, 5, "warm")  # warm belly
    g.rect(16, 15, 18, 16, "v")  # beak
    g.px(17, 17, "u")
    g.rect(14, 26, 14, 29, "u")
    g.rect(20, 26, 20, 29, "u")
    g.outline()
    eyes(g, 12, 20, 11, face, 2)
    return g.rows()


def pebbit(frame: int, face: str) -> list[str]:
    g = canvas()
    twitch = frame % 4 == 2
    g.ball(11, 7 if twitch else 6, 2.6, 6, "stone")  # ears
    g.ball(23, 6, 2.6, 6, "stone")
    g.rect(11, 3, 11, 8, "F")
    g.rect(23, 3, 23, 8, "F")
    g.ball(17, 24, 11, 8, "stone")
    g.ball(17, 15, 9, 7.5, "stone")
    g.ball(8, 29, 3, 2, "stone")
    g.ball(26, 29, 3, 2, "stone")
    for x, y in ((24, 22), (25, 23), (9, 20)):
        g.px(x, y, "c")
    g.outline()
    eyes(g, 12, 20, 13, face, 3)
    g.rect(16, 17, 18, 17, "F")
    g.px(17, 18, "E")
    blush(g, 10, 23, 18)
    return g.rows()


def lampwick(frame: int, face: str) -> list[str]:
    g = canvas()
    glow = frame % 2
    g.rect(15, 18, 19, 29, "c")
    g.rect(15, 18, 15, 29, "d")
    g.ball(17, 31, 7, 2.2, "stone")
    g.rect(9, 21, 14, 22, "c")  # arms
    g.rect(20, 21, 25, 22, "c")
    g.ball(17, 11, 9, 9, "warm")
    g.ball(15 + glow, 9, 4 + glow, 4 + glow, "warm")
    g.rect(9, 2, 25, 3, "b")  # the little cap
    g.rect(13, 0, 21, 1, "b")
    g.outline()
    eyes(g, 12, 19, 10, face, 3)
    smile(g, 15, 15, 4, open_=face == "hit")
    return g.rows()


def ripplet(frame: int, face: str) -> list[str]:
    g = canvas()
    sway = [0, 1, 0, -1][frame % 4]
    g.ball(17, 21, 12, 10, "water")
    g.poly([(17 + sway * 2, 3), (25, 15), (9, 15)], "water")
    g.ball(12, 17, 3, 4, "water")
    g.outline()
    g.px(11, 15, "s")
    g.px(11, 16, "s")
    g.px(12, 14, "s")
    eyes(g, 12, 20, 19, face, 3)
    blush(g, 9, 24, 23)
    smile(g, 15, 24, 4, open_=face == "hit")
    return g.rows()


def plateling(frame: int, face: str) -> list[str]:
    g = canvas()
    lift = [0, -2, -4, -2][frame % 4]
    # the tiny barbell it lifts above its head
    g.rect(7, 4 + lift, 27, 5 + lift, "e")
    g.rect(5, 2 + lift, 7, 7 + lift, "c")
    g.rect(27, 2 + lift, 29, 7 + lift, "c")
    g.rect(6, 6 + lift, 8, 12, "d")  # arms
    g.rect(26, 6 + lift, 28, 12, "d")
    g.ball(17, 20, 13, 12, "stone")
    g.ball(17, 20, 9, 8.5, "stone")
    g.outline()
    shine = [9, 11, 13, 11][frame % 4]
    g.rect(shine, 12, shine + 1, 13, "g")
    eyes(g, 12, 20, 17, face, 3)
    smile(g, 15, 23, 4, open_=face == "hit")
    g.px(17, 27, "b")
    return g.rows()


def chalkpuff(frame: int, face: str) -> list[str]:
    g = canvas()
    puff = [0, 1, 0, -1][frame % 4]
    for cx, cy, r in (
        (9, 20, 7),
        (25, 20, 7),
        (17, 14 - puff, 9),
        (17, 23, 9),
        (12, 12, 5),
        (23, 12 + puff, 5),
    ):
        g.ball(cx, cy, r, r * 0.9, "puff")
    g.outline()
    eyes(g, 12, 20, 17, face, 3)
    blush(g, 9, 24, 21)
    smile(g, 15, 22, 4, open_=face == "hit")
    return g.rows()


def wanderwisp(frame: int, face: str) -> list[str]:
    g = canvas()
    s = [0, 2, 0, -2][frame % 4]
    g.poly([(17 + s, 1), (25, 16), (27, 24), (17, 31), (7, 24), (9, 16)], "spirit")
    g.poly([(17 - s, 9), (22, 18), (22, 25), (17, 29), (12, 25), (12, 18)], "warm")
    g.ball(10 + s // 2, 6, 2, 3, "spirit")
    g.ball(25 - s // 2, 9, 1.6, 2.4, "spirit")
    g.outline()
    for x0 in (13, 19):
        if face == "blink":
            g.rect(x0, 20, x0 + 2, 20, "z")
        elif face == "hit":
            g.rect(x0, 20, x0 + 2, 20, "E")
            g.px(x0 + 1, 19, "E")
        else:
            g.rect(x0, 19, x0 + 2, 20, "I")
            g.px(x0 + 1, 19, "J")
    return g.rows()


def starpebble(frame: int, face: str) -> list[str]:
    g = canvas()
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 15.5 if i % 2 == 0 else 7
        pts.append((17 + r * math.cos(a), 18 + r * math.sin(a)))
    g.poly(pts, "warm")
    g.outline()
    tw = frame % 4
    for i, (x, y) in enumerate(((17, 1), (32, 13), (3, 13))):
        if tw == i:
            g.px(x, y, "y")
            g.px(x - 1, y, "x")
            g.px(x + 1, y, "x")
    eyes(g, 12, 20, 16, face, 3)
    blush(g, 10, 24, 21)
    smile(g, 15, 21, 4, open_=face == "hit")
    return g.rows()


CREATURES = {
    "mossling": mossling,
    "leafwing": leafwing,
    "pebbit": pebbit,
    "lampwick": lampwick,
    "ripplet": ripplet,
    "plateling": plateling,
    "chalkpuff": chalkpuff,
    "wanderwisp": wanderwisp,
    "starpebble": starpebble,
}


def build() -> dict:
    sprites: dict[str, dict] = {}
    for stage in range(4):
        sprites[f"slumbrock_{stage}"] = {
            "idle": [slumbrock(stage, f) for f in range(2)],
            "blink": slumbrock(stage, 0, "blink"),
            "hit": slumbrock(stage, 0, "hit"),
            "yawn": slumbrock(stage, 0, "yawn"),
            "fps": 1.6 if stage < 3 else 4,
        }
    for name, fn in CREATURES.items():
        sprites[name] = {
            "idle": [fn(f, "idle") for f in range(4)],
            "blink": fn(0, "blink"),
            "hit": fn(0, "hit"),
            "fps": 6 if name in ("leafwing", "wanderwisp", "plateling") else 4,
        }
    return sprites


def frames_of(sprite: dict) -> list[list[str]]:
    extra = [sprite["yawn"]] if "yawn" in sprite else []
    return [*sprite["idle"], sprite["blink"], sprite["hit"], *extra]


def preview(sprites: dict, path: Path, scale: int = 6) -> None:
    from PIL import Image

    def rgb(h: str):
        return tuple(int(h[i : i + 2], 16) for i in (1, 3, 5))

    rows = list(sprites.items())
    cell = 52 * scale
    width = max(len(frames_of(s)) for _, s in rows) * cell
    sheet = Image.new("RGB", (width, len(rows) * cell), rgb("#262b44"))
    for r, (_, sprite) in enumerate(rows):
        for c, frame in enumerate(frames_of(sprite)):
            for y, line in enumerate(frame):
                for x, ch in enumerate(line):
                    if ch == ".":
                        continue
                    colour = rgb(PALETTE[ch])
                    for dy in range(scale):
                        for dx in range(scale):
                            sheet.putpixel(
                                (
                                    c * cell + x * scale + dx + scale,
                                    r * cell + y * scale + dy + scale,
                                ),
                                colour,
                            )
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    sprites = build()
    for name, sprite in sprites.items():
        for frame in frames_of(sprite):
            widths = {len(r) for r in frame}
            assert len(widths) == 1, f"{name}: ragged rows {widths}"
            assert all(ch == "." or ch in PALETTE for r in frame for ch in r), (
                f"{name}: unknown key"
            )
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"palette": PALETTE, "sprites": sprites}), encoding="utf-8")
    print(f"wrote {len(sprites)} sprites to {OUT_JSON}")
    if args.preview:
        preview(sprites, OUT_PNG)
        print(f"wrote {OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
