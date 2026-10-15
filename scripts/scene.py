"""BorsaSemih sahne kütüphanesi: JSON spec -> HyperFrames projesi -> şeffaf .webm overlay.

Tüm sahneler frame.md'deki atomları kullanır (renk, Montserrat/JetBrains Mono, kart, hareket dili).
Böylece her videoda aynı "tasarlanmış" aile çıkar ve sahneleri her seferinde sıfırdan yazmayız.

Kullanım:
  python scene.py spec.json -o edit/animations/slot_1          # proje yaz + lint + render.webm
  python scene.py spec.json -o ... --no-render                  # sadece HTML (önizleme için)
  python scene.py spec.json -o ... --still 1.2                  # t=1.2 sn'de tek kare PNG (hızlı QA)

Spec (ortak alanlar):
  {"type": "stat|compare|list|ticker|question|cta|timeline|chapter|quote|terminal",
   "format": "reels|youtube",            # 1080x1920 veya 1920x1080
   "region": "band|panel|full",          # band: başın üstü kart / panel: split paneli / full: tam ekran
   "duration": 3.5,                      # sn (overlay süresi)
   "land": 1.0,                          # sahnenin "iniş" anı (sn, overlay başına göre) = konuşmadaki anahtar kelime
   "eyebrow": "BIST · faiz kararı", "source": "Kaynak: TCMB, 23.10.2026",
   "step": "3/6"}                        # opsiyonel: numaralı madde rozeti (her tipte)
  stat:     value, decimals, prefix, suffix, unit, label, (bar: 0-1 doluluk), (direction: up|down)
  compare:  old, new, note                      ("$5" -> "$4", note "%20 daha ucuz")
  list:     title, items:[...], at:[sn,...]     (her madde konuşmada hangi sn'de söyleniyorsa)
  ticker:   code, price, change ("+3,2" / "-1,4")
  question: text  (*kelime* turuncu olur)       — konuşanın üstüne perde + büyük cümle
  cta:      text, sub (varsayılan "Yorumlara yaz ↓")
  timeline: points:[{"label":"2008","text":"Kriz"},...], at:[sn,...]
  chapter:  index ("Bölüm 2"), title           — YouTube bölüm kartı
  quote:    text, who
  terminal: lines:[...], at:[sn,...]           — "$ not.txt" satırları yazılarak gelir (kapanış dersi)
Metinlerde *kelime* -> turuncu vurgu. Tamamı büyük harf kullanma.
"""
from __future__ import annotations

import argparse, html, json, re, shutil, subprocess, sys
from pathlib import Path

_B = Path(__file__).resolve().parent
PKG = _B if (_B / "fonts").exists() else _B.parent   # ~/studio/ veya paket kökü
C = dict(bg="#08142D", card="rgba(8,20,45,0.92)", card_solid="#0E1F42", stripe="#2F80FF",
         accent="#FF8C1E", up="#2BD47D", down="#FF5A5F", text="#FFFFFF", muted="#A9B4C8",
         dim="#6B7894", hair="rgba(255,255,255,0.10)", grid="rgba(47,128,255,0.07)", scrim="rgba(0,0,0,0.55)")


def tr_num(v: float, decimals: int = 0) -> str:
    s = f"{abs(v):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if v < 0 else "") + s


def rich(t: str) -> str:
    t = html.escape(t)
    return re.sub(r"\*(.+?)\*", r'<span class="acc">\1</span>', t)


def region_rect(fmt, region):
    W, H = (1080, 1920) if fmt == "reels" else (1920, 1080)
    if region == "full":
        return W, H, (0, 0, W, H), True
    if fmt == "reels":
        # panel: alt 220 px altyazı şeridi (split anında altyazı yüze değil buraya düşer, bkz make_ass)
        return W, H, ((0, 0, W, 864) if region == "panel" else (60, 130, W - 120, 420)), region == "panel"
    return W, H, ((0, 0, 960, H) if region == "panel" else (80, 70, 900, 360)), region == "panel"


