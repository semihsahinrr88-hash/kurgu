"""Yama 3: EDL range'lerine "zoom" (sabit punch-in, örn 1.12), "push" (segment boyunca yavaş itme, örn 0.05)
ve "layout" (talk | split | pip) ekler. Dikey (Reels) ve yatay (YouTube) kaynağı otomatik ayırır.
split: Reels'te konuşan alt %55 / üst %45 panel; YouTube'da konuşan sağ %50 / sol %50 panel (krem #EFE8DB; eski lacivert için STUDIO_THEME=lacivert; HyperFrames
paneli overlay olarak oraya oturur). pip: konuşan sağ altta küçük çerçevede, ekranın geri kalanı içerik alanı."""
s = open('render.py').read()
if '"layout"' in s:
    print("yama 3 zaten var"); raise SystemExit
# panel zemini temadan (scene.py ile aynı): krem varsayılan
PANEL_HDR = 'import os as _os\n_PANEL = "0x08142D" if _os.environ.get("STUDIO_THEME") == "lacivert" else "0xEFE8DB"\n_FRAME = "0x2F80FF" if _os.environ.get("STUDIO_THEME") == "lacivert" else "0xFF8C1E"\n'
if "from __future__ import annotations\n" in s:
    s = s.replace("from __future__ import annotations\n", "from __future__ import annotations\n" + PANEL_HDR, 1)
else:
    s = PANEL_HDR + s
s = s.replace("    rate: str | None = None,\n) -> None:\n    \"\"\"Extract a cut range",
              "    rate: str | None = None,\n    zoom: float = 1.0,\n    push: float = 0.0,\n    layout: str = \"talk\",\n) -> None:\n    \"\"\"Extract a cut range", 1)
s = s.replace("    vf_parts.append(scale)\n    if grade_filter:",
"""    vf_parts.append(scale)
    if portrait:
        W, H = (720, 1280) if draft else (1080, 1920)
        cy = 0.35   # dikeyde yüz üstte
    else:
        W, H = (1280, 720) if draft else (1920, 1080)
        cy = 0.40   # yatay (YouTube) kadrajda yüz ortaya yakın
    if zoom > 1.0 or push > 0.0:
        # punch-in / push-in; yüz üstte olduğu için dikey merkez %35'te (kafa kesilmez)
        if push > 0.0:
            zexpr = f"({zoom:.4f}+{push:.4f}*t/{max(duration,0.1):.3f})"
            vf_parts.append(f"scale=w='trunc({W}*{zexpr}/2)*2':h='trunc({H}*{zexpr}/2)*2':eval=frame:flags=bicubic")
        else:
            vf_parts.append(f"scale=trunc({W}*{zoom:.4f}/2)*2:trunc({H}*{zoom:.4f}/2)*2:flags=bicubic")
        vf_parts.append(f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{cy}")
    if layout == "split" and portrait:      # Reels: konuşan altta %55, üst panel boş
        ph = int(H * 0.55) // 2 * 2
        vf_parts.append(f"crop={W}:{ph}:0:({H}-{ph})*0.25,pad={W}:{H}:0:{H-ph}:color={_PANEL}")
    elif layout == "split":                 # YouTube: konuşan sağda %50, sol panel boş
        pw = int(W * 0.5) // 2 * 2
        vf_parts.append(f"crop={pw}:{H}:({W}-{pw})/2:0,pad={W}:{H}:{W-pw}:0:color={_PANEL}")
    elif layout == "pip":
        k = 0.45 if portrait else 0.32
        pw, phh = int(W * k) // 2 * 2, int(H * k) // 2 * 2
        x = W - pw - int(W * 0.05)
        y = H - phh - int(H * (0.22 if portrait else 0.08))
        vf_parts.append(f"scale={pw}:{phh},pad={W}:{H}:{x}:{y}:color={_PANEL},"
                        f"drawbox=x={x-4}:y={y-4}:w={pw+8}:h={phh+8}:color={_FRAME}@0.9:t=4")
    if grade_filter:""", 1)
s = s.replace("extract_segment(src_path, start, duration, seg_filter, out_path, preview=preview, draft=draft, rate=out_rate)",
              "extract_segment(src_path, start, duration, seg_filter, out_path, preview=preview, draft=draft, rate=out_rate,\n                        zoom=float(r.get(\"zoom\", 1.0)), push=float(r.get(\"push\", 0.0)), layout=r.get(\"layout\", \"talk\"))", 1)
open('render.py', 'w').write(s)
print("yama 3 (zoom/push/layout) uygulandı")
