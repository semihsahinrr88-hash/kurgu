"""Teslim: platforma uygun final + kapak.

  python export.py reels  <final.mp4> <out.mp4>        # Instagram Reels / Shorts / TikTok (1080x1920)
  python export.py youtube <final.mp4> <out.mp4>       # YouTube 16:9
  python export.py cover <video> <out.jpg> --t 1.2 --title "Faiz *düşerse* ne olur?" [--youtube]

Reels: H.264 High, yuv420p, sabit 30 fps, ~12 Mbps tepe, AAC 48 kHz 256k, faststart.
Instagram yüklemede yeniden sıkıştırır; temiz kaynak vermek bulanıklığı azaltır.
Kapak (Reels): 1080x1920, başlık ızgara kırpmasında görünsün diye ORTA 1080x1350 alanda
(profil ızgarası 3:4 ortayı gösterir). *kelime* turuncu. Tamamı büyük harf yok.
YouTube kapağı: 1280x720, sol yarıda başlık, sağda yüz.
"""
from __future__ import annotations
import argparse, re, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

_B = Path(__file__).resolve().parent
PKG = _B if (_B / "fonts").exists() else _B.parent   # ~/studio/ veya paket kökü
ACCENT, WHITE = (255, 140, 30), (255, 255, 255)


def enc(src, out, w, h, fps=30):
    vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x08142D,fps={fps},format=yuv420p"
    subprocess.run(["ffmpeg", "-y", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-profile:v", "high", "-preset", "slow",
                    "-crf", "17", "-maxrate", "12M" if h > w else "16M", "-bufsize", "24M", "-g", str(fps * 2),
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", str(out)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print(out)


def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t.replace("*", ""), font=font) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + [cur]


def cover(video, out, t, title, youtube=False):
    W, H = (1280, 720) if youtube else (1080, 1920)
    tmp = Path(out).with_suffix(".frame.png")
    subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-update", "1", str(tmp)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    im = Image.open(tmp).convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
    # okunurluk perdesi
    sh = Image.new("L", (W, H), 0); g = ImageDraw.Draw(sh)
    if youtube:
        for x in range(W): g.line([(x, 0), (x, H)], fill=int(200 * max(0, 1 - x / (W * 0.62))))
    else:
        for y in range(H): g.line([(0, y), (W, y)], fill=int(200 * min(1, max(0, (y - H * 0.36) / (H * 0.26)))))
    im = Image.composite(Image.new("RGB", (W, H), (8, 20, 45)), im, sh)
    d = ImageDraw.Draw(im)
    size = 64 if youtube else 104
    font = ImageFont.truetype(str(PKG / "fonts" / "Montserrat-Black.ttf"), size)
    maxw = W * 0.52 if youtube else W - 140
    lines = wrap(d, title, font, maxw)
    lh = int(size * 1.08)
    y0 = (H - lh * len(lines)) // 2 if youtube else int(H * 0.5)  # Reels: 3:4 ızgara kırpmasının içinde
    x0 = 56 if youtube else 70
    for i, ln in enumerate(lines):
        x = x0
        for part in re.split(r"(\*[^*]+\*)", ln):
            if not part:
                continue
            col = ACCENT if part.startswith("*") else WHITE
            txt = part.strip("*")
            d.text((x + 3, y0 + i * lh + 4), txt, font=font, fill=(0, 0, 0))
            d.text((x, y0 + i * lh), txt, font=font, fill=col)
            x += d.textlength(txt, font=font)
    im.save(out, quality=94)
    tmp.unlink(missing_ok=True)
    print(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["reels", "youtube", "cover"])
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--t", type=float, default=1.0)
    ap.add_argument("--title", default="")
    ap.add_argument("--youtube", action="store_true")
    a = ap.parse_args()
    if a.mode == "reels":
        enc(a.src, a.out, 1080, 1920)
    elif a.mode == "youtube":
        enc(a.src, a.out, 1920, 1080)
    else:
        cover(a.src, a.out, a.t, a.title, a.youtube)
