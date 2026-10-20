"""Fikir animasyonları (prop) + kanıtlı hook (proof) — scene.py tarafından çağrılır.

Bir cümlenin fikrini küçük bir animasyonla anlatır (Justin'deki model menüsü / effort düğmesi gibi),
ama BorsaSemih diliyle: krem zemin, koyu mürekkep, tek turuncu. Hepsi SVG + GSAP, ücretsiz render.

prop spec:
  {"type": "prop", "prop": "<ad>", "region": "panel|band|full", "duration": 4, "land": 2.0,
   "title": "Paran nereye *akıyor*?", "step": "2/6", "at": [..], ...}
Prop adları ve alanları:
  kasa        — sermaye 10 dilim; bir dilim "tek hisse" olur, sonra batar, %90 yerinde kalır.
                at: [doldurma, batma]  label ("Tek hisse"), loss ("-%10"), keep ("Kalan %90 yerinde")
  yasak_para  — Kira/Taksit/Borç kartları borsa kutusuna girmeye çalışır, geri itilir.
                items (varsayılan ["Kira","Taksit","Borç"]), at:[her kart], target ("Borsa"), note
  plan_formu  — işlem planı formu satır satır dolar, sonunda damga.
                items (satır etiketleri), at:[her satır], stamp ("Yazılı plan"), stamp_at
  para_akisi  — Mevduat/Altın/Borsa/Döviz arasında para akar; land'de para hedefe toplanır.
                items (4 düğüm), at:[her düğüm], target ("Borsa")
  risk        — yarım daire kadran, ibre value'ya (0-1) döner. labels (3 adet), note
  odak        — birçok piyasa çipi; land'de biri seçilir, diğerleri söner.
                items, pick (seçilecek öğe), note
  yonetim     — "İyi günde" konuşma balonları dolar, "Kötü günde" sessizlik.
                good (balon metinleri), bad ("…"), at:[balonlar..., kötü gün]

proof spec (hook): {"type":"proof","region":"band","duration":3,"items":[{"img":"a.png"} | {"n":"1","text":"Yönetim"}], "at":[..]}
  Kartlar hızla yelpaze gibi dizilir (sonucu ilk saniyede göster). img yolları spec dosyasına göre.
"""
from __future__ import annotations

import html, json, math, re

VB_W, VB_H = 920, 440


def _rich(t: str, C) -> str:
    t = html.escape(t)
    return re.sub(r"\*(.+?)\*", r'<tspan fill="%s">\1</tspan>' % C["accent_ink"], t)


def _richh(t: str) -> str:
    t = html.escape(t)
    return re.sub(r"\*(.+?)\*", r'<span class="acc">\1</span>', t)


def _at(spec, n, start=0.5, dur=None):
    at = spec.get("at")
    if at and len(at) >= n:
        return [float(x) for x in at[:n]]
    dur = dur or float(spec.get("duration", 4))
    gap = max(0.45, (dur - 1.4 - start) / max(1, n))
    return [start + i * gap for i in range(n)]


def _txt(x, y, s, C, size=34, weight=800, fill=None, anchor="middle", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="Montserrat" font-weight="{weight}" font-size="{size}" '
            f'fill="{fill or C["text"]}" text-anchor="{anchor}" dominant-baseline="middle" {extra}>{s}</text>')


def _mono(x, y, s, C, size=24, fill=None, anchor="middle", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="JetBrains Mono" font-weight="500" font-size="{size}" '
            f'fill="{fill or C["muted"]}" text-anchor="{anchor}" dominant-baseline="middle" {extra}>{html.escape(s)}</text>')


