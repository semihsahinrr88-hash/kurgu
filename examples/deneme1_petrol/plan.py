"""deneme1 — 6 hata (petrol tema + fx denemesi). EDL'i böl, layout/zoom ata, sahne + fx spec'lerini yaz."""
import json, copy
from pathlib import Path

E = Path(__file__).resolve().parent
src = E / "edl.auto.json"
if not src.exists():
    src.write_text((E / "edl.json").read_text())
edl = json.load(open(src))
W = {c: [x for x in json.load(open(E / f"transcripts/{c}.json"))["words"] if x.get("type") == "word"] for c in edl["sources"]}


def wsrc(src_, word, n=0, after=0.0):
    hits = [w for w in W[src_] if w["text"].lower().strip(".,").startswith(word.lower()) and w["start"] >= after]
    return hits[n]["start"]


SPLITS = {9: wsrc("IMG_6594", "kira") - 0.06,
          11: wsrc("IMG_6596", "eğer", 1) - 0.06,
          12: wsrc("IMG_6603", "eski") - 0.06}
R = []
for i, r in enumerate(edl["ranges"]):
    if i in SPLITS:
        a, b = copy.deepcopy(r), copy.deepcopy(r)
        a["end"] = b["start"] = round(SPLITS[i], 3)
        R += [a, b]
    else:
        R.append(r)


def words_in(r):
    return [w for w in W[r["source"]] if w["start"] >= r["start"] - 0.02 and w["start"] < r["end"]]


for r in R:
    r["quote"] = " ".join(w["text"] for w in words_in(r))

L = [
 dict(beat="HOOK", push=0.05, reason="hook: sert açılış + 6 madde ön izleme kartları"),
 dict(beat="M1", layout="split", reason="1. madde — iyi gün/kötü gün: yönetim prop"),
 dict(beat="VURGU", zoom=1.12, reason="'ben oradan uzaklaşıyorum' — kişisel tavır, punch-in"),
 dict(beat="TALK", push=0.04, reason="öneri cümlesi, sakin push"),
 dict(beat="M2", layout="split", reason="2. madde — para piyasalar arasında akar: para akışı prop"),
 dict(beat="M2", layout="split", reason="mevduat/altın/borsa/döviz sayılırken düğümler yanar"),
 dict(beat="VURGU", zoom=1.12, reason="'borsaya ne zaman gireceğini' — yüze dönüş"),
 dict(beat="M3", zoom=1.12, reason="3. madde — 'tek hisseye yığma' iddia cümlesi"),
 dict(beat="M3", layout="split", reason="%10 kuralı: kasa prop (dolar, batar, %90 yerinde)"),
 dict(beat="M4", push=0.04, reason="4. madde girişi 'kısa vadede lazım olacak para', yüz"),
 dict(beat="M4", layout="split", reason="kira/taksit/borç sayılırken: yasak para prop"),
 dict(beat="VURGU", zoom=1.12, reason="'duygularını yönetemezsin' — ciddi uyarı, sadece zoom"),
 dict(beat="M5", layout="split", reason="5. madde — giriş/çıkış/miktar/süre: işlem planı formu"),
 dict(beat="SONUÇ", zoom=1.15, reason="zirve: 'planlamazsan kaybetmeyi planlamış olursun' → fx kinetic_captions"),
 dict(beat="M6", zoom=1.12, reason="6. madde girişi 'her piyasada olmaya çalışma'"),
 dict(beat="M6", layout="split", reason="iki tavşan → 'bir piyasa seç': odak prop"),
 dict(beat="M6", layout="split", reason="seçim devam (odak)"),
 dict(beat="ÖZET", push=0.04, reason="'bunları bilmek kolay' — 6 maddenin hepsi → fx checklist (özet)"),
 dict(beat="CTA", zoom=1.12, reason="'kaydetmeyi unutma' → donmuş kare + fx save_cta"),
]
assert len(L) == len(R), (len(L), len(R))
for r, l in zip(R, L):
    r.update(l)

