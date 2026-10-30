"""Рисует картинки-баннеры для бота. Нужна библиотека Pillow: pkg install python-pillow.
Если Pillow нет, бот просто работает без картинок."""
import math
import os
import random

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None

CACHE = "pics_cache"
W, H = 720, 360
FONTS = [
    "/system/fonts/Roboto-Bold.ttf", "/system/fonts/Roboto-Regular.ttf",
    "/system/fonts/NotoSans-Bold.ttf", "/system/fonts/NotoSans-Regular.ttf",
    "/system/fonts/DroidSans-Bold.ttf", "/system/fonts/DroidSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]
TITLES = {
    "start": "ДОБРО ПОЖАЛОВАТЬ", "help": "ПОМОЩЬ", "stats": "СТАТИСТИКА", "shop": "МАГАЗИН",
    "battle": "БИТВА", "win": "ПОБЕДА!", "lose": "ПОРАЖЕНИЕ", "guess": "УГАДАЙ ЧИСЛО",
    "tod": "ПРАВДА ИЛИ ДЕЙСТВИЕ", "duo": "ИГРА С ДРУГОМ", "menu": "МЕНЮ",
    "boss": "БОСС", "goblin": "ГОБЛИН", "skeleton": "СКЕЛЕТ", "ogre": "ОГР", "wolf": "ВОЛК",
    "win_guess": "ВЕРНО!", "win_duo": "ПОБЕДА В ДУЭЛИ", "leave": "ДО ВСТРЕЧИ",
}
THEMES = {
    "start": ((88, 52, 200), (30, 20, 90)), "help": ((30, 110, 200), (15, 30, 90)),
    "stats": ((20, 150, 130), (10, 50, 70)), "shop": ((230, 150, 30), (120, 50, 20)),
    "battle": ((200, 40, 50), (60, 10, 30)), "win": ((240, 180, 40), (150, 60, 20)),
    "lose": ((90, 90, 110), (20, 20, 35)), "guess": ((60, 160, 90), (15, 60, 50)),
    "tod": ((200, 60, 160), (70, 20, 100)), "duo": ((40, 130, 220), (60, 40, 150)),
    "menu": ((100, 100, 200), (30, 30, 80)),
    "boss": ((170, 30, 40), (40, 5, 15)), "goblin": ((80, 160, 60), (15, 50, 25)),
    "skeleton": ((60, 90, 110), (10, 20, 35)), "ogre": ((140, 110, 50), (50, 30, 15)),
    "wolf": ((90, 100, 130), (20, 25, 45)), "win_guess": ((70, 180, 110), (20, 70, 60)),
    "win_duo": ((60, 140, 230), (130, 60, 190)), "leave": ((120, 110, 140), (35, 30, 55)),
}


def _rot(pts, ang, cx, cy):
    a = math.radians(ang)
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def _sword(d, cx, cy, ang):
    parts = [
        ([(cx - 10, cy - 110), (cx + 10, cy - 110), (cx + 10, cy + 20), (cx - 10, cy + 20)], (226, 233, 246)),
        ([(cx - 10, cy - 110), (cx + 10, cy - 110), (cx, cy - 140)], (226, 233, 246)),
        ([(cx - 36, cy + 20), (cx + 36, cy + 20), (cx + 36, cy + 34), (cx - 36, cy + 34)], (245, 196, 64)),
        ([(cx - 7, cy + 34), (cx + 7, cy + 34), (cx + 7, cy + 78), (cx - 7, cy + 78)], (140, 84, 48)),
    ]
    for pts, col in parts:
        d.polygon(_rot(pts, ang, cx, cy), fill=col, outline=(40, 40, 60))


def _swords(d, cx, cy):
    _sword(d, cx, cy + 10, 40)
    _sword(d, cx, cy + 10, -40)


def _star(d, cx, cy, r, fill=(255, 214, 64)):
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.45
        a = math.radians(-90 + i * 36)
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    d.polygon(pts, fill=fill, outline=(120, 80, 10))


def _shield(d, cx, cy):
    d.polygon([(cx - 70, cy - 80), (cx + 70, cy - 80), (cx + 70, cy + 10), (cx, cy + 90), (cx - 70, cy + 10)],
              fill=(60, 100, 220), outline=(230, 230, 255))
    d.polygon([(cx - 52, cy - 62), (cx + 52, cy - 62), (cx + 52, cy + 4), (cx, cy + 68), (cx - 52, cy + 4)],
              fill=(210, 50, 70))
    _star(d, cx, cy - 8, 34)


def _book(d, cx, cy):
    d.rounded_rectangle((cx - 100, cy - 75, cx + 100, cy + 75), 14, fill=(60, 100, 220), outline=(220, 230, 255), width=3)
    d.rounded_rectangle((cx - 86, cy - 62, cx + 86, cy + 62), 8, fill=(245, 245, 250))
    d.line((cx, cy - 62, cx, cy + 62), fill=(150, 150, 170), width=3)
    for i in range(4):
        y = cy - 38 + i * 26
        d.line((cx - 72, y, cx - 14, y), fill=(120, 130, 190), width=5)
        d.line((cx + 14, y, cx + 72, y), fill=(120, 130, 190), width=5)


def _bars(d, cx, cy):
    cols = [(255, 120, 90), (255, 200, 70), (90, 220, 150)]
    for i, hgt in enumerate((60, 100, 145)):
        x = cx - 90 + i * 66
        d.rounded_rectangle((x, cy + 75 - hgt, x + 48, cy + 75), 8, fill=cols[i], outline=(255, 255, 255), width=2)
    d.line((cx - 105, cy + 78, cx + 105, cy + 78), fill=(255, 255, 255), width=4)


def _coin(d, cx, cy, r):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(250, 200, 50), outline=(130, 85, 10), width=4)
    d.ellipse((cx - r * 0.65, cy - r * 0.65, cx + r * 0.65, cy + r * 0.65), fill=(255, 225, 110), outline=(200, 140, 20), width=3)
    _star(d, cx, cy, r * 0.4, fill=(235, 170, 30))