def build(spec: dict) -> str:
    fmt = spec.get("format", "reels")
    region = spec.get("region", "band")
    typ = spec["type"]
    if typ in ("question",):
        region = "full"
    dur = float(spec.get("duration", 3.5))
    land = float(spec.get("land", min(1.0, dur / 3)))
    W, H, (rx, ry, rw, rh), filled = region_rect(fmt, region)
    k = 1.0 if fmt == "reels" else 0.78
    bg = "transparent"
    if filled and typ != "question":
        bg = f"{C['bg']}; background-image: linear-gradient({C['grid']} 2px, transparent 2px), linear-gradient(90deg, {C['grid']} 2px, transparent 2px); background-size: 60px 60px"
    if typ == "question":
        bg = C["scrim"]
    eyebrow = spec.get("eyebrow", "")
    source = spec.get("source", "")
    body, js = "", ""

    def eb(txt, cls="eb"):
        return f'<div class="{cls}">{html.escape(txt)}</div>' if txt else ""

    if typ == "stat":
        dec = int(spec.get("decimals", 0))
        val = float(spec["value"])
        dirn = spec.get("direction")
        col = C["up"] if dirn == "up" else C["down"] if dirn == "down" else C["text"]
        bar = spec.get("bar")
        body = f"""<div class="card" id="card">{eb(eyebrow)}
  <div class="statrow"><span class="pre">{html.escape(spec.get('prefix',''))}</span><span id="num" class="stat" style="color:{col}">{tr_num(0, dec)}</span><span class="suf">{html.escape(spec.get('suffix',''))}</span><span class="unit">{html.escape(spec.get('unit',''))}</span></div>
  {f'<div class="label">{rich(spec["label"])}</div>' if spec.get('label') else ''}
  {'<div class="track"><div id="fill" class="fill"></div></div>' if bar is not None else ''}
  {eb(source, 'src')}</div>"""
        t0 = max(0.35, land - 0.85)
        js = f"""const o={{v:0}}; tl.to(o,{{v:{val},duration:{land - t0:.3f},ease:"power2.out",onUpdate:()=>{{document.getElementById('num').textContent=fmt(o.v,{dec});}}}},{t0:.3f});
tl.fromTo('#num',{{scale:1}},{{scale:1.06,duration:0.12,yoyo:true,repeat:1,ease:"power2.out"}},{land:.3f});"""
        if bar is not None:
            js += f"\ntl.fromTo('#fill',{{width:'0%'}},{{width:'{float(bar)*100:.1f}%',duration:{land - t0:.3f},ease:'power2.out'}},{t0:.3f});"
    elif typ == "compare":
        n = len(spec["old"]) + len(spec["new"])
        avail = (rw if region == "band" else rw * 0.86) - 14 - 104 * k - 160 * k
        cmp_px = int(min(132 * k, avail / (0.66 * max(n, 1))))
        body = f"""<div class="card" id="card">{eb(eyebrow)}
  <div class="cmp" style="font-size:{cmp_px}px"><span id="old" class="old">{html.escape(spec['old'])}<i id="strike"></i></span><span class="arrow">→</span><span id="new" class="new">{html.escape(spec['new'])}</span></div>
  {f'<div id="note" class="chip">{rich(spec["note"])}</div>' if spec.get('note') else ''}
  {eb(source, 'src')}</div>"""
        js = f"""tl.fromTo('#strike',{{scaleX:0}},{{scaleX:1,duration:0.3,ease:"power2.out"}},{max(0.4, land - 0.45):.3f});
tl.to('#old',{{color:'{C['dim']}',duration:0.3}},{max(0.4, land - 0.45):.3f});
tl.fromTo('#new',{{opacity:0,x:-24,scale:0.9}},{{opacity:1,x:0,scale:1,duration:0.4,ease:"power3.out"}},{land - 0.3:.3f});
tl.fromTo('#note',{{opacity:0,y:16}},{{opacity:1,y:0,duration:0.35,ease:"power3.out"}},{land + 0.25:.3f});"""
    elif typ in ("list", "timeline"):
        items = spec["items"] if typ == "list" else spec["points"]
        at = spec.get("at") or [0.5 + i * max(0.6, (dur - 1.2) / max(1, len(items))) for i in range(len(items))]
        if typ == "list":
            lis = "".join(f'<li id="i{i}"><span class="ck">✓</span><span>{rich(t)}</span></li>' for i, t in enumerate(items))
            body = f"""<div class="card" id="card">{eb(eyebrow)}{f'<div class="h2">{rich(spec["title"])}</div>' if spec.get('title') else ''}<ul class="list">{lis}</ul>{eb(source,'src')}</div>"""
        else:
            pts = "".join(f'<div class="pt" id="i{i}"><div class="dot"></div><div class="yr">{html.escape(p["label"])}</div><div class="pt-t">{rich(p.get("text",""))}</div></div>' for i, p in enumerate(items))
            body = f"""<div class="card wide" id="card">{eb(eyebrow)}{f'<div class="h2">{rich(spec["title"])}</div>' if spec.get('title') else ''}<div class="tl"><div class="line"></div>{pts}</div>{eb(source,'src')}</div>"""
        js = ""
        for i, t in enumerate(at):
            t = float(t)
            js += f"tl.fromTo('#i{i}',{{opacity:0,x:-24}},{{opacity:1,x:0,duration:0.35,ease:'power3.out'}},{max(0.3, t - 0.2):.3f});\n"
            js += f"tl.to('#i{i}',{{color:'{C['accent']}',duration:0.2}},{t:.3f});\n"
            if i:
                js += f"tl.to('#i{i-1}',{{color:'{C['muted']}',duration:0.2}},{t:.3f});\n"
            if typ == "timeline":
                js += f"tl.to('#i{i} .dot',{{backgroundColor:'{C['accent']}',scale:1.3,duration:0.2}},{t:.3f});\n"
                if i:
                    js += f"tl.to('#i{i-1} .dot',{{backgroundColor:'{C['stripe']}',scale:1,duration:0.2}},{t:.3f});\n"
    elif typ == "ticker":
        ch = spec.get("change", "")
        upc = not ch.strip().startswith("-")
        col = C["up"] if upc else C["down"]
        est = (0.74 * 96 * len(spec["code"]) + 0.6 * 64 * len(spec.get("price", "")) + 0.62 * 52 * (len(ch) + 3) + 140) * k
        avail = (rw if region == "band" else rw * 0.86) - 14 - 104 * k
        ts = min(1.0, avail / est)
        body = f"""<div class="card" id="card">{eb(eyebrow)}<div class="tick" style="zoom:{ts:.3f}"><span class="code">{html.escape(spec['code'])}</span><span class="price">{html.escape(spec.get('price',''))}</span>
  <span id="chg" class="chg" style="color:{col};background:{col}2E">{'▲' if upc else '▼'} %{html.escape(ch.lstrip('+-'))}</span></div>{eb(source,'src')}</div>"""
        js = f"tl.fromTo('#chg',{{opacity:0,scale:0.6}},{{opacity:1,scale:1,duration:0.35,ease:'back.out(2)'}},{land:.3f});"
    elif typ == "question":
        body = f"""<div class="qwrap" id="card"><div class="h1">{rich(spec['text'])}</div></div>"""
    elif typ == "cta":
        body = f"""<div class="card" id="card"><div class="h2">{rich(spec['text'])}</div><div class="cta">{html.escape(spec.get('sub','Yorumlara yaz ↓'))}</div></div>"""
    elif typ == "chapter":
        body = f"""<div class="card" id="card">{eb(spec.get('index',''))}<div class="h1">{rich(spec['title'])}</div></div>"""
    elif typ == "terminal":
        lines = spec["lines"]
        at = spec.get("at") or [0.4 + i * max(0.7, (dur - 1.2) / max(1, len(lines))) for i in range(len(lines))]
        lis = "".join(f'<div class="tl-line" id="l{i}"><span class="pr">$</span> <span id="t{i}"></span></div>' for i in range(len(lines)))
        body = f"""<div class="card term" id="card">{eb(eyebrow or 'not.txt')}{lis}</div>"""
        js = ""
        for i, (ln, t) in enumerate(zip(lines, at)):
            n = len(ln); d = min(1.2, 0.035 * n)
            js += (f"tl.set('#l{i}',{{opacity:1}},{float(t):.3f});"
                   f"(function(){{const o={{n:0}};const s={json.dumps(ln)};tl.to(o,{{n:{n},duration:{d:.3f},ease:'none',"
                   f"onUpdate:()=>{{document.getElementById('t{i}').textContent=s.slice(0,Math.round(o.n));}}}},{float(t):.3f});}})();\n")
    elif typ == "quote":
        body = f"""<div class="card" id="card"><div class="qm">“</div><div class="h2">{rich(spec['text'])}</div>{eb(spec.get('who',''),'src')}</div>"""
    else:
        raise SystemExit(f"bilinmeyen sahne tipi: {typ}")

    if spec.get("step"):  # numaralı madde rozeti: "3/6" -> kartın en üstünde turuncu
        a_, _, b_ = str(spec["step"]).partition("/")
        badge = f'<div class="step" id="step">{html.escape(a_)}<span>/{html.escape(b_)}</span></div>' if b_ else f'<div class="step" id="step">{html.escape(a_)}</div>'
        body = re.sub(r'(<div class="card[^"]*" id="card">)', lambda m: m.group(1) + badge, body, count=1)
        js = f"tl.fromTo('#step',{{opacity:0,y:14}},{{opacity:1,y:0,duration:0.35,ease:'power3.out'}},0.2);\n" + js
    stage_bg = bg if region == "full" or typ == "question" else "transparent"
    region_bg = bg if region == "panel" else "transparent"
    exit_t = max(land + 0.6, dur - 0.32)
    fonts = "".join(
        f"@font-face{{font-family:'{fam}';src:url('fonts/{f}') format('truetype');font-weight:{w};}}"
        for fam, f, w in [("Montserrat", "Montserrat-Medium.ttf", 500), ("Montserrat", "Montserrat-SemiBold.ttf", 600),
                          ("Montserrat", "Montserrat-Bold.ttf", 700), ("Montserrat", "Montserrat-ExtraBold.ttf", 800),
                          ("Montserrat", "Montserrat-Black.ttf", 900), ("JetBrains Mono", "JetBrainsMono-Medium.ttf", 500)])
    px = lambda v: f"{v * k:.0f}px"
    center = "center" if region in ("panel", "full") else "flex-start"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{fonts}
