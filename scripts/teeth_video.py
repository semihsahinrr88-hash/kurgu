"""STANDART (03.11.2026 Semih onayladı): base.mp4 -> base_t.mp4 — diş beyazlatma (kare kare, sadece dişler) + hafif gürültü temizliği + netleştirme. Ses aynen.
Ten rengine DOKUNMAZ. Base render'dan hemen sonra çalıştır; fx/sahne/birleştirme base_t.mp4 üzerinden yapılır.
  python3 teeth_video.py edit/base.mp4 edit/base_t.mp4 [--strength 0.9]
Önce tek kare kontrol: python3 teeth_video.py --still <video> <sn> <cikti.jpg>  (solda önce, sağda sonra; Semih'e göster)
84 sn 60 fps ≈ 12 dk (2 CPU)."""
import sys, subprocess, cv2, numpy as np
sys.path.insert(0, __file__.rsplit('/',1)[0]); import teeth
if sys.argv[1] == "--still":
    v, t, out = sys.argv[2], float(sys.argv[3]), sys.argv[4]
    cap = cv2.VideoCapture(v); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, fr = cap.read()
    lm = teeth.landmarks(teeth.make_detector(), fr); o, _ = teeth.whiten(fr, lm, 0.9)
    x, y, bw, bh = cv2.boundingRect(lm[teeth.INNER].astype(np.int32)); cx, cy = x + bw // 2, y + bh // 2
    crop = lambda im: cv2.resize(im[max(cy-170,0):cy+170, max(cx-340,0):cx+340], None, fx=1.6, fy=1.6)
    cv2.imwrite(out, np.hstack([crop(fr), crop(o)])); raise SystemExit
src, dst = sys.argv[1], sys.argv[2]
STRENGTH = float(sys.argv[sys.argv.index("--strength") + 1]) if "--strength" in sys.argv else 0.9
cap = cv2.VideoCapture(src); fps = cap.get(cv2.CAP_PROP_FPS); w = int(cap.get(3)); h = int(cap.get(4)); n = int(cap.get(7))
det = teeth.make_detector(video=True)
enc = subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s",f"{w}x{h}","-r",f"{fps}","-i","-","-i",src,
    "-map","0:v","-map","1:a","-vf","hqdn3d=1.2:1.0:3:3,unsharp=5:5:0.55:5:5:0","-c:v","libx264","-preset","medium","-crf","14",
    "-pix_fmt","yuv420p","-c:a","copy",dst], stdin=subprocess.PIPE)
i = 0; last = None; miss = 0
while True:
    ok, fr = cap.read()
    if not ok: break
    lm = teeth.landmarks(det, fr, int(i * 1000 / fps))
    if lm is None and last is not None and miss < 3: lm = last; miss += 1
    elif lm is not None: last = lm; miss = 0
    out, _ = teeth.whiten(fr, lm, STRENGTH)
    enc.stdin.write(out.tobytes()); i += 1
    if i % 600 == 0: print(f"{i}/{n}", flush=True)
enc.stdin.close(); enc.wait(); print("bitti", i)
