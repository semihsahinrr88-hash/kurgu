"""Sesi kaynak kliplerden EDL + offs.json'a göre örnek hassasiyetinde yeniden kurar (04.11.2026).
Neden: base.mp4'e sonradan parça eklemek/çıkarmak için AAC dosyalarını concat etmek ek yerlerinde sessiz delik bırakıyor.
  python3 rebuild_audio.py <edit_dir> <video_only.mp4> <cikti.mp4>
"""
import json, subprocess, sys, wave
import numpy as np
from pathlib import Path
E, V, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
e = json.load(open(E / "edl.json")); o = json.load(open(E / "offs.json")); offs, end = o["offs"], o["end"]
SR = 48000; out = np.zeros((int(end * SR) + SR, 2), np.float32); cache = {}
def src(n):
    if n not in cache:
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", e["sources"][n], "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"])
        cache[n] = np.frombuffer(raw, np.float32).reshape(-1, 2)
    return cache[n]
for i, r in enumerate(e["ranges"]):
    a = int(r["start"] * SR); L = int(round(((offs[i + 1] if i + 1 < len(offs) else end) - offs[i]) * SR))
    x = src(r["source"])[a:a + L].copy()
    if len(x) < L: x = np.vstack([x, np.zeros((L - len(x), 2), np.float32)])
    f = int(0.03 * SR); ramp = np.linspace(0, 1, f)[:, None]; x[:f] *= ramp; x[-f:] *= ramp[::-1]
    s = int(round(offs[i] * SR)); out[s:s + L] += x
wav = Path(OUT).with_suffix(".wav"); w = wave.open(str(wav), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(out[:int(end * SR)], -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", V, "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", OUT], check=True)
print("hazır:", OUT)
