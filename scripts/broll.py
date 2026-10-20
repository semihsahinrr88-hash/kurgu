"""BorsaSemih video B-roll: Pixabay video arşivinden ücretsiz, ticari kullanıma açık klip bul → kes → 9:16 / 16:9 hazırla.

Lisans: Pixabay Content License — ticari kullanım serbest, atıf zorunlu değil (yine de edit/broll/credits.json'a yazılır).
Kural: marka logosu / tanınır kişi yüzü öne çıkan klibi seçme; içerikle birebir ilgili değilse kullanma.

Anahtar: PIXABAY_KEY ortam değişkeni ya da ~/.config/borsasemih/pixabay_key dosyası. REPOYA YAZMA (repo herkese açık).

  python broll.py search "stock market screen" [--n 8] [--format reels|youtube] [--type film|animation|all]
        -> aday listesi + edit/broll/cand_<sorgu>.jpg (numaralı küçük resim sayfası, storyboard onayı için)
  python broll.py get <pixabay_id> -o edit/broll/b1.mp4 [--dur 2.5] [--start 4.0] [--format reels|youtube]
        [--x 0.5] [--push 0.04] [--grade warm|cool|none]
        -> indirir, --start'tan --dur kadar keser, kadrajlar (x = yatay odak 0-1), hafif push-in, renk uyumu, 30 fps, sessiz
  python broll.py credits edit/broll        -> kullanılan kliplerin listesi

Sorgular İngilizce daha iyi sonuç verir: enflasyon → "supermarket prices", ihracat → "cargo port containers",
faiz → "bank building", borsa → "stock market screen", altın → "gold bars", dolar → "dollar banknotes".
EDL'de opak overlay: {"file": "broll/b1.mp4", "start_in_output": 7.2, "duration": 2.5} ; ses: whoosh, girişten 0.10 sn önce.
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

API = "https://pixabay.com/api/videos/"
CA = "/root/.ccr/ca-bundle.crt"
SIZES = {"reels": (1080, 1920), "youtube": (1920, 1080)}
GRADES = {  # stok klibi BorsaSemih çekimlerine yaklaştırır (F ten LUT'u insan teni içindir, burada kullanılmaz)
    "warm": "eq=contrast=1.04:saturation=0.90:gamma=0.98,colorbalance=rs=0.03:gs=0.01:bs=-0.03:rm=0.02:bm=-0.02",
    "cool": "eq=contrast=1.05:saturation=0.85,colorbalance=rs=-0.02:bs=0.03:bm=0.02",
    "none": "null",
}


def key() -> str:
    k = os.environ.get("PIXABAY_KEY", "").strip()
    f = Path.home() / ".config/borsasemih/pixabay_key"
    if not k and f.exists():
        k = f.read_text().strip()
    if not k:
        sys.exit("PIXABAY_KEY yok. Semih'ten iste; ~/.config/borsasemih/pixabay_key dosyasına yaz (repoya değil).")
    return k


def _ctx():
    import ssl
    return ssl.create_default_context(cafile=CA) if Path(CA).exists() else None


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "borsasemih-studio/1.0"})
    with urllib.request.urlopen(req, context=_ctx(), timeout=120) as r:
        return r.read()


def api(**params) -> dict:
    params = {k: v for k, v in params.items() if v is not None}
    return json.loads(fetch(API + "?" + urllib.parse.urlencode({"key": key(), **params})))


def hit(vid: int) -> dict:
    d = api(id=vid)
    if not d.get("hits"):
        sys.exit(f"Klip bulunamadı: {vid}")
    return d["hits"][0]


def pick_rendition(h: dict, fmt: str) -> dict:
    """Kırpma sonrası hedef çözünürlüğü karşılayan EN KÜÇÜK dosya; yoksa en büyüğü."""
    W, H = SIZES[fmt]
    vs = [v for v in h["videos"].values() if v.get("url")]
    def ok(v):
        w, hh = v["width"], v["height"]
        crop_w, crop_h = (hh * W / H, hh) if w / hh > W / H else (w, w * H / W)
        return crop_w >= W * 0.98 and crop_h >= H * 0.98
    good = sorted([v for v in vs if ok(v)], key=lambda v: v["size"])
    return good[0] if good else max(vs, key=lambda v: v["width"] * v["height"])


def score(h: dict, fmt: str, q: str = "") -> float:
    words = [w[:5] for w in re.findall(r"[a-z]+", q.lower()) if len(w) > 2]
    rel = sum(w in h.get("tags", "").lower() for w in words) / max(len(words), 1)
    v = max(h["videos"].values(), key=lambda v: v["width"] * v["height"])
    vertical = v["height"] > v["width"]
    s = 4.0 * rel + (1.5 if vertical == (fmt == "reels") else 0.0) + min(v["height"], 2160) / 1080
    s += min(h.get("likes", 0), 2000) / 1000 + (0.5 if h.get("type") == "film" else 0)
    return s - (1.0 if h.get("duration", 0) < 4 else 0)


def cmd_search(a):
    d = api(q=a.query, per_page=min(max(a.n * 3, 9), 60), safesearch="true",
            video_type=None if a.type == "all" else a.type, lang=a.lang)
    hits = sorted(d.get("hits", []), key=lambda h: -score(h, a.format, a.query))[: a.n]
    if not hits:
        sys.exit(f"'{a.query}' için sonuç yok — daha genel ya da İngilizce bir sorgu dene.")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, h in enumerate(hits, 1):
        v = max(h["videos"].values(), key=lambda v: v["width"] * v["height"])
        orient = "dikey" if v["height"] > v["width"] else "yatay"
        ai = " [AI]" if "ai generated" in h["tags"].lower() else ""
        print(f"{i:>2}. id={h['id']:<8} {h['duration']:>3}s  {v['width']}x{v['height']} {orient:<5} {h['type']:<9}{ai} {h['tags'][:70]}")
        rows.append((i, h))
    slug = re.sub(r"[^a-z0-9]+", "_", a.query.lower()).strip("_")[:40]
    sheet = out / f"cand_{slug}.jpg"
    try:
        contact_sheet(rows, sheet)
        print(f"\nküçük resim sayfası: {sheet}")
    except Exception as e:  # küçük resim sayfası opsiyonel
        print(f"(küçük resim sayfası yapılamadı: {e})")
    (out / f"cand_{slug}.json").write_text(json.dumps([h for _, h in rows], ensure_ascii=False, indent=1))


def contact_sheet(rows, path: Path):
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont
    tw, th, cols = 480, 270, 3
    n = len(rows); r = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, r * th), (20, 38, 43))
    b = Path(__file__).resolve().parent
    fpath = (b if (b / "fonts").exists() else b.parent) / "fonts"
    fonts = sorted(fpath.glob("Montserrat*Bold*.ttf")) or sorted(fpath.glob("*.ttf"))
    font = ImageFont.truetype(str(fonts[0]), 30) if fonts else ImageFont.load_default()
    for k, (i, h) in enumerate(rows):
        v = min(h["videos"].values(), key=lambda v: v["width"])
        im = Image.open(BytesIO(fetch(v["thumbnail"]))).convert("RGB")
        im.thumbnail((tw, th)); cell = Image.new("RGB", (tw, th), (20, 38, 43))
        cell.paste(im, ((tw - im.width) // 2, (th - im.height) // 2))
        dr = ImageDraw.Draw(cell)
        dr.rectangle((0, 0, 150, 44), fill=(15, 124, 140))
        dr.text((10, 5), f"{i} · {h['duration']}s", fill="white", font=font)
        sheet.paste(cell, ((k % cols) * tw, (k // cols) * th))
    sheet.save(path, quality=85)


def cmd_get(a):
    h = hit(a.id)
    v = pick_rendition(h, a.format)
    cache = Path.home() / ".cache/borsasemih_broll"; cache.mkdir(parents=True, exist_ok=True)
    src = cache / f"{h['id']}_{v['width']}x{v['height']}.mp4"
    if not src.exists():
        print(f"indiriliyor {v['width']}x{v['height']} ({v['size'] / 1e6:.1f} MB)…")
        src.write_bytes(fetch(v["url"]))
    dur = float(h["duration"])
    start = a.start if a.start is not None else max(0.0, min(dur * 0.3, dur - a.dur))
    if start + a.dur > dur:
        start = max(0.0, dur - a.dur)
    W, H = SIZES[a.format]
    x = min(max(a.x, 0.0), 1.0)
    # kadrajı doldur (cover) → yatay odakla kırp → hafif push-in → renk
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
          f"crop={W}:{H}:(iw-{W})*{x}:(ih-{H})/2,"
          f"scale=w='trunc({W}*(1+{a.push}*t/{a.dur})/2)*2':h='trunc({H}*(1+{a.push}*t/{a.dur})/2)*2':eval=frame,"
          f"crop={W}:{H},{GRADES[a.grade]},fps=30,format=yuv420p")
    out = Path(a.o); out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-t", f"{a.dur:.2f}", "-i", str(src),
                    "-vf", vf, "-an", "-c:v", "libx264", "-crf", "16", "-preset", "medium", str(out)], check=True)
    cred = out.parent / "credits.json"
    c = json.loads(cred.read_text()) if cred.exists() else []
    c = [e for e in c if e.get("file") != out.name] + [{"file": out.name, "pixabay_id": h["id"], "page": h["pageURL"],
         "user": h.get("user"), "start": round(start, 2), "dur": a.dur, "license": "Pixabay Content License"}]
    cred.write_text(json.dumps(c, ensure_ascii=False, indent=1))
    print(f"{out}  ← id {h['id']} @ {start:.2f}s, {a.dur}s, {W}x{H}, grade={a.grade}")


def cmd_credits(a):
    f = Path(a.dir) / "credits.json"
    for e in (json.loads(f.read_text()) if f.exists() else []):
        print(f"{e['file']}: {e['page']} ({e['user']})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search"); s.add_argument("query"); s.add_argument("--n", type=int, default=8)
    s.add_argument("--format", choices=SIZES, default="reels"); s.add_argument("--type", choices=["film", "animation", "all"], default="all")
    s.add_argument("--lang", default="en"); s.add_argument("--out", default="edit/broll"); s.set_defaults(f=cmd_search)
    g = sp.add_parser("get"); g.add_argument("id", type=int); g.add_argument("-o", required=True)
    g.add_argument("--dur", type=float, default=2.5); g.add_argument("--start", type=float)
    g.add_argument("--format", choices=SIZES, default="reels"); g.add_argument("--x", type=float, default=0.5)
    g.add_argument("--push", type=float, default=0.04); g.add_argument("--grade", choices=GRADES, default="warm"); g.set_defaults(f=cmd_get)
    c = sp.add_parser("credits"); c.add_argument("dir", nargs="?", default="edit/broll"); c.set_defaults(f=cmd_credits)
    a = p.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