def _coins(d, cx, cy):
    _coin(d, cx - 80, cy + 40, 52)
    _coin(d, cx + 80, cy + 40, 52)
    _coin(d, cx, cy - 20, 66)


def _skull(d, cx, cy):
    d.ellipse((cx - 62, cy - 85, cx + 62, cy + 30), fill=(235, 235, 240), outline=(30, 30, 40), width=3)
    d.rounded_rectangle((cx - 36, cy + 5, cx + 36, cy + 62), 10, fill=(235, 235, 240), outline=(30, 30, 40), width=3)
    d.ellipse((cx - 42, cy - 40, cx - 10, cy - 6), fill=(25, 25, 35))
    d.ellipse((cx + 10, cy - 40, cx + 42, cy - 6), fill=(25, 25, 35))
    d.polygon([(cx, cy - 2), (cx - 9, cy + 16), (cx + 9, cy + 16)], fill=(25, 25, 35))
    for i in range(-2, 3):
        d.line((cx + i * 14, cy + 34, cx + i * 14, cy + 60), fill=(30, 30, 40), width=3)


def _dice(d, cx, cy):
    d.rounded_rectangle((cx - 75, cy - 75, cx + 75, cy + 75), 24, fill=(250, 250, 255), outline=(30, 40, 60), width=4)
    for dx, dy in ((-40, -40), (40, -40), (0, 0), (-40, 40), (40, 40)):
        d.ellipse((cx + dx - 14, cy + dy - 14, cx + dx + 14, cy + dy + 14), fill=(210, 40, 60))


def _mask(d, cx, cy):
    d.ellipse((cx - 70, cy - 90, cx + 70, cy + 80), fill=(250, 210, 80), outline=(120, 70, 10), width=4)
    d.polygon([(cx - 50, cy - 35), (cx - 12, cy - 25), (cx - 50, cy - 5)], fill=(40, 20, 40))
    d.polygon([(cx + 50, cy - 35), (cx + 12, cy - 25), (cx + 50, cy - 5)], fill=(40, 20, 40))
    d.arc((cx - 40, cy - 5, cx + 40, cy + 55), 20, 160, fill=(40, 20, 40), width=7)


def _person(d, cx, cy, s=1.0, col=(240, 240, 255)):
    d.ellipse((cx - 38 * s, cy - 95 * s, cx + 38 * s, cy - 19 * s), fill=col, outline=(30, 30, 60), width=3)
    d.pieslice((cx - 75 * s, cy - 5 * s, cx + 75 * s, cy + 140 * s), 180, 360, fill=col, outline=(30, 30, 60), width=3)


def _duo(d, cx, cy):
    _person(d, cx - 75, cy + 5, 0.8, (255, 200, 120))
    _person(d, cx + 75, cy + 5, 0.8, (150, 220, 255))
    _star(d, cx, cy - 40, 24)