# ---------------------------------------------------------------- prop'lar
def p_kasa(spec, C):
    t_fill, t_crash = _at(spec, 2, start=0.7)
    n, gap = 10, 12
    sw = (VB_W - 40 - gap * (n - 1)) / n
    y0, h = 120, 170
    segs = ""
    for i in range(n):
        x = 20 + i * (sw + gap)
        segs += (f'<g id="s{i}" opacity="0"><rect x="{x:.1f}" y="{y0}" width="{sw:.1f}" height="{h}" rx="12" '
                 f'fill="{C["track"]}" stroke="{C["hair"]}" stroke-width="2"/></g>')
    x0 = 20
    fill = (f'<rect id="f0" x="{x0}" y="{y0}" width="{sw:.1f}" height="{h}" rx="12" fill="{C["accent"]}" '
            '/>')
    pct = _txt(x0 + sw / 2, y0 + h / 2, "%10", C, size=30, weight=900, fill="#FFFFFF", extra='id="p0" opacity="0"')
    lab = _txt(x0, y0 - 40, html.escape(spec.get("label", "Tek hisse")), C, size=34, anchor="start", extra='id="lab" opacity="0"')
    rest_x = x0 + sw + gap
    brace = (f'<path id="br" d="M{rest_x:.1f} {y0+h+26} v14 H{VB_W-20} v-14" fill="none" stroke="{C["up"]}" '
             f'stroke-width="4" stroke-linecap="round" opacity="0"/>')
    keep = _txt((rest_x + VB_W - 20) / 2, y0 + h + 82, html.escape(spec.get("keep", "Kalan %90 yerinde")), C, size=40,
                weight=800, fill=C["up"], extra='id="keep" opacity="0"')
    loss = _txt(x0 + sw / 2, y0 + h + 82, html.escape(spec.get("loss", "-%10")), C, size=40, weight=900,
                fill=C["down"], extra='id="loss" opacity="0"')
    top = _mono(VB_W - 20, y0 - 40, spec.get("eyebrow2", "Sermaye = 10 dilim"), C, anchor="end", extra='id="cap" opacity="0"')
    svg = segs + fill + pct + lab + brace + keep + loss + top
    js = f"tl.to('#cap',{{opacity:1,duration:0.3}},0.25);\n"
    for i in range(n):
        js += f"tl.fromTo('#s{i}',{{opacity:0,y:18}},{{opacity:1,y:0,duration:0.3,ease:'power3.out'}},{0.25 + i*0.045:.3f});\n"
    js += (f"tl.fromTo('#f0',{{scaleY:0,transformOrigin:'50% 100%'}},{{scaleY:1,duration:0.45,ease:'power3.out'}},{t_fill:.3f});"
           f"tl.to(['#p0','#lab'],{{opacity:1,duration:0.3}},{t_fill + 0.2:.3f});\n"
           f"tl.to('#f0',{{fill:'{C['down']}',duration:0.25}},{t_crash:.3f});"
           f"tl.to(['#f0','#p0'],{{y:46,opacity:0.25,duration:0.5,ease:'power2.in'}},{t_crash + 0.15:.3f});"
           f"tl.fromTo('#loss',{{opacity:0,y:-10}},{{opacity:1,y:0,duration:0.3}},{t_crash + 0.4:.3f});"
           f"tl.to('#br',{{opacity:1,duration:0.3}},{t_crash + 0.55:.3f});"
           f"tl.fromTo('#keep',{{opacity:0,x:-20}},{{opacity:1,x:0,duration:0.35,ease:'power3.out'}},{t_crash + 0.6:.3f});\n")
    for i in range(1, n):
        js += f"tl.to('#s{i} rect',{{stroke:'{C['up']}',duration:0.25}},{t_crash + 0.55 + i*0.03:.3f});"
    return svg, js


def _bag_icon(cx, cy, C, s=1.0):
    return (f'<g transform="translate({cx},{cy}) scale({s})"><rect x="-120" y="-110" width="240" height="220" rx="26" '
            f'fill="{C["card_solid"]}" stroke="{C["text"]}" stroke-width="5"/>'
            f'<polyline points="-80,50 -35,10 5,30 75,-50" fill="none" stroke="{C["up"]}" stroke-width="9" '
            f'stroke-linecap="round" stroke-linejoin="round"/><polyline points="45,-52 77,-52 77,-20" fill="none" '
            f'stroke="{C["up"]}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/></g>')


