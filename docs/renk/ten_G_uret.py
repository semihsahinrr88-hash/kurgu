"""Referans (oguzhan) ten/renk görünümü: F grade'in ÜSTÜNE uygulanan Lab dönüşümü + .cube üretimi."""
import numpy as np, math, sys
from skimage import color
ROT = math.radians(-12)   # ten tonunu sarıdan biraz kırmızı-şeftaliye
CH = 0.70                 # doygunluk (chroma) çarpanı
def tf(rgb):
    lab = color.rgb2lab(rgb.reshape(-1, 1, 3)).reshape(-1, 3)
    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]
    # ışık: parlak bölgeyi (alın) yumuşak bastır, gölgeleri hafif aç
    x = L / 100
    L2 = 100 * (x - 0.13 * x ** 2.2 + 0.03 * (1 - x) ** 3 * x)
    a2 = CH * (a * math.cos(ROT) - b * math.sin(ROT))
    b2 = CH * (a * math.sin(ROT) + b * math.cos(ROT))
    out = color.lab2rgb(np.stack([L2, a2, b2], 1).reshape(-1, 1, 3)).reshape(rgb.shape)
    return np.clip(out, 0, 1)
def cube(path, n=33):
    g = np.linspace(0, 1, n)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    out = tf(rgb)
    with open(path, "w") as f:
        f.write(f'TITLE "ten_ref"\nLUT_3D_SIZE {n}\n')
        for v in out:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
if __name__ == "__main__":
    cube(sys.argv[1] if len(sys.argv) > 1 else "ten_ref.cube")
