"""BorsaSemih altyazı stili (.ass): Montserrat ExtraBold, beyaz, normal harf, anahtar kelimeler turuncu,
sola hizalı, alt üçte birlik bant, en fazla 2 satır. render.py'nin chunk mantığını kullanır.

Kullanım:
  python make_ass.py <edit_dir> [--hl "faiz,enflasyon,THYAO"] [--words 5] [--youtube] [-o <edit_dir>/captions.ass]
--youtube: yatay video için alt-orta hizalı, 54 punto, kare başına ≤7 kelime.
Otomatik turuncu: rakam/yüzde/para içeren kelimeler + 3-6 harfli BÜYÜK hisse kodları + --hl listesi.
Çıktıyı render sonrası  -vf "ass=captions.ass:fontsdir=<fonts>"  ile EN SONA bas.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import render

WHITE, ORANGE = r"\c&HFFFFFF&", r"\c&H1E8CFF&"   # ASS renk BGR: #FF8C1E turuncu


def ts(t):
    t = max(0.0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def is_key(word, hl):
    w = word.strip(".,!?;:\"'")
    lw = w.replace("I", "ı").replace("İ", "i").lower()
    return (bool(re.search(r"\d|%|₺|\$|€", w)) or bool(re.fullmatch(r"[A-ZÇĞİÖŞÜ]{3,6}", w))
            or any(lw.startswith(h) for h in hl))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir", type=Path)
    ap.add_argument("--hl", default="", help="virgüllü vurgulanacak kelime kökleri")
    ap.add_argument("--words", type=int, default=5, help="bir altyazı karesindeki en fazla kelime")
    ap.add_argument("--size", type=int, default=74)
    ap.add_argument("--margin-v", type=int, default=520, help="alttan px (Instagram UI'nin üstü)")
    ap.add_argument("--youtube", action="store_true", help="yatay 1920x1080: alt orta, tek-iki satır, daha küçük")
    ap.add_argument("-o", type=Path)
    a = ap.parse_args()
    if a.youtube:
        PX, PY, al, ml, mr = 1920, 1080, 2, 160, 160
        if a.size == 74: a.size = 54
        if a.margin_v == 520: a.margin_v = 70
        if a.words == 5: a.words = 7
    else:
        PX, PY, al, ml, mr = 1080, 1920, 1, 90, 170
    hl = [h.strip().replace("I", "ı").replace("İ", "i").lower() for h in a.hl.split(",") if h.strip()]
    render.CHUNK_WORDS = max(3, a.words - 1); render.CHUNK_MAX_WORDS = a.words
    edl = json.loads((a.edit_dir / "edl.json").read_text())
    ev, off = [], 0.0
    for r in edl["ranges"]:
        s0, s1 = float(r["start"]), float(r["end"])
        tr = json.loads((a.edit_dir / "transcripts" / f"{r['source']}.json").read_text())
        for ch in render.chunk_words(render._words_in_range(tr, s0, s1)):
            st = max(s0, ch[0]["start"]) - s0 + off
            en = min(s1, ch[-1]["end"]) - s0 + off
            parts = []
            for i, w in enumerate(ch):
                t = w["text"].strip()
                if i == len(ch) - 1:
                    t = t.rstrip(".,;:")
                parts.append("{" + (ORANGE if is_key(t, hl) else WHITE) + "}" + t)
            ev.append([st, max(en, st + 0.35), " ".join(parts)])
        off += s1 - s0
    for i in range(len(ev) - 1):                      # boşlukta titreme olmasın: sonraki kareye kadar tut (≤0.3 sn)
        if 0 < ev[i + 1][0] - ev[i][1] < 0.3:
            ev[i][1] = ev[i + 1][0]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {PX}
PlayResY: {PY}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Semih,Montserrat ExtraBold,{a.size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,4,3,{al},{ml},{mr},{a.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    out = a.o or a.edit_dir / "captions.ass"
    out.write_text(head + "".join(f"Dialogue: 0,{ts(s)},{ts(e)},Semih,,0,0,0,,{{\\fad(60,0)}}{t}\n" for s, e, t in ev),
                   encoding="utf-8")
    print(f"{out} | {len(ev)} kare")


if __name__ == "__main__":
    main()
