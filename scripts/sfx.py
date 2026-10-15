"""BorsaSemih ses efektleri: lisansı temiz kütüphane (Pixabay Content License, sfx/CREDITS.md) + miksaj.

  python sfx.py list                                   -> mevcut efektler ve önerilen kullanım
  python sfx.py mix <video> <cues.json> <out.mp4>      -> efektleri videoya ekler (video kopyalanır)
cues.json: [{"t": 3.20, "type": "whoosh-short", "db": -18}, ...]  (t = ÇIKTI zaman çizelgesi, sn)

Hangi olay → hangi efekt (frame.md "Ses dili"):
  kart / panel girişi  → pop  veya click-soft         (iniş karesinde)
  sahne / konu geçişi  → whoosh-short                 (kesimden 0.15 sn önce)
  B-roll girişi        → whoosh                       (girişten 0.10 sn önce)
  rakam iniş anı       → ping
  liste maddesi        → tick (sentez, çok kısa) veya key-press
  sonuç / çarpıcı cümle→ impact-bass-1  YA DA  chime  (ikisi birden değil)
  terminal / daktilo   → typing
  hook açılışı         → impact-bass-2 (riser 10 sn sürer: t = iniş − 10.0; sadece YouTube girişinde)
Kütüphane dosyaları -16 LUFS'a normalize; varsayılan seviyeler konuşmanın altında kalır.
"""
from __future__ import annotations
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np

_B = Path(__file__).resolve().parent
PKG = _B if (_B / "fonts").exists() else _B.parent   # ~/studio/ veya paket kökü
LIB = PKG / "sfx"
SR = 48000
DEF_DB = {"pop": -12, "click-soft": -10, "click": -12, "whoosh-short": -14, "whoosh": -15,
          "whoosh-cinematic": -16, "ping": -15, "chime": -17, "impact-bass-1": -14, "impact-bass-2": -14,
          "riser": -18, "key-press": -14, "typing": -18, "notification": -16, "sparkle": -18, "tick": -18}


def _tick(path: Path):
    n = int(0.04 * SR); t = np.arange(n) / SR
    x = np.random.default_rng(4).standard_normal(n) * np.minimum(1, t / 0.0005) * np.exp(-t / 0.006)
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def resolve(name: str) -> Path:
    p = LIB / f"{name}.wav"
    if p.exists():
        return p
    if name == "tick":
        _tick(p); return p
    aliases = {"hit": "impact-bass-1", "ding": "chime", "swoosh": "whoosh-short"}
    if name in aliases:
        return resolve(aliases[name])
    raise SystemExit(f"efekt yok: {name}. Mevcut: {', '.join(sorted(x.stem for x in LIB.glob('*.wav')))}")


def mix(video: Path, cues_path: Path, out: Path):
    cues = json.loads(Path(cues_path).read_text())
    if not cues:
        raise SystemExit("cues boş")
    cmd = ["ffmpeg", "-y", "-i", str(video)]
    parts, labels = [], []
    for i, c in enumerate(cues, start=1):
        cmd += ["-i", str(resolve(c["type"]))]
        ms = max(0, int(round(float(c["t"]) * 1000)))
        db = c.get("db", DEF_DB.get(c["type"], -16))
        parts.append(f"[{i}:a]aresample={SR},volume={db}dB,adelay={ms}|{ms}[s{i}]"); labels.append(f"[s{i}]")
    parts.append(f"[0:a]aresample={SR}[v0];[v0]{''.join(labels)}amix=inputs={len(cues)+1}:normalize=0:duration=first[a]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[a]", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "256k", str(out)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print(f"{out} | {len(cues)} efekt")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "list":
        m = json.loads((LIB / "manifest.json").read_text())
        for k, v in sorted(m.items()):
            print(f"{k:18} {v['duration']:>5}s  {DEF_DB.get(k, -16):>4} dB  {v['description'][:90]}")
        print(f"{'tick':18}  0.04s   -18 dB  Sentez, çok kısa tık — liste maddesi")
    elif a and a[0] == "mix" and len(a) >= 4:
        mix(Path(a[1]), Path(a[2]), Path(a[3]))
    else:
        print(__doc__)
