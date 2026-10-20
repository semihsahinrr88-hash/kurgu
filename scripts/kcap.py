"""Kelime kutulu altyazı (karaoke) — referans: oguzhan.guzelkaralar. ORTALI, beyaz kalın, söylenen kelime yarı saydam kutuda.

make_ass.py'nin (sola hizalı, renkli kelime) alternatifi; çıktı bir ALFA KATMANI (.mov, qtrle) — final birleştirmede
ass yerine EN SON overlay edilir. Her kelime-durumu tek PNG, ffmpeg concat ile 30 fps'e dökülür (hızlı).

Kullanım:
  python3 kcap.py <edit_dir> [-o <edit_dir>/kcap.mov] [--skip 51.5-54.9,...] [--words 5] [--y 1290]
Gereken: <edit_dir>/edl.json (+ offs.json varsa gerçek zamanlar onunla), transcripts/<kaynak>.json
split layout'lu range'lerde altyazı panel şeridine (y≈690) koyu mürekkeple taşınır.
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

_B = Path(__file__).resolve().parent
PKG = _B if (_B / "fonts").exists() else _B.parent
SIZE = int(os.environ.get("KCAP_SIZE", 56))  # 20.10: 68 fazla büyük bulundu (Semih) → A altyazısıyla aynı görünür boy
F = ImageFont.truetype(str(PKG / "fonts" / "Montserrat-ExtraBold.ttf"), SIZE)
W, H = 1080, 1920


def words_out(E: Path):
    edl = json.loads((E / "edl.json").read_text())
    offs = json.loads((E / "offs.json").read_text())["offs"] if (E / "offs.json").exists() else None
    T = {}
    out, t = [], 0.0
    for i, r in enumerate(edl["ranges"]):
        s = r["source"]
        if s not in T:
            T[s] = [w for w in json.loads((E / "transcripts" / f"{s}.json").read_text())["words"] if w.get("type") == "word"]
        o = offs[i] if offs else t
        dur = r["end"] - r["start"]
        for w in T[s]:
            if r["start"] - 0.02 <= w["start"] < r["end"]:
                out.append(dict(text=w["text"], s=o + w["start"] - r["start"], e=min(o + w["end"] - r["start"], o + dur),
                                split=r.get("layout") == "split", rng=i))
        t += dur
    return out


def chunks(ws, maxw=5):
    ch, cur = [], []
    for k, w in enumerate(ws):
        if cur and (len(cur) >= maxw or w["s"] - cur[-1]["e"] > 0.45 or w["rng"] != cur[-1]["rng"] and w["s"] - cur[-1]["e"] > 0.15):
            ch.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w["text"]):
            ch.append(cur); cur = []
    if cur:
        ch.append(cur)
    return ch


def layout(words):
    """iki satıra dengeli böl; her kelimenin (x, satır) konumu"""
    txt = [w["text"].rstrip(".,") if not w["text"].endswith("?") else w["text"] for w in words]
    sp = F.getlength(" ")
    widths = [F.getlength(t) for t in txt]
    best, cut = 1e9, len(txt)
    if sum(widths) + sp * (len(txt) - 1) > 900:
        for c in range(1, len(txt)):
            a = sum(widths[:c]) + sp * (c - 1); b = sum(widths[c:]) + sp * (len(txt) - c - 1)
            if max(a, b) < best:
                best, cut = max(a, b), c
    lines = [list(range(cut)), list(range(cut, len(txt)))] if cut < len(txt) else [list(range(len(txt)))]
    pos = {}
    for li, ln in enumerate(lines):
        lw = sum(widths[i] for i in ln) + sp * (len(ln) - 1)
        x = (W - lw) / 2
        for i in ln:
            pos[i] = (x, li, widths[i]); x += widths[i] + sp
    return txt, pos, len(lines)


def render(words, active, split, y0):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    txt, pos, nl = layout(words)
    d = ImageDraw.Draw(im)
    lh = int(SIZE * 1.3)
    y_top = (y0 if not split else 640) - (nl - 1) * lh / 2
    if active is not None:
        x, li, ww = pos[active]
        y = y_top + li * lh
        box = (255, 255, 255, 72) if not split else (15, 124, 140, 60)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle([x - 12, y - 5, x + ww + 12, y + int(SIZE * 1.2)], 14, fill=box)
        im.alpha_composite(ov)
    for i, t in enumerate(txt):
        x, li, ww = pos[i]
        y = y_top + li * lh
        if split:
            d.text((x, y), t, font=F, fill=(20, 38, 43))
        else:
            d.text((x, y), t, font=F, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir", type=Path)
    ap.add_argument("-o", type=Path)
    ap.add_argument("--skip", default="", help="altyazı olmayacak aralıklar: 51.5-54.9,63-64")
    ap.add_argument("--words", type=int, default=5)
    ap.add_argument("--y", type=float, default=1290)
    ap.add_argument("--end", type=float, help="toplam süre (varsayılan offs end)")
    a = ap.parse_args()
    E = a.edit_dir
    out = a.o or E / "kcap.mov"
    skip = [tuple(map(float, x.split("-"))) for x in a.skip.split(",") if x]
    ws = [w for w in words_out(E) if not any(s0 <= w["s"] < s1 for s0, s1 in skip)]
    end = a.end or (json.loads((E / "offs.json").read_text())["end"] if (E / "offs.json").exists() else ws[-1]["e"] + 0.5)
    tmp = Path(tempfile.mkdtemp(prefix="kcap_"))
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(tmp / "empty.png")
    seq, t = [], 0.0
    CH = chunks(ws, a.words)
    for ci, ch in enumerate(CH):
        c0 = ch[0]["s"]
        c1 = CH[ci + 1][0]["s"] if ci + 1 < len(CH) else min(end, ch[-1]["e"] + 0.4)
        c1 = min(c1, ch[-1]["e"] + 0.6)
        if c0 > t + 1e-3:
            seq.append(("empty.png", c0 - t)); t = c0
        for k, w in enumerate(ch):
            s = max(t, w["s"]); e = ch[k + 1]["s"] if k + 1 < len(ch) else c1
            if e - s <= 0.001:
                continue
            fn = f"c{ci:04d}_{k:02d}.png"
            render(ch, k, ch[0]["split"], a.y).save(tmp / fn)
            seq.append((fn, e - t)); t = e
    if end > t:
        seq.append(("empty.png", end - t))
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{tmp / f}'\nduration {d:.4f}\n" for f, d in seq) + f"file '{tmp / seq[-1][0]}'\n")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", "fps=30,format=argb",
                        "-c:v", "qtrle", "-t", f"{end:.3f}", str(out)], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-1500:]); raise SystemExit(1)
    print(f"{out} | {len(CH)} kare grubu, {len(ws)} kelime, {end:.2f} sn")


if __name__ == "__main__":
    main()
