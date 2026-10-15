"""render.py her segmenti kaynak fps'ine göre tam kareye YUVARLAR (yukarı). 20 segmentte ~0.2 sn kayma birikir:
EDL'den hesaplanan zamanlara konan overlay/altyazı/efekt videonun sonuna doğru geç kalır.

Bu script gerçek (kareye yuvarlanmış) segment başlangıçlarını hesaplar ve iki dosya yazar:
  <edit_dir>/offs.json      {"offs": [segment başlangıçları], "end": toplam}   -> overlay / sfx / gömülü kelime zamanları
  <edit_dir>/edl_adj.json   end'leri yuvarlanmış süreye göre uzatılmış EDL      -> make_ass.py bununla çalıştırılır

Kullanım: python frame_offsets.py <edit_dir> [--fps 60]   (fps = kaynak videonun fps'i; ffprobe ile bak)
Doğrulama: offs.json "end" == ffprobe base.mp4 video süresi (±1 kare) olmalı.
"""
import argparse, json, math
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("edit_dir", type=Path)
ap.add_argument("--fps", type=float, default=30)
a = ap.parse_args()
e = json.loads((a.edit_dir / "edl.json").read_text())
off, offs = 0.0, []
for r in e["ranges"]:
    d = math.ceil((r["end"] - r["start"]) * a.fps - 1e-6) / a.fps
    offs.append(round(off, 4)); r["end"] = round(r["start"] + d, 5); off += d
(a.edit_dir / "edl_adj.json").write_text(json.dumps(e, ensure_ascii=False, indent=1))
(a.edit_dir / "offs.json").write_text(json.dumps({"offs": offs, "end": round(off, 4)}))
print(f"{len(offs)} segment, gerçek süre {off:.3f} sn")
for i, t in enumerate(offs):
    print(f"  {i:2d}  {t:7.3f}  {e['ranges'][i].get('beat', '')}")
