"""Re-time Whisper word timestamps onto the real speech (energy) so captions stay in sync.

Whisper (esp. large-v3) can lag 0.3-0.5s and stretch word ends into pauses, which makes
captions late and can drop words that "fall" into a cut pause. This detects speech islands
with ffmpeg silencedetect, assigns each word to its island (monotonic), and spreads the
island's words proportionally to character length. Edits <edit_dir>/transcripts/<stem>.json
in place (backup: <stem>.orig.json).

Usage: python retime_words.py <edit_dir> <source_video> [--noise -38] [--min-sil 0.15]
"""
from __future__ import annotations

import argparse, json, re, shutil, subprocess
from collections import defaultdict
from pathlib import Path


def silences(video, noise, d):
    err = subprocess.run(["ffmpeg", "-i", str(video), "-af", f"silencedetect=n={noise}dB:d={d}",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    return list(zip(st, en + [None] * (len(st) - len(en))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir", type=Path)
    ap.add_argument("source", type=Path)
    ap.add_argument("--noise", type=float, default=-38)
    ap.add_argument("--min-sil", type=float, default=0.15)
    a = ap.parse_args()
    p = a.edit_dir / "transcripts" / f"{a.source.stem}.json"
    bak = p.with_suffix(".orig.json")
    if not bak.exists():
        shutil.copy(p, bak)
    d = json.loads(bak.read_text())
    words = [w for w in d["words"] if w["type"] == "word"]
    end_t = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                  "-of", "csv=p=0", str(a.source)], capture_output=True, text=True).stdout)
    sil = [(s, e if e is not None else end_t) for s, e in silences(a.source, a.noise, a.min_sil)]
    isl, t = [], 0.0
    for s, e in sil:
        if s > t + 0.05:
            isl.append((t, s))
        t = e
    if t < end_t - 0.05:
        isl.append((t, end_t))
    groups, k = defaultdict(list), 0
    for w in words:
        best, bs = k, -1e9
        for j in range(k, len(isl)):
            s, e = isl[j]
            ov = min(w["end"], e) - max(w["start"], s)
            sc = ov if ov > 0 else -min(abs(w["start"] - e), abs(w["end"] - s))
            if sc > bs:
                bs, best = sc, j
        k = best
        groups[best].append(w)
    for j, ws in groups.items():
        s, e = isl[j]
        L = sum(len(w["text"]) + 1 for w in ws)
        t = s
        for w in ws:
            dur = (e - s) * (len(w["text"]) + 1) / L
            w["start"], w["end"] = round(t, 3), round(t + dur, 3)
            t += dur
    out, prev = [], 0.0
    events = [w for w in d["words"] if w["type"] == "audio_event"]
    for w in sorted(words + events, key=lambda x: x["start"]):
        if w["start"] > prev:
            out.append({"text": " ", "type": "spacing", "start": prev, "end": w["start"], "speaker_id": "speaker_0"})
        out.append(w)
        prev = max(prev, w["end"])
    d["words"] = out
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    for j in sorted(groups):
        print(f"[{isl[j][0]:6.2f}-{isl[j][1]:6.2f}] " + " ".join(w["text"] for w in groups[j]))


if __name__ == "__main__":
    main()