html,body{{margin:0;background:transparent;}}
#stage{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:{stage_bg};font-family:'Montserrat',sans-serif;color:{C['text']};}}
#region{{position:absolute;left:{rx}px;top:{ry}px;width:{rw}px;height:{rh}px;box-sizing:border-box;padding-bottom:{220 if (region == 'panel' and fmt == 'reels') else 0}px;display:flex;flex-direction:column;justify-content:{center};align-items:{'center' if region != 'band' else 'stretch'};background:{region_bg};}}
.card{{box-sizing:border-box;background:{C['card']};border-left:14px solid {C['stripe']};border-radius:28px;padding:{px(44)} {px(52)};box-shadow:0 24px 60px rgba(0,0,0,.35);width:{'100%' if region == 'band' else '86%'};}}
.card.wide{{width:{'100%' if region == 'band' else '92%'};}}
.eb,.src{{font-family:'JetBrains Mono',monospace;font-weight:500;font-size:{px(30)};color:{C['muted']};letter-spacing:.02em;}}
.eb{{margin-bottom:{px(14)};}} .src{{margin-top:{px(18)};font-size:{px(24)};color:{C['dim']};}}
.statrow{{display:flex;align-items:baseline;gap:0;}}
.stat{{font-weight:900;font-size:{px(168)};line-height:.95;letter-spacing:-.03em;font-variant-numeric:tabular-nums;display:inline-block;}}
.pre,.suf{{font-weight:800;font-size:{px(110)};}} .unit{{font-weight:700;font-size:{px(64)};color:{C['muted']};margin-left:{px(8)};}}
.label{{font-weight:700;font-size:{px(42)};color:{C['muted']};margin-top:{px(8)};}}
.track{{height:{px(20)};border-radius:10px;background:rgba(255,255,255,.08);margin-top:{px(22)};overflow:hidden;}} .fill{{height:100%;width:0;background:{C['accent']};border-radius:10px;}}
.cmp{{display:flex;align-items:center;gap:{px(28)};font-weight:900;letter-spacing:-.03em;white-space:nowrap;}}
.old{{position:relative;color:{C['text']};}} .old i{{position:absolute;left:-4%;right:-4%;top:52%;height:{px(12)};background:{C['down']};transform-origin:left;transform:scaleX(0);border-radius:6px;}}
.arrow{{color:{C['dim']};font-weight:700;font-size:{px(90)};}} .new{{color:{C['accent']};opacity:0;}}
.chip{{display:inline-block;margin-top:{px(18)};padding:{px(10)} {px(24)};border-radius:999px;background:{C['accent']}2E;color:{C['accent']};font-weight:800;font-size:{px(40)};opacity:0;}}
.h1{{font-weight:900;font-size:{px(104)};line-height:1.04;letter-spacing:-.02em;}}
.h2{{font-weight:800;font-size:{px(66)};line-height:1.1;letter-spacing:-.01em;margin-bottom:{px(12)};}}
.acc{{color:{C['accent']};}}
.list{{list-style:none;margin:{px(10)} 0 0;padding:0;}} .list li{{display:flex;gap:{px(22)};font-weight:700;font-size:{px(54)};line-height:1.2;padding:{px(14)} 0;opacity:0;}}
.ck{{color:{C['stripe']};font-weight:900;}}
.tl{{position:relative;display:flex;justify-content:space-between;margin-top:{px(40)};padding-top:{px(20)};}}
.tl .line{{position:absolute;left:0;right:0;top:{px(36)};height:4px;background:{C['hair']};}}
.pt{{position:relative;display:flex;flex-direction:column;align-items:center;flex:1;opacity:0;color:{C['text']};}}
.dot{{width:{px(30)};height:{px(30)};border-radius:50%;background:{C['stripe']};}}
.yr{{font-weight:900;font-size:{px(48)};margin-top:{px(14)};}} .pt-t{{font-weight:600;font-size:{px(32)};color:{C['muted']};text-align:center;margin-top:{px(6)};}}
.tick{{display:flex;align-items:center;gap:{px(26)};white-space:nowrap;}} .code{{font-weight:900;font-size:{px(96)};}} .price{{font-weight:700;font-size:{px(64)};color:{C['muted']};}}
.chg{{font-weight:800;font-size:{px(52)};padding:{px(8)} {px(22)};border-radius:999px;}}
.qwrap{{box-sizing:border-box;width:100%;padding:0 {px(80)};margin-top:{'-'+px(240) if fmt == 'reels' else '0'};}}
.cta{{margin-top:{px(18)};font-weight:800;font-size:{px(52)};color:{C['accent']};}}
.term{{background:{C['card_solid']};font-family:'JetBrains Mono',monospace;}} .tl-line{{font-family:'JetBrains Mono',monospace;font-weight:500;font-size:{px(44)};line-height:1.5;opacity:0;white-space:pre-wrap;}} .pr{{color:{C['accent']};}}
.step{{font-weight:900;font-size:{px(84)};line-height:1;color:{C['accent']};letter-spacing:-.02em;margin-bottom:{px(10)};}} .step span{{font-size:{px(44)};color:{C['dim']};font-weight:800;}}
.qm{{font-weight:900;font-size:{px(160)};line-height:.6;color:{C['accent']};height:{px(70)};}}
</style></head><body>
<div id="stage" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="{W}" data-height="{H}">
 <div id="region" class="clip" data-start="0" data-duration="{dur}" data-track-index="0">{body}</div>
