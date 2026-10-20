"""BorsaSemih efekt kütüphanesi (fx) — videonun KENDİSİNİ işleyen 22 efekt + 2 kalıp.

scene.py şeffaf bilgi kartı (overlay .webm) üretir; fx.py ise bir kurgu aralığını (segment) alır, kareleri
işler ve aynı uzunlukta OPAK bir mp4 döndürür. Final birleştirmede bu mp4, base.mp4'ün o aralığının üstüne
opak overlay olarak konur (compose.py: `overlay=enable='between(t,T,T+d)'`). Ses dokunulmaz.

Referans: "22 video efekti — Claude ile, sadece kod" Reels'i (20.10.2026, Semih paylaştı). Hepsi ücretsiz,
CPU'da, numpy + OpenCV + PIL. Konuşanı ayırması gereken efektler `hyperframes remove-background` maskesini
kullanır (yoksa otomatik üretir, `<segment>.subj.mov` olarak cache'ler).

Kullanım:
  python3 fx.py spec.json --base edit/base.mp4 --at 12.40 --dur 3.2 -o edit/fx/slot_3.mp4   # aralığı kes + işle
  python3 fx.py spec.json --in seg.mp4 -o out.mp4 [--mask subj.mov]                           # hazır segment
  python3 fx.py spec.json --in seg.mp4 --still 1.2 -o kare.png                                # tek kare QA (~5 sn)
  python3 fx.py list                                                                           # efektler + alanlar

Spec ortak alanları: {"fx": "<ad>", "theme": "krem|petrol|lacivert", ...efekte özel alanlar}
Koordinatlar çıktı pikselidir (Reels 1080×1920). Metinde *kelime* = vurgu rengi. Tamamı büyük harf YOK.
"""
from __future__ import annotations

import argparse, json, math, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

_B = Path(__file__).resolve().parent
PKG = _B if (_B / "fonts").exists() else _B.parent
FONTS = PKG / "fonts"
sys.path.insert(0, str(_B))
try:
    from scene import THEMES
except Exception:  # scene.py yoksa minimum tema
    THEMES = {"krem": dict(bg="#EFE8DB", accent="#FF8C1E", accent_ink="#D9670A", text="#221E1B", muted="#6F6458",
                           dim="#9A8E80", hair="#CFC4B3", up="#1E9E5A", down="#D9434A", light=True)}

# ───────────────────────────── yardımcılar ─────────────────────────────

def hexrgb(h: str):
    h = h.lstrip("#")
    if h.startswith("rgba") or len(h) not in (6, 8):
        return (240, 240, 240)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ramp(t, t0, d):
    return clamp((t - t0) / d) if d > 0 else float(t >= t0)


def out3(p):
    return 1 - (1 - p) ** 3


def in3(p):
    return p ** 3


def inout3(p):
    return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2


def back(p, s=1.7):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


_FC: dict = {}
FONT_FILES = {"black": "Montserrat-Black.ttf", "xb": "Montserrat-ExtraBold.ttf", "bold": "Montserrat-Bold.ttf",
              "semi": "Montserrat-SemiBold.ttf", "med": "Montserrat-Medium.ttf", "mono": "JetBrainsMono-Medium.ttf",
              "monob": "JetBrainsMono-Bold.ttf", "serif": "InstrumentSerif-Italic.ttf", "hand": "Caveat.ttf"}


def font(name: str, size: int):
    key = (name, int(size))
    if key not in _FC:
        f = ImageFont.truetype(str(FONTS / FONT_FILES.get(name, name)), int(size))
        if name == "hand":
            try:
                f.set_variation_by_axes([700])
            except Exception:
                pass
        _FC[key] = f
    return _FC[key]


SYM = set("✓✔→↓↑▲▼★•")
SYM_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def sym_font(size):
    key = ("__sym", int(size))
    if key not in _FC:
        try:
            _FC[key] = ImageFont.truetype(SYM_FONT, int(size))
        except Exception:
            _FC[key] = None
    return _FC[key]


def split_sym(text):
    """Montserrat'ta olmayan simgeleri (✓ → ▲) ayrı parça yap."""
    out, cur = [], ""
    for ch in text:
        if ch in SYM:
            if cur: out.append((cur, False))
            out.append((ch, True)); cur = ""
        else:
            cur += ch
    if cur: out.append((cur, False))
    return out


def rich_runs(text: str):
    """'Paran *nereye* gidiyor' -> [(metin, vurgulu_mu), ...]"""
    out = []
    for i, part in enumerate(re.split(r"\*(.+?)\*", text)):
        if part:
            out.append((part, i % 2 == 1))
    return out


def text_img(text, fnt, fill, acc=None, stroke=0, stroke_fill=(0, 0, 0), shadow=False):
    """Tek satır zengin metin -> sıkı RGBA PIL görüntü."""
    runs = []
    sf = sym_font(int(fnt.size * 0.85))
    for r, a in rich_runs(text):
        for piece, is_sym in split_sym(r):
            runs.append((piece, a, sf if (is_sym and sf) else fnt))
    pad = stroke + (12 if shadow else 2)
    widths = [f.getlength(r) for r, _, f in runs]
    asc, desc = fnt.getmetrics()
    W, H = int(sum(widths) + 2 * pad + 4), int(asc + desc + 2 * pad)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for (r, a, f), w in zip(runs, widths):
        col = (acc if (a and acc) else fill)
        dy = (asc - f.getmetrics()[0]) if f is not fnt else 0
        d.text((x, pad + dy), r, font=f, fill=col, stroke_width=stroke, stroke_fill=stroke_fill)
        x += w
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * .55)))
        base = Image.new("RGBA", im.size, (0, 0, 0, 0))
        base.alpha_composite(sh, (0, 4))
        base.alpha_composite(im)
        im = base
    return im


def rounded(w, h, r, fill, outline=None, width=0):
    im = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill, outline=outline, width=width)
    return im


def with_shadow(im: Image.Image, blur=22, off=(0, 14), op=0.45):
    pad = blur * 2
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 255))
    sh.putalpha(im.getchannel("A").point(lambda v: int(v * op)))
    out.alpha_composite(sh, (pad + off[0], pad + off[1]))
    out = out.filter(ImageFilter.GaussianBlur(blur / 2))
    out.alpha_composite(im, (pad, pad))
    return out, pad


def over(dst: np.ndarray, src: Image.Image, x, y, opacity=1.0, scale=1.0, rot=0.0, anchor="tl"):
    """RGBA PIL'i float32 HxWx3 kareye bindir. anchor: tl | c (x,y merkez)."""
    if opacity <= 0.003 or scale <= 0.01:
        return dst
    if scale != 1.0:
        src = src.resize((max(1, int(src.width * scale)), max(1, int(src.height * scale))), Image.BICUBIC)
    if rot:
        src = src.rotate(rot, resample=Image.BICUBIC, expand=True)
    if anchor == "c":
        x, y = x - src.width / 2, y - src.height / 2
    x, y = int(round(x)), int(round(y))
    H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + src.width), min(H, y + src.height)
    if x1 <= x0 or y1 <= y0:
        return dst
    a = np.asarray(src, dtype=np.float32)[y0 - y:y1 - y, x0 - x:x1 - x]
    al = a[..., 3:4] / 255.0 * opacity
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - al) + a[..., :3] * al
    return dst


def blend(a, b, m):
    """m: HxW (0-1) — b'yi m oranında a'nın üstüne koy."""
    return a * (1 - m[..., None]) + b * m[..., None]


