import sys, math
sys.path.insert(0, "/root/studio")
from fx import font, text_img, rounded, with_shadow
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

W, H = 1080, 1920
INK = (20, 38, 43)          # #14262B
CARD = (16, 30, 34, 238)    # koyu petrol kart
PET = (15, 124, 140)        # #0F7C8C
PETV = (53, 194, 210)       # #35C2D2 (videoda)
MUTED = (143, 160, 163)     # #8FA0A3
LIGHT = (233, 236, 236)     # #E9ECEC
WHITE = (255, 255, 255)
BAND = (60, 115, 960, 450)  # x, y, w, h


def bg(name="bg.png"):
    return Image.open(name).convert("RGBA")


def caption(im, text, hl=None, karaoke=False):
    f = font("xb", 64)
    d = ImageDraw.Draw(im)
    words = text.split()
    lines = [words[: (len(words) + 1) // 2], words[(len(words) + 1) // 2:]]
    y = 1330
    for ln in lines:
        s = " ".join(ln)
        x = (W - f.getlength(s)) / 2 if karaoke else 70
        for w in ln:
            ww = f.getlength(w)
            if karaoke and w == hl:
                box = rounded(ww + 26, 84, 16, (255, 255, 255, 70))
                im.alpha_composite(box, (int(x - 13), y - 4))
            col = PETV if (not karaoke and w == hl) else WHITE
            d.text((x, y), w, font=f, fill=col, stroke_width=4 if karaoke else 3, stroke_fill=(0, 0, 0))
            x += ww + f.getlength(" ")
        y += 86


def card(w, h, r=30):
    return rounded(w, h, r, CARD)


def put(im, c, x, y):
    s, p = with_shadow(c, 22, (0, 12), 0.45)
    im.alpha_composite(s, (int(x - p), int(y - p)))


def label(im, n, title, sub):
    f = font("black", 46)
    d = ImageDraw.Draw(im)
    bar = rounded(W - 80, 150, 24, (10, 20, 23, 225))
    im.alpha_composite(bar, (40, 1700 - 150))
    d.text((80, 1572), f"{n}  {title}", font=f, fill=WHITE)
    d.text((80, 1632), sub, font=font("semi", 32), fill=(200, 210, 212))


def save(im, name):
    im.convert("RGB").save(name, quality=90)
    print(name)


# 1) Takvim yaprağı
im = bg()
cx, cy = W / 2, 330
cw, ch = 420, 380
def page(year, top):
    pg = rounded(cw, ch, 26, (248, 249, 249, 255))
    dd = ImageDraw.Draw(pg)
    dd.rounded_rectangle([0, 0, cw - 1, 92], 26, fill=PET)
    dd.rectangle([0, 60, cw - 1, 92], fill=PET)
    t = text_img(top, font("xb", 40), WHITE); pg.alpha_composite(t, ((cw - t.width) // 2, 18))
    t = text_img(year, font("black", 140), INK); pg.alpha_composite(t, ((cw - t.width) // 2, 112))
    t = text_img("Küresel kriz", font("mono", 26), MUTED); pg.alpha_composite(t, ((cw - t.width) // 2, 306))
    return pg
for k in range(2, 0, -1):
    put(im, rounded(cw, ch, 26, (205 + k * 10, 210 + k * 10, 210 + k * 10, 255)), cx - cw / 2 + 8 * k, cy - ch / 2 + 8 * k)
put(im, page("2008", "Eylül"), cx - cw / 2, cy - ch / 2)
# üstte çevrilmekte olan eski yaprak (2007), kıvrılmış
old = page("2007", "Ocak").crop((0, 0, cw, ch // 2))
old = old.resize((cw, ch // 6)).transform((cw, ch // 6), Image.AFFINE, (1, -0.15, 0, 0, 1, 0), resample=Image.BICUBIC)
old = Image.eval(old, lambda v: v)
im.alpha_composite(old, (int(cx - cw / 2), int(cy - ch / 2 - ch // 6 + 4)))
d0 = ImageDraw.Draw(im)
for k in (cx - 110, cx + 110):
    d0.rounded_rectangle([k - 9, cy - ch / 2 - 18, k + 9, cy - ch / 2 + 22], 6, fill=(60, 70, 72))
caption(im, "2008 krizinde endeks yarı yarıya düştü", "2008")
label(im, "1", "Takvim yaprağı", "Tarih/yıl geçince bantta yaprak çevrilir")
save(im, "1_takvim.jpg")

# 2) Kilitli liste
im = bg()
c = card(960, 470)
d = ImageDraw.Draw(c)
d.text((40, 28), "6 hata · 6 kural", font=font("mono", 26), fill=MUTED)
t = text_img("Para nereye *akacak?*", font("black", 58), WHITE, acc=PETV); c.alpha_composite(t, (30, 60))
rows = [("01", "Yönetim", True), ("02", "Para akışı", True), ("03", "Tek hisse", False), ("04", "Kira parası", False), ("05", "Plan", False)]
for k, (n, txt, open_) in enumerate(rows):
    y = 150 + k * 60
    d.rounded_rectangle([30, y, 930, y + 50], 12, fill=(30, 50, 55) if open_ else (26, 40, 44), outline=PET if k == 1 else None, width=3)
    d.text((52, y + 10), n, font=font("monob", 26), fill=PETV)
    if open_:
        d.text((110, y + 6), txt, font=font("xb", 34), fill=WHITE)
        d.text((870, y + 8), "✓", font=font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30), fill=PETV)
    else:
        blur = Image.new("RGBA", (420, 50), (0, 0, 0, 0))
        ImageDraw.Draw(blur).text((10, 6), txt + " ••••", font=font("xb", 34), fill=(200, 210, 212))
        c.alpha_composite(blur.filter(ImageFilter.GaussianBlur(9)), (100, y))
        lx, ly = 880, y + 10
        d.rounded_rectangle([lx - 14, ly + 12, lx + 14, ly + 34], 5, fill=(200, 210, 212))
        d.arc([lx - 10, ly - 2, lx + 10, ly + 22], 180, 360, fill=(200, 210, 212), width=4)
put(im, c, 60, 105)
caption(im, "2 numara para nereye akıyor", "para")
label(im, "2", "Kilitli liste", "Maddeler kilitli başlar, anlattıkça tek tek açılır")
save(im, "2_kilitli_liste.jpg")

# 3) Hisse / sektör kartı
im = bg()
c = card(960, 400)
d = ImageDraw.Draw(c)
d.text((40, 30), "Sektör 01", font=font("monob", 28), fill=PETV)
d.text((40, 66), "Bankacılık", font=font("black", 72), fill=WHITE)
rz = rounded(250, 50, 25, PET + (255,)); ImageDraw.Draw(rz).text((22, 9), "F/K ort. 4,2", font=font("xb", 28), fill=WHITE)
c.alpha_composite(rz, (670, 34))
for k, (code, ch_) in enumerate([("GARAN", "+%2,4"), ("AKBNK", "+%1,1"), ("YKBNK", "-%0,6")]):
    x = 40 + k * 300
    t_ = rounded(280, 190, 20, (244, 246, 246, 255))
    dt = ImageDraw.Draw(t_)
    dt.text((24, 22), code, font=font("black", 56), fill=INK)
    col = (30, 158, 90) if ch_.startswith("+") else (217, 67, 74)
    dt.text((24, 110), ("▲ " if ch_.startswith("+") else "▼ ") + ch_[1:], font=font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38), fill=col)
    c.alpha_composite(t_, (x, 180))
put(im, c, 60, 120)
caption(im, "Bankalar hâlâ çok ucuz fiyatlanıyor", "ucuz")
label(im, "3", "Hisse / sektör kartı", "Sektör başlığı + 3 hisse kodu + not rozeti")
save(im, "3_hisse_karti.jpg")

# 4) Yatay kıyas çubukları
im = bg()
c = card(960, 360)
d = ImageDraw.Draw(c)
d.text((40, 30), "Yıllık getiri", font=font("monob", 28), fill=PETV)
d.text((40, 90), "Son 10 yıl ortalama", font=font("mono", 26), fill=MUTED)
d.rounded_rectangle([40, 130, 40 + 190, 178], 8, fill=(95, 110, 114))
d.text((250, 132), "%12", font=font("black", 44), fill=(200, 210, 212))
d.text((40, 210), "Bu yıl · BIST 100", font=font("mono", 26), fill=MUTED)
d.rounded_rectangle([40, 250, 40 + 740, 298], 8, fill=PETV)
d.text((800, 252), "%47", font=font("black", 44), fill=WHITE)
rz = rounded(190, 52, 26, (255, 255, 255, 255)); ImageDraw.Draw(rz).text((26, 9), "4 kat", font=font("black", 32), fill=INK)
c.alpha_composite(rz, (730, 30))
put(im, c, 60, 140)
caption(im, "Bu yıl tam dört katı getirdi", "dört")
label(im, "4", "Yatay kıyas çubukları", "Eski/küçük gri çubuk → yeni/büyük petrol çubuk + rozet")
save(im, "4_kiyas_cubuk.jpg")

# 5) Karşı karşıya sütunlar (tam ekran)
im = Image.new("RGBA", (W, H), (14, 22, 25, 255))
d = ImageDraw.Draw(im)
for y in range(200, 1500, 90):
    d.line([(60, y), (1020, y)], fill=(28, 40, 44), width=2)
d.text((80, 150), "Son 5 yıl · 100.000 TL ne oldu?", font=font("mono", 30), fill=MUTED)
base_y = 1280
d.rectangle([170, base_y - 360, 470, base_y], fill=(90, 104, 108))
# bina simgesi
d.polygon([(200, base_y - 360), (440, base_y - 360), (320, base_y - 440)], fill=(120, 134, 138))
for k in range(5):
    d.rectangle([205 + k * 48, base_y - 340, 225 + k * 48, base_y - 230], fill=(70, 84, 88))
d.text((228, base_y - 150), "185 bin", font=font("black", 50), fill=WHITE)
d.rectangle([610, base_y - 880, 910, base_y], fill=PETV)
d.text((650, base_y - 845), "640 bin", font=font("black", 54), fill=INK)
d.text((200, base_y + 30), "Mevduat", font=font("xb", 44), fill=(200, 210, 212))
d.text((690, base_y + 30), "Borsa", font=font("xb", 44), fill=PETV)
st = rounded(560, 100, 14, (255, 255, 255, 255))
ImageDraw.Draw(st).text((40, 16), "Borsa > Mevduat", font=font("black", 58), fill=INK)
st = st.rotate(-4, expand=True, resample=Image.BICUBIC)
put(im, st, 250, 190)
f_ = font("xb", 64)
ImageDraw.Draw(im).text((120, 1450), "Aradaki fark üç buçuk kat", font=f_, fill=WHITE, stroke_width=3, stroke_fill=(0, 0, 0))
label(im, "5", "Karşı karşıya sütunlar", "Tam ekran, zirve karşılaştırma; sonda damga basılır")
save(im, "5_karsi_karsiya.jpg")

# 6) Çizimli kaynak kartı
im = bg()
c = rounded(960, 400, 22, (250, 250, 248, 255))
d = ImageDraw.Draw(c)
d.rectangle([0, 0, 959, 56], fill=(230, 232, 232))
for k, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
    d.ellipse([24 + k * 30, 18, 42 + k * 30, 36], fill=col)
d.text((380, 16), "kap.org.tr", font=font("mono", 24), fill=(120, 120, 120))
d.text((40, 84), "Özel Durum Açıklaması · 14.10.2026", font=font("monob", 24), fill=(90, 90, 90))
txt = ["Şirketimiz 2026 yılı için hisse başına", "brüt 4,50 TL nakit temettü dağıtılmasına", "karar vermiştir. Ödeme tarihi 28.10.2026."]
for k, ln in enumerate(txt):
    d.text((40, 140 + k * 56), ln, font=font("serif", 44), fill=(30, 30, 30))
# el çizimi alt çizgi + daire
pts = [(40 + i * 12, 254 + 3 * math.sin(i / 3)) for i in range(0, 62)]
d.line(pts, fill=(53, 194, 210), width=7, joint="curve")
d.ellipse([480, 128, 760, 196], outline=PET, width=6)
put(im, c, 60, 120)
# imleç
cur = Image.new("RGBA", (40, 56), (0, 0, 0, 0))
ImageDraw.Draw(cur).polygon([(2, 2), (2, 46), (14, 34), (24, 54), (32, 50), (22, 30), (38, 30)], fill=(20, 20, 20), outline=WHITE)
im.alpha_composite(cur, (790, 330))
caption(im, "Şirket hisse başına 4,50 lira temettü dağıtıyor", "4,50")
label(im, "6", "Çizimli kaynak kartı", "Gerçek haber/KAP görüntüsü; önemli yer çizilir, imleç gezer")
save(im, "6_kaynak_karti.jpg")

# 7) Altyazı iki seçenek
a = bg(); caption(a, "Bugün borsada en çok kazandıran sektör", "kazandıran")
b = bg(); caption(b, "Bugün borsada en çok kazandıran sektör", "kazandıran", karaoke=True)
im = Image.new("RGBA", (W, H), (14, 22, 25, 255))
im.alpha_composite(a.crop((0, 1100, W, 1560)).resize((W, 460)), (0, 220))
im.alpha_composite(b.crop((0, 1100, W, 1560)).resize((W, 460)), (0, 860))
d = ImageDraw.Draw(im)
d.text((60, 150), "A · Şu anki: sola hizalı, vurgu kelimesi petrol", font=font("xb", 38), fill=WHITE)
d.text((60, 790), "B · Yeni: ortada, söylenen kelime kutuda", font=font("xb", 38), fill=WHITE)
label(im, "7", "Kelime kutulu altyazı", "B seçeneği: kutu kelime kelime ilerler")
save(im, "7_altyazi.jpg")
