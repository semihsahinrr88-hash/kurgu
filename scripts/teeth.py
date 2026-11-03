"""Hafif diş beyazlatma: mediapipe ağız içi maskesi + Lab'da sarılık azaltma."""
import cv2, numpy as np, mediapipe as mp, sys
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
MODEL = str(__import__("pathlib").Path.home() / "studio" / "models" / "face_landmarker.task")
INNER = [78,191,80,81,82,13,312,311,310,415,308,324,318,402,317,14,87,178,88,95]

def make_detector(video=False):
    o = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=MODEL),
        running_mode=vision.RunningMode.VIDEO if video else vision.RunningMode.IMAGE, num_faces=1)
    return vision.FaceLandmarker.create_from_options(o)

def landmarks(det, bgr, ts=None):
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    r = det.detect_for_video(img, ts) if ts is not None else det.detect(img)
    if not r.face_landmarks: return None
    h, w = bgr.shape[:2]
    return np.array([[p.x*w, p.y*h] for p in r.face_landmarks[0]])

def whiten(bgr, lm, strength=1.0):
    if lm is None: return bgr, 0.0
    h, w = bgr.shape[:2]
    poly = lm[INNER].astype(np.int32)
    x, y, bw, bh = cv2.boundingRect(poly)
    if bh < 3: return bgr, 0.0
    pad = 6; x0, y0 = max(x-pad,0), max(y-pad,0); x1, y1 = min(x+bw+pad,w), min(y+bh+pad,h)
    roi = bgr[y0:y1, x0:x1]
    mask = np.zeros(roi.shape[:2], np.float32)
    cv2.fillPoly(mask, [poly - [x0, y0]], 1.0)
    mask = cv2.erode(mask, np.ones((2,2),np.uint8))
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = lab[...,0], lab[...,1], lab[...,2]
    # diş olasılığı: aydınlık + düşük kırmızılık (dudak/dil/diş eti dışarıda kalır)
    pt = np.clip((L - 95) / 45, 0, 1) * np.clip((150 - A) / 12, 0, 1)
    m = cv2.GaussianBlur(mask * pt, (0,0), 1.4) * strength
    B2 = B - (B - 128).clip(0) * 0.55          # sarılığı al
    L2 = L + (255 - L) * 0.10                  # biraz aydınlat
    lab[...,2] = B*(1-m) + B2*m; lab[...,0] = L*(1-m) + L2*m
    out = bgr.copy(); out[y0:y1, x0:x1] = cv2.cvtColor(lab.clip(0,255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    return out, float(m.sum())
