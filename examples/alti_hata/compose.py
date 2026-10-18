import subprocess, json
o = json.load(open('offs.json')); offs, END = o['offs'], o['end']
edl = json.load(open('edl.plan.json'))
nxt = lambda j: offs[j + 1] if j + 1 < len(offs) else END
OV = [("hook_proof", 0, 0, 0.15), ("m1_yonetim", 1, 1, 0), ("m2_akis", 4, 5, 0), ("m3_kasa", 8, 8, 0),
      ("m4_yasak", 10, 10, 0), ("m5_plan", 12, 12, 0), ("m6_odak", 15, 16, 0)]
ov = [(f"animations/{n}/render.webm", round(offs[i] + d, 3), round(nxt(j) - offs[i] - d, 3)) for n, i, j, d in OV]
# sfx: EDL zamanından gerçek zamana
eo, t = [], 0.0
for r in edl['ranges']:
    eo.append(t); t += r['end'] - r['start']
cues = json.load(open('sfx_cues.json'))
for c in cues:
    i = max(k for k in range(len(eo)) if eo[k] <= c['t'] + 1e-6)
    c['t'] = round(max(0, c['t'] + offs[i] - eo[i]), 3)
json.dump(cues, open('sfx_cues_adj.json', 'w'), indent=1)
FZ = 2.25
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", "base.mp4"]
for f, _, _ in ov: cmd += ["-c:v", "libvpx-vp9", "-i", f]
cmd += ["-c:v", "libvpx-vp9", "-i", "animations/cta/render.webm"]
fc = [f"[0:v]fps=30,tpad=stop_mode=clone:stop_duration={FZ}[v0]"]; cur = "v0"
for i, (f, t0, d) in enumerate(ov, 1):
    fc.append(f"[{i}:v]setpts=PTS-STARTPTS+{t0}/TB[o{i}]")
    fc.append(f"[{cur}][o{i}]overlay=0:0:eof_action=pass:enable='between(t,{t0},{t0 + d - 0.02})'[v{i}]"); cur = f"v{i}"
c = len(ov) + 1
fc.append(f"[{c}:v]setpts=PTS-STARTPTS+{END}/TB[cta]")
fc.append(f"[{cur}][cta]overlay=0:0:eof_action=pass:enable='between(t,{END},{END + FZ})'[vc]")
fc.append("[vc]ass=captions.ass:fontsdir=/root/studio/fonts,format=yuv420p[vout]")
fc.append(f"[0:a]apad=pad_dur={FZ}[aout]")
cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium",
        "-crf", "17", "-r", "30", "-c:a", "aac", "-b:a", "256k", "-shortest", "stage2.mp4"]
print(ov)
r = subprocess.run(cmd, capture_output=True, text=True); print("compose", r.returncode, r.stderr[-800:])