def _house(d, cx, cy):
    d.polygon([(cx - 95, cy - 5), (cx, cy - 85), (cx + 95, cy - 5)], fill=(210, 60, 70), outline=(40, 20, 30))
    d.rectangle((cx - 72, cy - 5, cx + 72, cy + 75), fill=(250, 235, 200), outline=(40, 20, 30), width=3)
    d.rectangle((cx - 16, cy + 20, cx + 16, cy + 75), fill=(120, 70, 40))


def _confetti(d):
    rnd = random.Random(7)
    cols = [(255, 90, 90), (255, 210, 70), (90, 220, 150), (90, 170, 255), (230, 120, 255)]
    for _ in range(34):
        x, y, r = rnd.randint(10, W - 10), rnd.randint(8, 250), rnd.randint(4, 8)
        d.ellipse((x - r, y - r, x + r, y + r), fill=rnd.choice(cols))


def _win(d, cx, cy):
    _confetti(d)
    _star(d, cx, cy, 95)


def _win_guess(d, cx, cy):
    _confetti(d)
    _dice(d, cx - 15, cy + 15)
    _star(d, cx + 85, cy - 70, 42)


def _win_duo(d, cx, cy):
    _confetti(d)
    _person(d, cx - 60, cy + 15, 0.9, (255, 200, 120))
    _person(d, cx + 85, cy + 35, 0.6, (150, 220, 255))
    _star(d, cx - 60, cy - 90, 30)


def _boss(d, cx, cy):
    d.polygon([(cx - 62, cy - 55), (cx - 92, cy - 140), (cx - 20, cy - 78)], fill=(245, 235, 205), outline=(40, 20, 20))
    d.polygon([(cx + 62, cy - 55), (cx + 92, cy - 140), (cx + 20, cy - 78)], fill=(245, 235, 205), outline=(40, 20, 20))
    d.ellipse((cx - 78, cy - 80, cx + 78, cy + 70), fill=(205, 40, 50), outline=(50, 10, 15), width=4)
    d.polygon([(cx - 55, cy - 30), (cx - 12, cy - 15), (cx - 50, cy + 2)], fill=(255, 225, 60))
    d.polygon([(cx + 55, cy - 30), (cx + 12, cy - 15), (cx + 50, cy + 2)], fill=(255, 225, 60))
    d.rounded_rectangle((cx - 42, cy + 20, cx + 42, cy + 52), 8, fill=(40, 10, 20))
    for i in (-30, -10, 10, 30):
        d.polygon([(cx + i - 7, cy + 20), (cx + i + 7, cy + 20), (cx + i, cy + 38)], fill=(250, 250, 250))


def _goblin(d, cx, cy):
    g = (120, 195, 85)
    d.polygon([(cx - 60, cy - 30), (cx - 128, cy - 70), (cx - 62, cy + 15)], fill=g, outline=(30, 70, 25))
    d.polygon([(cx + 60, cy - 30), (cx + 128, cy - 70), (cx + 62, cy + 15)], fill=g, outline=(30, 70, 25))
    d.ellipse((cx - 70, cy - 80, cx + 70, cy + 72), fill=g, outline=(30, 70, 25), width=4)
    for sx in (-1, 1):
        d.ellipse((cx + sx * 30 - 14, cy - 35, cx + sx * 30 + 14, cy - 5), fill=(255, 240, 120), outline=(30, 70, 25))
        d.ellipse((cx + sx * 30 - 5, cy - 28, cx + sx * 30 + 5, cy - 12), fill=(20, 20, 20))
    d.polygon([(cx, cy - 8), (cx - 10, cy + 18), (cx + 10, cy + 18)], fill=(90, 160, 65))
    d.arc((cx - 38, cy + 8, cx + 38, cy + 58), 15, 165, fill=(30, 40, 20), width=6)


def _bones(d, cx, cy):
    for sgn in (-1, 1):
        x1, y1, x2, y2 = cx - 70 * sgn, cy + 55, cx + 70 * sgn, cy + 110
        d.line((x1, y1, x2, y2), fill=(240, 240, 235), width=12)
        for x, y in ((x1, y1), (x2, y2)):
            d.ellipse((x - 12, y - 14, x + 12, y + 2), fill=(240, 240, 235))
            d.ellipse((x - 12, y - 2, x + 12, y + 14), fill=(240, 240, 235))


def _skeleton(d, cx, cy):
    _bones(d, cx, cy - 20)
    _skull(d, cx, cy - 25)


