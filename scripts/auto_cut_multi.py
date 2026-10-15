"""Çok parçalı çekim: her klibe auto_cut.py uygular, sırayla tek EDL'de birleştirir, zaman çizelgesini yazar.

Kullanım:
  python auto_cut_multi.py <edit_dir> klip1.mov klip2.mov ... [--keep-maybe] [--max-gap 0.3] [--grade bronz]
Sıra = verilen sıra (telefon IMG numarası çoğu zaman çekim sırasıdır; içerikle doğrula).
Çıktılar: <edit_dir>/edl.json  +  <edit_dir>/timeline.txt (çıktı zamanı + kelime zamanları; plan tablosu için)
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

BRONZ = ("eq=contrast=1.04:saturation=1.06:gamma=1.0,selectivecolor=reds=-0.10 0 0.07 0.04:yellows=-0.06 0.01 0.06 0.03,vibrance=intensity=0.14,curves=all='0/0 0.6/0.6 0.8/0.775 0.92/0.865 1/0.935',unsharp=3:3:0.12")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir", type=Path)
    ap.add_argument("clips", nargs="+", type=Path)
    ap.add_argument("--keep-maybe", action="store_true")
    ap.add_argument("--max-gap", default="0.35")
    ap.add_argument("--grade", default="bronz")
    a = ap.parse_args()
    here = Path(__file__).resolve().parent
    sources, ranges = {}, []
    for c in a.clips:
        cmd = [sys.executable, str(here / "auto_cut.py"), str(a.edit_dir), str(c), "--max-gap", a.max_gap]
        if a.keep_maybe:
            cmd.append("--keep-maybe")
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        print(f"{c.stem}: {out.splitlines()[0] if out else '?'}")
        e = json.loads((a.edit_dir / "edl.json").read_text())
        sources.update(e["sources"]); ranges += e["ranges"]
    grade = BRONZ if a.grade == "bronz" else a.grade
    tot = sum(r["end"] - r["start"] for r in ranges)
    (a.edit_dir / "edl.json").write_text(json.dumps({"version": 1, "sources": sources, "ranges": ranges, "grade": grade,
                                                     "overlays": [], "total_duration_s": round(tot, 2)}, ensure_ascii=False, indent=1))
    lines, off = [], 0.0
    for r in ranges:
        tr = json.loads((a.edit_dir / "transcripts" / f"{r['source']}.json").read_text())
        ws = [w for w in tr["words"] if w["type"] == "word" and w["start"] >= r["start"] - 0.01 and w["end"] <= r["end"] + 0.01]
        lines.append(f"[{off:6.2f}-{off + r['end'] - r['start']:6.2f}] {r['source']} " +
                     " ".join(f"{w['text']}@{off + w['start'] - r['start']:.2f}" for w in ws))
        off += r["end"] - r["start"]
    (a.edit_dir / "timeline.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"edl.json: {len(ranges)} segment, {tot:.1f} sn → timeline.txt")


if __name__ == "__main__":
    main()
