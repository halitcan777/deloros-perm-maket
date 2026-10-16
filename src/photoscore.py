"""Оценка «это живое фото или афиша/коллаж/рендер». Чем больше, тем больше похоже на фото.
flat — доля плоских участков (у афиш и графики высокая), sat — доля «кислотных» пикселей (у ИИ-рендеров и плашек)."""
import os, json
from PIL import Image, ImageFilter, ImageStat

def score(path):
    im = Image.open(path)
    im.draft('RGB', (256, 256))
    im = im.convert('RGB')
    w, h = im.size
    small = im.resize((128, max(1, round(128 * h / w))))
    g = small.convert('L')
    px = list(g.getdata()); W = g.width
    flat = sum(1 for i in range(len(px) - 1) if (i + 1) % W and abs(px[i] - px[i + 1]) <= 1) / max(1, len(px))
    hsv = small.convert('HSV')
    hs = list(hsv.getdata())
    sat = sum(1 for H, S, V in hs if S > 170 and V > 120) / len(hs)
    blue = sum(1 for H, S, V in hs if 140 <= H <= 185 and S > 120 and V > 90) / len(hs)
    edges = ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).mean[0]
    return {'flat': round(flat, 3), 'sat': round(sat, 3), 'blue': round(blue, 3), 'edges': round(edges, 1), 'ar': round(w / h, 2)}
