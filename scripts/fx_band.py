"""Baş üstü bandı bileşenleri (20.10.2026) — referans: oguzhan.guzelkaralar "2040" Reels'i, BorsaSemih petrol diliyle.

fx.py'ye kayıtlı efektler (fx.py import eder). Hepsi konuşanı tam ekranda bırakır; kart başın üstündeki boş
duvarda (Reels y≈115-560) durur. `versus` tek istisna: tam ekran zirve karşılaştırması.

  year         büyük yıl rakamı sayarak gelir + ince petrol çizgi + mono etiket (takvim yerine, Semih 1B'yi seçti)
  locked_list  açık döngü listesi: maddeler bulanık + kilitli, `unlock` maddesinin kilidi `at`'de açılır
  stock_card   sektör/hisse kartı: üst etiket + başlık + hisse kodu kartları (değişim %) + rozet
  bars         yatay kıyas çubukları: gri (eski) → petrol (yeni) + rozet ("4 kat")
  versus       tam ekran iki sütun yükselir + damga ("Borsa > Mevduat")
  source_card  kaynak kartı: site adı + tarih + GERÇEK alıntı; önemli kısım el çizimi alt çizgi/daireyle işaretlenir, imleç gezer
               (metin mutlaka bulunan kaynaktan birebir — uydurma yok; spec'e "url" yaz)
"""
from __future__ import annotations

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fx import (fx, Base, font, text_img, rounded, with_shadow, over, ramp, out3, in3, inout3, back, hexrgb, SYM_FONT)

CARD = (16, 30, 34, 236)
ROW = (30, 50, 55, 255)
ROW_DIM = (24, 38, 42, 255)
LIGHT = (233, 236, 236)
GREY = (200, 210, 212)
MUTED_D = (143, 160, 163)
UP, DOWN = (52, 199, 120), (235, 87, 87)


def band_xy(self, h):
    x = self.g("x", 60)
    y = self.g("y", 115)
    return x, y


def card_in(t, dur, t0=0.0):
    p = out3(ramp(t, t0, 0.35))
    q = 1 - ramp(t, dur - 0.3, 0.3)
    return p * q, (1 - p) * -30


def fmt_tr(v, dec=0):
    s = f"{v:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


@fx("year", "Bant: büyük yıl rakamı sayarak gelir (from → to), altında petrol çizgi uzar, mono etiket. "
            "Alanlar: to (2008), from (to-3), label ('Küresel kriz · Eylül'), y (150), size (210)")
class Year(Base):
    def setup(self):
        self.to = int(self.g("to", 2008))
        self.fr = int(self.g("from", self.to - 3))
        self.size = int(self.g("size", 210))
        self.lab = text_img(self.g("label", ""), font("mono", 32), (225, 232, 233), shadow=True) if self.g("label") else None

    def frame(self, i, t, img, m):
        out = img.copy()
        q = 1 - ramp(t, self.dur - 0.3, 0.3)
        p = out3(ramp(t, 0.05, 0.6))
        v = round(self.fr + (self.to - self.fr) * p)
        num = text_img(str(v), font("black", self.size), (255, 255, 255), shadow=True)
        y = float(self.g("y", 150))
        over(out, num, self.W / 2, y + num.height / 2 + 20 * (1 - p), q * min(1, p * 2.5), 0.92 + 0.08 * p, anchor="c")
        lw = 300 * out3(ramp(t, 0.35, 0.45))
        if lw > 2:
            ln = Image.new("RGBA", (int(lw), 6), self.acc + (255,))
            over(out, ln, self.W / 2 - lw / 2, y + num.height - 12, q)
        if self.lab:
            over(out, self.lab, self.W / 2, y + num.height + 30, q * ramp(t, 0.55, 0.3), anchor="c")
        return out


