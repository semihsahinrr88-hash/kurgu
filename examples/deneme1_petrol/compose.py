"""deneme1 birleştirme: base.mp4 + HyperFrames sahneleri + fx segmentleri + donmuş kare CTA (fx save_cta) + altyazı EN SON.
Ön koşul: base.mp4, offs.json (frame_offsets.py), animations/*/render.webm, captions.ass, plan_meta.json.
  python3 compose.py fx      -> fx segmentlerini üretir (edit/fx/*.mp4)
  python3 compose.py         -> stage2.mp4 (+ sfx_cues_adj.json)
"""
import json, subprocess, sys
from pathlib import Path

E = Path(__file__).resolve().parent
ST = Path.home() / "studio"
o = json.load(open(E / "offs.json")); offs, END = o["offs"], o["end"]
meta = json.load(open(E / "plan_meta.json"))
eo = meta["ranges_out"]
FZ = meta["freeze"]
nxt = lambda j: offs[j + 1] if j + 1 < len(offs) else END


def adj(t):
    """EDL çıktı zamanı → base.mp4 gerçek zamanı (kare yuvarlaması)."""
    i = max(k for k in range(len(eo)) if eo[k] <= t + 1e-6)
    return round(max(0.0, t + offs[i] - eo[i]), 3)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-1500:], r.stderr[-1500:]); raise SystemExit(f"hata: {cmd[:4]}")
    return r


FXD = E / "fx"; FXD.mkdir(exist_ok=True)
if len(sys.argv) > 1 and sys.argv[1] == "fx":
    for f in meta["fx"]:
        i, j = f["range"]
        t0, d = offs[i], round(nxt(j) - offs[i], 3)
        print(f["name"], t0, d, flush=True)
        run(["python3", str(ST / "fx.py"), str(E / "specs" / f"{f['name']}.json"), "--base", str(E / "base.mp4"),
             "--at", str(t0), "--dur", str(d), "-o", str(FXD / f"{f['name']}.mp4")])
    # donmuş kare CTA: son kareyi FZ sn tut, save_cta uygula
    run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.1", "-i", str(E / "base.mp4"), "-frames:v", "1", "-update", "1", str(FXD / "last.png")])
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", str(FZ), "-i", str(FXD / "last.png"), "-r", "30",
         "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(FXD / "freeze.mp4")])
    run(["python3", str(ST / "fx.py"), str(E / "specs" / "fx_cta.json"), "--in", str(FXD / "freeze.mp4"), "-o", str(FXD / "fx_cta.mp4")])
    print("fx hazır")
    raise SystemExit

# sahne overlay'leri (EDL zamanı → gerçek zaman)
OV = []
for s in meta["scenes"]:
    t0 = adj(s["start_in_output"])
    OV.append((s["file"], t0, s["duration"], True))
for f in meta["fx"]:
    i, j = f["range"]
    OV.append((f"fx/{f['name']}.mp4", offs[i], round(nxt(j) - offs[i], 3), False))

cues = json.load(open(E / "sfx_cues.json"))
for c in cues:
    c["t"] = adj(c["t"])
cues.append({"t": round(END + 0.12, 3), "type": "pop"})
json.dump(cues, open(E / "sfx_cues_adj.json", "w"), indent=1)

cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(E / "base.mp4")]
for f, _, _, webm in OV:
    cmd += (["-c:v", "libvpx-vp9"] if webm else []) + ["-i", str(E / f)]
cmd += ["-i", str(FXD / "fx_cta.mp4")]
fc = [f"[0:v]fps=30,tpad=stop_mode=clone:stop_duration={FZ}[v0]"]; cur = "v0"
for k, (f, t0, d, _) in enumerate(OV, 1):
    fc.append(f"[{k}:v]setpts=PTS-STARTPTS+{t0}/TB[o{k}]")
    fc.append(f"[{cur}][o{k}]overlay=0:0:eof_action=pass:enable='between(t,{t0},{t0 + d - 0.02:.3f})'[v{k}]"); cur = f"v{k}"
c = len(OV) + 1
fc.append(f"[{c}:v]setpts=PTS-STARTPTS+{END}/TB[cta]")
fc.append(f"[{cur}][cta]overlay=0:0:eof_action=pass:enable='gte(t,{END})'[vc]")
fc.append(f"[vc]ass={E / 'captions.ass'}:fontsdir={ST / 'fonts'},format=yuv420p[vout]")
fc.append(f"[0:a]apad=pad_dur={FZ}[aout]")
cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium",
        "-crf", "17", "-r", "30", "-c:a", "aac", "-b:a", "256k", "-t", f"{END + FZ:.3f}", str(E / "stage2.mp4")]
for x in OV:
    print(x)
run(cmd)
print("stage2 hazır")
