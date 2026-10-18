"""Sahne önizleme (hyperframes render'ından hızlı): scene.py'nin yazdığı index.html'i Chromium'da açar,
GSAP zaman çizelgesini istenen anlara sarar ve kare alır. İstenirse arka plana video karesi koyar.

  python peek.py <sahne_klasörü> --at 0.5 1.5 3 -o kareler/        # PNG kareler (şeffaf)
  python peek.py <sahne_klasörü> --mp4 onizleme.mp4 --bg kare.jpg   # 30 fps kısa mp4 (sesiz)
  --split : bg karesini Reels split düzenine koyar (konuşan alt %55, panel üstte)

Not: final overlay için yine scene.py (hyperframes render → webm) kullanılır; bu araç QA ve storyboard içindir.
"""
from __future__ import annotations

import argparse, json, subprocess, tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

INIT = "window.__timelines = {};"


def load(page, d: Path):
    page.add_init_script(INIT)
    page.goto((d / "index.html").resolve().as_uri())
    for _ in range(150):
        if page.evaluate("!!(window.__timelines && window.__timelines.main)"):
            break
        page.wait_for_timeout(100)
    else:
        raise SystemExit("zaman çizelgesi yüklenmedi")
    meta = page.evaluate("(()=>{const s=document.getElementById('stage');return {w:+s.dataset.width,h:+s.dataset.height,d:+s.dataset.duration};})()")
    return meta


def shoot(page, t, path):
    page.evaluate(f"void window.__timelines.main.seek({t}, false)")
    page.locator("#stage").screenshot(path=str(path), omit_background=True)


def compose_bg(png: Path, bg: Path, out: Path, split: bool, W: int, H: int):
    if split:
        flt = (f"[1:v]scale={W}:-2,crop={W}:{int(H*0.55)}:0:(ih-{int(H*0.55)})*0.55[s];"
               f"color=c=0xEFE8DB:s={W}x{H}[c];[c][s]overlay=0:{H-int(H*0.55)}[b];[b][0:v]overlay=0:0")
    else:
        flt = f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[b];[b][0:v]overlay=0:0"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(png), "-i", str(bg), "-filter_complex", flt,
                    "-frames:v", "1", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", type=Path)
    ap.add_argument("--at", type=float, nargs="*")
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--mp4", type=Path)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--bg", type=Path)
    ap.add_argument("--split", action="store_true")
    a = ap.parse_args()
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        meta = load(page, a.dir)
        page.set_viewport_size({"width": meta["w"], "height": meta["h"]})
        if a.at:
            out = a.out or (a.dir / "peek")
            out.mkdir(parents=True, exist_ok=True)
            for t in a.at:
                f = out / f"t{t:05.2f}.png"
                shoot(page, t, f)
                if a.bg:
                    compose_bg(f, a.bg, f.with_suffix(".jpg"), a.split, meta["w"], meta["h"])
                print(f)
        if a.mp4:
            tmp = Path(tempfile.mkdtemp())
            n = int(meta["d"] * a.fps)
            for i in range(n):
                shoot(page, i / a.fps, tmp / f"f{i:04d}.png")
            if a.bg:
                fl = (f"[1:v]scale={meta['w']}:-2,crop={meta['w']}:{int(meta['h']*0.55)}:0:(ih-{int(meta['h']*0.55)})*0.55[s];"
                      f"color=c=0xEFE8DB:s={meta['w']}x{meta['h']}[c];[c][s]overlay=0:{meta['h']-int(meta['h']*0.55)}[bb];[bb][0:v]overlay=0:0") if a.split else \
                     (f"[1:v]scale={meta['w']}:{meta['h']}:force_original_aspect_ratio=increase,crop={meta['w']}:{meta['h']}[bb];[bb][0:v]overlay=0:0")
                cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", str(tmp / "f%04d.png"),
                       "-loop", "1", "-i", str(a.bg), "-filter_complex", fl + ",format=yuv420p", "-t", str(meta["d"]),
                       "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", str(a.mp4)]
            else:
                cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", str(tmp / "f%04d.png"),
                       "-vf", "format=yuv420p", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", str(a.mp4)]
            subprocess.run(cmd, check=True)
            print(a.mp4)
        b.close()


if __name__ == "__main__":
    main()