def lock_icon(col=GREY):
    im = Image.new("RGBA", (34, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.arc([7, 0, 27, 24], 180, 360, fill=col, width=4)
    d.line([(7, 12), (7, 18)], fill=col, width=4); d.line([(27, 12), (27, 18)], fill=col, width=4)
    d.rounded_rectangle([2, 16, 32, 38], 5, fill=col)
    return im


def check_icon(col):
    im = Image.new("RGBA", (34, 34), (0, 0, 0, 0))
    ImageDraw.Draw(im).line([(5, 18), (13, 26), (29, 8)], fill=col, width=5, joint="curve")
    return im


@fx("locked_list", "Bant: açık döngü listesi. Maddeler bulanık + kilitli; `opened` kadarı açık başlar, `unlock` maddesi `at` anında açılır. "
                   "Alanlar: title ('Para nereye *akacak?*'), eyebrow, items [...], opened (0), unlock (index|null), at (0.6), y (115)")
class LockedList(Base):
    def setup(self):
        self.items = self.g("items") or ["Madde 1", "Madde 2", "Madde 3"]
        self.opened = int(self.g("opened", 0))
        self.unlock = self.g("unlock")
        self.at = float(self.g("at", 0.6))
        self.w = int(self.g("w", 960))
        self.rh = int(self.g("row_h", 58))
        n = len(self.items)
        self.h = 150 + n * (self.rh + 10) + 14
        self.title = text_img(self.g("title", "Para nereye *akacak?*"), font("black", 56), (255, 255, 255), acc=self.acc)
        self.rows_open, self.rows_blur = [], []
        for k, it in enumerate(self.items):
            row = Image.new("RGBA", (self.w - 60, self.rh), (0, 0, 0, 0))
            d = ImageDraw.Draw(row)
            d.text((22, (self.rh - 34) // 2), f"{k + 1:02d}", font=font("monob", 28), fill=self.acc)
            d.text((84, (self.rh - 44) // 2), it, font=font("xb", 36), fill=(255, 255, 255))
            self.rows_open.append(row)
            bl = Image.new("RGBA", (self.w - 60, self.rh), (0, 0, 0, 0))
            db = ImageDraw.Draw(bl)
            db.text((84, (self.rh - 44) // 2), it + " ••••", font=font("xb", 36), fill=GREY)
            bl = bl.filter(ImageFilter.GaussianBlur(10))
            ImageDraw.Draw(bl).text((22, (self.rh - 34) // 2), f"{k + 1:02d}", font=font("monob", 28), fill=self.acc)
            self.rows_blur.append(bl)
        self.lock, self.check = lock_icon(), check_icon(self.acc)

    def frame(self, i, t, img, m):
        out = img.copy()
        op, dy = card_in(t, self.dur)
        c = rounded(self.w, self.h, 28, CARD)
        d = ImageDraw.Draw(c)
        if self.g("eyebrow"):
            d.text((34, 26), self.g("eyebrow"), font=font("mono", 26), fill=MUTED_D)
        c.alpha_composite(self.title, (26, 58))
        for k in range(len(self.items)):
            y = 150 + k * (self.rh + 10)
            is_new = self.unlock is not None and k == int(self.unlock)
            u = ramp(t, self.at, 0.35) if is_new else (1.0 if k < self.opened else 0.0)
            active = is_new and t >= self.at - 0.1
            d.rounded_rectangle([30, y, self.w - 30, y + self.rh], 12, fill=ROW if u > 0.5 else ROW_DIM,
                                outline=self.acc if active else None, width=3)
            if u < 1:
                c.alpha_composite(Image.blend(self.rows_blur[k], Image.new("RGBA", self.rows_blur[k].size, (0, 0, 0, 0)), u), (30, y))
            if u > 0:
                r = self.rows_open[k].copy(); r.putalpha(r.getchannel("A").point(lambda a, u=u: int(a * u)))
                c.alpha_composite(r, (30, y))
            ix, iy = self.w - 80, y + (self.rh - 40) // 2
            if u < 1:
                lk = self.lock
                if is_new and t >= self.at:
                    s_ = 1 + 0.4 * math.sin(min(1, (t - self.at) / 0.25) * math.pi)
                    lk = lk.resize((int(34 * s_), int(40 * s_)))
                    lk.putalpha(lk.getchannel("A").point(lambda a: int(a * (1 - u))))
                c.alpha_composite(lk, (ix - (lk.width - 34) // 2, iy - (lk.height - 40) // 2))
            if u >= 0.6:
                c.alpha_composite(self.check, (ix, iy + 3))
        s, p = with_shadow(c, 20, (0, 12), 0.45)
        x, y0 = self.g("x", 60), self.g("y", 115)
        over(out, s, x - p, y0 - p + dy, op)
        return out


@fx("stock_card", "Bant: sektör/hisse kartı. Alanlar: eyebrow ('Sektör 01'), title ('Bankacılık'), tickers [{code, change ('+2,4'), note}], "
                  "badge ('F/K ort. 4,2'), at [her kart], badge_at, y (120)")
class StockCard(Base):
    def setup(self):
        self.tk = self.g("tickers") or [{"code": "GARAN", "change": "+2,4"}]
        n = len(self.tk)
        self.at = self.g("at") or [0.35 + 0.18 * k for k in range(n)]
        self.w, self.h = 960, 400
        self.tiles = []
        tw = (self.w - 80 - 20 * (n - 1)) // n
        for it in self.tk:
            tl = rounded(tw, 190, 20, (244, 246, 246, 255))
            dt = ImageDraw.Draw(tl)
            code = it["code"]
            fs = 56 if len(code) <= 5 else 46
            dt.text((24, 22), code, font=font("black", fs), fill=hexrgb("#14262B"))
            ch = str(it.get("change", ""))
            if ch:
                up = not ch.strip().startswith("-")
                dt.text((24, 112), ("▲ " if up else "▼ ") + "%" + ch.strip().lstrip("+-"),
                        font=font(SYM_FONT, 36), fill=(30, 158, 90) if up else (217, 67, 74))
            elif it.get("note"):
                dt.text((24, 120), it["note"], font=font("semi", 30), fill=(90, 100, 104))
            self.tiles.append(tl)
        self.tw = tw
        self.badge = None
        if self.g("badge"):
            bt = text_img(self.g("badge"), font("xb", 28), (255, 255, 255))
            self.badge = rounded(bt.width + 30, 52, 26, hexrgb(self.C["accent"]) + (255,))
            self.badge.alpha_composite(bt, (15, 4))

    def frame(self, i, t, img, m):
        out = img.copy()
        op, dy = card_in(t, self.dur)
        c = rounded(self.w, self.h, 28, CARD)
        d = ImageDraw.Draw(c)
        d.text((40, 30), self.g("eyebrow", ""), font=font("monob", 28), fill=self.acc)
        d.text((40, 66), self.g("title", ""), font=font("black", 72), fill=(255, 255, 255))
        for k, tl in enumerate(self.tiles):
            p = ramp(t, self.at[k], 0.3)
            if p <= 0:
                continue
            t2 = tl.copy(); t2.putalpha(t2.getchannel("A").point(lambda a, p=p: int(a * min(1, p * 2))))
            c.alpha_composite(t2, (40 + k * (self.tw + 20), int(180 - 30 * (1 - out3(p)))))
        if self.badge is not None:
            ba = float(self.g("badge_at", self.at[-1] + 0.35))
            if t >= ba:
                q = back(ramp(t, ba, 0.25), 2.2)
                b = self.badge.resize((max(1, int(self.badge.width * q)), max(1, int(self.badge.height * q))))
                c.alpha_composite(b, (self.w - 40 - self.badge.width + (self.badge.width - b.width) // 2, 34))
        s, p = with_shadow(c, 20, (0, 12), 0.45)
        over(out, s, self.g("x", 60) - p, self.g("y", 120) - p + dy, op)
        return out


@fx("bars", "Bant: yatay kıyas çubukları. Alanlar: eyebrow ('Yıllık getiri'), rows [{label, value ('%12'), frac (0-1), muted (true=gri)}], "
            "at [her satır], badge ('4 kat'), badge_at, y (140)")
class Bars(Base):
    def setup(self):
        self.rows = self.g("rows") or [{"label": "Önce", "value": "%12", "frac": 0.25, "muted": True},
                                       {"label": "Şimdi", "value": "%47", "frac": 0.95}]
        self.at = self.g("at") or [0.35 + 0.6 * k for k in range(len(self.rows))]
        self.w = 960
        self.h = 110 + 120 * len(self.rows)

    def frame(self, i, t, img, m):
        out = img.copy()
        op, dy = card_in(t, self.dur)
        c = rounded(self.w, self.h, 28, CARD)
        d = ImageDraw.Draw(c)
        d.text((40, 30), self.g("eyebrow", ""), font=font("monob", 28), fill=self.acc)
        maxw = self.w - 260
        for k, r in enumerate(self.rows):
            y = 90 + 120 * k
            d.text((40, y), r.get("label", ""), font=font("mono", 26), fill=MUTED_D)
            p = out3(ramp(t, self.at[k], 0.55))
            bw = max(0, maxw * float(r.get("frac", 0.5)) * p)
            col = (95, 110, 114) if r.get("muted") else self.acc
            if bw > 4:
                d.rounded_rectangle([40, y + 40, 40 + bw, y + 88], 8, fill=col)
            if p > 0.6:
                d.text((60 + bw, y + 40), r.get("value", ""), font=font("black", 44),
                       fill=GREY if r.get("muted") else (255, 255, 255))
        if self.g("badge"):
            ba = float(self.g("badge_at", self.at[-1] + 0.6))
            if t >= ba:
                q = back(ramp(t, ba, 0.25), 2.2)
                bt = text_img(self.g("badge"), font("black", 32), hexrgb("#14262B"))
                b = rounded(bt.width + 40, 56, 28, (255, 255, 255, 255)); b.alpha_composite(bt, (20, 6))
                b = b.resize((max(1, int(b.width * q)), max(1, int(b.height * q))))
                c.alpha_composite(b, (self.w - 40 - b.width, 26))
        s, p = with_shadow(c, 20, (0, 12), 0.45)
        over(out, s, self.g("x", 60) - p, self.g("y", 140) - p + dy, op)
        return out


@fx("versus", "TAM EKRAN zirve karşılaştırması: iki sütun yükselir (değerler sayarak), sonunda damga. "
              "Alanlar: eyebrow, left {label, value, num, icon:'bina'}, right {label, value, num}, stamp ('Borsa > Mevduat'), at [sol, sağ], stamp_at, "
              "unit (' bin')")
class Versus(Base):
    def setup(self):
        self.L = self.g("left") or {"label": "Mevduat", "num": 185, "icon": "bina"}
        self.R = self.g("right") or {"label": "Borsa", "num": 640}
        self.at = self.g("at") or [0.3, 0.9]
        self.bg = np.ones((self.H, self.W, 3), np.float32) * np.array([14, 22, 25], np.float32)
        im = Image.fromarray(self.bg.astype(np.uint8)); d = ImageDraw.Draw(im)
        for y in range(200, 1500, 90):
            d.line([(60, y), (1020, y)], fill=(28, 40, 44), width=2)
        self.bg = np.asarray(im, np.float32)

    def frame(self, i, t, img, m):
        W, H = self.W, self.H
        a = out3(ramp(t, 0, 0.3)) * (1 - ramp(t, self.dur - 0.3, 0.3))
        im = Image.fromarray(self.bg.astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(im)
        if self.g("eyebrow"):
            d.text((80, 120), self.g("eyebrow"), font=font("mono", 30), fill=MUTED_D)
        base_y, maxh = 1280, 880
        mx = max(float(self.L.get("num", 1)), float(self.R.get("num", 1)))
        unit = self.g("unit", " bin")
        for side, (x0, col, txtcol) in zip((self.L, self.R), ((170, (90, 104, 108), (255, 255, 255)), (610, self.acc, (14, 22, 25)))):
            k = 0 if side is self.L else 1
            p = out3(ramp(t, self.at[k], 0.7))
            h = maxh * float(side.get("num", 1)) / mx * p
            if h > 2:
                d.rectangle([x0, base_y - h, x0 + 300, base_y], fill=col)
                if side.get("icon") == "bina" and h > 140:
                    d.polygon([(x0 + 30, base_y - h), (x0 + 270, base_y - h), (x0 + 150, base_y - h - 80)], fill=(120, 134, 138))
                    for j in range(5):
                        d.rectangle([x0 + 35 + j * 48, base_y - h + 20, x0 + 55 + j * 48, base_y - h + 130], fill=(70, 84, 88))
                v = side.get("value") or (fmt_tr(float(side.get("num", 0)) * p) + unit)
                if p > 0.15:
                    tt = text_img(v, font("black", 54), txtcol)
                    yy = base_y - h + (150 if side.get("icon") == "bina" else 30)
                    yy = min(yy, base_y - 80)
                    im.alpha_composite(tt, (int(x0 + 150 - tt.width / 2), int(yy)))
            lab = text_img(side.get("label", ""), font("xb", 44), GREY if k == 0 else self.acc)
            im.alpha_composite(lab, (int(x0 + 150 - lab.width / 2), base_y + 24))
        out = np.asarray(im.convert("RGB"), np.float32)
        sa = float(self.g("stamp_at", self.at[1] + 0.9))
        if self.g("stamp") and t >= sa:
            q = ramp(t, sa, 0.22)
            st = text_img(self.g("stamp"), font("black", 58), hexrgb("#14262B"))
            b = rounded(st.width + 70, 100, 14, (255, 255, 255, 255)); b.alpha_composite(st, (35, 12))
            sc = 1.6 - 0.6 * out3(q)
            over(out, with_shadow(b, 16, (0, 10), 0.5)[0], W / 2, 250, min(1, q * 2), sc, -4, anchor="c")
        return img * (1 - a) + out * a


@fx("source_card", "Bant: kaynak kartı — GERÇEK kaynaktan birebir alıntı (uydurma yok, spec'e url yaz). Site adı + tarih + metin; "
                   "`highlight` ifadesinin altı el çizimiyle çizilir, `circle` ifadesi daireye alınır, imleç gezer. "
                   "Alanlar: site ('kap.org.tr'), eyebrow ('Özel Durum Açıklaması · 14.10.2026'), text, highlight, circle, url, at (0.6), y (120)")
class SourceCard(Base):
    def setup(self):
        self.w = 960
        f = font("serif", 44)
        self.f = f
        words = str(self.g("text", "")).split()
        lines, cur = [], []
        for w in words:
            if cur and f.getlength(" ".join(cur + [w])) > self.w - 80:
                lines.append(cur); cur = [w]
            else:
                cur.append(w)
        if cur:
            lines.append(cur)
        self.lines = lines[:5]
        self.h = 140 + 56 * len(self.lines) + 30
        # her kelimenin kutusu
        self.boxes = []
        for li, ln in enumerate(self.lines):
            x = 40
            for w in ln:
                ww = f.getlength(w)
                self.boxes.append((w, x, 130 + li * 56, ww))
                x += ww + f.getlength(" ")

        def span(phrase):
            if not phrase:
                return []
            ph = phrase.split()
            ws = [b[0] for b in self.boxes]
            for s in range(len(ws) - len(ph) + 1):
                if [w.strip(".,;:") for w in ws[s:s + len(ph)]] == [p.strip(".,;:") for p in ph]:
                    return self.boxes[s:s + len(ph)]
            return []
        self.hl = span(self.g("highlight"))
        self.ci = span(self.g("circle"))
        self.at = float(self.g("at", 0.6))

    def frame(self, i, t, img, m):
        out = img.copy()
        op, dy = card_in(t, self.dur)
        c = rounded(self.w, self.h, 22, (250, 250, 248, 255))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle([0, 0, self.w - 1, 56], 22, fill=(230, 232, 232)); d.rectangle([0, 30, self.w - 1, 56], fill=(230, 232, 232))
        for k, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([24 + k * 30, 18, 42 + k * 30, 36], fill=col)
        site = self.g("site", "")
        d.text(((self.w - font("mono", 24).getlength(site)) / 2, 16), site, font=font("mono", 24), fill=(110, 110, 110))
        d.text((40, 76), self.g("eyebrow", ""), font=font("monob", 24), fill=(90, 90, 90))
        for w, x, y, ww in self.boxes:
            d.text((x, y), w, font=self.f, fill=(28, 28, 28))
        pet = hexrgb(self.C["accent"])
        # alt çizgi: kelime satırlarına göre, soldan sağa çizilir
        p = ramp(t, self.at, 0.6)
        if self.hl and p > 0:
            segs = {}
            for w, x, y, ww in self.hl:
                segs.setdefault(y, [x, x + ww])
                segs[y][1] = x + ww
            total = sum(b - a for a, b in segs.values())
            left = total * p
            for y, (a, b) in sorted(segs.items()):
                L = min(b - a, left); left -= L
                if L <= 1:
                    break
                pts = [(a + s, y + 54 + 2.5 * math.sin(s / 23)) for s in np.linspace(0, L, max(2, int(L / 8)))]
                d.line(pts, fill=self.acc if not self.C.get("light") else (53, 194, 210), width=7, joint="curve")
        q = ramp(t, self.at + 0.5, 0.5)
        if self.ci and q > 0:
            x0 = min(b[1] for b in self.ci) - 14; x1 = max(b[1] + b[3] for b in self.ci) + 14
            y0 = min(b[2] for b in self.ci) - 4; y1 = max(b[2] for b in self.ci) + 62
            cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
            th = -2.4 + np.linspace(0, 2 * math.pi * 1.08 * q, 80)
            pts = [(cx + rx * (1 + 0.03 * k / 80) * math.cos(a), cy + ry * (1 + 0.03 * k / 80) * math.sin(a)) for k, a in enumerate(th)]
            d.line(pts, fill=pet, width=6, joint="curve")
        s, pd = with_shadow(c, 20, (0, 12), 0.45)
        X, Y = self.g("x", 60), self.g("y", 120) + dy
        over(out, s, X - pd, Y - pd, op)
        # imleç: kartın sağ altından vurguya doğru gelir
        if self.hl:
            tx = X + self.hl[-1][1] + self.hl[-1][3] + 10; ty = Y + self.hl[-1][2] + 40
            k = inout3(ramp(t, 0.2, self.at + 0.3))
            cx_, cy_ = X + self.w - 60 + (tx - (X + self.w - 60)) * k, Y + self.h - 30 + (ty - (Y + self.h - 30)) * k
            cur = Image.new("RGBA", (40, 56), (0, 0, 0, 0))
            ImageDraw.Draw(cur).polygon([(2, 2), (2, 46), (14, 34), (24, 54), (32, 50), (22, 30), (38, 30)], fill=(20, 20, 20), outline=(255, 255, 255))
            over(out, cur, cx_, cy_, op)
        return out