def p_yasak_para(spec, C):
    items = spec.get("items") or ["Kira", "Taksit", "Borç"]
    at = _at(spec, len(items), start=0.6)
    bx, by = 740, 210
    svg = _bag_icon(bx, by, C) + _txt(bx, by + 160, html.escape(spec.get("target", "Borsa")), C, size=40, weight=900)
    js = f"tl.fromTo('#bag',{{opacity:0,scale:0.9}},{{opacity:1,scale:1,duration:0.4,ease:'power3.out'}},0.2);\n"
    svg = f'<g id="bag" style="transform-origin:{bx}px {by}px">{svg}</g>'
    n = len(items)
    ch = 92
    gap = (VB_H - 40 - n * ch) / max(1, n - 1) if n > 1 else 0
    for i, it in enumerate(items):
        y = 20 + i * (ch + gap)
        cid = f"c{i}"
        svg += (f'<g id="{cid}" opacity="0"><rect x="20" y="{y:.0f}" width="300" height="{ch}" rx="18" fill="{C["card"]}" '
                f'stroke="{C["text"]}" stroke-width="3"/>'
                f'{_txt(170, y + ch/2, html.escape(it), C, size=40, weight=800)}'
                f'<g id="x{i}" opacity="0"><line x1="60" y1="{y+ch/2:.0f}" x2="280" y2="{y+ch/2:.0f}" stroke="{C["down"]}" stroke-width="6" stroke-linecap="round"/>'
                f'<circle cx="318" cy="{y+8:.0f}" r="26" fill="{C["down"]}"/>'
                f'<path d="M306 {y-4:.0f} l24 24 M330 {y-4:.0f} l-24 24" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round"/></g></g>')
        t = at[i]
        js += (f"tl.fromTo('#{cid}',{{opacity:0,x:-30}},{{opacity:1,x:0,duration:0.3,ease:'power3.out'}},{max(0.25, t-0.35):.3f});"
               f"tl.to('#{cid}',{{x:270,duration:0.35,ease:'power2.in'}},{t:.3f});"
               f"tl.to('#bag',{{x:8,duration:0.08,yoyo:true,repeat:1}},{t+0.35:.3f});"
               f"tl.to('#x{i}',{{opacity:1,duration:0.12}},{t+0.37:.3f});"
               f"tl.to('#{cid}',{{x:0,opacity:0.6,duration:0.4,ease:'power3.out'}},{t+0.5:.3f});\n")
    if spec.get("note"):
        svg += _txt(VB_W / 2, VB_H - 6, _rich(spec["note"], C), C, size=36, weight=800, extra='id="note" opacity="0"')
        js += f"tl.to('#note',{{opacity:1,duration:0.3}},{at[-1] + 0.9:.3f});"
    return svg, js


