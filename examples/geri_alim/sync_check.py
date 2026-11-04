"""Opak efekt / split / gömülü kelime parçalarının görüntüsü base ile aynı anda mı? (04.11.2026)
Her parçanın alt bölgesini (ağız/çene) base_t.mp4'le kare kare karşılaştırır, kaymayı saniye olarak yazar.
0,0-0,033 normal (1 kare). 0,1+ ise dudak senkronu bozuk: o parçayı yeniden üret.
  python3 sync_check.py   (edit klasöründe, compose.py yanında)
"""
import glob, json, os, subprocess
import numpy as np
exec(open("compose.py").read().split("FX = sorted")[0].replace("mode = sys.argv", "#"))
def frames(f, ss, t, crop):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{ss:.4f}", "-t", f"{t:.3f}", "-i", f, "-vf", f"fps=30,{crop},scale=108:70,format=gray", "-f", "rawvideo", "-"])
    return np.frombuffer(raw, np.uint8).reshape(-1, 70, 108).astype(float)
items = []
for p in sorted(glob.glob("specs/f*.json")) + sorted(glob.glob("specs/p*.json")):
    n = os.path.basename(p)[:-5]; sp = json.load(open(p))
    if "cut_of" in sp: continue
    a, d = win(n); items.append((n, f"fx/{n}.mp4", a, d, n.startswith("p")))
bad = 0
for n, f, a, d, split in items:
    if d < 0.9 or not os.path.exists(f): continue
    fx = frames(f, 0, d, "crop=1080:700:0:1100")
    base = frames(str(BASE), max(0, a - 0.5), d + 1.0, f"crop=1080:700:0:{1100 - 864 + SPLIT_Y0}" if split else "crop=1080:700:0:1100")
    lags = []
    for k in range(3, len(fx) - 3, max(1, len(fx) // 5)):
        e = [(np.abs(fx[k] - base[j]).mean(), j) for j in range(len(base))]; lags.append(round((min(e)[1] - 15 - k) / 30, 3))
    worst = max(abs(x) for x in lags); bad += worst > 0.07
    print(f"{n:14s} {'TAMAM' if worst <= 0.07 else 'KAYMA!'} {lags}")
print("sorun yok" if not bad else f"{bad} parçada kayma var")
