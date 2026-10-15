"""Draft EDL for a single talking-head take: removes fillers, dead air and obvious retakes.

This is a FIRST DRAFT for the editor (Claude) to review against takes_packed.md - not a
replacement for judgment. Follows video-use hard rules: cuts on word boundaries, padded
edges (default 50ms before / 80ms after), never inside a word.

Usage:
  python auto_cut.py <edit_dir> <source_video> [--max-gap 0.35] [--keep-maybe] [--grade none]
Writes <edit_dir>/edl.json and prints a cut report.
"""
from __future__ import annotations

import argparse, json, re
from pathlib import Path


def norm(t):
    return re.sub(r"[^\wçğıöşü ]", "", t.lower().replace("I", "ı").replace("İ", "i")).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir", type=Path)
    ap.add_argument("source", type=Path)
    ap.add_argument("--max-gap", type=float, default=0.35, help="silence longer than this is cut")
    ap.add_argument("--pad-before", type=float, default=0.05)
    ap.add_argument("--pad-after", type=float, default=0.08)
    ap.add_argument("--keep-maybe", action="store_true", help="keep 'yani/işte/hani' style words")
    ap.add_argument("--no-retake", action="store_true", help="disable retake detection")
    ap.add_argument("--grade", default="none")
    a = ap.parse_args()

    src = a.source.resolve()
    name = src.stem
    tr = json.loads((a.edit_dir / "transcripts" / f"{name}.json").read_text())
    words = [w for w in tr["words"] if w["type"] == "word"]
    events = [w for w in tr["words"] if w["type"] == "audio_event" and w.get("filler")]

    removed = []
    keep = []
    for w in words:
        if w.get("filler") or (w.get("maybe_filler") and not a.keep_maybe):
            removed.append(("filler", w["text"], w["start"]))
        else:
            keep.append(w)

    # sentences = runs of kept words split on gaps > max_gap or sentence punctuation + gap
    runs, cur = [], []
    for w in keep:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            if gap > a.max_gap or any(e["start"] >= cur[-1]["end"] and e["end"] <= w["start"] for e in events):
                runs.append(cur); cur = []
        cur.append(w)
    if cur:
        runs.append(cur)

    # retake detection: a run whose opening 3 words are repeated by a later run within 2 runs
    if not a.no_retake:
        def head(r): return " ".join(norm(x["text"]) for x in r[:3])
        drop = set()
        for i, r in enumerate(runs):
            if i in drop:
                continue
            for j in (i + 1, i + 2, i + 3):
                if j < len(runs) and len(r) >= 2 and head(r) and head(r) == head(runs[j]):
                    for k in range(i, j):          # failed take + any fragments before the restart
                        drop.add(k)
                        removed.append(("retake", " ".join(x["text"] for x in runs[k]), runs[k][0]["start"]))
                    break
        runs = [r for i, r in enumerate(runs) if i not in drop]

    ranges = []
    for r in runs:
        s = max(0.0, r[0]["start"] - a.pad_before)
        e = r[-1]["end"] + a.pad_after
        if ranges and s <= ranges[-1]["end"]:          # padded edges overlap -> merge
            ranges[-1]["end"] = round(e, 3)
            ranges[-1]["quote"] += " " + " ".join(x["text"] for x in r)
            continue
        ranges.append({"source": name, "start": round(s, 3), "end": round(e, 3),
                       "beat": "", "quote": " ".join(x["text"] for x in r), "reason": "auto"})

    total = sum(x["end"] - x["start"] for x in ranges)
    edl = {"version": 1, "sources": {name: str(src)}, "ranges": ranges, "grade": a.grade,
           "overlays": [], "total_duration_s": round(total, 2)}
    (a.edit_dir / "edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=2))

    orig = words[-1]["end"] if words else 0
    print(f"edl.json: {len(ranges)} segments, {total:.1f}s (source speech span {orig:.1f}s)")
    for kind, text, t in removed:
        print(f"  cut [{kind:6}] @ {t:6.2f}s  {text}")
    for e in events:
        print(f"  cut [voiced gap] {e['start']:.2f}-{e['end']:.2f}s (unlabelled sound between words)")


if __name__ == "__main__":
    main()