t = 0.0
for r in R:
    r["_out"] = t
    t += r["end"] - r["start"]
TOTAL = t


def wt(i, text, n=0):
    r = R[i]
    hits = [w for w in words_in(r) if w["text"].lower().strip(".,").startswith(text.lower())]
    return round(hits[n]["start"] - r["start"] + r["_out"], 3)


def span(i, j):
    return R[i]["_out"], R[j]["_out"] + R[j]["end"] - R[j]["start"]


# ---- HyperFrames sahneleri (şeffaf webm)
S, OV = {}, []
def scene(name, spec, s0, s1):
    spec = dict(spec, format="reels", theme="petrol", duration=round(s1 - s0, 3))
    S[name] = spec
    OV.append({"file": f"animations/{name}/render.webm", "start_in_output": round(s0, 3), "duration": round(s1 - s0, 3), "range_start": s0})

scene("hook_proof", {"type": "proof", "region": "band",
      "items": [{"n": "1", "text": "Yönetim"}, {"n": "2", "text": "Para akışı"}, {"n": "3", "text": "Tek hisse"},
                {"n": "4", "text": "Kira parası"}, {"n": "5", "text": "Plan"}, {"n": "6", "text": "Odak"}],
      "at": [0.15, 0.3, 0.45, 0.6, 0.75, 0.9]}, 0.15, R[0]["end"] - R[0]["start"] - 0.1)

s0, s1 = span(1, 1)
scene("m1_yonetim", {"type": "prop", "prop": "yonetim", "region": "panel", "step": "1/6", "title": "Kötü günde *nerede*?",
      "at": [round(wt(1, x) - s0, 2) for x in ["iyi", "sürekli", "konuşup", "sessizleşiyorsa"]]}, s0, s1)
s0, s1 = span(4, 5)
scene("m2_akis", {"type": "prop", "prop": "para_akisi", "region": "panel", "step": "2/6", "title": "Para nereye *akıyor*?",
      "at": [round(wt(5, x) - s0, 2) for x in ["mevduat", "altın", "borsa", "döviz"]],
      "land": round(wt(5, "birinden") - s0, 2), "target": "Borsa"}, s0, s1)
s0, s1 = span(8, 8)
scene("m3_kasa", {"type": "prop", "prop": "kasa", "region": "panel", "step": "3/6", "title": "Tek hisseye *en fazla %10*",
      "at": [round(wt(8, "%10") - s0, 2), round(wt(8, "yok") - s0, 2)]}, s0, s1)
s0, s1 = span(10, 10)
scene("m4_yasak", {"type": "prop", "prop": "yasak_para", "region": "panel", "step": "4/6", "title": "Bu para borsaya *girmez*",
      "at": [round(max(0.6, wt(10, "parası", 0) - s0), 2), round(wt(10, "parası", 1) - s0, 2), round(wt(10, "parası", 2) - s0, 2)]}, s0, s1)
s0, s1 = span(12, 12)
scene("m5_plan", {"type": "prop", "prop": "plan_formu", "region": "panel", "step": "5/6", "title": "Girmeden önce *yaz*",
      "at": [round(wt(12, x) - s0, 2) for x in ["gireceğini", "çıkacağını", "koyacağını", "taşıyacağını"]],
      "stamp": "Yazılı plan", "stamp_at": round(wt(12, "yaz") - s0, 2)}, s0, s1)
s0, s1 = span(15, 16)
scene("m6_odak", {"type": "prop", "prop": "odak", "region": "panel", "step": "6/6", "title": "Bir piyasa *seç*",
      "pick": "Borsa", "land": round(wt(15, "seç") - s0, 2)}, s0, s1)