def p_plan_formu(spec, C):
    items = spec.get("items") or ["Nereden gireceğim", "Nereden çıkacağım", "Ne kadar koyacağım", "Ne kadar bekleyeceğim"]
    at = _at(spec, len(items), start=0.6)
    n = len(items)
    top, rh = 70, (VB_H - 90) / n
    svg = (f'<rect x="10" y="0" width="{VB_W-20}" height="{VB_H}" rx="26" fill="{C["card_solid"]}" stroke="{C["hair"]}" stroke-width="3"/>'
           + _mono(44, 38, spec.get("eyebrow2", "işlem planı · girmeden önce"), C, anchor="start"))
    js = ""
    for i, it in enumerate(items):
        y = top + i * rh + rh / 2
        svg += (f'<g id="r{i}" opacity="0.35">{_txt(44, y, html.escape(it), C, size=36, weight=700, anchor="start")}'
                f'<line id="u{i}" x1="560" y1="{y+18:.0f}" x2="{VB_W-110}" y2="{y+18:.0f}" stroke="{C["accent"]}" '
                f'stroke-width="6" stroke-linecap="round"/>'
                f'<line x1="560" y1="{y+18:.0f}" x2="{VB_W-110}" y2="{y+18:.0f}" stroke="{C["hair"]}" stroke-width="3" opacity="0.8"/>'
                f'<path id="k{i}" d="M{VB_W-86} {y} l14 14 l26 -30" fill="none" stroke="{C["accent_ink"]}" stroke-width="8" '
                f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="70" stroke-dashoffset="70"/></g>')
        t = at[i]
        js += (f"tl.to('#r{i}',{{opacity:1,duration:0.2}},{t-0.1:.3f});"
               f"tl.fromTo('#u{i}',{{scaleX:0,transformOrigin:'0% 50%'}},{{scaleX:1,duration:0.45,ease:'power2.out'}},{t:.3f});"
               f"tl.to('#k{i}',{{strokeDashoffset:0,duration:0.25,ease:'power2.out'}},{t+0.4:.3f});\n")
    if spec.get("stamp"):
        st = float(spec.get("stamp_at", at[-1] + 1.0))
        cx, cy = VB_W - 230, VB_H - 90
        svg += (f'<g id="stamp" opacity="0" style="transform-origin:{cx}px {cy}px" transform="rotate(-8 {cx} {cy})">'
                f'<rect x="{cx-190}" y="{cy-44}" width="380" height="88" rx="14" fill="{C["bg"]}" stroke="{C["accent"]}" stroke-width="6"/>'
                f'{_txt(cx, cy+2, html.escape(spec["stamp"]), C, size=40, weight=900, fill=C["accent_ink"])}</g>')
        js += f"tl.fromTo('#stamp',{{opacity:0,scale:1.6}},{{opacity:1,scale:1,duration:0.3,ease:'power3.in'}},{st:.3f});"
    return svg, js


def p_para_akisi(spec, C):
    items = spec.get("items") or ["Mevduat", "Altın", "Borsa", "Döviz"]
    target = spec.get("target", "Borsa")
    at = _at(spec, len(items), start=0.5)
    land = float(spec.get("land", at[-1] + 0.8))
    pos = [(170, 80), (750, 80), (750, 360), (170, 360)][:len(items)]
    svg, js = "", ""
    # kenar yolları (döngü) — noktalar SADECE bu kesikli çizgilerin üstünde gezer (19.10.2026: hap metinlerini kapatmasın)
    edges = []
    for i in range(len(pos)):
        (x1, y1), (x2, y2) = pos[i], pos[(i + 1) % len(pos)]
        if y1 == y2:
            a, b = (x1 + (130 if x2 > x1 else -130), y1), (x2 + (-130 if x2 > x1 else 130), y2)
        else:
            a, b = (x1, y1 + (50 if y2 > y1 else -50)), (x2, y2 + (-50 if y2 > y1 else 50))
        edges.append((a, b))
        svg += f'<path id="e{i}" d="M{a[0]} {a[1]} L{b[0]} {b[1]}" fill="none" stroke="{C["hair"]}" stroke-width="5" stroke-dasharray="4 14" stroke-linecap="round" opacity="0"/>'
        js += f"tl.to('#e{i}',{{opacity:1,duration:0.3}},{0.3 + i*0.08:.3f});"
    ti = items.index(target) if target in items else 2
    # hedefe bağlanan çizgi uçları (toplanma noktaları hap kenarında, metnin dışında)
    n_ = len(pos)
    docks = [edges[(ti - 1) % n_][1], edges[ti][0]]
    # akan para noktaları — haplardan ÖNCE çizilir (z-sırası: hapların altında kalır)
    for i, (a, b) in enumerate(edges):
        for j in range(2):
            cid = f"d{i}_{j}"
            svg += f'<circle id="{cid}" cx="{a[0]}" cy="{a[1]}" r="11" fill="{C["accent"]}" opacity="0"/>'
            t0 = 0.6 + j * 0.5 + i * 0.12
            if i == (ti - 1) % n_:
                dock = b
            elif i == ti:
                dock = a
            else:  # karşı kenar: çizgi boyunca en yakın hedef ucuna (orta boşluktan, hap üstünden değil)
                dock = min(docks, key=lambda d: (d[0] - (a[0] + b[0]) / 2) ** 2 + (d[1] - (a[1] + b[1]) / 2) ** 2)
            js += (f"tl.set('#{cid}',{{opacity:1}},{t0:.3f});"
                   f"tl.fromTo('#{cid}',{{attr:{{cx:{a[0]},cy:{a[1]}}}}},{{attr:{{cx:{b[0]},cy:{b[1]}}},duration:0.9,ease:'power1.inOut',repeat:{max(0, int((land-t0)/0.9)-1)}}},{t0:.3f});"
                   f"tl.to('#{cid}',{{attr:{{cx:{dock[0]},cy:{dock[1]}}},duration:0.45,ease:'power3.in'}},{land:.3f});"
                   f"tl.to('#{cid}',{{opacity:0,duration:0.1}},{land+0.45:.3f});\n")
    for i, ((x, y), it) in enumerate(zip(pos, items)):
        svg += (f'<g id="n{i}" opacity="0"><rect id="nb{i}" x="{x-125}" y="{y-46}" width="250" height="92" rx="46" '
                f'fill="{C["bg"]}" stroke="{C["text"]}" stroke-width="3"/>{_txt(x, y+2, html.escape(it), C, size=38, weight=800, extra=f"id=\"nt{i}\"")}</g>')
        js += (f"tl.fromTo('#n{i}',{{opacity:0,scale:0.85,transformOrigin:'{x}px {y}px'}},{{opacity:1,scale:1,duration:0.3,ease:'back.out(2)'}},{max(0.2, at[i]-0.15):.3f});"
               f"tl.to('#nb{i}',{{stroke:'{C['accent']}',duration:0.15}},{at[i]:.3f});"
               f"tl.to('#nb{i}',{{stroke:'{C['text']}',duration:0.3}},{at[i]+0.45:.3f});\n")
    js += (f"tl.to('#nb{ti}',{{fill:'{C['accent']}',stroke:'{C['accent']}',duration:0.25}},{land+0.4:.3f});"
           f"tl.to('#nt{ti}',{{fill:'#FFFFFF',duration:0.25}},{land+0.4:.3f});"
           f"tl.fromTo('#n{ti}',{{scale:1}},{{scale:1.12,duration:0.18,yoyo:true,repeat:1,transformOrigin:'{pos[ti][0]}px {pos[ti][1]}px'}},{land+0.4:.3f});")
    for i in range(len(pos)):
        if i != ti:
            js += f"tl.to('#n{i}',{{opacity:0.4,duration:0.3}},{land+0.4:.3f});"
    if spec.get("note"):
        svg += _txt(VB_W / 2, VB_H / 2 + 4, _rich(spec["note"], C), C, size=36, weight=800, extra='id="note" opacity="0"')
        js += f"tl.to('#note',{{opacity:1,duration:0.3}},{land+0.6:.3f});"
    return svg, js


def p_risk(spec, C):
    v = max(0.0, min(1.0, float(spec.get("value", 0.85))))
    land = float(spec.get("land", 1.6))
    labels = spec.get("labels") or ["Düşük", "Orta", "Yüksek"]
    cx, cy, r = VB_W / 2, 380, 300
    def pt(a, rr):  # a: 0..1 soldan sağa
        ang = math.pi * (1 - a)
        return cx + rr * math.cos(ang), cy - rr * math.sin(ang)
    cols = [C["up"], C["dim"], C["down"]]
    svg = ""
    for i in range(3):
        a0, a1 = i / 3 + 0.008, (i + 1) / 3 - 0.008
        (x0, y0), (x1, y1) = pt(a0, r), pt(a1, r)
        svg += f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}" fill="none" stroke="{cols[i]}" stroke-width="34" stroke-linecap="butt" opacity="0.9"/>'
        lx, ly = pt((i + 0.5) / 3, r - 80)
        svg += _txt(lx, ly, html.escape(labels[i]), C, size=32, weight=800, fill=C["muted"])
    for j in range(13):
        (x0, y0), (x1, y1) = pt(j / 12, r + 26), pt(j / 12, r + 40)
        svg += f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{C["hair"]}" stroke-width="4"/>'
    svg = f'<g id="dial" opacity="0">{svg}</g>'
    svg += (f'<g id="needle">'
            f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - r + 40}" stroke="{C["text"]}" stroke-width="12" stroke-linecap="round"/></g>'
            f'<circle cx="{cx}" cy="{cy}" r="26" fill="{C["text"]}"/>')
    deg = -90 + 180 * v
    js = (f"gsap.set('#needle',{{rotation:-90,svgOrigin:'{cx} {cy}'}});tl.to('#dial',{{opacity:1,duration:0.35}},0.2);"
          f"tl.to('#needle',{{rotation:{deg - 70:.1f},duration:0.5,ease:'power2.inOut',svgOrigin:'{cx} {cy}'}},{max(0.4, land - 1.1):.3f});"
          f"tl.to('#needle',{{rotation:{deg:.1f},duration:0.6,ease:'back.out(2.2)',svgOrigin:'{cx} {cy}'}},{land - 0.55:.3f});")
    if spec.get("note"):
        svg += _txt(cx, VB_H - 6, _rich(spec["note"], C), C, size=36, weight=800, extra='id="note" opacity="0"')
        js += f"tl.to('#note',{{opacity:1,duration:0.3}},{land + 0.15:.3f});"
    return svg, js