def scale_about(img, s, cx, cy):
    """Kareyi (cx,cy) etrafında s kadar büyüt (kamera punch-in)."""
    H, W = img.shape[:2]
    M = np.float32([[s, 0, cx - s * cx], [0, s, cy - s * cy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def zoom_blur(img, s0, s1, cx, cy, n=7):
    acc = np.zeros_like(img)
    for k in range(n):
        acc += scale_about(img, s0 + (s1 - s0) * k / max(1, n - 1), cx, cy)
    return acc / n


# el çizimi (doodle) — titreyen çizgiler
def jitter(pts, amp, seed):
    rng = np.random.default_rng(seed)
    n = len(pts)
    # yumuşak gürültü: birkaç kontrol noktası arası interpolasyon
    k = max(4, n // 12)
    ctrl = rng.normal(0, amp, (k + 1, 2))
    idx = np.linspace(0, k, n)
    lo = np.floor(idx).astype(int); hi = np.minimum(lo + 1, k); f = (idx - lo)[:, None]
    return pts + ctrl[lo] * (1 - f) + ctrl[hi] * f


def draw_poly(layer, pts, color, width, progress=1.0):
    if progress <= 0 or len(pts) < 2:
        return
    n = max(2, int(len(pts) * min(1.0, progress)))
    p = np.round(pts[:n]).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(layer, [p], False, (*color, 255), int(width), cv2.LINE_AA)


def rect_pts(x, y, w, h, n=120, over_=0.06):
    per = 2 * (w + h)
    ts = np.linspace(0, 1 + over_, n)
    out = []
    for t in ts:
        d = (t % 1) * per
        if d < w: out.append((x + d, y))
        elif d < w + h: out.append((x + w, y + d - w))
        elif d < 2 * w + h: out.append((x + w - (d - w - h), y + h))
        else: out.append((x, y + h - (d - 2 * w - h)))
    return np.array(out, np.float32)


def ellipse_pts(cx, cy, rx, ry, n=90, turns=1.12, start=-2.2):
    th = start + np.linspace(0, 2 * math.pi * turns, n)
    grow = np.linspace(1.0, 1.08, n)
    return np.stack([cx + rx * grow * np.cos(th), cy + ry * grow * np.sin(th)], 1).astype(np.float32)


def arrow_pts(a, b, bend=0.25, n=40):
    a, b = np.array(a, np.float32), np.array(b, np.float32)
    mid = (a + b) / 2
    nrm = np.array([-(b - a)[1], (b - a)[0]], np.float32) * bend
    c = mid + nrm
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 2 * a + 2 * (1 - t) * t * c + t ** 2 * b).astype(np.float32)


def arrow_head(pts, size=34):
    b, a = pts[-1], pts[-5]
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    l = [b, b - size * np.array([math.cos(ang - .5), math.sin(ang - .5)])]
    r = [b, b - size * np.array([math.cos(ang + .5), math.sin(ang + .5)])]
    return np.array(l, np.float32), np.array(r, np.float32)


# ───────────────────────────── IO ─────────────────────────────

def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    j = json.loads(r.stdout)
    s = j["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(d), float(j["format"]["duration"])


def frames(path, W, H, fps, ss=None, gray_alpha=False):
    pre = ["-ss", str(ss)] if ss is not None else []
    if gray_alpha:
        dec = ["-c:v", "libvpx-vp9"] if str(path).endswith(".webm") else []
        cmd = ["ffmpeg", "-v", "error", *pre, *dec, "-i", str(path), "-vf",
               f"fps={fps},scale={W}:{H},format=rgba,alphaextract,format=gray", "-f", "rawvideo", "-"]
        sz = W * H
    else:
        cmd = ["ffmpeg", "-v", "error", *pre, "-i", str(path), "-vf", f"fps={fps},scale={W}:{H}", "-pix_fmt", "rgb24",
               "-f", "rawvideo", "-"]
        sz = W * H * 3
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        while True:
            b = p.stdout.read(sz)
            if len(b) < sz:
                break
            a = np.frombuffer(b, np.uint8)
            yield (a.reshape(H, W).astype(np.float32) / 255.0) if gray_alpha else a.reshape(H, W, 3).astype(np.float32)
    finally:
        p.kill(); p.wait()


def clean_mask(m: np.ndarray) -> np.ndarray:
    """remove-background maskesini temizle: yarı saydam sis ve küçük adacıkları at, kenarı yumuşak tut."""
    m = np.clip((m - 0.25) / 0.5, 0, 1)
    b = (m > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(b, 8)
    if n > 2:
        big = st[1:, cv2.CC_STAT_AREA].max()
        keep = np.zeros(n, np.uint8)
        keep[1:] = st[1:, cv2.CC_STAT_AREA] >= big * 0.04
        km = cv2.dilate(keep[lab], np.ones((9, 9), np.uint8)).astype(np.float32)
        m = m * km
    return cv2.GaussianBlur(m, (0, 0), 1.0)


def ensure_mask(seg: Path, mask: Path | None) -> Path:
    if mask and Path(mask).exists():
        return Path(mask)
    m = seg.with_suffix(".subj.mov")
    if not m.exists():
        print(f"konuşan ayrılıyor (remove-background) → {m.name} …", flush=True)
        r = subprocess.run(["npx", "--yes", "hyperframes", "remove-background", str(seg), "-o", str(m)],
                           capture_output=True, text=True)
        if r.returncode or not m.exists():
            raise SystemExit("remove-background başarısız:\n" + r.stdout[-800:] + r.stderr[-800:])
    return m


# ───────────────────────────── efektler ─────────────────────────────
# Her efekt: class, NEEDS_MASK, __init__(spec, W, H, fps, dur, C), frame(i, t, img, m) -> img (float32 RGB 0-255)

REG: dict = {}


def fx(name, doc):
    def deco(cls):
        cls.NAME, cls.DOC = name, doc
        REG[name] = cls
        return cls
    return deco


class Base:
    NEEDS_MASK = False

    def __init__(self, s, W, H, fps, dur, C):
        self.s, self.W, self.H, self.fps, self.dur, self.C = s, W, H, fps, dur, C
        # videonun üstünde koyu tema rengi kaybolur → parlak varyant (accent_video); kart/kağıt üstünde accent
        self.acc = hexrgb(s.get("color", C.get("accent_video", C["accent"])))
        self.acc_card = hexrgb(s.get("color_card", C["accent"]))
        self.ink = hexrgb(C.get("text", "#14262B"))
        self.paper = hexrgb(C.get("bg", "#EFE8DB"))
        self.setup()

    def setup(self):
        pass

    def g(self, k, d=None):
        return self.s.get(k, d)

    def fade_io(self, t, fin=0.35, fout=0.3):
        return min(out3(ramp(t, 0, fin)), 1 - ramp(t, self.dur - fout, fout))


def make_card(item, w, h, C, radius=34):
    """orbit / screen_wall kartı: görsel (img) veya metin kartı."""
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if item.get("img"):
        im = Image.open(item["img"]).convert("RGB")
        r = max(w / im.width, h / im.height)
        im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
        im = im.crop(((im.width - w) // 2, (im.height - h) // 2, (im.width - w) // 2 + w, (im.height - h) // 2 + h))
        msk = Image.new("L", (w, h), 0)
        ImageDraw.Draw(msk).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
        card.paste(im, (0, 0), msk)
    else:
        card.alpha_composite(rounded(w, h, radius, hexrgb(C["bg"]) + (255,)))
        d = ImageDraw.Draw(card)
        acc = hexrgb(C["accent"])
        if item.get("n"):
            d.text((28, 18), str(item["n"]), font=font("black", int(h * 0.30)), fill=acc)
        y = int(h * 0.52)
        for line in str(item.get("text", "")).split("\n"):
            d.text((28, y), line, font=font("xb", int(h * 0.11)), fill=hexrgb(C["text"]))
            y += int(h * 0.13)
        if item.get("sub"):
            d.text((28, h - int(h * 0.14)), item["sub"], font=font("mono", int(h * 0.065)), fill=hexrgb(C["muted"]))
    ImageDraw.Draw(card).rounded_rectangle([0, 0, w - 1, h - 1], radius, outline=(255, 255, 255, 235), width=5)
    return card


@fx("orbit", "Kartlar/ekran görüntüleri konuşanın etrafında 3B yörüngede döner; arkaya geçen kart konuşanın ARKASINDA kalır. "
             "Alanlar: items [{img}|{n,text,sub}], center [x,y] (baş), radius [rx,ry], card [w,h], turns (0.35), tilt")
class Orbit(Base):
    NEEDS_MASK = True

    def setup(self):
        W, H = self.W, self.H
        self.cx, self.cy = self.g("center", [W * 0.45, H * 0.42])
        self.rx, self.ry = self.g("radius", [W * 0.36, H * 0.07])
        cw, ch = self.g("card", [int(W * 0.21), int(W * 0.37)])
        items = self.g("items") or [{"n": str(i + 1), "text": "Kart"} for i in range(5)]
        self.cards = [with_shadow(make_card(it, cw, ch, self.C))[0] for it in items]
        self.turns = float(self.g("turns", 0.35))

    def frame(self, i, t, img, m):
        n = len(self.cards)
        op = self.fade_io(t, 0.45, 0.35)
        grow = out3(ramp(t, 0, 0.55))
        th0 = -math.pi / 2 + 2 * math.pi * self.turns * (t / self.dur)
        poses = []
        for k, c in enumerate(self.cards):
            th = th0 + 2 * math.pi * k / n
            z = math.sin(th)  # +1 önde
            x = self.cx + self.rx * math.cos(th) * (0.35 + 0.65 * grow)
            y = self.cy + self.ry * z + 40 * math.cos(th) * float(self.g("tilt", 0.3))
            sc = (0.72 + 0.28 * (z + 1) / 2) * (0.6 + 0.4 * grow)
            poses.append((z, x, y, sc, c))
        out = img.copy()
        for z, x, y, sc, c in sorted(poses, key=lambda p: p[0]):
            if z < 0:
                over(out, c, x, y, op * (0.75 + 0.25 * (z + 1)), sc, anchor="c")
        out = blend(out, img, m)  # konuşan arkadaki kartların önünde
        for z, x, y, sc, c in sorted(poses, key=lambda p: p[0]):
            if z >= 0:
                over(out, c, x, y, op, sc, anchor="c")
        return out


@fx("frame_break", "Görüntü bir çerçeveye küçülür, konuşan çerçeveden DIŞARI taşar (başı çerçevenin üstünde). "
                   "Alanlar: window [x,y,w,h] (son çerçeve), bg (tema), border ('#FFFFFF'), radius (40), in (0.55)")
class FrameBreak(Base):
    NEEDS_MASK = True

    def setup(self):
        W, H = self.W, self.H
        self.win = self.g("window", [int(W * 0.10), int(H * 0.42), int(W * 0.80), int(H * 0.50)])
        self.bgc = np.array(hexrgb(self.g("bg", self.C.get("bg"))), np.float32)
        self.bc = hexrgb(self.g("border", "#FFFFFF"))
        # zemin: tema rengi + hafif radyal karartma
        yy, xx = np.mgrid[0:H, 0:W]
        v = 1 - 0.18 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 4
        self.bg = (self.bgc[None, None] * v[..., None]).astype(np.float32)

    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        p = out3(ramp(t, 0, float(self.g("in", 0.55))))
        q = 1 - out3(ramp(t, self.dur - 0.35, 0.35))
        p = min(p, q)
        x, y, w, h = self.win
        x, y, w, h = (0 + (x - 0) * p, 0 + (y - 0) * p, W + (w - W) * p, H + (h - H) * p)
        r = int(self.g("radius", 40) * p)
        win = np.zeros((H, W), np.uint8)
        cv2.rectangle(win, (0, 0), (0, 0), 0)
        im = Image.new("L", (W, H), 0)
        ImageDraw.Draw(im).rounded_rectangle([x, y, x + w, y + h], r, fill=255)
        wm = np.asarray(im, np.float32) / 255.0
        out = blend(self.bg, img, wm)
        # çerçeve kenarı (konuşanın altında kalır)
        bl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(bl).rounded_rectangle([x, y, x + w, y + h], r, outline=self.bc + (int(255 * p),), width=6)
        over(out, bl, 0, 0)
        # konuşan dışarı taşar (çerçeve dışında hafif gölge)
        sh = cv2.GaussianBlur(m, (0, 0), 18)
        sh = np.roll(sh, 16, 0) * (1 - wm) * 0.35 * p
        out = out * (1 - sh[..., None])
        return blend(out, img, m * np.maximum(p, wm) if p < 1 else m)


def preset_bg(kind, W, H, C, img_path=None):
    if img_path:
        im = Image.open(img_path).convert("RGB")
        r = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
        im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
        return np.asarray(im, np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    if kind == "gun_batimi":  # referanstaki pop gün batımı (marka dışı — sadece eğlenceli/kişisel içerikte)
        top, mid = np.array([255, 120, 60], np.float32), np.array([240, 60, 120], np.float32)
        bg = top * (1 - yy) + mid * yy
        bg = np.repeat(bg, W, 1)
        hz = int(H * 0.62)
        bg[hz:] = np.array([40, 180, 190], np.float32)
        im = Image.fromarray(bg.astype(np.uint8))
        d = ImageDraw.Draw(im)
        d.ellipse([W * .52, hz - W * .2, W * .92, hz + W * .2], fill=(255, 200, 60))
        bgn = np.asarray(im, np.float32).copy()
        bgn[hz:] = np.array([40, 180, 190], np.float32)
        for k in range(6):
            y = hz + 60 + k * 70
            cv2.line(bgn, (int(W * (0.15 + 0.1 * (k % 3))), y), (int(W * (0.45 + 0.1 * (k % 2))), y), (255, 255, 255), 5, cv2.LINE_AA)
        return bgn
    # "grafik": tema zemininde yükselen grafik (finans arka planı)
    paper = np.array(hexrgb(C.get("bg")), np.float32)
    bg = np.ones((H, W, 3), np.float32) * paper
    im = Image.fromarray(bg.astype(np.uint8))
    d = ImageDraw.Draw(im)
    hair = hexrgb(C.get("hair", "#C9D1D1")) if C.get("hair", "").startswith("#") else (200, 205, 205)
    for x in range(0, W, 90):
        d.line([(x, 0), (x, H)], fill=hair, width=2)
    for y in range(0, H, 90):
        d.line([(0, y), (W, y)], fill=hair, width=2)
    rng = np.random.default_rng(7)
    n = 26
    xs = np.linspace(W * 0.02, W * 0.98, n)
    ys = H * 0.62 - np.cumsum(rng.normal(14, 30, n))
    acc = hexrgb(C["accent"])
    for k in range(n):  # mumlar
        o, c = ys[k] + rng.normal(0, 22), ys[k]
        col = hexrgb(C.get("up", "#1E9E5A")) if c < o else hexrgb(C.get("down", "#D9434A"))
        d.line([(xs[k], min(o, c) - 30), (xs[k], max(o, c) + 30)], fill=col, width=4)
        d.rectangle([xs[k] - 12, min(o, c), xs[k] + 12, max(o, c) + 2], fill=col)
    d.line(list(zip(xs, ys - 40)), fill=acc, width=9, joint="curve")
    return np.asarray(im, np.float32)


@fx("green_screen", "Arka plan silinir, yerine grafik/görsel gelir; konuşan önde kalır. Alanlar: bg ('grafik' | 'gun_batimi'), "
                    "image (yol — ör. TradingView ekran görüntüsü), reveal (0.45 sn dairesel açılış), dim (görsel kararma 0-1)")
class GreenScreen(Base):
    NEEDS_MASK = True

    def setup(self):
        self.bg = preset_bg(self.g("bg", "grafik"), self.W, self.H, self.C, self.g("image"))
        self.bg *= (1 - float(self.g("dim", 0.0)))
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        self.dist = np.sqrt((xx - self.W * .45) ** 2 + (yy - self.H * .4) ** 2) / math.hypot(self.W, self.H)

    def frame(self, i, t, img, m):
        rv = float(self.g("reveal", 0.45))
        p = out3(ramp(t, 0, rv)) * (1 - in3(ramp(t, self.dur - 0.3, 0.3)))
        circ = np.clip((p * 1.1 - self.dist) / 0.05, 0, 1)
        bgm = circ * (1 - m)
        # kenar ışığı: konuşanın konturuna ince açık hat (kesik görünmesin)
        return blend(img, self.bg, bgm)


@fx("mirror", "Görüntünün yarısı ayna gibi kopyalanır; ortada vurgu renginde çizgi gezer. Alanlar: side ('left' kaynak), in (0.45)")
class Mirror(Base):
    def frame(self, i, t, img, m):
        W = self.W
        p = out3(ramp(t, 0, float(self.g("in", 0.45)))) * (1 - in3(ramp(t, self.dur - 0.3, 0.3)))
        src = img if self.g("side", "left") == "left" else img[:, ::-1]
        mir = src[:, ::-1]
        edge = int(W - (W / 2) * p)
        out = src.copy()
        out[:, edge:] = mir[:, edge:]
        if self.g("side", "left") != "left":
            out = out[:, ::-1]
            edge = W - edge
        if 0.01 < p:
            cv2.line(out, (edge, 0), (edge, self.H), self.acc, 4, cv2.LINE_AA)
            glow = np.zeros(out.shape[:2], np.float32)
            glow[:, max(0, edge - 2):edge + 2] = 1
            glow = cv2.GaussianBlur(glow, (0, 0), 14) * 0.6
            out = blend(out, np.array(self.acc, np.float32)[None, None] * np.ones_like(out), glow)
        return out


@fx("ui_world", "Videonun içinde canlı arayüz: sohbet penceresi (soru + cevap), terminal (yazılan komut + ilerleme çubuğu), "
                "onay çipleri. Alanlar: chat {title,user,reply,x,y,w}, terminal {title,cmd,label,x,y,w,from,to}, chips {items,x,y}, at {chat,reply,terminal,chips}")
class UIWorld(Base):
    def setup(self):
        W, H = self.W, self.H
        self.chat = self.g("chat", {"title": "Claude", "user": "Bu videoya 22 efekt ekle", "reply": "Tamamdır, render alıyorum ✓"})
        self.term = self.g("terminal", {"title": "terminal", "cmd": "npx hyperframes render", "label": "Render alınıyor"})
        self.chips = self.g("chips", {"items": ["Efekt ✓", "Ses ✓", "Altyazı ✓"]})
        self.at = {"chat": 0.15, "reply": 0.7, "terminal": 0.5, "chips": 1.4, **(self.g("at") or {})}
        cw = int(self.chat.get("w", W * 0.62))
        self.chat_xy = (self.chat.get("x", W - cw - 50), self.chat.get("y", int(H * 0.06)))
        self.cw = cw
        self.tw = int(self.term.get("w", W * 0.60))
        self.term_xy = (self.term.get("x", 60), self.term.get("y", int(H * 0.53)))
        self.chip_xy = (self.chips.get("x", 60), self.chips.get("y", int(H * 0.645)))
        dark = (24, 26, 30, 236)
        self.win_c = dark

    def window(self, w, h, title):
        im = rounded(w, h, 26, self.win_c, outline=(255, 255, 255, 40), width=2)
        d = ImageDraw.Draw(im)
        for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([24 + k * 30, 22, 40 + k * 30, 38], fill=c)
        d.text((24 + 3 * 30 + 10, 17), title, font=font("mono", 24), fill=(150, 150, 155))
        return im

    def frame(self, i, t, img, m):
        out = img
        fo = 1 - ramp(t, self.dur - 0.3, 0.3)
        # sohbet
        a = self.at
        if t >= a["chat"]:
            p = out3(ramp(t, a["chat"], 0.4))
            h = 230 if t >= a["reply"] else 140
            win = self.window(self.cw, h, self.chat.get("title", "Claude"))
            d = ImageDraw.Draw(win)
            fu = font("semi", 30)
            u = self.chat.get("user", "")
            ut = text_img(u, fu, (245, 245, 245))
            uw = ut.width + 36
            d.rounded_rectangle([self.cw - uw - 24, 62, self.cw - 24, 116], 27, fill=(52, 54, 60))
            win.alpha_composite(ut, (int(self.cw - uw - 6), 66))
            if t >= a["reply"]:
                q = out3(ramp(t, a["reply"], 0.3))
                r = self.chat.get("reply", "")
                rt = text_img(r, fu, (255, 255, 255))
                bub = rounded(rt.width + 36, 56, 28, self.acc + (255,))
                bub.alpha_composite(rt, (18, 4))
                win.alpha_composite(bub, (24, 140)) if q > 0.5 else None
            ws, pad = with_shadow(win, 20, (0, 10), 0.5)
            over(out, ws, self.chat_xy[0] - pad, self.chat_xy[1] - pad - 30 * (1 - p), p * fo)
        # terminal
        if t >= a["terminal"]:
            p = out3(ramp(t, a["terminal"], 0.4))
            win = self.window(self.tw, 190, self.term.get("title", "terminal"))
            d = ImageDraw.Draw(win)
            cmd = self.term.get("cmd", "")
            n = int(len(cmd) * ramp(t, a["terminal"] + 0.15, 0.03 * len(cmd)))
            fm = font("mono", 30)
            d.text((26, 66), "$ ", font=fm, fill=self.acc)
            d.text((26 + fm.getlength("$ "), 66), cmd[:n], font=fm, fill=(235, 235, 235))
            t1 = a["terminal"] + 0.15 + 0.03 * len(cmd)
            if t >= t1:
                pr = inout3(ramp(t, t1, max(0.4, a["chips"] - t1)))
                v0, v1 = float(self.term.get("from", 0)), float(self.term.get("to", 100))
                pct = v0 + (v1 - v0) * pr
                d.text((26, 108), f"{self.term.get('label', '')} %{pct:.0f}", font=font("mono", 26), fill=(160, 160, 165))
                d.rounded_rectangle([26, 152, self.tw - 26, 160], 4, fill=(60, 62, 68))
                d.rounded_rectangle([26, 152, 26 + (self.tw - 52) * pr, 160], 4, fill=self.acc)
            ws, pad = with_shadow(win, 20, (0, 10), 0.5)
            over(out, ws, self.term_xy[0] - pad, self.term_xy[1] - pad + 30 * (1 - p), p * fo)
        # çipler
        x = self.chip_xy[0]
        for k, c in enumerate(self.chips.get("items", [])):
            tk = a["chips"] + 0.18 * k
            if t < tk:
                break
            p = ramp(t, tk, 0.3)
            fc = font("xb", 30)
            ct = text_img(c, fc, (20, 22, 26))
            w = ct.width + 40
            chip = rounded(w, 62, 31, (255, 255, 255, 245))
            chip.alpha_composite(ct, (20, 8))
            over(out, chip, x + w / 2, self.chip_xy[1] + 31, fo, 0.6 + 0.4 * back(p), anchor="c")
            x += w + 18
        return out


@fx("paper_cut", "Kağıt kolaj: zemin beyaz kağıt + yırtık renkli şeritler, konuşan beyaz çıkartma kenarlı, alt şeritte "
                 "harf harf 'fidye notu' kelime. Alanlar: word ('Dergiden'), colors [üst, alt], letter_gap (0.09 sn)")
class PaperCut(Base):
    NEEDS_MASK = True

    def setup(self):
        W, H = self.W, self.H
        cols = self.g("colors") or [self.C["accent"], self.C.get("muted", "#8FA0A3")]
        self.c1, self.c2 = hexrgb(cols[0]), hexrgb(cols[1])
        paper = np.ones((H, W, 3), np.float32) * np.array([247, 245, 240], np.float32)
        noise = np.random.default_rng(3).normal(0, 3.5, (H, W, 1)).astype(np.float32)
        self.paper = np.clip(paper + noise, 0, 255)
        rng = np.random.default_rng(11)

        def strip(y0, hgt):
            xs = np.linspace(0, W, 40)
            top = y0 + rng.normal(0, 9, 40) + 14 * np.sin(xs / 37)
            bot = y0 + hgt + rng.normal(0, 9, 40) + 14 * np.cos(xs / 41)
            poly = list(zip(xs, top)) + list(zip(xs[::-1], bot[::-1]))
            im = Image.new("L", (W, H), 0)
            ImageDraw.Draw(im).polygon(poly, fill=255)
            return np.asarray(im.filter(ImageFilter.GaussianBlur(1)), np.float32) / 255
        self.s1, self.s2 = strip(H * 0.13, H * 0.08), strip(H * 0.66, H * 0.07)
        self.word = self.g("word", "Dergiden")
        fonts_ = ["black", "serif", "monob", "xb", "hand"]
        self.letters = []
        for k, ch in enumerate(self.word):
            f = font(fonts_[k % len(fonts_)], 96 if fonts_[k % len(fonts_)] != "hand" else 110)
            bgc = [(20, 20, 20), (255, 255, 255), self.c1, (245, 225, 120)][k % 4]
            fg = (255, 255, 255) if bgc in [(20, 20, 20), self.c1] else (20, 20, 20)
            tw = f.getlength(ch)
            tile = Image.new("RGBA", (int(tw + 34), 124), bgc + (255,))
            ImageDraw.Draw(tile).text((17, 6), ch, font=f, fill=fg)
            tile, _ = with_shadow(tile, 6, (2, 4), 0.4)
            self.letters.append((tile, rng.uniform(-9, 9)))
        self.sticker_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))

    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        p = out3(ramp(t, 0, 0.4))
        fo = 1 - ramp(t, self.dur - 0.3, 0.3)
        out = self.paper.copy()
        sx = int(W * (1 - p))
        s1 = np.roll(self.s1, -sx, 1) if sx else self.s1
        s2 = np.roll(self.s2, sx, 1) if sx else self.s2
        out = blend(out, np.ones_like(out) * np.array(self.c1, np.float32), s1)
        out = blend(out, np.ones_like(out) * np.array(self.c2, np.float32), s2)
        mb = (m > 0.5).astype(np.uint8)
        dil = cv2.dilate(mb, self.sticker_k).astype(np.float32)
        dil = cv2.GaussianBlur(dil, (0, 0), 1.2)
        sh = np.roll(cv2.GaussianBlur(dil, (0, 0), 10), 12, 0) * 0.3
        out = out * (1 - sh[..., None])
        out = blend(out, np.full_like(out, 255), dil)
        out = blend(out, img, m)
        x = W * 0.08
        y = H * 0.66 + 4
        gap = float(self.g("letter_gap", 0.09))
        for k, (tile, rot) in enumerate(self.letters):
            tk = 0.35 + gap * k
            if t >= tk:
                q = back(ramp(t, tk, 0.18), 2.4)
                over(out, tile, x + tile.width / 2, y + tile.height / 2, 1.0, q, rot, anchor="c")
            x += tile.width * 0.78
        return blend(img, out, np.full(img.shape[:2], fo * min(1, p * 3), np.float32))


@fx("cover_story", "Dergi kapağı: üstte 'Sayı 22 · Ekim 2026' mono satır, dev serif italik başlık (konuşanın ARKASINDA), "
                   "altta kalın manşet + italik alt başlık + barkod. Alanlar: masthead ('Borsa'), issue, date, headline ('22 efekt'), sub, behind (true)")
class CoverStory(Base):
    NEEDS_MASK = True

    def setup(self):
        W, H = self.W, self.H
        self.mast = text_img(self.g("masthead", "Borsa"), font("serif", int(W * 0.30)), (255, 255, 255), shadow=True)
        self.issue = text_img(self.g("issue", "Sayı 22"), font("mono", 30), (235, 235, 235))
        self.date = text_img(self.g("date", "Ekim 2026"), font("mono", 30), (235, 235, 235))
        self.head = text_img(self.g("headline", "*22 efekt*"), font("black", int(W * 0.12)), (255, 255, 255),
                             acc=self.acc, shadow=True)
        self.sub = text_img(self.g("sub", "kurgu programı olmadan"), font("serif", int(W * 0.06)), (240, 240, 240), shadow=True)
        bc = Image.new("RGBA", (170, 70), (255, 255, 255, 255))
        d = ImageDraw.Draw(bc)
        rng = np.random.default_rng(5)
        x = 8
        while x < 160:
            w = int(rng.integers(2, 6))
            d.rectangle([x, 6, x + w, 52], fill=(10, 10, 10))
            x += w + int(rng.integers(2, 5))
        d.text((10, 52), "8 690000 220226", font=font("mono", 13), fill=(10, 10, 10))
        self.bar = bc
        yy = np.linspace(0, 1, H)[:, None]
        self.grad = (np.clip((yy - 0.62) / 0.38, 0, 1) ** 1.3 * 0.75 + np.clip((0.12 - yy) / 0.12, 0, 1) * 0.45).astype(np.float32)
        self.grad = np.repeat(self.grad, W, 1)

    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        fo = 1 - ramp(t, self.dur - 0.3, 0.3)
        out = img * (1 - self.grad[..., None] * fo)
        p = out3(ramp(t, 0.05, 0.5))
        over(out, self.mast, W / 2, H * 0.17 - 40 * (1 - p), p * fo, anchor="c")
        if self.g("behind", True):
            out = blend(out, img * (1 - self.grad[..., None] * fo), m)  # başlık konuşanın arkasında
        q = out3(ramp(t, 0.2, 0.4))
        over(out, self.issue, 60, 70, q * fo)
        over(out, self.date, W - 60 - self.date.width, 70, q * fo)
        r = out3(ramp(t, 0.35, 0.45))
        over(out, self.head, 50, H * 0.80 + 50 * (1 - r), r * fo)
        over(out, self.sub, 56, H * 0.80 + self.head.height - 10 + 50 * (1 - r), r * fo)
        over(out, self.bar, W - 230, H * 0.885, r * fo)
        return out


@fx("triptych", "Görüntü 3 dikey panele bölünür; paneller sırayla kayarak gelir, her biri farklı kadraj (geniş/yakın/detay). "
                "Alanlar: panels [[fx,fy,zoom],...] (odak noktası + zoom), gap (16), bg")
class Triptych(Base):
    def setup(self):
        W, H = self.W, self.H
        self.panels = self.g("panels") or [[W * 0.25, H * 0.45, 1.0], [W * 0.35, H * 0.30, 1.9], [W * 0.6, H * 0.55, 1.5]]
        self.gap = int(self.g("gap", 16))
        self.bgc = np.array(hexrgb(self.g("bg", "#0E0F11")), np.float32)

    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        n = len(self.panels)
        pw = (W - self.gap * (n + 1)) / n
        out = np.ones_like(img) * self.bgc
        fo = ramp(t, self.dur - 0.3, 0.3)
        for k, (fx_, fy, z) in enumerate(self.panels):
            p = out3(ramp(t, 0.08 * k, 0.45))
            x0 = int(self.gap + k * (pw + self.gap))
            src = scale_about(img, z, fx_, fy) if z != 1 else img
            # panel içeriği: odak noktası panel ortasına gelsin
            sx = int(np.clip(fx_ - pw / 2, 0, W - pw))
            col = src[:, sx:sx + int(pw)]
            dy = int((H if k % 2 == 0 else -H) * (1 - p))
            y0, y1 = max(0, dy), min(H, H + dy)
            out[y0:y1, x0:x0 + col.shape[1]] = col[y0 - dy:y1 - dy]
        return blend(out, img, np.full(img.shape[:2], fo, np.float32))


@fx("doodle_boil", "El çizimi: konuşanın konturu + nesnelerin etrafına titreyen (boil) beyaz çizgiler, okla el yazısı etiketler. "
                   "Alanlar: outline (true), shapes [{type:rect|ellipse, box:[x,y,w,h], label, label_xy}], arrows [{from,to,label,label_xy}], "
                   "color ('#FFFFFF'), width (7), boil_fps (8)")
class DoodleBoil(Base):
    NEEDS_MASK = True

    def setup(self):
        self.col = hexrgb(self.g("color", "#FFFFFF"))
        self.wd = int(self.g("width", 7))
        self.step = max(1, int(round(self.fps / float(self.g("boil_fps", 8)))))

    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        seed = i // self.step
        layer = np.zeros((H, W, 4), np.uint8)
        fo = 1 - ramp(t, self.dur - 0.25, 0.25)
        if self.g("outline", True):
            mb = (cv2.resize(m, (W // 2, H // 2)) > 0.5).astype(np.uint8)
            cs, _ = cv2.findContours(mb, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if cs:
                c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(np.float32) * 2
                c = c[::6]
                # kadraj kenarına yapışan kısımları çizme
                keep = (c[:, 0] > 8) & (c[:, 0] < W - 8) & (c[:, 1] > 8) & (c[:, 1] < H - 8)
                pts = jitter(c, 3.0, seed)
                prog = ramp(t, 0.05, 0.6)
                n = int(len(pts) * prog)
                seg = []
                for k in range(n):
                    if keep[k]:
                        seg.append(pts[k])
                    elif len(seg) > 1:
                        draw_poly(layer, np.array(seg), self.col, self.wd); seg = []
                    else:
                        seg = []
                if len(seg) > 1:
                    draw_poly(layer, np.array(seg), self.col, self.wd)
        L = Image.fromarray(layer, "RGBA")
        lay = np.array(L)
        for k, sh in enumerate(self.g("shapes", [])):
            tk = 0.35 + 0.35 * k
            prog = ramp(t, tk, 0.45)
            x, y, w, h = sh["box"]
            pts = rect_pts(x, y, w, h) if sh.get("type", "rect") == "rect" else ellipse_pts(x + w / 2, y + h / 2, w / 2, h / 2)
            draw_poly(lay, jitter(pts, 2.6, seed * 7 + k), self.col, self.wd, prog)
        for k, ar in enumerate(self.g("arrows", [])):
            tk = 0.5 + 0.35 * k
            prog = ramp(t, tk, 0.35)
            pts = jitter(arrow_pts(ar["from"], ar["to"], ar.get("bend", 0.25)), 2.0, seed * 13 + k)
            draw_poly(lay, pts, self.col, self.wd - 1, prog)
            if prog >= 1:
                l, r = arrow_head(pts)
                draw_poly(lay, l, self.col, self.wd - 1); draw_poly(lay, r, self.col, self.wd - 1)
        L = Image.fromarray(lay, "RGBA")
        out = img.copy()
        over(out, L, 0, 0, fo)
        labels = [(s.get("label"), s.get("label_xy") or [s["box"][0] + s["box"][2] - 120, s["box"][1] - 80], 0.6 + 0.35 * k)
                  for k, s in enumerate(self.g("shapes", []))]
        labels += [(a.get("label"), a.get("label_xy") or [a["from"][0] - 20, a["from"][1] - 90], 0.75 + 0.35 * k)
                   for k, a in enumerate(self.g("arrows", []))]
        for k, (lab, xy, tk) in enumerate(labels):
            if not lab or t < tk:
                continue
            rot = math.sin(seed * 1.7 + k) * 2.0
            ti = text_img(lab, font("hand", int(self.g("label_size", 92))), self.col, shadow=True)
            over(out, ti, xy[0], xy[1], fo * ramp(t, tk, 0.15), 1.0, rot)
        return out


@fx("screen_wall", "Ekran görüntüsü duvarı: görseller ızgara halinde sırayla düşer (kanıt/çok kaynak). "
                   "Alanlar: items [{img}|{text,sub}], cols (4), box [x,y,w,h] (varsayılan başın üstü bandı), gap, stagger (0.07)")
class ScreenWall(Base):
    def setup(self):
        W, H = self.W, self.H
        self.box = self.g("box", [40, int(H * 0.04), W - 80, int(H * 0.26)])
        items = self.g("items") or [{"text": f"Grafik {k + 1}"} for k in range(8)]
        cols = int(self.g("cols", 4))
        rows = math.ceil(len(items) / cols)
        gap = int(self.g("gap", 14))
        x, y, w, h = self.box
        cw, ch = (w - gap * (cols - 1)) / cols, (h - gap * (rows - 1)) / rows
        self.cells = []
        for k, it in enumerate(items):
            r, c = divmod(k, cols)
            card = make_card(it, int(cw), int(ch), self.C, radius=18)
            self.cells.append((card, x + c * (cw + gap) + cw / 2, y + r * (ch + gap) + ch / 2))
        self.st = float(self.g("stagger", 0.07))

    def frame(self, i, t, img, m):
        out = img.copy()
        fo = 1 - ramp(t, self.dur - 0.3, 0.3)
        out *= 1 - 0.25 * out3(ramp(t, 0, 0.3)) * fo
        for k, (card, cx, cy) in enumerate(self.cells):
            p = ramp(t, 0.1 + self.st * k, 0.35)
            if p <= 0:
                continue
            over(out, with_shadow(card, 12, (0, 8), 0.5)[0], cx, cy - 80 * (1 - out3(p)), fo * min(1, p * 2), 0.85 + 0.15 * back(p), anchor="c")
        return out


@fx("spotlight", "Ortam kararır, yumuşak bir ışık halkası hedefi aydınlatır (gezebilir). Alanlar: path [[x,y,t],...], radius (380), "
                 "dark (0.82 kararma), in (0.35)")
class Spotlight(Base):
    def setup(self):
        self.path = self.g("path") or [[self.W * 0.62, self.H * 0.42, 0.0], [self.W * 0.35, self.H * 0.33, self.dur * 0.7]]
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        self.xx, self.yy = xx.astype(np.float32), yy.astype(np.float32)

    def pos(self, t):
        P = self.path
        if t <= P[0][2]:
            return P[0][:2]
        for a, b in zip(P, P[1:]):
            if t <= b[2]:
                q = inout3((t - a[2]) / max(1e-6, b[2] - a[2]))
                return [a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q]
        return P[-1][:2]

    def frame(self, i, t, img, m):
        x, y = self.pos(t)
        r = float(self.g("radius", 380)) * (0.6 + 0.4 * out3(ramp(t, 0, 0.5)))
        d = np.sqrt((self.xx - x) ** 2 + ((self.yy - y) * 0.9) ** 2)
        light = np.clip(1 - (d - r * 0.55) / (r * 0.6), 0, 1) ** 1.6
        p = out3(ramp(t, 0, float(self.g("in", 0.35)))) * (1 - ramp(t, self.dur - 0.3, 0.3))
        dark = float(self.g("dark", 0.82)) * p
        k = (1 - dark) + dark * light * 1.08
        return np.clip(img * k[..., None], 0, 255)


@fx("glass_type", "Buzlu cam yazı: dev harflerin içi bulanık-aydınlık video, ince beyaz kontur; arka plan kararır. "
                  "Alanlar: text ('Video\\nakışı' — satırlar \\n ile), size (200), y (0.36·H)")
class GlassType(Base):
    def setup(self):
        W, H = self.W, self.H
        lines = str(self.g("text", "Video\nakışı")).split("\n")
        f = font("black", int(self.g("size", 200)))
        im = Image.new("L", (W, H), 0)
        st = Image.new("L", (W, H), 0)
        d, ds = ImageDraw.Draw(im), ImageDraw.Draw(st)
        lh = f.getmetrics()[0] + f.getmetrics()[1] * 0.2
        y0 = float(self.g("y", H * 0.36)) - lh * len(lines) / 2
        for k, ln in enumerate(lines):
            w = f.getlength(ln)
            x = (W - w) / 2 + (k - (len(lines) - 1) / 2) * float(self.g("stagger_x", 60))
            d.text((x, y0 + k * lh), ln, font=f, fill=255)
            ds.text((x, y0 + k * lh), ln, font=f, fill=0, stroke_width=3, stroke_fill=255)
        self.mask = np.asarray(im, np.float32) / 255
        self.stroke = np.clip(np.asarray(st, np.float32) / 255 - self.mask, 0, 1)

    def frame(self, i, t, img, m):
        p = out3(ramp(t, 0, 0.5)) * (1 - ramp(t, self.dur - 0.3, 0.3))
        blur = cv2.GaussianBlur(img, (0, 0), 22)
        frost = np.clip(blur * 1.25 + 38, 0, 255)
        bgd = img * (1 - 0.45 * p)
        out = blend(bgd, frost, self.mask * p)
        return blend(out, np.full_like(img, 255), self.stroke * p * 0.75)


@fx("checklist", "Beyaz kart: başlık + kutucuklu maddeler sırayla işaretlenir. Alanlar: title, items, at [sn...], x, y, w")
class Checklist(Base):
    def setup(self):
        self.items = self.g("items") or ["Kurgu", "Efektler", "Ses efektleri", "Altyazı", "Render"]
        n = len(self.items)
        self.at = self.g("at") or [0.5 + k * 0.35 for k in range(n)]
        self.w = int(self.g("w", self.W * 0.58))
        self.xy = (self.g("x", (self.W - self.w) / 2), self.g("y", self.H * 0.30))

    def frame(self, i, t, img, m):
        out = img.copy()
        fo = 1 - ramp(t, self.dur - 0.3, 0.3)
        p = out3(ramp(t, 0, 0.35))
        n = len(self.items)
        cp = bool(self.g("compact"))
        rh, fs, ts, top, bx = (56, 30, 38, 92, 16) if cp else (78, 38, 46, 120, 21)
        h = top + 10 + rh * n
        card = rounded(self.w, h, 30, (255, 255, 255, 250))
        d = ImageDraw.Draw(card)
        d.text((44, 30 if cp else 38), self.g("title", "Video planı"), font=font("xb", ts), fill=(20, 22, 26))
        for k, it in enumerate(self.items):
            y = top + rh * k
            cy = y + rh * 0.36
            done = t >= self.at[k]
            q = back(ramp(t, self.at[k], 0.2), 2.2) if done else 0
            if done:
                s_ = bx * q
                d.rounded_rectangle([66 - s_, cy - s_, 66 + s_, cy + s_], 7, fill=self.acc_card)
                if q > 0.6:
                    d.line([(57, cy + 1), (64, cy + 8), (77, cy - 8)], fill=(255, 255, 255), width=4, joint="curve")
            else:
                d.rounded_rectangle([66 - bx, cy - bx, 66 + bx, cy + bx], 7, outline=(200, 203, 208), width=3)
            d.text((104, y + (rh * 0.36) - fs * 0.62), it, font=font("bold" if done else "semi", fs),
                   fill=(20, 22, 26) if done else (170, 172, 178))
        cs, pad = with_shadow(card, 26, (0, 16), 0.45)
        over(out, cs, self.xy[0] + self.w / 2, self.xy[1] + h / 2 + 40 * (1 - p), p * fo, 0.94 + 0.06 * p, anchor="c")
        return out


@fx("cinemascope", "Sinema bantları kayarak gelir (2.39:1 hissi) + sinematik renk (gölge camgöbeği, ten sıcak). "
                   "Alanlar: keep (0.42 görünür yükseklik oranı), center_y (0.47), title (bantta küçük serif yazı, ops.), grade (true)")
class Cinemascope(Base):
    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        p = out3(ramp(t, 0, 0.45)) * (1 - in3(ramp(t, self.dur - 0.35, 0.35)))
        keep = float(self.g("keep", 0.42))
        cy = float(self.g("center_y", 0.47)) * H
        half = (H / 2) * (1 - p) + (keep * H / 2) * p
        out = img.copy()
        if self.g("grade", True):
            lum = out.mean(2, keepdims=True) / 255
            tint = np.array([-14, 6, 16], np.float32) * (1 - lum) + np.array([14, 2, -10], np.float32) * lum
            g = np.clip((out - 128) * 1.12 + 128 + tint, 0, 255)
            out = out * (1 - p) + g * p
        top, bot = int(max(0, cy - half)), int(min(H, cy + half))
        out[:top] = 0
        out[bot:] = 0
        if self.g("title") and p > 0.5:
            ti = text_img(self.g("title"), font("serif", 64), (235, 235, 235))
            over(out, ti, W / 2, bot + (H - bot) * 0.35, ramp(t, 0.4, 0.4) * (1 - ramp(t, self.dur - 0.35, 0.3)), anchor="c")
        return out


@fx("headline_wall", "Gazete manşetleri üst üste düşer (kategori + tarih + serif italik başlık). "
                     "Alanlar: items [{cat,date,text}], at [sn...], x, y, w, rot (±3°)")
class HeadlineWall(Base):
    def setup(self):
        self.items = self.g("items") or [{"cat": "Gündem", "date": "20.10.2026", "text": "Manşet"}]
        self.at = self.g("at") or [0.15 + 0.45 * k for k in range(len(self.items))]
        self.w = int(self.g("w", self.W * 0.66))
        self.cards = []
        rng = np.random.default_rng(2)
        for it in self.items:
            f = font("serif", 56)
            lines = self.wrap(it["text"], f, self.w - 70)
            h = 92 + 64 * len(lines) + 20
            c = Image.new("RGBA", (self.w, h), (246, 243, 236, 255))
            d = ImageDraw.Draw(c)
            d.text((34, 24), it.get("cat", ""), font=font("monob", 22), fill=(30, 30, 30))
            dt = it.get("date", "")
            d.text((self.w - 34 - font("monob", 22).getlength(dt), 24), dt, font=font("monob", 22), fill=(30, 30, 30))
            d.line([(34, 58), (self.w - 34, 58)], fill=(30, 30, 30), width=2)
            for k, ln in enumerate(lines):
                d.text((34, 70 + 64 * k), ln, font=f, fill=(20, 20, 20))
            self.cards.append((with_shadow(c, 16, (0, 10), 0.5)[0], rng.uniform(-3, 3) * float(self.g("rot", 1))))
        self.x = self.g("x", (self.W - self.w) / 2)
        self.y = self.g("y", self.H * 0.06)

    @staticmethod
    def wrap(text, f, maxw):
        out, cur = [], ""
        for w in text.split():
            if cur and f.getlength(cur + " " + w) > maxw:
                out.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        return out + ([cur] if cur else [])

    def frame(self, i, t, img, m):
        out = img.copy()
        fo = 1 - ramp(t, self.dur - 0.3, 0.3)
        y = self.y
        for k, ((c, rot), tk) in enumerate(zip(self.cards, self.at)):
            if t >= tk:
                p = ramp(t, tk, 0.28)
                over(out, c, self.x + self.w / 2 + (k % 2 * 2 - 1) * 14, y + c.height / 2 - 60 * (1 - out3(p)),
                     fo * min(1, p * 2), 1.15 - 0.15 * out3(p), rot, anchor="c")
            y += c.height - 40
        return out


@fx("chart_grow", "Dev sayaç (0 → değer) + sütunlar sırayla büyür, son sütun sayaçla aynı anda iner. "
                  "Alanlar: value, label ('efekt, sıfır kurgu'), bars [..], prefix, suffix, decimals, land (sayaç iniş sn), box [x,y,w,h]")
class ChartGrow(Base):
    def setup(self):
        W, H = self.W, self.H
        self.val = float(self.g("value", 22))
        self.bars = self.g("bars") or [self.val * f for f in (0.18, 0.36, 0.55, 0.73, 0.86, 1.0)]
        self.box = self.g("box", [70, int(H * 0.05), W - 140, int(H * 0.36)])
        self.land = float(self.g("land", min(1.6, self.dur * 0.6)))
        yy = np.linspace(0, 1, H)[:, None]
        self.scrim = np.repeat(np.clip(1 - yy / 0.5, 0, 1) * 0.55, W, 1).astype(np.float32)

    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        fo = 1 - ramp(t, self.dur - 0.3, 0.3)
        p0 = out3(ramp(t, 0, 0.3)) * fo
        out = img * (1 - self.scrim[..., None] * p0)
        x, y, w, h = self.box
        q = out3(ramp(t, 0.15, self.land - 0.15))
        dec = int(self.g("decimals", 0))
        v = self.val * q
        s = f"{self.g('prefix', '')}{v:,.{dec}f}{self.g('suffix', '')}".replace(",", "X").replace(".", ",").replace("X", ".")
        num = text_img(s, font("black", int(W * 0.2)), self.acc, shadow=True)
        over(out, num, x + w - num.width, y, p0)
        lab = text_img(self.g("label", "efekt, sıfır kurgu"), font("xb", 40), (255, 255, 255), shadow=True)
        over(out, lab, x + w - lab.width - 10, y + num.height - 18, p0)
        n = len(self.bars)
        bw = w / n * 0.68
        base_y = y + h
        mx = max(self.bars)
        top_h = h - num.height - 40
        for k, b in enumerate(self.bars):
            tk = 0.15 + (self.land - 0.45) * k / max(1, n - 1)
            pk = out3(ramp(t, tk, 0.45))
            bh = top_h * (b / mx) * pk
            bx = x + k * (w / n)
            if bh < 2:
                continue
            bar = rounded(bw, max(4, bh), 8, self.acc + (255,))
            over(out, with_shadow(bar, 10, (0, 6), 0.35)[0], bx - 20, base_y - bh - 20, fo)
            lt = text_img(f"{b:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", "."), font("bold", 26), (255, 255, 255))
            over(out, lt, bx + bw / 2 - lt.width / 2, base_y - bh - 38, fo * pk)
        return out


@fx("lower_third", "İsim bandı: vurgu renginde blok + isim (koyu, kalın), altında unvan (beyaz). Soldan silinerek gelir. "
                   "Alanlar: name ('Semih Şahin'), title ('BorsaSemih'), x (60), y (0.56·H)")
class LowerThird(Base):
    def setup(self):
        self.name = text_img(self.g("name", "Semih Şahin"), font("black", 50), self.ink)
        self.title = text_img(self.g("title", "BorsaSemih"), font("semi", 32), (255, 255, 255), shadow=True)
        self.xy = (self.g("x", 60), self.g("y", self.H * 0.56))

    def frame(self, i, t, img, m):
        out = img.copy()
        x, y = self.xy
        p = out3(ramp(t, 0.05, 0.4))
        q = 1 - in3(ramp(t, self.dur - 0.3, 0.3))
        w = self.name.width + 40
        bar = rounded(max(2, w * p * q), self.name.height + 10, 6, self.acc + (255,))
        over(out, bar, x, y)
        if p > 0.5:
            nm = self.name.crop((0, 0, int(max(1, (w * p * q) - 20)), self.name.height))
            over(out, nm, x + 20, y + 5, q)
        over(out, self.title, x + 20 - 30 * (1 - out3(ramp(t, 0.3, 0.35))), y + self.name.height + 20,
             ramp(t, 0.3, 0.3) * q)
        return out


@fx("zoom_through", "Geçiş: kesimden önce kamera hedefe hızla dalar (zoom blur), sonraki plan büyük-bulanık başlayıp yerine oturur. "
                    "Kesim segmentin içinde: cut (sn), point [x,y] (dalınan nokta, ör. ekran), pre (0.35), post (0.35)")
class ZoomThrough(Base):
    def frame(self, i, t, img, m):
        c = float(self.g("cut", self.dur / 2))
        pre, post = float(self.g("pre", 0.35)), float(self.g("post", 0.35))
        px, py = self.g("point", [self.W * 0.6, self.H * 0.4])
        if c - pre <= t < c:
            q = in3(ramp(t, c - pre, pre))
            s = 1 + 2.4 * q
            return zoom_blur(img, s, s * (1 + 0.18 * q), px, py, 6) * (1 - 0.15 * q) + 255 * 0.15 * q
        if c <= t < c + post:
            q = 1 - out3(ramp(t, c, post))
            s = 1 + 0.9 * q
            return zoom_blur(img, s, s * (1 + 0.12 * q), self.W / 2, self.H * 0.42, 6)
        return img


@fx("kinetic_captions", "Söylenen kelimeler ekranda kelime kelime dizilir (karışık tipografi: kalın / serif italik / vurgu). "
                        "Alanlar: lines [[{w, s:'b'|'s'|'a', at}]...] — at = kelimenin söylendiği sn; box (koyu cam kutu, true), y (0.38·H)")
class KineticCaptions(Base):
    STY = {"b": ("black", 76, "white"), "s": ("serif", 96, "white"), "a": ("black", 104, "acc"), "m": ("xb", 56, "white")}

    def setup(self):
        lines = self.g("lines") or [[{"w": "Söylediğim", "s": "b", "at": 0.3}], [{"w": "her", "s": "s", "at": 0.6}],
                                    [{"w": "kelime", "s": "a", "at": 0.9}], [{"w": "ekranda", "s": "b", "at": 1.3}]]
        self.rows = []
        for ln in lines:
            row = []
            for wd in ln:
                fn, sz, col = self.STY.get(wd.get("s", "b"), self.STY["b"])
                rgb = self.acc if col == "acc" else (255, 255, 255)
                row.append((text_img(wd["w"], font(fn, sz), rgb, shadow=True), float(wd.get("at", 0.3))))
            self.rows.append(row)

    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        fo = 1 - ramp(t, self.dur - 0.3, 0.3)
        out = img.copy()
        hs = [max(im.height for im, _ in r) - 18 for r in self.rows]
        tot = sum(hs)
        y = float(self.g("y", H * 0.38)) - tot / 2
        if self.g("box", True):
            bw = max(sum(im.width for im, _ in r) + 2 * (len(r) - 1) for r in self.rows) + 120
            bx = rounded(bw, tot + 90, 36, (12, 12, 14, 150))
            over(out, bx, W / 2, y + tot / 2 + 10, fo * out3(ramp(t, 0, 0.3)), anchor="c")
        for r, h in zip(self.rows, hs):
            rw = sum(im.width for im, _ in r) + 2 * (len(r) - 1)
            x = (W - rw) / 2
            for im, at in r:
                if t >= at - 0.05:
                    p = ramp(t, at - 0.05, 0.22)
                    over(out, im, x + im.width / 2, y + h / 2 + 24 * (1 - out3(p)), fo * min(1, p * 2), 0.9 + 0.1 * back(p), anchor="c")
                x += im.width + 2
            y += h
        return out


@fx("pull_back_reveal", "Açılış: çok yakın kadrajdan (yüz/detay) geniş plana çekilerek ortam açığa çıkar. "
                        "Alanlar: point [x,y] (başlangıç odağı), zoom (2.2), dur_in (segment süresi), reverse (false → push-in)")
class PullBack(Base):
    def frame(self, i, t, img, m):
        px, py = self.g("point", [self.W * 0.3, self.H * 0.33])
        z = float(self.g("zoom", 2.2))
        d = float(self.g("dur_in", self.dur))
        q = inout3(ramp(t, 0, d))
        if self.g("reverse"):
            q = 1 - q
        s = z + (1 - z) * q
        cx, cy = px + (self.W / 2 - px) * q, py + (self.H / 2 - py) * q
        out = scale_about(img, s, cx, cy) if s > 1.001 else img
        if q < 0.25:
            out = cv2.GaussianBlur(out, (0, 0), 3 * (1 - q / 0.25) + 0.01)
        return out


@fx("freeze_frame", "Kare donar (hafif flaş + karartma), üstüne vurgu renginde el çizimi daireler/oklar ve el yazısı notlar gelir. "
                    "Alanlar: at (donma sn, 0), shapes/arrows (doodle_boil ile aynı), color (tema vurgusu), dim (0.15). "
                    "Not: video donar ama ses akar — konuşma olmayan anda ya da kapanışta kullan.")
class FreezeFrame(DoodleBoil):
    NEEDS_MASK = False

    def setup(self):
        self.s.setdefault("outline", False)
        self.s.setdefault("color", self.C.get("accent_video", self.C["accent"]))
        super().setup()
        self.col = hexrgb(self.s["color"])
        self.held = None

    def frame(self, i, t, img, m):
        at = float(self.g("at", 0.0))
        if t < at:
            return img
        if self.held is None:
            self.held = img.copy()
        tt = t - at
        base = self.held * (1 - float(self.g("dim", 0.15)) * out3(ramp(tt, 0, 0.2)))
        flash = max(0.0, 1 - tt / 0.12) * 0.55
        base = base * (1 - flash) + 255 * flash
        return super().frame(i, tt + 0.0, base, m)


@fx("whip_pan", "Geçiş: kesimde yatay hızlı kaydırma + hareket bulanıklığı + ince ışık çizgileri. "
                "Alanlar: cut (sn), dir ('left'), pre (0.18), post (0.2), streaks (true)")
class WhipPan(Base):
    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        c = float(self.g("cut", self.dur / 2))
        pre, post = float(self.g("pre", 0.18)), float(self.g("post", 0.2))
        sgn = -1 if self.g("dir", "left") == "left" else 1
        if c - pre <= t < c:
            q = in3(ramp(t, c - pre, pre)); off = sgn * W * 0.55 * q
        elif c <= t < c + post:
            q = 1 - out3(ramp(t, c, post)); off = -sgn * W * 0.55 * q
        else:
            return img
        M = np.float32([[1, 0, off], [0, 1, 0]])
        sh = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_WRAP)
        k = int(9 + 160 * q) | 1
        out = cv2.blur(sh, (k, 1))
        if self.g("streaks", True) and q > 0.2:
            rng = np.random.default_rng(i)
            for _ in range(5):
                y = int(rng.uniform(0.1, 0.9) * H)
                cv2.line(out, (0, y), (W, y), (255, 255, 255), 2, cv2.LINE_AA)
        return out


# ─────────── kalıplar (referans videonun açılış/kapanışı) ───────────

@fx("hook_stack", "Hook başlığı: 2-4 satır dev kalın yazı satır satır (alttan) gelir, son satır(lar) vurgu renginde; video kararır. "
                  "Alanlar: lines ['Bu videodaki', 'her efekti', '*Claude yaptı*'], at [sn...], size (120), y (0.30·H)")
class HookStack(Base):
    def setup(self):
        self.lines = self.g("lines") or ["Bu videodaki", "her efekti", "*Claude yaptı*"]
        self.at = self.g("at") or [0.05 + 0.25 * k for k in range(len(self.lines))]
        sz = int(self.g("size", 120))
        self.ims = [text_img(l, font("black", sz), (255, 255, 255), acc=self.acc, stroke=0, shadow=True) for l in self.lines]

    def frame(self, i, t, img, m):
        out = img * (1 - 0.35 * out3(ramp(t, 0, 0.25)) * (1 - ramp(t, self.dur - 0.25, 0.25)))
        y = float(self.g("y", self.H * 0.30)) - sum(im.height - 30 for im in self.ims) / 2
        fo = 1 - ramp(t, self.dur - 0.25, 0.25)
        for im, at in zip(self.ims, self.at):
            p = ramp(t, at, 0.25)
            if p > 0:
                over(out, im, self.W / 2, y + im.height / 2 + 40 * (1 - out3(p)), fo * min(1, p * 2), anchor="c")
            y += im.height - 30
        return out


@fx("save_cta", "Kapanış: video bulanıklaşıp kararır, kaydet (bookmark) simgesi düşer + 'Bu videoyu kaydet' + alt satır. "
                "Alanlar: text ('Bu videoyu\\n*kaydet*' — satırlar \\n), sub ('Lazım olunca bulursun'), size (104), y (0.32·H)")
class SaveCTA(Base):
    def setup(self):
        lines = str(self.g("text", "Bu videoyu\n*kaydet*")).split("\n")
        ims = [text_img(l, font("black", int(self.g("size", 104))), (255, 255, 255), acc=self.acc, shadow=True) for l in lines]
        self.t1 = Image.new("RGBA", (max(i.width for i in ims), sum(i.height - 22 for i in ims) + 22), (0, 0, 0, 0))
        y_ = 0
        for im_ in ims:
            self.t1.alpha_composite(im_, ((self.t1.width - im_.width) // 2, y_)); y_ += im_.height - 22
        self.t2 = text_img(self.g("sub", "Lazım olunca bulursun"), font("semi", 40), (210, 212, 216), shadow=True)
        ic = Image.new("RGBA", (120, 150), (0, 0, 0, 0))
        ImageDraw.Draw(ic).polygon([(0, 0), (120, 0), (120, 150), (60, 104), (0, 150)], fill=self.acc + (255,))
        self.icon = ic

    def frame(self, i, t, img, m):
        p = out3(ramp(t, 0, 0.4))
        bl = cv2.GaussianBlur(img, (0, 0), 14)
        out = blend(img, bl * 0.42, np.full(img.shape[:2], p, np.float32))
        y = float(self.g("y", self.H * 0.32))
        q = back(ramp(t, 0.15, 0.35), 2.0)
        over(out, self.icon, self.W / 2, y - 120 - 60 * (1 - min(1, q)), min(1, ramp(t, 0.15, 0.15)), anchor="c")
        r = ramp(t, 0.3, 0.3)
        over(out, self.t1, self.W / 2, y + self.t1.height / 2 - 30 + 30 * (1 - out3(r)), r, anchor="c")
        over(out, self.t2, self.W / 2, y + self.t1.height + 10, ramp(t, 0.5, 0.3), anchor="c")
        return out


# ───────────────────────────── çalıştırıcı ─────────────────────────────

def run(spec, seg: Path, out: Path, mask: Path | None = None, still: float | None = None):
    th = spec.get("theme", os.environ.get("STUDIO_THEME", "krem"))
    C = dict(THEMES.get(th, next(iter(THEMES.values()))))
    cls = REG[spec["fx"]]
    W, H, fps, dur = probe(seg)
    fps = float(spec.get("fps", round(fps, 3)))
    eff = cls(spec, W, H, fps, dur, C)
    mpath = ensure_mask(seg, mask) if cls.NEEDS_MASK else None
    if still is not None:
        i = int(still * fps)
        # freeze_frame vb. durumlu efektler için baştan oynat (kısa segment)
        stateful = spec["fx"] in ("freeze_frame",)
        src = frames(seg, W, H, fps, None if stateful else still)
        ms = frames(mpath, W, H, fps, None if stateful else still, gray_alpha=True) if mpath else None
        k0 = 0 if stateful else i
        for k, img in enumerate(src, k0):
            m = clean_mask(next(ms)) if ms else np.zeros((H, W), np.float32)
            res = eff.frame(k, k / fps, img, m)
            if k >= i:
                Image.fromarray(np.clip(res, 0, 255).astype(np.uint8)).save(out)
                print(f"kare: {out}")
                return
        return
    tmp = out.with_suffix(".noaudio.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                            "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    ms = frames(mpath, W, H, fps, gray_alpha=True) if mpath else None
    n = 0
    for k, img in enumerate(frames(seg, W, H, fps)):
        m = next(ms, None) if ms else None
        m = np.zeros((H, W), np.float32) if m is None else clean_mask(m)
        res = eff.frame(k, k / fps, img, m)
        enc.stdin.write(np.clip(res, 0, 255).astype(np.uint8).tobytes())
        n += 1
    enc.stdin.close(); enc.wait()
    # sesi kaynaktan geri koy (varsa)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-i", str(seg), "-map", "0:v", "-map", "1:a?",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", str(out)], capture_output=True, text=True)
    if r.returncode:
        shutil.move(tmp, out)
    else:
        tmp.unlink(missing_ok=True)
    print(f"{spec['fx']}: {n} kare → {out}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for k, c in REG.items():
            print(f"• {k}{'  [maske]' if c.NEEDS_MASK else ''}\n    {c.DOC}")
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("--in", dest="inp", type=Path, help="hazır segment")
    ap.add_argument("--base", type=Path, help="base.mp4 (—at/—dur ile segment kesilir)")
    ap.add_argument("--at", type=float)
    ap.add_argument("--dur", type=float)
    ap.add_argument("--mask", type=Path)
    ap.add_argument("--still", type=float)
    ap.add_argument("-o", "--out", type=Path, required=True)
    a = ap.parse_args()
    spec = json.loads(a.spec.read_text())
    seg = a.inp
    if a.base:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        seg = a.out.with_suffix(".src.mp4")
        if not seg.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a.at:.3f}", "-t", f"{a.dur:.3f}", "-i", str(a.base),
                            "-vf", "fps=30", "-c:v", "libx264", "-crf", "12", "-c:a", "aac", "-b:a", "256k", str(seg)], check=True)
    for k in ("image",):  # spec'e göre göreli yollar
        if spec.get(k) and not Path(spec[k]).is_absolute():
            spec[k] = str(a.spec.parent / spec[k])
    for it in spec.get("items", []) or []:
        if isinstance(it, dict) and it.get("img") and not Path(it["img"]).is_absolute():
            it["img"] = str(a.spec.parent / it["img"])
    run(spec, seg, a.out, a.mask, a.still)


if __name__ == "__main__":
    main()