# ---- fx (videonun kendisini işleyen efektler, opak mp4) — Reels'te en fazla 3
FX = []
def fxe(name, spec, i, j=None):
    s0, s1 = span(i, j if j is not None else i)
    FX.append({"name": name, "range": [i, j if j is not None else i], "spec": dict(spec, theme="petrol"),
               "edl_start": round(s0, 3), "edl_dur": round(s1 - s0, 3)})

# zirve cümle: kelime kelime (her kelimenin söylendiği an)
i = 13; s0 = R[i]["_out"]
k = lambda w, n=0: round(wt(i, w, n) - s0, 2)
fxe("fx_zirve", {"fx": "kinetic_captions", "y": 330, "lines": [
    [{"w": "Eğer", "s": "m", "at": k("eğer")}, {"w": " bunu", "s": "m", "at": k("bunu")}],
    [{"w": "planlamazsan", "s": "a", "at": k("planlamazsan")}],
    [{"w": "kaybetmeyi", "s": "s", "at": k("kaybetmeyi")}],
    [{"w": "planlamış olursun", "s": "b", "at": k("planlamış")}]]}, 13)
# özet: 'bunları' → 6 madde hızla işaretlenir (başın üstündeki bantta, yüzü kapatmadan)
i = 17; s0 = R[i]["_out"]
fxe("fx_ozet", {"fx": "checklist", "title": "İşlem açmadan önce", "compact": True, "y": 70, "w": 640,
    "items": ["Yönetim kötü günde ne yapıyor?", "Para nereye akıyor?", "Tek hisseye en fazla %10",
              "Kira, taksit, borç parası değil", "Giriş, çıkış, süre yazılı", "Tek piyasa"],
    "at": [round(0.45 + 0.42 * n, 2) for n in range(6)]}, 17)

FREEZE = 2.4
CTA = {"fx": "save_cta", "theme": "petrol", "text": "Bu videoyu *kaydet*", "sub": "İşlem açmadan önce bir daha bak", "y": 560}

for name, spec in S.items():
    d = E / "specs"; d.mkdir(exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1))
for f in FX:
    (E / "specs" / f"{f['name']}.json").write_text(json.dumps(f["spec"], ensure_ascii=False, indent=1))
(E / "specs" / "fx_cta.json").write_text(json.dumps(CTA, ensure_ascii=False, indent=1))

# ---- ses efektleri (EDL çıktı zamanı; compose offs'a çevirir)
SFX = [{"t": 0.0, "type": "impact-bass-2"}]
for i in (1, 4, 8, 10, 12, 15):
    SFX.append({"t": round(max(0, R[i]["_out"] - 0.15), 3), "type": "whoosh-short"})
SFX.append({"t": wt(13, "planlamazsan"), "type": "impact-bass-1"})
for n in range(6):
    SFX.append({"t": round(R[17]["_out"] + 0.45 + 0.42 * n, 3), "type": "tick", "db": -6})
json.dump(SFX, open(E / "sfx_cues.json", "w"), indent=1)

meta = {"ranges_out": [r["_out"] for r in R], "fx": FX, "freeze": FREEZE, "total": TOTAL,
        "scenes": [{**o, "range": next(k for k, r in enumerate(R) if abs(r["_out"] - o["range_start"]) < 1e-6) if o["range_start"] > 0.2 else 0} for o in OV]}
json.dump(meta, open(E / "plan_meta.json", "w"), ensure_ascii=False, indent=1)
for r in R:
    r.pop("_out", None)
edl["ranges"] = R
edl["overlays"] = [{k: v for k, v in o.items() if k != "range_start"} for o in OV]
edl["total_duration_s"] = round(TOTAL, 2)
json.dump(edl, open(E / "edl.json", "w"), ensure_ascii=False, indent=1)
base = dict(edl, overlays=[])
json.dump(base, open(E / "edl_base.json", "w"), ensure_ascii=False, indent=1)
print(f"{len(R)} range, {TOTAL:.1f} sn (+{FREEZE} donmuş CTA), {len(OV)} sahne, {len(FX)}+1 fx, {len(SFX)} ses efekti")
