import subprocess, json
o=json.load(open('offs.json'))['offs']; END=72.6167
ov=[("animations/s1/render.webm",o[1],3.97),("animations/s2/render.webm",o[4],7.53),("animations/s3/render.webm",o[8],3.09),
    ("animations/s4/render.webm",o[10],7.64),("animations/s5/render.webm",o[12],8.62),("animations/s6/render.webm",o[15],3.65)]
cmd=["ffmpeg","-y","-loglevel","error","-i","base.mp4"]
for f,_,_ in ov: cmd+=["-c:v","libvpx-vp9","-i",f]
cmd+=["-i","embed/embed.mp4","-c:v","libvpx-vp9","-i","animations/cta/render.webm"]
fc=["[0:v]fps=30,tpad=stop_mode=clone:stop_duration=2.25[v0]"]; cur="v0"
for i,(f,t,d) in enumerate(ov,1):
    fc.append(f"[{i}:v]setpts=PTS-STARTPTS+{t}/TB[o{i}]"); fc.append(f"[{cur}][o{i}]overlay=0:0:eof_action=pass:enable='between(t,{t},{t+d})'[v{i}]"); cur=f"v{i}"
e=len(ov)+1
fc.append(f"[{e}:v]setpts=PTS-STARTPTS+{o[13]}/TB[emb]"); fc.append(f"[{cur}][emb]overlay=0:0:eof_action=pass:enable='between(t,{o[13]},{o[14]-0.01})'[ve]")
c=e+1
fc.append(f"[{c}:v]setpts=PTS-STARTPTS+{END}/TB[cta]"); fc.append(f"[ve][cta]overlay=0:0:eof_action=pass:enable='between(t,{END},{END+2.25})'[vc]")
fc.append("[vc]ass=captions.ass:fontsdir=/root/studio/fonts,format=yuv420p[vout]"); fc.append("[0:a]apad=pad_dur=2.25[aout]")
cmd+=["-filter_complex",";".join(fc),"-map","[vout]","-map","[aout]","-c:v","libx264","-preset","medium","-crf","17","-r","30","-c:a","aac","-b:a","256k","-shortest","stage2.mp4"]
r=subprocess.run(cmd,capture_output=True,text=True); print("compose", r.returncode, r.stderr[-800:])