def p_odak(spec, C):
    items = spec.get("items") or ["Borsa", "Kripto", "Altın", "Döviz", "VİOP", "Emtia"]
    pick = spec.get("pick", items[0])
    land = float(spec.get("land", 2.0))
    pos = [(170, 90), (470, 70), (760, 110), (150, 300), (460, 330), (770, 300), (310, 200), (620, 210)]
    svg, js = "", ""
    pi = items.index(pick) if pick in items else 0
    for i, it in enumerate(items[:len(pos)]):
        x, y = pos[i]
        w = 90 + 25 * len(it)
        svg += (f'<g id="o{i}" opacity="0"><rect id="ob{i}" x="{x-w/2:.0f}" y="{y-42}" width="{w:.0f}" height="84" rx="42" '
                f'fill="{C["card"]}" stroke="{C["text"]}" stroke-width="3"/>{_txt(x, y+2, html.escape(it), C, size=36, weight=800, extra=f"id=\"ot{i}\"")}</g>')
        t = 0.25 + i * 0.12
        js += f"tl.fromTo('#o{i}',{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.3,ease:'power3.out'}},{t:.3f});"
        # dağınık hafif salınım yok (sallantı marka dışı) — sadece giriş
    px_, py_ = pos[pi]
    for i in range(min(len(items), len(pos))):
        if i != pi:
            js += f"tl.to('#o{i}',{{opacity:0.12,scale:0.9,transformOrigin:'{pos[i][0]}px {pos[i][1]}px',duration:0.4,ease:'power2.out'}},{land:.3f});"
    js += (f"tl.to('#o{pi}',{{x:{VB_W/2 - px_:.0f},y:{VB_H/2 - 10 - py_:.0f},scale:1.45,transformOrigin:'{px_}px {py_}px',duration:0.55,ease:'power3.inOut'}},{land:.3f});"
           f"tl.to('#ob{pi}',{{fill:'{C['accent']}',stroke:'{C['accent']}',duration:0.3}},{land + 0.3:.3f});"
           f"tl.to('#ot{pi}',{{fill:'#FFFFFF',duration:0.3}},{land + 0.3:.3f});")
    if spec.get("note"):
        svg += _txt(VB_W / 2, VB_H - 20, _rich(spec["note"], C), C, size=36, weight=800, extra='id="note" opacity="0"')
        js += f"tl.to('#note',{{opacity:1,duration:0.3}},{land + 0.7:.3f});"
    return svg, js


