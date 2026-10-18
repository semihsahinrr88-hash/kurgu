"""Storyboard: render'dan ÖNCE kare kare onay görseli (Justin'in "shot by shot artboard" adımı).

EDL'deki her range için bir kare üretir: kaynak kare + zoom/layout (render.py ile aynı matematik)
+ o anda ekranda olan sahnenin (overlay) karesi + altyazı cümlesi + numara/saniye/neden etiketi.
Sonuç tek bir JPG (Semih telefondan bakar, "3 numarayı tam ekran yap" der).

  python storyboard.py <proje>/edit [-o <proje>/edit/storyboard.jpg] [--cols 4]

Sahne kareleri peek.py ile alınır (overlay'in "file" yolunun klasöründeki index.html).
Render gerektirmez: sahneler --no-render ile yazılmış olması yeterli.
"""
from __future__ import annotations

import argparse, json, subprocess, tempfile, textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts" if (HERE / "fonts").exists() else HERE.parent / "fonts"
W, H = 1080, 1920
PANEL = (0xEF, 0xE8, 0xDB)
ORANGE = (0xFF, 0x8C, 0x1E)
INK = (0x22, 0x1E, 0x1B)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def src_frame(src: str, t: float, zoom: float, push: float, layout: str, out: Path):
    z = zoom + push * 0.5
    vf = [f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"]
    if z > 1.0:
        vf.append(f"scale=trunc({W}*{z:.4f}/2)*2:trunc({H}*{z:.4f}/2)*2,crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.35")
    if layout == "split":
        ph = int(H * 0.55) // 2 * 2
        vf.append(f"crop={W}:{ph}:0:({H}-{ph})*0.55,pad={W}:{H}:0:{H-ph}:color=0xEFE8DB")
    elif layout == "pip":
        pw, phh = int(W * 0.45) // 2 * 2, int(H * 0.45) // 2 * 2
        x, y = W - pw - int(W * 0.05), H - phh - int(H * 0.22)
        vf.append(f"scale={pw}:{phh},pad={W}:{H}:{x}:{y}:color=0xEFE8DB")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
                    "-vf", ",".join(vf), str(out)], check=True)


def scene_still(scene_dir: Path, t: float, out: Path) -> bool:
    if not (scene_dir / "index.html").exists():
        return False
    r = subprocess.run(["python3", str(HERE / "peek.py"), str(scene_dir), "--at", f"{t:.2f}", "-o", str(out.parent / scene_dir.name)],
                       capture_output=True, text=True)
    p = out.parent / scene_dir.name / f"t{t:05.2f}.png"
    if r.returncode or not p.exists():
        return False
    p.rename(out)
    return True


def draw_caption(img: Image.Image, text: str, layout: str):
    d = ImageDraw.Draw(img)
    f = font("Montserrat-ExtraBold.ttf", 62)
    lines = textwrap.wrap(text, 24)[:2]
    y = (650 if layout == "split" else 1400) + (0 if len(lines) > 1 else 40)
    for ln in lines:
        col = INK if layout == "split" else (255, 255, 255)
        if layout != "split":
            for dx in (-3, 3):
                for dy in (-3, 3):
                    d.text((70 + dx, y + dy), ln, font=f, fill=(0, 0, 0))
        d.text((70, y), ln, font=f, fill=col)
        y += 80


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--thumb", type=int, default=360)
    a = ap.parse_args()
    edl = json.loads((a.edit / "edl.json").read_text())
    srcs = edl["sources"]
    overlays = edl.get("overlays", [])
    tmp = Path(tempfile.mkdtemp())
    cards = []
    t_out = 0.0
    for i, r in enumerate(edl["ranges"]):
        dur = r["end"] - r["start"]
        sample = t_out + dur / 2
        ov = None
        for o in overlays:
            s0, s1 = o["start_in_output"], o["start_in_output"] + o["duration"]
            if min(s1, t_out + dur) - max(s0, t_out) > 0.25:
                ov = o
                spec_p = a.edit / Path(o["file"]).parent / "spec.json"
                sp = json.loads(spec_p.read_text()) if spec_p.exists() else {}
                land = max([float(sp.get("land", 0))] + [float(x) for x in sp.get("at", [])] + [float(sp.get("stamp_at", 0))] or [1.0])
                sample = min(max(s0 + land + 0.6, t_out + 0.1), min(s1, t_out + dur) - 0.35)
                break
        fr = tmp / f"f{i}.png"
        src_frame(srcs[r["source"]], r["start"] + (sample - t_out), float(r.get("zoom", 1.0)), float(r.get("push", 0.0)),
                  r.get("layout", "talk"), fr)
        img = Image.open(fr).convert("RGBA")
        tag = ""
        if ov:
            st = tmp / f"s{i}.png"
            if scene_still(a.edit / Path(ov["file"]).parent, sample - ov["start_in_output"], st):
                img.alpha_composite(Image.open(st).convert("RGBA").resize((W, H)))
            tag = Path(ov["file"]).parent.name
        draw_caption(img, r.get("quote", ""), r.get("layout", "talk"))
        th = img.convert("RGB").resize((a.thumb, int(a.thumb * H / W)))
        lab = f"{r.get('layout','talk')}" + (f" · zoom {r['zoom']}" if r.get("zoom") else "") + (f" · push" if r.get("push") else "")
        cards.append((th, i + 1, t_out, lab, tag, r.get("reason", "")))
        t_out += dur
    cols = a.cols
    tw, thh = cards[0][0].size
    pad, lab_h = 24, 150
    rows = (len(cards) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (thh + lab_h + pad) + pad + 70), PANEL)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 18), f"Storyboard · {len(cards)} sahne · {t_out:.1f} sn", font=font("Montserrat-Black.ttf", 40), fill=INK)
    fn, fs, fm = font("Montserrat-Black.ttf", 44), font("Montserrat-Bold.ttf", 22), font("JetBrainsMono-Medium.ttf", 20)
    for k, (th, n, t0, lab, tag, why) in enumerate(cards):
        x = pad + (k % cols) * (tw + pad)
        y = 70 + pad + (k // cols) * (thh + lab_h + pad)
        sheet.paste(th, (x, y))
        d.rounded_rectangle((x + tw - 78, y + thh - 66, x + tw - 10, y + thh - 10), 12, fill=ORANGE)
        d.text((x + tw - 44, y + thh - 38), str(n), font=fn, fill=(255, 255, 255), anchor="mm")
        d.text((x, y + thh + 10), f"{int(t0//60)}:{t0%60:04.1f}  {lab}", font=fm, fill=INK)
        if tag:
            d.text((x, y + thh + 38), f"sahne: {tag}", font=fm, fill=(0xD9, 0x67, 0x0A))
        for j, ln in enumerate(textwrap.wrap(why, 30)[:3]):
            d.text((x, y + thh + 66 + j * 26), ln, font=fs, fill=(0x6F, 0x64, 0x58))
    out = a.out or (a.edit / "storyboard.jpg")
    sheet.save(out, quality=88)
    print(out)


if __name__ == "__main__":
    main()