</div>
<script src="gsap.min.js"></script>
<script>
function fmt(v,d){{const s=Math.abs(v).toFixed(d).split('.');s[0]=s[0].replace(/\\B(?=(\\d{{3}})+(?!\\d))/g,'.');return (v<0?'-':'')+s.join(',');}}
document.fonts.ready.then(()=>{{
const tl=gsap.timeline({{paused:true}});
tl.fromTo('#region',{{opacity:{0 if region != 'band' else 1}}},{{opacity:1,duration:0.3,ease:'power2.out'}},0);
tl.fromTo('#card',{{opacity:0,x:-24,scale:0.97}},{{opacity:1,x:0,scale:1,duration:0.4,ease:'power3.out'}},0.05);
{js}
tl.to('#card',{{opacity:0,x:-16,duration:0.28,ease:'power2.in'}},{exit_t:.3f});
tl.to('#region',{{opacity:{0 if region != 'band' else 1},duration:0.25,ease:'power2.in'}},{exit_t + 0.05:.3f});
window.__timelines["main"]=tl;
}});
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--still", type=float)
    ap.add_argument("--mp4", action="store_true", help="opak mp4 (full/panel sahne için de webm önerilir)")
    a = ap.parse_args()
    spec = json.loads(a.spec.read_text())
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "fonts").mkdir(exist_ok=True)
    for f in (PKG / "fonts").glob("*.ttf"):
        shutil.copy(f, out / "fonts" / f.name)
    shutil.copy(PKG / "templates" / "gsap.min.js", out / "gsap.min.js")
    (out / "index.html").write_text(build(spec), encoding="utf-8")
    (out / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    print(f"yazıldı: {out/'index.html'}")
    if a.no_render and a.still is None:
        return
    lint = subprocess.run(["npx", "--yes", "hyperframes", "lint"], cwd=out, capture_output=True, text=True)
    if lint.returncode:
        print(lint.stdout[-1500:], lint.stderr[-800:])
    if a.still is not None:
        r = subprocess.run(["npx", "--yes", "hyperframes", "snapshot", ".", "--at", str(a.still), "--no-end", "--keep", "-o", "stills"],
                           cwd=out, capture_output=True, text=True)
        print(r.stdout[-600:], r.stderr[-600:])
        return
    fmt = "mp4" if a.mp4 else "webm"
    r = subprocess.run(["npx", "--yes", "hyperframes", "render", ".", "--format", fmt, "-o", f"render.{fmt}"],
                       cwd=out, capture_output=True, text=True)
    print(r.stdout[-800:], r.stderr[-800:])
    print(f"render: {out/('render.' + fmt)}" if (out / f"render.{fmt}").exists() else "RENDER BAŞARISIZ")


if __name__ == "__main__":
    main()