def p_yonetim(spec, C):
    good = spec.get("good") or ["Rekor kâr!", "Yeni yatırım", "Hedef büyük"]
    bad = spec.get("bad", "…")
    at = _at(spec, len(good) + 1, start=0.5)
    svg = (_mono(230, 22, spec.get("left", "iyi günde"), C) + _mono(690, 22, spec.get("right", "kötü günde"), C)
           + f'<line x1="460" y1="0" x2="460" y2="{VB_H}" stroke="{C["hair"]}" stroke-width="3"/>')
    js = ""
    for i, g in enumerate(good):
        y = 80 + i * 112
        w = 90 + 21 * len(g)
        x = 230 - w / 2 + (i % 2) * 24 - 12
        svg += (f'<g id="g{i}" opacity="0"><rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="84" rx="24" fill="{C["card"]}" stroke="{C["text"]}" stroke-width="3"/>'
                f'<path d="M{x+30:.0f} {y+82} l-8 22 l28 -22" fill="{C["card"]}" stroke="{C["text"]}" stroke-width="3" stroke-linejoin="round"/>'
                f'{_txt(x + w/2, y + 43, html.escape(g), C, size=34, weight=800)}</g>')
        js += f"tl.fromTo('#g{i}',{{opacity:0,scale:0.7,transformOrigin:'230px {y+42}px'}},{{opacity:1,scale:1,duration:0.3,ease:'back.out(2)'}},{at[i]:.3f});"
    tb = at[-1]
    svg += (f'<g id="bd" opacity="0"><rect x="600" y="180" width="180" height="84" rx="24" fill="none" stroke="{C["dim"]}" stroke-width="3" stroke-dasharray="10 10"/>'
            f'{_txt(690, 220, html.escape(bad), C, size=44, weight=900, fill=C["dim"])}</g>'
            + _txt(690, 330, html.escape(spec.get("bad_note", "Ses yok")), C, size=38, weight=800, fill=C["down"], extra='id="bn" opacity="0"'))
    js += (f"tl.to('#bd',{{opacity:1,duration:0.3}},{tb:.3f});tl.to('#bd',{{opacity:0.35,duration:0.6}},{tb+0.5:.3f});"
           f"tl.fromTo('#bn',{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.3}},{tb+0.6:.3f});")
    return svg, js


