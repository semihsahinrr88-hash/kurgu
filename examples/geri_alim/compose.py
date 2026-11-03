"""geri_alim birleştirme. python3 compose.py fx | captions | (boş = stage2) | final"""
import json, subprocess, sys, re
from pathlib import Path
E = Path(__file__).resolve().parent; ST = Path.home()/"studio"
BASE = E/"base_t.mp4"; FZ = 2.25
o = json.load(open(E/"offs.json")); offs, END = o["offs"], o["end"]
edl = json.load(open(E/"edl.json")); eo = []; t = 0
for r in edl["ranges"]: eo.append(t); t += r["end"]-r["start"]
def adj(t):
    i = max(k for k in range(len(eo)) if eo[k] <= t+1e-6); return round(max(0.0, t+offs[i]-eo[i]), 3)
def run(c):
    r = subprocess.run([str(x) for x in c], capture_output=True, text=True)
    if r.returncode: print(r.stdout[-1500:], r.stderr[-2500:]); raise SystemExit("hata")
    return r
FX = sorted(p.stem for p in (E/"specs").glob("f*.json"))
FXD = E/"fx"; FXD.mkdir(exist_ok=True)
def win(name):
    sp = json.load(open(E/"specs"/f"{name}.json"))
    if "cut_of" in sp: return round(offs[sp["cut_of"]]-0.25, 3), 0.5
    w = sp["win"]; a = adj(w[0]); b = adj(w[0]+w[1]-0.001); return a, round(b-a, 3)
SPLIT = sorted(p.stem for p in (E/"specs").glob("p*.json")); SPLIT_Y0 = 690
mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode == "fx":
    only = sys.argv[2:]
    for n in FX:
        if only and n not in only: continue
        a, d = win(n); sp = json.load(open(E/"specs"/f"{n}.json")); sp.pop("win", None); sp.pop("cut_of", None)
        json.dump(sp, open(FXD/f"{n}.spec.json","w"), ensure_ascii=False)
        print(n, a, d, flush=True)
        run(["python3", ST/"fx.py", FXD/f"{n}.spec.json", "--base", BASE, "--at", a, "--dur", d, "-o", FXD/f"{n}.mp4"])
    for n in SPLIT:  # split: üst 864 px panel sahnesi, altta konuşan (base_t kırpma)
        if only and n not in only: continue
        a, d = win(n); print(n, a, d, flush=True)
        run(["ffmpeg","-y","-v","error","-ss",a,"-t",d,"-i",BASE,"-c:v","libvpx-vp9","-i",E/"animations"/n/"render.webm","-filter_complex",
             f"[0:v]fps=30,crop=1080:1056:0:{SPLIT_Y0},pad=1080:1920:0:864:color=0xE9ECEC[b];[1:v]setpts=PTS-STARTPTS[p];[b][p]overlay=0:0:shortest=0:eof_action=repeat,format=yuv420p",
             "-an","-t",d,"-c:v","libx264","-crf","14",FXD/f"{n}.mp4"])
    run(["ffmpeg","-y","-v","error","-sseof","-0.05","-i",BASE,"-frames:v","1","-update","1",FXD/"last.png"])
    run(["ffmpeg","-y","-v","error","-loop","1","-t",FZ,"-i",FXD/"last.png","-r","30","-c:v","libx264","-crf","12","-pix_fmt","yuv420p",FXD/"freeze.mp4"])
    print("fx hazır"); raise SystemExit
if mode == "captions":
    ass = (E/"captions.ass").read_text(encoding="utf-8")
    skips = [win("f01_hook"), win("f12_kinetic")]
    def ts(s): h, m, x = s.split(":"); return int(h)*3600+int(m)*60+float(x)
    out = []
    for ln in ass.splitlines():
        if ln.startswith("Dialogue:"):
            p = ln.split(",", 3); s0, s1 = ts(p[1]), ts(p[2])
            if any(s0 < a+d and s1 > a for a, d in skips): continue
        out.append(ln)
    (E/"captions_f.ass").write_text("\n".join(out)+"\n", encoding="utf-8"); print("captions_f hazır"); raise SystemExit
OV = []
for n in FX:
    a, d = win(n); OV.append((FXD/f"{n}.mp4", a, d, False))
for n in SPLIT:
    a, d = win(n); OV.append((FXD/f"{n}.mp4", a, d, False))
ew = json.load(open(E/"embed/win.json")); OV.append((E/"embed/embed.mp4", ew["a"], round(ew["b"]-ew["a"], 3), False))
OV += [(E/"broll/b2_para.mp4", adj(70.15), 2.3, False)]
for p in sorted((E/"specs").glob("s*.json")):
    s = json.load(open(p))
    if s["start"] == "END": continue
    OV.append((E/"animations"/p.stem/"render.webm", adj(s["start"]), s["duration"], True))
cues = json.load(open(E/"sfx_cues.json"))
for c in cues: c["t"] = adj(c["t"])
cues.append({"t": round(END+0.15, 3), "type": "pop"}); json.dump(cues, open(E/"sfx_cues_adj.json","w"), indent=1)
cmd = ["ffmpeg","-y","-loglevel","error","-i",BASE]
for f, _, _, w in OV: cmd += (["-c:v","libvpx-vp9"] if w else []) + ["-i", f]
cmd += ["-i", FXD/"freeze.mp4", "-c:v","libvpx-vp9","-i", E/"animations/s19_cta/render.webm", "-i", E/"kcap.mov"]
fc = [f"[0:v]fps=30,tpad=stop_mode=clone:stop_duration={FZ}[v0]"]; cur = "v0"
for k, (f, a, d, _) in enumerate(OV, 1):
    fc.append(f"[{k}:v]setpts=PTS-STARTPTS+{a}/TB[o{k}]")
    fc.append(f"[{cur}][o{k}]overlay=0:0:eof_action=pass:enable='between(t,{a},{a+d-0.02:.3f})'[v{k}]"); cur = f"v{k}"
c = len(OV)+1
fc.append(f"[{c}:v]setpts=PTS-STARTPTS+{END}/TB[fz]"); fc.append(f"[{cur}][fz]overlay=0:0:eof_action=pass:enable='gte(t,{END})'[vf]")
fc.append(f"[{c+1}:v]setpts=PTS-STARTPTS+{END}/TB[ct]"); fc.append(f"[vf][ct]overlay=0:0:eof_action=pass:enable='gte(t,{END})'[vc]")
fc.append(f"[{c+2}:v]setpts=PTS-STARTPTS[kc]"); fc.append("[vc][kc]overlay=0:0:eof_action=pass,format=yuv420p[vout]")
fc.append(f"[0:a]apad=pad_dur={FZ}[aout]")
cmd += ["-filter_complex",";".join(fc),"-map","[vout]","-map","[aout]","-c:v","libx264","-preset","medium","-crf","17","-r","30",
        "-c:a","aac","-b:a","256k","-t",f"{END+FZ:.3f}",E/"stage2.mp4"]
for x in OV: print(x[0].name, x[1], x[2])
run(cmd); print("stage2 hazır")
