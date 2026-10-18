"""6 hata — kurgu planı: EDL'i böl, layout/zoom ata, sahne spec'lerini yaz, overlay'leri ekle."""
import json, copy
from pathlib import Path

E = Path(__file__).resolve().parent
edl = json.load(open(E / "edl.auto.json")) if (E / "edl.auto.json").exists() else json.load(open(E / "edl.json"))
json.dump(edl, open(E / "edl.auto.json", "w"), ensure_ascii=False, indent=1)
W = {c: [x for x in json.load(open(E / f"transcripts/{c}.json"))["words"] if x.get("type") == "word"] for c in edl["sources"]}

# 1) bölmeler (kaynak saniyesi, kelime aralığında)
SPLITS = {("IMG_6594", 9): 4.06, ("IMG_6596", 11): 9.30, ("IMG_6603", 12): 3.30}
R = []
for i, r in enumerate(edl["ranges"]):
    k = (r["source"], i)
    if k in SPLITS:
        a, b = copy.deepcopy(r), copy.deepcopy(r)
        a["end"] = b["start"] = SPLITS[k]
        R += [a, b]
    else:
        R.append(r)

def words_in(r):
    return [w for w in W[r["source"]] if w["start"] >= r["start"] - 0.02 and w["start"] < r["end"]]

for r in R:
    r["quote"] = " ".join(w["text"] for w in words_in(r))

# 2) layout / zoom / neden  (index -> ayar)
L = [
 dict(beat="HOOK", push=0.05, reason="hook: sert açılış + 6 madde ön izlemesi"),
 dict(beat="M1", layout="split", reason="1. madde — iyi gün / kötü gün fikri: yönetim prop"),
 dict(beat="VURGU", zoom=1.12, reason="'ben oradan uzaklaşıyorum' — kişisel kural, punch-in"),
 dict(beat="TALK", push=0.04, reason="öneri cümlesi, sakin push"),
 dict(beat="M2", layout="split", reason="2. madde — para piyasalar arasında akar: para akışı prop"),
 dict(beat="M2", layout="split", reason="mevduat/altın/borsa/döviz söylenirken düğümler yanar"),
 dict(beat="VURGU", zoom=1.12, reason="'borsaya ne zaman gireceğini' — para borsaya toplanır, sonra yüz"),
 dict(beat="M3", zoom=1.12, reason="3. madde — 'tek hisseye yığma' iddia cümlesi"),
 dict(beat="M3", layout="split", reason="%10 kuralı: kasa prop (dolar, batar, %90 yerinde)"),
 dict(beat="M4", push=0.04, reason="4. madde girişi, yüz"),
 dict(beat="M4", layout="split", reason="kira/taksit/borç sayılırken: yasak para prop"),
 dict(beat="VURGU", zoom=1.12, reason="'duygularını yönetemezsin' — ciddi uyarı, sadece zoom"),
 dict(beat="M5", layout="split", reason="5. madde — giriş/çıkış/miktar/süre: işlem planı formu"),
 dict(beat="SONUÇ", zoom=1.15, reason="'planlamazsan kaybetmeyi planlamış olursun' — zirve cümle"),
 dict(beat="M6", zoom=1.12, reason="6. madde girişi 'her piyasada olmaya çalışma'"),
 dict(beat="M6", layout="split", reason="iki tavşan → 'bir piyasa seç': odak prop"),
 dict(beat="M6", layout="split", reason="seçim devam (odak)"),
 dict(beat="KAPANIŞ", push=0.04, reason="kapanış dersi"),
 dict(beat="CTA", zoom=1.12, reason="'kaydetmeyi unutma' → donmuş kare + CTA"),
]
assert len(L) == len(R), (len(L), len(R))
for r, l in zip(R, L):
    r.update(l)

# çıktı zamanları
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

# 3) sahneler
S, OV = {}, []
def scene(name, spec, s0, s1):
    spec = dict(spec, format="reels", duration=round(s1 - s0, 3))
    S[name] = spec
    OV.append({"file": f"animations/{name}/render.webm", "start_in_output": round(s0, 3), "duration": round(s1 - s0, 3)})

h0, h1 = 0.15, 3.25
scene("hook_proof", {"type": "proof", "region": "band",
      "items": [{"n": "1", "text": "Yönetim"}, {"n": "2", "text": "Para akışı"}, {"n": "3", "text": "Tek hisse"},
                {"n": "4", "text": "Kira parası"}, {"n": "5", "text": "Plan"}, {"n": "6", "text": "Odak"}],
      "at": [0.15, 0.3, 0.45, 0.6, 0.75, 0.9]}, h0, h1)

s0, s1 = span(1, 1)
scene("m1_yonetim", {"type": "prop", "prop": "yonetim", "region": "panel", "step": "1/6", "title": "Kötü günde *nerede*?",
      "at": [round(wt(1, "iyi") - s0, 2), round(wt(1, "sürekli") - s0, 2), round(wt(1, "konuşup") - s0, 2), round(wt(1, "sessizleşiyorsa") - s0, 2)]}, s0, s1)

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

for name, spec in S.items():
    d = E / "specs"; d.mkdir(exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1))

# 4) efektler (her biri ekrandaki bir olaya bağlı)
SFX = [{"t": 0.0, "type": "impact-bass-2"}]
for i in (1, 4, 8, 10, 12, 15):
    SFX.append({"t": round(max(0, R[i]["_out"] - 0.15), 3), "type": "whoosh-short"})
SFX.append({"t": wt(13, "planlamazsan"), "type": "impact-bass-1"})
json.dump(SFX, open(E / "sfx_cues.json", "w"), indent=1)

for r in R:
    r.pop("_out", None)
edl["ranges"] = R
edl["overlays"] = OV
edl["total_duration_s"] = round(TOTAL, 2)
json.dump(edl, open(E / "edl.json", "w"), ensure_ascii=False, indent=1)
print(f"{len(R)} range, {TOTAL:.1f} sn, {len(OV)} sahne, {len(SFX)} efekt")
for name, spec in S.items():
    print(name, {k: v for k, v in spec.items() if k in ("at", "land", "duration", "stamp_at")})