PROPS = dict(kasa=p_kasa, yasak_para=p_yasak_para, plan_formu=p_plan_formu, para_akisi=p_para_akisi,
             risk=p_risk, odak=p_odak, yonetim=p_yonetim)


def build_prop(spec, C, px):
    name = spec["prop"]
    if name not in PROPS:
        raise SystemExit(f"bilinmeyen prop: {name} (var olanlar: {', '.join(PROPS)})")
    svg, js = PROPS[name](spec, C)
    head = ""
    js_head = ""
    if spec.get("step") or spec.get("title"):
        a_, _, b_ = str(spec.get("step", "")).partition("/")
        num = f'<div class="pnum" id="pnum">{html.escape(a_.strip())}</div>' if a_.strip() else ""
        ttl = f'<div class="ptitle" id="ptitle">{_richh(spec.get("title", ""))}</div>' if spec.get("title") else ""
        lab = f'<div class="eb plab">{html.escape(a_.strip())} / {html.escape(b_.strip())}</div>' if b_ else ""
        head = f'<div class="phead">{num}<div class="pht">{lab}{ttl}</div></div>'
        js_head = ("tl.fromTo('#pnum',{opacity:0,y:24},{opacity:1,y:0,duration:0.4,ease:'power3.out'},0.08);"
                   "tl.fromTo('#ptitle',{opacity:0,x:-24},{opacity:1,x:0,duration:0.4,ease:'power3.out'},0.16);\n")
    body = (f'<div class="card prop" id="card">{head}<svg class="psvg" viewBox="0 0 {VB_W} {VB_H}" '
            f'xmlns="http://www.w3.org/2000/svg" overflow="visible">{svg}</svg></div>')
    css = (f".prop .phead{{display:flex;align-items:center;gap:{px(28)};margin-bottom:{px(18)};}}"
           f".pnum{{font-weight:900;font-size:{px(150)};line-height:.8;color:{C['accent']};letter-spacing:-.04em;}}"
           f".pht{{min-width:0;}} .plab{{margin-bottom:{px(6)} !important;}}"
           f".ptitle{{font-weight:800;font-size:{px(58)};line-height:1.08;letter-spacing:-.01em;}}"
           f".psvg{{width:100%;height:auto;display:block;}}")
    return body, js_head + js, css