def _ogre(d, cx, cy):
    c = (160, 150, 80)
    d.ellipse((cx - 90, cy - 85, cx + 90, cy + 75), fill=c, outline=(60, 50, 20), width=4)
    d.rectangle((cx - 66, cy - 42, cx + 66, cy - 22), fill=(110, 100, 50))
    for sx in (-1, 1):
        d.ellipse((cx + sx * 32 - 11, cy - 20, cx + sx * 32 + 11, cy + 2), fill=(255, 250, 220))
        d.ellipse((cx + sx * 32 - 4, cy - 16, cx + sx * 32 + 4, cy - 4), fill=(30, 20, 10))
    d.ellipse((cx - 18, cy + 2, cx + 18, cy + 28), fill=(135, 125, 65))
    d.rounded_rectangle((cx - 55, cy + 32, cx + 55, cy + 62), 10, fill=(50, 20, 20))
    for sx in (-1, 1):
        d.polygon([(cx + sx * 40 - 10, cy + 35), (cx + sx * 40 + 10, cy + 35), (cx + sx * 46, cy - 5)], fill=(250, 250, 240), outline=(80, 70, 40))


def _wolf(d, cx, cy):
    c = (165, 170, 190)
    d.polygon([(cx - 78, cy - 20), (cx - 62, cy - 120), (cx - 15, cy - 60)], fill=c, outline=(40, 40, 60))
    d.polygon([(cx + 78, cy - 20), (cx + 62, cy - 120), (cx + 15, cy - 60)], fill=c, outline=(40, 40, 60))
    d.polygon([(cx - 80, cy - 40), (cx + 80, cy - 40), (cx + 55, cy + 40), (cx, cy + 80), (cx - 55, cy + 40)], fill=c, outline=(40, 40, 60))
    d.polygon([(cx - 30, cy + 10), (cx + 30, cy + 10), (cx + 20, cy + 62), (cx - 20, cy + 62)], fill=(215, 218, 230))
    d.ellipse((cx - 14, cy + 6, cx + 14, cy + 26), fill=(25, 25, 35))
    for sx in (-1, 1):
        d.polygon([(cx + sx * 55, cy - 20), (cx + sx * 15, cy - 8), (cx + sx * 50, cy + 5)], fill=(255, 215, 60))
        d.ellipse((cx + sx * 36 - 4, cy - 14, cx + sx * 36 + 4, cy - 4), fill=(20, 20, 20))


def _leave(d, cx, cy):
    d.rounded_rectangle((cx - 110, cy - 85, cx - 10, cy + 80), 8, fill=(130, 80, 45), outline=(50, 30, 15), width=4)
    d.ellipse((cx - 38, cy - 5, cx - 22, cy + 11), fill=(250, 200, 60))
    d.polygon([(cx + 20, cy - 25), (cx + 80, cy - 25), (cx + 80, cy - 55), (cx + 130, cy), (cx + 80, cy + 55), (cx + 80, cy + 25), (cx + 20, cy + 25)],
              fill=(250, 250, 255), outline=(40, 40, 70))


ICONS = {
    "start": _shield, "help": _book, "stats": _bars, "shop": _coins, "battle": _swords,
    "win": _win, "lose": _skull, "guess": _dice,
    "tod": _mask, "duo": _duo, "menu": _house,
    "boss": _boss, "goblin": _goblin, "skeleton": _skeleton, "ogre": _ogre, "wolf": _wolf,
    "win_guess": _win_guess, "win_duo": _win_duo, "leave": _leave,
}


def _font(size):
    for path in FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return None


def _draw(kind):
    c1, c2 = THEMES[kind]
    img = Image.new("RGB", (W, H), c1)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line((0, y, W, y), fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    ICONS[kind](d, W // 2, 145)
    size = 46
    font = _font(size)
    if font:
        text = TITLES[kind]
        while size > 20 and d.textbbox((0, 0), text, font=font)[2] > W - 60:
            size -= 4
            font = _font(size)
        w = d.textbbox((0, 0), text, font=font)[2]
        x, y = (W - w) // 2, 292
        d.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0))
        d.text((x, y), text, font=font, fill=(255, 255, 255))
    return img


def get_pic(kind):
    """Путь к картинке (создаёт при первом обращении) или None, если рисовать нечем."""
    if Image is None or kind not in ICONS:
        return None
    path = os.path.join(CACHE, f"{kind}.png")
    if os.path.exists(path):
        return path
    try:
        os.makedirs(CACHE, exist_ok=True)
        _draw(kind).save(path)
        return path
    except Exception:
        return None
