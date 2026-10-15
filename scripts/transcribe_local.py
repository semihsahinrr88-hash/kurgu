"""Free, local word-level transcription (faster-whisper) -> ElevenLabs-Scribe-compatible JSON.

Drop-in replacement for video-use's transcribe.py: writes <edit_dir>/transcripts/<stem>.json
with the same `words` schema (type word/spacing/audio_event, start, end, speaker_id), so
pack_transcripts.py, render.py (--build-subtitles) and timeline_view.py work unchanged.

Turkish filler handling (Whisper tends to swallow fillers):
  1. initial_prompt seeded with fillers -> nudges Whisper to write them verbatim
  2. known filler tokens are tagged  "filler": true  (ııı, eee, hmm, şey ...)
  3. voiced audio inside word gaps (energy, not silence) is inserted as
     audio_event "(filler?)" -> catches the ones Whisper skipped entirely

Usage:
  python transcribe_local.py <video> [--edit-dir DIR] [--language tr] [--model large-v3-turbo]
Cached: skips if the transcript already exists (delete it to force).
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, tempfile, time, wave
from pathlib import Path

import numpy as np

FILLERS = {"ı", "ıı", "ııı", "ıııı", "e", "ee", "eee", "eeee", "ehh", "eh", "ehm", "ıhm",
           "hmm", "hm", "mmm", "mm", "aa", "aaa", "ah", "uh", "um", "umm", "uhm", "öö", "ööö"}
MAYBE_FILLERS = {"şey", "yani", "işte", "hani", "falan", "şimdi", "aslında", "böyle"}
# Whisper's classic Turkish hallucinations on silence/music (dropped when the audio under them is quiet)
HALLUCINATIONS = ["altyazı m.k", "altyazı", "izlediğiniz için teşekkürler", "abone olmayı unutmayın",
                  "beğenmeyi unutmayın", "teşekkürler", "m.k."]
PROMPT = {
    "tr": "Eee, ııı, şey... Hmm, yani, işte. Arkadaşlar merhaba, bugün borsa, hisse, BIST, faiz konuşuyoruz.",
    "en": "Umm, uh, so, like... Hmm, okay.",
}


def norm(t: str) -> str:
    return re.sub(r"[^\wçğıöşü]", "", t.lower().replace("I", "ı").replace("İ", "i"))


def norm_phrase(t: str) -> str:
    return re.sub(r"[^\wçğıöşü ]", "", t.lower().replace("I", "ı").replace("İ", "i")).strip()


def extract(video: Path, wav: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "pcm_s16le", str(wav)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load_pcm(wav: Path) -> np.ndarray:
    with wave.open(str(wav)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def voiced_spans(pcm, sr, t0, t1, thr, min_len=0.18):
    """Return [(s,e)] sub-spans of [t0,t1] whose 20ms RMS exceeds thr."""
    hop = int(0.02 * sr)
    a, b = int(t0 * sr), int(t1 * sr)
    seg = pcm[a:b]
    if len(seg) < hop:
        return []
    n = len(seg) // hop
    rms = np.sqrt((seg[: n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    on = rms > thr
    spans, start = [], None
    for i, v in enumerate(list(on) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if (i - start) * 0.02 >= min_len:
                spans.append((t0 + start * 0.02, t0 + i * 0.02))
            start = None
    return spans


def transcribe(video: Path, edit_dir: Path, language: str, model_name: str, force=False) -> Path:
    out = edit_dir / "transcripts" / f"{video.stem}.json"
    if out.exists() and not force:
        print(f"cached: {out}")
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    from faster_whisper import WhisperModel

    t_start = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        extract(video, wav)
        pcm = load_pcm(wav)
        sr = 16000
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segs, info = model.transcribe(
            pcm, language=language, word_timestamps=True, vad_filter=False,
            initial_prompt=PROMPT.get(language), condition_on_previous_text=False,
            beam_size=5,
        )
        raw = [(w.word.strip(), float(w.start), float(w.end), float(w.probability))
               for s in segs for w in (s.words or []) if w.word.strip()]

    # hallucination guard: drop words sitting on near-silence, and known silence phrases
    def rms(s, e):
        seg = pcm[int(s * sr): int(e * sr)]
        return float(np.sqrt((seg ** 2).mean())) if len(seg) else 0.0
    loud = sorted(rms(s, e) for _, s, e, _ in raw) or [0.05]
    quiet = loud[len(loud) // 2] * 10 ** (-30 / 20)  # only near-silence (keeps quiet real words)
    kept = []
    for t, s, e, p in raw:
        if rms(s, e) < quiet:
            print(f"  dropped (silent, likely hallucination): {t!r} @ {s:.2f}")
            continue
        kept.append((t, s, e, p))
    # phrase-level blacklist: known silence phrases at the very end
    bad = {norm_phrase(h) for h in HALLUCINATIONS}
    for k in (3, 2, 1):
        if len(kept) >= k and norm_phrase(" ".join(x[0] for x in kept[-k:])) in bad:
            print(f"  dropped (hallucination phrase): {[x[0] for x in kept[-k:]]}")
            kept = kept[:-k]
            break
    raw = kept

    # speech loudness reference -> gap threshold (12 dB under median speech RMS)
    speech_rms = []
    for _, s, e, _ in raw:
        seg = pcm[int(s * sr): int(e * sr)]
        if len(seg):
            speech_rms.append(float(np.sqrt((seg ** 2).mean())))
    ref = float(np.median(speech_rms)) if speech_rms else 0.05
    thr = ref * 10 ** (-12 / 20)

    words, n_fill, n_gap = [], 0, 0
    prev_end = 0.0
    for text, s, e, p in raw:
        gap = s - prev_end
        if gap >= 0.25:
            for vs, ve in voiced_spans(pcm, sr, prev_end + 0.05, s - 0.05, thr):
                words.append({"text": "(filler?)", "type": "audio_event", "start": round(vs, 3),
                              "end": round(ve, 3), "speaker_id": "speaker_0", "filler": True})
                n_gap += 1
        if gap > 0:
            words.append({"text": " ", "type": "spacing", "start": round(prev_end, 3),
                          "end": round(s, 3), "speaker_id": "speaker_0"})
        n = norm(text)
        w = {"text": text, "type": "word", "start": round(s, 3), "end": round(e, 3),
             "speaker_id": "speaker_0", "logprob": round(p, 3)}
        if n in FILLERS or re.fullmatch(r"h?(ı+|e+|a+|ö+)h?|m+|h+m+", n or "-"):
            w["filler"] = True
            n_fill += 1
        elif n in MAYBE_FILLERS:
            w["maybe_filler"] = True
        words.append(w)
        prev_end = e

    payload = {"language_code": language, "engine": f"faster-whisper/{model_name}",
               "text": " ".join(t for t, *_ in raw), "words": words}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"saved {out} | {len(raw)} words, {n_fill} filler tokens, {n_gap} voiced gaps "
          f"| {time.time() - t_start:.0f}s")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--edit-dir", type=Path)
    ap.add_argument("--language", default="tr")
    ap.add_argument("--model", default="large-v3-turbo",
                    help="large-v3-turbo (default, best speed/quality), medium, small, large-v3")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    for v in a.videos:
        v = v.resolve()
        transcribe(v, (a.edit_dir or v.parent / "edit").resolve(), a.language, a.model, a.force)


if __name__ == "__main__":
    main()