# ---------------------------------------------------------------- kanıtlı hook
def build_proof(spec, C, px, W, region_w, region_h):
    items = spec["items"]
    n = len(items)
    at = _at(spec, n, start=0.15, dur=float(spec.get("duration", 3)))
    cw = min(260, (region_w - 20) / max(1, n) - 12)
    ch = cw * 1.45 if any("img" in it for it in items) else cw * 1.2
    span = region_w - cw - 20
    cards, js = "", ""
    for i, it in enumerate(items):
        x = 10 + (span * i / max(1, n - 1) if n > 1 else span / 2)
        rot = (i - (n - 1) / 2) * 3.5
        y = (region_h - ch) / 2 + abs(i - (n - 1) / 2) * 8
        if "img" in it:
            inner = f'<img src="{html.escape(it["img"])}" style="width:100%;height:100%;object-fit:cover;border-radius:{px(18)};">'
        else:
            inner = (f'<div class="pfn">{html.escape(str(it.get("n", i + 1)))}</div>'
                     f'<div class="pft">{_richh(it.get("text", ""))}</div>')
        cards += (f'<div class="pf" id="pf{i}" style="left:{x:.0f}px;top:{y:.0f}px;width:{cw:.0f}px;height:{ch:.0f}px;'
                  f'transform:rotate({rot:.1f}deg)">{inner}</div>')
        js += (f"tl.fromTo('#pf{i}',{{opacity:0,y:60,scale:0.8}},{{opacity:1,y:0,scale:1,duration:0.28,ease:'back.out(1.8)'}},{at[i]:.3f});\n")
    if spec.get("title"):
        cards += f'<div class="pftitle" id="pft">{_richh(spec["title"])}</div>'
        js += f"tl.fromTo('#pft',{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.35,ease:'power3.out'}},{at[-1] + 0.15:.3f});"
    body = f'<div id="card" class="proofwrap" style="position:relative;width:{region_w}px;height:{region_h}px;">{cards}</div>'
    css = (f".pf{{position:absolute;box-sizing:border-box;background:{C['card']};border-radius:{px(22)};box-shadow:{C['shadow']};"
           f"border:3px solid {C['bg']};padding:{px(8)};display:flex;flex-direction:column;justify-content:center;align-items:center;opacity:0;}}"
           f".pfn{{font-weight:900;font-size:{min(110, cw*0.62):.0f}px;line-height:.9;color:{C['accent']};}}"
           f".pft{{font-weight:800;font-size:{min(34, cw*0.19):.0f}px;line-height:1.1;text-align:center;margin-top:{px(10)};color:{C['text']};}}"
           f".pftitle{{position:absolute;left:0;right:0;bottom:-{px(10)};text-align:center;font-weight:900;font-size:{px(64)};color:#FFFFFF;"
           f"text-shadow:0 4px 18px rgba(0,0,0,.55);}}")
    return body, js, css
