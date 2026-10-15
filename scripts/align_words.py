"""Türkçe kelime zamanlarını wav2vec2 zorunlu hizalama (WhisperX) ile düzeltir.

Whisper'ın kelime zamanları 0.3-0.5 sn kayabiliyor; bu script transcribe_local.py'nin yazdığı
transkriptteki METNİ korur, sadece kelime başlangıç/bitişlerini sesin kendisine hizalar
(mpoyraz/wav2vec2-xls-r-300m-cv7-turkish). Filler/audio_event kayıtlarına dokunmaz.
retime_words.py (enerji adası yaması) yedek olarak durur: hizalama bir kelimeyi bulamazsa o
kelime Whisper zamanında kalır ve raporda "hizalanamadı" diye yazılır.

Kullanım: python align_words.py <edit_dir> <video> [--gap 0.6]
Yerinde düzenler; yedek: transcripts/<ad>.whisper.json
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir", type=Path)
    ap.add_argument("video", type=Path)
    ap.add_argument("--gap", type=float, default=0.6, help="bu boşluktan uzun duraklamada yeni segment")
    a = ap.parse_args()
    import torch, whisperx
    torch.set_num_threads(max(1, torch.get_num_threads()))
    p = a.edit_dir / "transcripts" / f"{a.video.stem}.json"
    bak = p.with_name(f"{a.video.stem}.whisper.json")
    if not bak.exists():
        shutil.copy(p, bak)
    d = json.loads(bak.read_text())
    words = [w for w in d["words"] if w["type"] == "word"]
    segs, cur = [], []
    for w in words:
        if cur and w["start"] - cur[-1]["end"] > a.gap:
            segs.append(cur); cur = []
        cur.append(w)
    if cur:
        segs.append(cur)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-y", "-i", str(a.video), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audio = whisperx.load_audio(str(wav))
    model, meta = whisperx.load_align_model(language_code="tr", device="cpu")
    tr = [{"start": max(0.0, s[0]["start"] - 0.15), "end": s[-1]["end"] + 0.15,
           "text": " ".join(w["text"].strip() for w in s)} for s in segs]
    res = whisperx.align(tr, model, meta, audio, "cpu", return_char_alignments=False)
    moved, miss, shifts = 0, 0, []
    for seg_src, seg_al in zip(segs, res["segments"]):
        al = [x for x in seg_al.get("words", [])]
        if len(al) != len(seg_src):  # tokenizasyon farkı: bu segmenti olduğu gibi bırak
            miss += len(seg_src); continue
        for w, x in zip(seg_src, al):
            if "start" in x and "end" in x:
                shifts.append(x["start"] - w["start"])
                w["start"], w["end"] = round(float(x["start"]), 3), round(float(x["end"]), 3)
                moved += 1
            else:
                miss += 1
    events = [w for w in d["words"] if w["type"] == "audio_event"]
    out, prev = [], 0.0
    for w in sorted(words + events, key=lambda x: x["start"]):
        if w["start"] > prev:
            out.append({"text": " ", "type": "spacing", "start": prev, "end": w["start"], "speaker_id": "speaker_0"})
        out.append(w); prev = max(prev, w["end"])
    d["words"] = out
    d["aligned"] = "wav2vec2-tr"
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    if shifts:
        import statistics
        print(f"hizalandı: {moved} kelime | hizalanamadı: {miss} | ortalama kayma {statistics.mean(shifts):+.3f} sn "
              f"(medyan {statistics.median(shifts):+.3f}, en büyük {max(shifts, key=abs):+.3f})")
    else:
        print(f"hizalama yapılamadı ({miss} kelime) — retime_words.py kullan")


if __name__ == "__main__":
    main()
