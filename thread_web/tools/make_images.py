"""ThRead 사이트 그래픽 생성기 (저작권 걱정 없이 직접 만든 이미지)

히어로 배경, 장르 타일, 쓰레드 대표 이미지, 카카오에 표지가 없는 책의 기본 표지를
그라데이션 + 흐린 색 덩어리 + '실(thread)' 곡선으로 그려 WebP 로 저장한다.

사용법 (thread_web 폴더에서):  pip install pillow 후  python tools/make_images.py
(Pillow 는 이미지를 만들 때만 필요해서 requirements.txt 에는 넣지 않았다)
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
FONT_BOLD = STATIC / "fonts" / "GmarketSansTTFBold.ttf"
FONT_MEDIUM = STATIC / "fonts" / "GmarketSansTTFMedium.ttf"
POINT = (254, 74, 81)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def gradient(size, top_left, bottom_right):
    """대각선 그라데이션"""
    w, h = size
    small = Image.new("RGB", (2, 2))
    small.putpixel((0, 0), top_left)
    small.putpixel((1, 1), bottom_right)
    mid = tuple((a + b) // 2 for a, b in zip(top_left, bottom_right))
    small.putpixel((1, 0), mid)
    small.putpixel((0, 1), mid)
    return small.resize((w, h), Image.BICUBIC)


def blobs(img, colors, seed, count=5, alpha=150):
    """흐린 색 덩어리를 얹어 메시 그라데이션처럼 보이게 한다"""
    rnd = random.Random(seed)
    w, h = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(count):
        r = rnd.uniform(0.25, 0.5) * max(w, h)
        cx, cy = rnd.uniform(-0.1, 1.1) * w, rnd.uniform(-0.1, 1.1) * h
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*colors[i % len(colors)], alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(max(w, h) * 0.12))
    return Image.alpha_composite(img.convert("RGBA"), layer)


def threads(img, color, seed, lines=3, width_ratio=0.004, alpha=110):
    """서비스 이름(ThRead)의 '실'을 표현하는 부드러운 곡선"""
    rnd = random.Random(seed)
    w, h = img.size
    scale = 2  # 크게 그린 뒤 줄여 곡선을 매끄럽게
    layer = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(lines):
        base = rnd.uniform(0.3, 0.8) * h * scale
        amp = rnd.uniform(0.05, 0.14) * h * scale
        freq = rnd.uniform(1.2, 2.4)
        phase = rnd.uniform(0, math.pi * 2)
        pts = [(x, base + math.sin(x / (w * scale) * math.pi * freq + phase) * amp) for x in range(-20, w * scale + 20, 6)]
        d.line(pts, fill=(*color, alpha), width=max(2, int(max(w, h) * scale * width_ratio)), joint="curve")
    return Image.alpha_composite(img, layer.resize((w, h), Image.LANCZOS))


def save(img, rel, quality=80):
    path = STATIC / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "WEBP", quality=quality, method=6)
    print(f"{rel:32s} {img.size[0]}x{img.size[1]}  {path.stat().st_size // 1024} KB")


# ---------- 히어로 (메인·로그인·서브 페이지 헤더 배경) ----------
def make_hero():
    img = gradient((1920, 1080), hex_rgb("1b1b2f"), hex_rgb("0d0d12"))
    img = blobs(img, [hex_rgb("3a1c3f"), hex_rgb("1f2b4d"), POINT, hex_rgb("2b1a24")], seed=7, count=6, alpha=120)
    img = threads(img, POINT, seed=3, lines=2, width_ratio=0.003, alpha=140)
    img = threads(img, (255, 255, 255), seed=11, lines=3, width_ratio=0.0015, alpha=40)
    save(img, "nav/hero.webp", quality=78)


# ---------- 장르 타일 ----------
GENRE_COLORS = {
    "travel": ("2a9d8f", "264653", "e9c46a"),
    "health": ("57cc99", "22577a", "c7f9cc"),
    "art": ("f72585", "7209b7", "ffbe0b"),
    "history": ("bc6c25", "283618", "dda15e"),
    "romance": ("ff8fab", "9d174d", "ffc2d1"),
    "philosophy": ("4a4e69", "22223b", "c9ada7"),
    "natural_science": ("4cc9f0", "3a0ca3", "80ffdb"),
    "baby": ("ffd6a5", "f4a261", "caffbf"),
    "youth": ("06d6a0", "118ab2", "ffd166"),
    "economy": ("e9d8a6", "005f73", "94d2bd"),
}


def make_genres():
    for i, (name, (a, b, c)) in enumerate(GENRE_COLORS.items()):
        img = gradient((800, 600), hex_rgb(a), hex_rgb(b))
        img = blobs(img, [hex_rgb(c), hex_rgb(a), hex_rgb(b)], seed=100 + i, count=5, alpha=150)
        img = threads(img, (255, 255, 255), seed=200 + i, lines=2, width_ratio=0.004, alpha=70)
        save(img, f"genre/{name}.webp")


# ---------- 쓰레드 대표 이미지 ----------
THREAD_COLORS = [
    ("f4acb7", "9d8189", "ffe5d9"),
    ("a8dadc", "457b9d", "f1faee"),
    ("cdb4db", "6d597a", "ffc8dd"),
    ("ffd166", "ef476f", "fff3b0"),
    ("90be6d", "277da1", "f9c74f"),
    ("adb5bd", "343a40", "e9ecef"),
]


def make_thread_images():
    for i, (a, b, c) in enumerate(THREAD_COLORS, 1):
        img = gradient((800, 450), hex_rgb(a), hex_rgb(b))
        img = blobs(img, [hex_rgb(c), hex_rgb(a), hex_rgb(b)], seed=300 + i, count=5, alpha=140)
        img = threads(img, (255, 255, 255), seed=400 + i, lines=3, width_ratio=0.003, alpha=80)
        save(img, f"threads/img{i}.webp")


# ---------- 카카오에 표지가 없는 책의 기본 표지 ----------
def make_no_cover():
    W, H = 300, 440  # 표지 비율 (150x220 의 2배)
    img = gradient((W, H), hex_rgb("3a3a4a"), hex_rgb("15151c"))
    img = blobs(img, [hex_rgb("4a4a5e"), POINT, hex_rgb("22222c")], seed=700, count=4, alpha=70)
    img = threads(img, POINT, seed=701, lines=1, width_ratio=0.006, alpha=150)
    img = threads(img, (255, 255, 255), seed=702, lines=2, width_ratio=0.004, alpha=60)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONT_MEDIUM), 26)
    d.text((W / 2, H - 60), "ThRead", font=font, fill=(255, 255, 255, 200), anchor="mm")
    save(img, "covers/no-cover.webp", quality=85)


if __name__ == "__main__":
    make_hero()
    make_genres()
    make_thread_images()
    make_no_cover()
