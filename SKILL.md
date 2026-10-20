---
name: "video-studyo"
description: "Ham video (dikey Reels veya yatay YouTube) verildiğinde BorsaSemih stüdyosuyla (github.com/semihsahinrr88-hash/kurgu) kesim, Türkçe kelime hizalama, baş üstü bandı kartları, altyazı, 22 video efekti, lisanslı ses efektleri, Instagram çıkışı ve kapakla final.mp4 üretme. Ücretsiz."
---

# Video Stüdyo v2 (BorsaSemih)

Kod, fontlar, ses kütüphanesi ve tasarım dosyası **github.com/semihsahinrr88-hash/kurgu** reposunda. Bu dosya sadece kurallar ve akış. Temel: video-use (kesim/render) + HyperFrames (motion graphics) + kendi BorsaSemih katmanımız. Transkripsiyon ücretsiz, lokal (faster-whisper + wav2vec2 Türkçe hizalama).

İki format: **Reels** (1080×1920, 30-90 sn) ve **YouTube** (1920×1080, uzun). Konuşan kafa, borsa içeriği. Her şeyin üstünde: **anlamsız edit yok** (§1 anlamlılık kuralı). Görsel kimlik: `~/studio/frame.md` — renk, font, kart, hareket ve ses dili oradan gelir, yeni renk/stil icat etme.

## 0. Kurulum (her yeni oturumda bir kez, ~3-5 dk)
```bash
CA=/root/.ccr/ca-bundle.crt; [ -f $CA ] && export SSL_CERT_FILE=$CA REQUESTS_CA_BUNDLE=$CA NODE_EXTRA_CA_CERTS=$CA
test -d ~/kurgu || git clone --depth 1 https://github.com/semihsahinrr88-hash/kurgu ~/kurgu
bash ~/kurgu/setup.sh
```
Repo bu oturumda yoksa önce `add_repo(owner="semihsahinrr88-hash", repo="kurgu", access="push")`. Kurulum: video-use helper'ları + 3 render.py yaması (normal harf altyazı, webm alfa, zoom/push/layout) + BorsaSemih scriptleri + fontlar + `sfx/` + HyperFrames Chrome ve skill'leri (`talking-head-recut`, `embedded-captions`, `hyperframes-audio`, `media-use`). Hepsi `~/studio/` altında. Yeni bir script/sahne/efekt geliştirirsen repoya commit + push et (bir sonraki oturum da kullanabilsin).

**Ham videoyu al:** bağlı klasörden `device_list_dir` → `device_stage_files` (işleme bulutta). Klasör bağlı değilse `device_request_folder_access` iste ya da sohbete eklemesini söyle. Proje: `~/studio/<proje>/`, tüm çıktılar `<proje>/edit/`. Bitince final'i `SendUserFile` ile gönder + `device_commit_files` ile kaynağın yanına `<ad>_final.mp4` yaz.

## 1. Format modu ve denge (ÖNCE BUNU BELİRLE)
`ffprobe` ile yön + süre → planın ilk satırı. Bütün kararlar bu moda göre.

| | **Reels** (dikey, ≤90 sn) | **YouTube** (yatay, uzun) |
|---|---|---|
| Amaç | ilk 1-3 sn'de durdur, sonuna kadar tut | anlat, öğret, güven ver |
| Görsel değişim | ~2-4 sn | ~6-12 sn |
| Layout dağılımı | çoğunluk talk + baş üstü bandı kartları, birkaç split/prop, 1-3 tam ekran | ~%60 talk, ~%30 split/pip, ~%10 tam ekran |
| `split` | konuşan altta %55, üst panel | konuşan sağda %50, sol panel |
| Zoom/punch-in | 30-60 sn'de 4-8 | dakikada ≤2-3, çoğunlukla yavaş `push` |
| Ses efekti | 30-60 sn'de 4-8 | dakikada ≤2-3, sadece geçişlerde |
| Altyazı | `make_ass.py` (sola hizalı, ≤5 kelime) | `make_ass.py --youtube` (alt orta, 54 pt, ≤7 kelime) |
| Hook | ilk 3 sn sert açılış (`impact-bass-2` + push) | ilk 15-30 sn vaat + kısa ön izleme |
| Bölüm | yok | her ana konu başında 1.5-2 sn `chapter` sahnesi |
| Kapanış | 2-2.5 sn donmuş kare + `cta` | son 10-20 sn özet (`terminal`/`quote`) + abone çağrısı |

**Anlamlılık kuralı (taviz yok):** Efekt ancak konuşmada onu gerektiren somut bir şey varsa girer: rakam, liste, karşılaştırma, tarih, grafik, soru, konu değişimi. Plan tablosunda her efektin yanına "neden" (hangi kelime/cümle). Nedeni yazılamayan efekt plana girmez. Şüphedeysen koyma. Duygusal/kişisel/ciddi anlarda (kayıp, risk uyarısı, samimi itiraf) efekt ve ses efekti yok — temiz kesim + altyazı. Aynı sahne tipi arka arkaya ikiden fazla yok. Yoğunluk sınırları üst sınırdır, hedef değil.

## 2. Süreç (Sor → Onayla → Uygula → Kendini denetle → Kaydet)
1. **Envanter + transkript.** `ffprobe`. `python3 transcribe_local.py <video>` (large-v3-turbo; Türkçe filler'ları prompt + "voiced gap" ile yakalar, sessizlik halüsinasyonlarını atar). Metin için ikinci geçiş gerekirse `--model large-v3 --edit-dir <proje>/edit_v3`, iki metni karşılaştır.
2. **Kelime hizalama (her zaman):** `python3 align_words.py <proje>/edit <video>` — metni korur, zamanları wav2vec2 Türkçe modeliyle sese hizalar (ilk çalıştırmada ~1.2 GB model iner). Rapordaki "ortalama kayma" ve "hizalanamadı" sayısına bak; hizalanamayan çoksa yedek: `python3 retime_words.py <proje>/edit <video>`. Hizalanmadan altyazı sesin gerisinde kalır ve kesilen boşluğa düşen kelimeler kaybolur. Sonra `python3 pack_transcripts.py --edit-dir <proje>/edit` → `takes_packed.md` (ana okuma görünümü) + 1 adet `timeline_view.py`.
3. **Taslak kesim:** çok parçalı çekimde `python3 auto_cut_multi.py <proje>/edit klip1 klip2 ... --keep-maybe --max-gap 0.3` (sırayı içerikle doğrula; telefon IMG numarası genelde çekim sırasıdır) → tek `edl.json` + `timeline.txt` (çıktı zamanı + kelime zamanları, plan tablosunu buradan yaz). Tek klipte `python3 auto_cut.py <proje>/edit <video>` → filler, 0.35 sn üstü sessizlik ve tekrar çekim (aynı 3 kelimeyle yeniden başlayan cümle → öncekini at) çıkmış `edl.json` + rapor. TASLAK: raporu ve `takes_packed.md`'yi oku, düzelt. Senaryolu çekimde `--keep-maybe` ("aslında gerçek tam tersi" gibi anlamlı kullanımlar kalmalı). Akıcı konuşmada duraklamayı enerjiyle bul: `ffmpeg -i <video> -af silencedetect=n=-38dB:d=0.22 -f null -` → ≥0.38 sn sessizliklerin ortasını kes (0.12 / 0.15 sn nefes payı). Tempo: Reels `--max-gap 0.3`, sakin anlatım 0.5.
4. **Planı sun, onay bekle (ZORUNLU).** İlk satır format modu. 4-6 cümle: ham → hedef süre, ne kesiliyor, hook, renk. Sonra **katman planı tablosu**: `saniye | cümle | layout | katman (zoom/push, sahne tipi, B-roll, efekt) | neden`. Bilgi sahnelerindeki rakamların kaynağını ve B-roll görsellerini burada iste. Onay yoksa render yok; onay gelince sorusuz ilerle. **Storyboard (görsel onay):** sahneleri `scene.py --no-render` ile yaz, EDL'i hazırla, `python3 storyboard.py <proje>/edit` → `edit/storyboard.jpg` (her range bir kare: layout/zoom + o anki sahne + altyazı + numara/neden). Tabloyla birlikte gönder; Semih numara üzerinden düzeltir ("3'ü tam ekran yap"). Render'a storyboard onayından sonra geç.
5. **Uygula:** EDL'e layout/zoom/push yaz (§8); range'i bölerken kesim noktasının kelime içine düşmediğini kontrol et. **Zaman kayması:** render.py her segmenti kaynak fps'ine göre yukarı yuvarlar (20 segmentte ~0.2 sn). Base render'dan sonra `python3 frame_offsets.py <proje>/edit --fps <kaynak fps>` → `offs.json` (overlay, sfx, gömülü kelime zamanları buradan) + `edl_adj.json` (make_ass bununla: geçici olarak edl.json yerine koy). `end` değeri base.mp4 süresiyle aynı olmalı. (Base: `render.py edit/edl_base.json -o edit/base.mp4 --no-subtitles --no-loudnorm` → render.py ara dosyayı zaten `edit/base.mp4` yazar; sondaki kendine-kopya adımı `exit 234` basar, zararsız — süreyi ffprobe ile doğrula.) Sahneleri `scene.py` ile üret (§4), efekt cue'ları `edit/sfx_cues.json` (§5). Önizleme: `python3 render.py edit/edl.json -o edit/preview.mp4 --preview --no-subtitles --no-loudnorm` + altyazı (§6 adım 2-3).
6. **Kendini denetle (göstermeden önce):** her kesim noktasında `timeline_view.py edit/preview.mp4 <t-1.5> <t+1.5>` → görüntü sıçraması, dalga formunda pop, overlay'in altyazıyı kapatması, yanlış kareden başlama. İlk/son 2 sn + her sahne/zoom anında bir kare: altyazı görünüyor mu, turuncu kelimeler doğru mu, yüz kesilmiş mi, kart yüzü kapatıyor mu, Türkçe karakterler (İ ı ş ğ) doğru mu. Ses: `ffmpeg -i out.mp4 -af ebur128=peak=true -f null -` (hedef -14 LUFS, ≤ -1 dBTP). Sesi dinleyemezsin, ölçümü raporla. En fazla 3 düzeltme turu; kalan sorunları söyle.
7. **Final + teslim + hafıza:** onaydan sonra `--preview`'sız render → §6 → `python3 export.py reels edit/final.mp4 edit/<ad>_reels.mp4` (YouTube: `export.py youtube`) + kapak `python3 export.py cover edit/final.mp4 edit/kapak.jpg --t <hook karesi> --title "Kısa *vurgulu* başlık"` (YouTube: `--youtube`). Teslim: sohbete gönderim sınırı **30 MiB** — 75 sn tam kalite ~95 MB tutar. `python3 export.py teslim edit/final.mp4 edit/<ad>_ig.mp4` (iki geçişli, ~28 MiB; Instagram zaten yeniden sıkıştırdığı için fark edilmez) gönder; tam kaliteyi bilgisayar bağlıysa `device_commit_files` ile kaynağın yanına yaz. `edit/project.md`'ye oturum özeti (Strateji / Kararlar / Gerekçe / Bekleyenler); yeni oturumda varsa önce onu oku.

## 3. Katman haritası — hangi an, hangi efekt
Her cümleyi etiketle, planda saniye saniye listele. Sahne tipleri `scene.py` adlarıyla:

| Konuşmada ne var? | Katman |
|---|---|
| Hook / ilk cümle | ilk segment `push: 0.05` + `impact-bass-2`; varsa en güçlü cümle başa (onayla) |
| Vurgulu kelime, iddia, "ama", "asıl mesele" | o segmente `zoom: 1.12`; sonraki 1.0'a döner (jump cut gizlenir) |
| Uzun sakin açıklama (>4 sn tek segment) | `push: 0.04-0.06` |
| Rakam, yüzde, fiyat, oran | `stat` (count-up, iniş = rakam kelimesi) + `ping` · eski→yeni ise `compare` + `pop` |
| Hisse kodu, endeks, emtia | `ticker` (band) veya grafik varsa tam ekran B-roll |
| Liste ("3 sebep", "birincisi…") | `split` + `list` (her madde `at` = söylendiği an) + her maddede `tick` |
| Fikir anlatılan madde/cümle (kural, örnek, "kira parasıyla girme", "%10'dan fazla koymam") | `split` + `prop` — söyleneni tekrar yazan liste/kart yerine fikri GÖSTEREN animasyon (önce `props.py`'deki hazırları dene; yoksa yeni prop yaz + push) |
| Maddeli videonun hook'u | `proof` kartları (gerçek ekran görüntüsü varsa onlar, yoksa madde ön izlemesi) |
| Soru / tez cümlesi | `question` (konuşan kararır, ortada büyük cümle, tek kelime turuncu) |
| Tarih, süreç, tarihçe | `timeline` (panel veya full) |
| Tablo, çok rakamlı karşılaştırma | `pip` + B-roll (tablo görseli) |
| Konu değişimi | `whoosh-short` + zoom seviyesi değişir; YouTube'da `chapter` |
| Grafik/haber/ekran görüntüsü | B-roll (§4b) + `whoosh` |
| Alıntı / "şu sözü seviyorum" | `quote` |
| Sonuç / çarpıcı cümle | `zoom: 1.15` + `impact-bass-1` YA DA `chime`; Reels başına en fazla 1 kez **gömülü kelime** (§4c) |
| Kapanış / CTA | donmuş kare + `cta` + `pop` · "kaydet" çağrısıysa `fx save_cta` |
| **— Video efektleri (`fx.py`, §4d) —** | |
| Kendini tanıtma ("ben Semih", ilk video, konuk) | `fx lower_third` |
| Birden çok hisse/piyasa sayılıyor (THYAO, altın, dolar…) | `fx orbit` (kartlar etrafında döner) |
| Grafik/ekran görüntüsü üstüne anlatım ("grafiğe bakın") | `fx green_screen` (image = TradingView ss) veya `fx frame_break` |
| Haber/gelişme ("faiz kararı çıktı", "KAP'a düştü") | `fx headline_wall` (gerçek manşetler, kaynaklı) |
| Getiri/büyüme rakamı, yıllar içinde artış | `fx chart_grow` (sayaç + sütunlar; `stat`ın güçlü hali) |
| Kontrol listesi ("almadan önce 4 şeye bakarım") | `fx checklist` (video üstünde; panelde `list`) |
| Tek kavram/başlık ("Nakit akışı", "Bileşik getiri") | `fx glass_type` |
| Manifesto/zirve cümlesi, her kelime önemli | `fx kinetic_captions` (o aralıkta altyazı kapalı) |
| Ciddi/dramatik hikâye (2008, büyük kayıp) | `fx cinemascope` (ses efekti yok) |
| "Şuraya bakın" — ekranda tek noktaya dikkat | `fx spotlight` |
| Kanıt/çok kaynak ("yüzlerce mesaj geldi") | `fx screen_wall` (gerçek ekran görüntüleri) |
| Ekrandaki bir şeyi gösterip açıklama | `fx doodle_boil` (konuşurken) / `fx freeze_frame` (duraklamada) |
| Yapay zekâ/araç/otomasyon anlatımı | `fx ui_world` |
| İki taraf ("bir yanda… öbür yanda") / üç seçenek | `fx mirror` / `fx triptych` |
| Seri/bölüm tanıtımı ("Borsa 101 · 3. bölüm") | `fx cover_story` |
| Sert geçiş, konu değişimi | `fx whip_pan` · ekrana "dalarak" geçiş: `fx zoom_through` |
| Açılış planı / mekân reveal | `fx pull_back_reveal` (yakından genişe) |
| Yazılı hook (ilk 3 sn, görsel kanıt yoksa) | `fx hook_stack` |
| **— Baş üstü bandı (`fx_band.py`, §4e) —** | |
| Yıl/tarih ("2008 krizinde", "2021'de faiz…") | `fx year` (rakam sayarak gelir + çizgi + etiket) |
| Maddeli video (6 hata, 5 hisse, 3 sinyal) | `fx locked_list` — hook'ta kilitli liste (açık döngü), her madde başında o maddenin kilidi açılır |
| Sektör / birden çok hisse | `fx stock_card` (sektör başlığı + hisse kodu kartları + rozet) |
| Eski↔yeni, ortalama↔bu yıl, enflasyon↔getiri | `fx bars` (gri → petrol çubuk + "4 kat" rozeti) |
| Videonun zirve karşılaştırması (mevduat vs borsa…) | `fx versus` — TAM EKRAN, videoda en fazla 1 |
| Haber / KAP / resmi açıklama iddiası | `fx source_card` — Claude kaynağı bulur, metin BİREBİR; bulamazsa kart yok |

**Yoğunluk (Reels; YouTube için §1):** 30-60 sn'de 4-8 punch-in, iki ardışık segment aynı zoomda olmasın. 4-8 ses efekti, her biri bir görsel olaya bağlı. Aynı anda tek kart/B-roll, ≥1.5 sn ekranda, ardışık iki kart arası ≥2 sn. İlk 0.5 sn'ye kart yok. Altyazı her zaman okunur (tam ekran sahnede de en üstte).

**Split'te altyazı (otomatik):** Reels split'inde konuşan alt %55'te olduğu için normal altyazı ağza düşer. `make_ass.py` split range'lerinde altyazıyı panelin alt şeridine (y≈650-850, %86 boy) taşır; `scene.py` panel sahnelerinde alt 220 px'i bu şerit için boş bırakır. Elle bir şey yapma, sadece QA'da kontrol et.

**Varsayılan yerleşim (20.10.2026, Semih onayladı): BAŞ ÜSTÜ BANDI.** Bilgi kartları konuşanın başının üstündeki boş duvarda (Reels y≈115-560) durur, konuşan tam ekranda kalır (referans: oguzhan.guzelkaralar, `docs/referans-oguzhan-2040.md`). `split` + `prop` artık sadece fikri büyük göstermek gereken birkaç anda; tam ekran (`versus`, B-roll) videoda 1-3 kez.

**Layout (EDL range alanı, Yama 3):** `talk` (varsayılan, tam ekran) · `split` (Reels: konuşan alt %55, panel üst 864 px; YouTube: konuşan sağ %50) · `pip` (konuşan sağ altta küçük çerçeve). Layout değişimi kesim noktasında olur; cümle ortasında gerekirse range'i kelime sınırında böl. İlk 3 sn her zaman `talk` + hook altyazısı.

## 4. Sahne kütüphanesi (`scene.py`) — önce bunu kullan
Her bilgi sahnesi tek bir JSON → şeffaf `.webm`. Tasarım frame.md'den gelir; sıfırdan HTML yazma. Kütüphanede olmayan bir sahne gerekiyorsa önce `hyperframes-registry` (`npx hyperframes catalog --query "..."`) ve `talking-head-recut` fikirlerine bak, sonra frame.md atomlarıyla yaz ve **scene.py'ye yeni tip olarak ekleyip repoya push et**.
```bash
python3 scene.py spec.json -o edit/animations/slot_1 --still 1.4   # önce tek kare QA (~10 sn)
python3 scene.py spec.json -o edit/animations/slot_1               # render.webm (~30 sn)
```
Tipler ve alanlar (ortak: `format` reels|youtube, `region` band|panel|full, `duration`, `land`, `eyebrow`, `source`, `step` ("3/6" numaralı madde rozeti, maddeli videolarda her panelde); metinde `*kelime*` = turuncu):
- `stat`: value, decimals, prefix ("%"), suffix, unit, label, bar (0-1), direction (up|down)
- `compare`: old, new, note — `ticker`: code, price, change ("+3,2") — `question`: text
- `list`: title, items, at[] — `timeline`: title, points[{label,text}], at[] — `chapter`: index, title — `quote`: text, who — `cta`: text, sub — `terminal`: lines[], at[] (yazılarak gelen "$" satırları, kapanış dersi)
- `prop` (fikir animasyonu, `props.py`): bir cümlenin FİKRİNİ küçük animasyonla anlatır. Alanlar: prop, title (`*kelime*`), step ("3/6" → solda turuncu numara), at[], land. Hazır prop'lar:
  `kasa` (sermaye 10 dilim, %10'luk dilim batar, %90 yerinde — at:[doldur, bat]) · `yasak_para` (Kira/Taksit/Borç kartları borsa kutusundan geri itilir) · `plan_formu` (giriş/çıkış/miktar/süre satırları dolar + `stamp`) · `para_akisi` (Mevduat/Altın/Borsa/Döviz arasında para akar, land'de `target`'a toplanır) · `risk` (kadran ibresi `value` 0-1) · `odak` (piyasa çipleri, land'de `pick` seçilir) · `yonetim` (iyi gün balonları / kötü gün sessizlik).
  Yeni bir fikir sık tekrar ediyorsa props.py'ye yeni prop olarak ekle + push. Prop da anlamlılık kuralına tabi: konuşmada o fikir yoksa girmez.
- `proof` (kanıtlı hook): items `[{"img":"grafik.png"}]` (gerçek ekran görüntüsü — tercih) veya `[{"n":"1","text":"Yönetim"}]` (maddeli videoda ön izleme); kartlar ilk 1-1.5 sn'de yelpaze gibi dizilir. `region: band`. İlk 3 sn kuralı: hook'ta tek izinli kart budur, 0.15 sn'den başlayabilir.
- Hızlı QA: `python3 peek.py <sahne_klasörü> --at 1.2 2.5 --bg kare.jpg [--split]` (hyperframes render'ı beklemeden kare) · `--mp4 x.mp4` kısa önizleme.
- Kütüphanede henüz yok, gerekince yaz ve ekle: nokta ızgarası ("binlerce yatırımcı" → yüzlerce nokta, bir kısmı turuncu), mini çizgi grafik, kapanış künyesi ("Montaj: Claude · Son kontrol: Semih", Semih isterse).
- `region`: `band` = başın üstündeki boş duvar (önce kare alıp başın nerede başladığına bak), `panel` = `split` layout'un paneli (EDL'de aynı range `layout: "split"` olmalı), `full` = tam ekran (opak zemin; altyazı üstte kalır).
- **Payoff senkronu:** `land` = anahtar kelimenin çıktı zamanı − overlay başlangıcı. Liste/timeline `at[]` aynı mantık.
- EDL: `"overlays": [{"file": "animations/slot_1/render.webm", "start_in_output": 3.4, "duration": 3.5}]`. Birden fazla sahne → paralel alt ajanlar (her biri kendi slot klasörü).
- Rakam kaynaklı olmalı (`source`). Varsayımsal rakamda `source: "Örnek hesaplama"` ve kullanıcıya söyle. Rakam biçimi Türkçe: 47,5 · 1.000 · %3,2.

### 4b. B-roll
Kaynak: Semih'in verdiği ekran görüntüleri (TradingView, haber, tablo) veya `scene.py`. İnternetten telifli görsel/video indirme; yoksa planda "öneri" yaz ve iste. Görseli klibe çevir:
```bash
ffmpeg -y -loop 1 -t 2.5 -i grafik.png -vf "scale=1080:1920:force_original_aspect_ratio=decrease:flags=bicubic,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0xEFE8DB,scale=w='trunc(1080*(1+0.05*t/2.5)/2)*2':h='trunc(1920*(1+0.05*t/2.5)/2)*2':eval=frame,crop=1080:1920,format=yuv420p" -r 30 -an edit/broll/b1.mp4
```
Opak overlay olarak ekle; 1.5-3 sn; ilgili cümleyle başlar.

### 4c. Gömülü kelime (konuşanın arkasında) — Reels'te en fazla 1, YouTube'da bölüm başına en fazla 1
En çarpıcı tek kelime/rakam ("%47,5", "Kriz") konuşanın ARKASINDA dev yazı. Pahalı görünür ama ucuzlar — sadece zirve anında. Tarif (reels1'de doğrulandı — saç kenarı temiz, ~2 dk / 3 sn segment CPU'da):
1. Segmenti base kurgudan **offs.json zamanıyla** çıkar (EDL zamanıyla değil — 0.1 sn kayarsa dudak senkronu bozulur): `ffmpeg -ss <offs[i]> -t <offs[i+1]-offs[i]> -i edit/base.mp4 -vf fps=30 -c:v libx264 -crf 12 -an seg.mp4`
2. Konuşanı ayır: `npx hyperframes remove-background seg.mp4 -o subj.webm --quality best`
3. Kelime PNG (PIL): Montserrat Black ~420 px, turuncu #FF8C1E, hafif gölge, yatay ortalı. **Dikey konum:** kelimenin alt üçte biri başın arkasına girmeli (kelime başın tamamen üstünde kalırsa "arkada" hissi olmaz). 1.15 zoom'lu dikey kadrajda y≈360 doğru çıktı; önce bir kare alıp başın üst sınırına göre ayarla.
4. Birleştir: `[seg][kelime: fade in 0.45/0.3, fade out sonda 0.3, alpha]overlay[a];[a][subj]overlay` → `embed.mp4`; final birleştirmede o aralığa opak overlay. Efekt sesi (`impact-bass-1`) kelimenin belirdiği karede.
5. QA: kelime okunuyor mu, saç/omuz kenarında titreme var mı. Kenar kötüyse bu efekti bırak — sade daha iyidir. Gelişmiş ihtiyaçta `embedded-captions` skill'ine bak (çekim tek kişilik ve tek planlı olmalı).

### 4d. Video efekt kütüphanesi (`fx.py`) — 22 efekt + 2 kalıp
Referans: "22 video efekti — Claude ile, sadece kod" Reels'i (20.10.2026, Semih "hepsini ekle, gerekli yerlerde kullanalım" dedi). `scene.py` şeffaf KART üretir; `fx.py` videonun KENDİSİNİ işler (maske, zoom, kağıt kolaj, el çizimi…) ve aralığın yerine geçen **opak mp4** döndürür. Hepsi ücretsiz, CPU (numpy + OpenCV + PIL).
```bash
python3 fx.py list                                                                      # efektler + alanlar
python3 fx.py spec.json --base edit/base.mp4 --at <offs zamanı> --dur 3.2 -o edit/fx/slot_3.mp4
python3 fx.py spec.json --in edit/fx/slot_3.src.mp4 --still 1.4 -o edit/fx/slot_3.png    # tek kare QA (~5 sn)
```
Spec: `{"fx": "<ad>", "theme": "petrol|krem", ...}` — koordinatlar çıktı pikseli (Reels 1080×1920), metinde `*kelime*` = vurgu, büyük harf yok.
- **Maskeli** (konuşanı ayırır, `remove-background` ~35 sn CPU / 1 sn video, `<seg>.subj.mov` cache): `orbit`, `frame_break`, `green_screen`, `paper_cut`, `cover_story` (başlık konuşanın arkasında), `doodle_boil`. Sadece o segmenti maskele, bütün videoyu değil.
- **Kart/arayüz** (maskesiz): `ui_world` (sohbet + terminal + çipler), `checklist`, `headline_wall`, `chart_grow`, `lower_third`, `kinetic_captions`, `glass_type`, `screen_wall`, `hook_stack`, `save_cta`.
- **Kamera/kurgu**: `mirror`, `triptych`, `spotlight`, `cinemascope`, `pull_back_reveal` (`reverse: true` → push-in), `freeze_frame` (video donar, ses akar — konuşmanın durduğu yerde ya da kapanışta), geçişler `zoom_through` ve `whip_pan` (`cut` = segment içindeki kesim anı; segmenti kesimin ±0.4 sn'sini kapsayacak şekilde al).
- Birleştirme (§6.3): fx mp4'ü base'in o aralığına opak overlay — `[k:v]setpts=PTS-STARTPTS+T/TB` + `overlay=eof_action=pass:enable='between(t,T,T+d)'` (webm değil, `-c:v libvpx-vp9` gerekmez). Zaman `offs.json`'dan (gömülü kelimedeki gibi; EDL zamanı dudak senkronunu kaydırır).
- **Sınır flaşı:** `--base` kesimi `at + 1/60` sn'den başlar (yoksa önceki range'in son karesi — ör. split paneli — 1 kare görünür). Teslimden önce tek kare sıçrama taraması yap (üst köşe parlaklığı, komşu karelerden >40 fark).
- Koordinat ayarı: önce `--still` ile kare al (baş/ekran nerede?), `center`/`window`/`box`/`shapes` değerlerini ona göre yaz; doodle/freeze etiketleri `label_xy`.
- **Doz:** Reels'te konuşmaya bağlı 5-8 fx (20.10 v2 kabul edildi; bant kartları bu sayıya dahil değil), aynı fx bir videoda bir kez (geçişler `whip_pan`/`zoom_through` hariç); YouTube'da bölüm başına ≤2. Anlamlılık kuralı aynen: konuşmada o şey yoksa fx yok. Duygusal/ciddi anda sadece `cinemascope` olabilir.
- **Marka notu:** `paper_cut` ve `green_screen bg: gun_batimi` eğlenceli/kişisel içerik içindir (BorsaSemih finans videosunda nadiren). `kinetic_captions`/`hook_stack` aralığında normal altyazıyı `captions.ass`'tan o aralık için çıkar (iki yazı üst üste binmesin).
- Fontlar: Instrument Serif Italic (kapak/manşet/kinetic) ve Caveat (el yazısı notlar) — ikisi de OFL, `fonts/`. Videonun üstünde vurgu `accent_video` (petrol: #35C2D2), kartta `accent`.
- Demo: `examples/fx_demo/` (24 efektin spec'leri). Yeni efekt gerekirse `fx.py`'ye `@fx("ad", "açıklama")` sınıfı ekle + push.

### 4e. Baş üstü bandı bileşenleri (`fx_band.py`, fx.py'ye kayıtlı) — 20.10.2026
Hepsi `fx.py spec.json --base edit/base.mp4 --at T --dur D -o edit/fx/x.mp4` ile (opak segment, §4d birleştirme). Koyu petrol kart (#101E22), vurgu `accent_video` #35C2D2, beyaz metin; `y` ile dikey konum (önce `--still` ile başın üst sınırına bak, kart başa değmesin).
- `year`: to, from, label, y, size — takvim yaprağı yerine (Semih "1B — sadece yıl"ı seçti; takvim kaba bulundu).
- `locked_list`: title, eyebrow, items, opened (açık başlayan sayısı), unlock (bu segmentte açılacak index), at — maddeli videoda hook'ta (opened 0, unlock null) + her madde başında 1.5-2.5 sn.
- `stock_card`: eyebrow, title, tickers [{code, change | note}], badge, at[], badge_at — logo YOK (telif), hisse kodu kartı.
- `bars`: eyebrow, rows [{label, value, frac, muted}], at[], badge.
- `versus` (tam ekran): eyebrow, left/right {label, num, value?, icon:'bina'}, unit, stamp, at[], stamp_at.
- `source_card`: site, eyebrow (tür · tarih), text (kaynaktan BİREBİR), highlight (altı çizilen ifade), circle (daireye alınan), url (planda Semih'e yaz), at. **Uydurma kaynak yok:** WebSearch/WebFetch ile bul, metni aynen al; bulunamazsa kart koyma ve söyle. Birebir ekran görüntüsü istenirse Claude in Chrome ile çekilir (Semih'in Chrome'u açıksa).
- Rakamlar konuşmadan + kaynaktan; demo/varsayımsal değer kullanılıyorsa Semih'e söyle.
- Demo: `examples/band_demo/` (6 bileşen spec'i).

### 4f. Altyazı seçeneği B — kelime kutulu (`kcap.py`)
`python3 kcap.py <edit_dir> -o edit/kcap.mov [--skip a-b,...]` → ortalı, beyaz kalın, söylenen kelime yarı saydam kutuda; alfa katmanı (qtrle mov), final birleştirmede `ass` yerine EN SON `overlay` edilir. split range'lerde panel şeridine koyu mürekkep. Boy 56 px (68 fazla büyük bulundu, 20.10; `KCAP_SIZE` ile değişir) — A altyazısıyla aynı görünür boy. `kinetic_captions`/`hook_stack` aralıklarını `--skip` ile çıkar. Semih A (make_ass, sola hizalı) ile B arasında henüz seçim yapmadı (20.10.2026) — seçene kadar planda sor.

## 5. Ses
**Ses temizliği varsayılan KAPALI.** Semih yankıyı çekimde engelliyor; sesi orijinal bırak, plana koyma. Sadece açıkça isterse DeepFilterNet tarifi (`docs/ses-temizligi.md` repoda).

**Ses efektleri:** `sfx/` lisanslı kütüphane (Pixabay Content License, ticari kullanım serbest — `sfx/CREDITS.md`). `python3 sfx.py list` ile gör. Olay → efekt: kart girişi `pop`/`click-soft` (iniş karesinde), geçiş `whoosh-short` (kesimden 0.15 sn önce), B-roll `whoosh` (0.1 sn önce), rakam inişi `ping`, liste maddesi `tick`, sonuç `impact-bass-1` ya da `chime`, terminal `typing`, hook `impact-bass-2`. Glitch sesleri marka dışı. `edit/sfx_cues.json`: `[{"t": 3.2, "type": "whoosh-short"}]` (t çıktı zamanı; `"db"` opsiyonel). Miksaj loudnorm'dan önce: `python3 sfx.py mix in.mp4 edit/sfx_cues.json out.mp4`.

**Müzik:** Kendi kütüphanemiz yok, telifli müzik indirme. Varsayılan müziksiz teslim; Semih Instagram'da trend sesi düşük ekler (planda hatırlat). Telifsiz parça verirse ducking:
```bash
ffmpeg -y -i in.mp4 -stream_loop -1 -i muzik.mp3 -filter_complex "[1:a]volume=-18dB,aresample=48000[m];[m][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[md];[0:a][md]amix=inputs=2:normalize=0:duration=first[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 256k out.mp4
```
**Loudness:** iki geçişli loudnorm (`render.apply_loudnorm_two_pass`) → -14 LUFS, ≤ -1 dBTP. Ölçüm -15 altında kalırsa önce `acompressor=threshold=-26dB:ratio=3:attack=5:release=90:makeup=8`.

**Renk — "ten F" (Semih onaylı, 15.10.2026; önceki bronz fazla turuncuydu):** `auto_cut_multi.py --grade bronz` EDL'e şunu yazar: `BRONZ` sabiti + `,lut3d=file=<studio>/luts/ten_F.cube`. LUT = eski bronz görünüm %72 + doğal görünüm %28 (Semih iki görünüm arasında %72'yi seçti). Asıl turunculuk kaynağı: iPhone HLG HDR → render.py'deki `hable desat=0` tonemap ten doygunluğunu ~2 katına çıkarıyor; LUT bunu dengeliyor. Ölçüm (IMG_6603 2. sn yüz): doygunluk ham 0.22 · eski 0.46 · F 0.40; patlak piksel %0.
Grade layout'tan ÖNCE uygulanır (patch_zoom): split/pip paneli tema rengini birebir korur. Yeni ışık/kamerada önce/sonra karesini Semih'e göster; "daha doğal/daha sıcak" isterse LUT karışım oranını değiştir (doğal zincir: `zscale=tin=bt709:t=bt709:pin=bt2020:p=bt709:min=bt2020nc:m=bt709` + `eq=contrast=1.08:saturation=1.05:gamma=0.96`).
**Split kadraj:** Reels split'te konuşan alt %55; kırpma penceresi `SPLIT_Y=0.55` (0.25 yüzü çok alta itiyordu — Semih: "beni o kadar alta kaydırma").

## 6. Final geçiş (render.py dışı)
**Hız notu:** iPhone 60 fps HEVC kaynak 2 CPU'lu bulutta yavaş çözülür (72 sn video ≈ 22 dk base render). Bu yüzden base'i (kesim + layout + zoom + grade, overlay'siz) BİR kez render et, sahne/gömülü kelime/CTA/altyazıyı tek ffmpeg birleştirme geçişinde ekle (repoda `examples/alti_hata/compose.py` örneği: her overlay `setpts=PTS-STARTPTS+T/TB` + `enable=between`, en sonda `ass`). Düzeltme gerekirse sadece birleştirme geçişi tekrarlanır, base değil. **Önizleme tuzağı:** şeffaf webm'de `-ss` girişten önce verilirse kare boş gelir; tek kare kontrolünde `-c:v libvpx-vp9 -i x.webm -ss T` (çıktı tarafı seek) kullan.
1. `python3 render.py edit/edl.json -o edit/stage1.mp4 --no-subtitles --no-loudnorm` (kesim + layout/zoom/push + grade + sahne/B-roll overlay'leri)
2. Altyazı: önce `master.srt` üret ve metni düzelt (`python3 -c "import sys,json;sys.path.insert(0,'.');import render;from pathlib import Path;E=Path('<proje>/edit');render.build_master_srt(json.load(open(E/'edl.json')),E,E/'master.srt')"`) → hisse kodları, rakam formatı ("1000" → "1.000"), yanlış kelimeler. Düzeltmeleri `edit/transcripts/<ad>.json` kelimelerine de işle, sonra `python3 make_ass.py <proje>/edit --hl "<konuya özel kökler>"` (YouTube `--youtube`). Kare başına 1-2 turuncu kelime; fazlaysa `--hl`'i daralt. Satır sonu `.`/`,` silinir, `?` kalır.
3. Tek ffmpeg: `[0:v]tpad=stop_mode=clone:stop_duration=2.25` → `cta` webm'i (`-c:v libvpx-vp9 -i`, `setpts=PTS-STARTPTS+T/TB`, `overlay=enable='between(t,T,T+dur)'`) → `ass=edit/captions.ass:fontsdir=/root/studio/fonts` **EN SON**; ses `apad=pad_dur=2.25`; libx264 crf 18 → `stage2.mp4`.
4. Efektler `sfx.py mix` → `stage3.mp4` (müzik verildiyse ducking).
5. Loudnorm → `final.mp4` → `export.py` (§2.7) + QA kareleri + ebur128. Kapak altyazısız kareden yapılır (base.mp4 + hook sahnesinin peek karesi → kısa mp4 → `export.py cover`); başlıkta turuncu her kelime ayrı yıldızlanır (`*6* *hatası*`).

## 7. Sert kurallar (taviz yok)
1. Altyazı filtre zincirinde EN SONA. 2. Segment başına extract → kayıpsız concat (render.py). 3. Her kesimde 30 ms ses fade. 4. Overlay'ler `setpts=PTS-STARTPTS+T/TB`. 5. Altyazı zamanları çıktı zaman çizelgesine göre. 6. Kelimenin ortasından asla kesme. 7. Kesim kenarına 30-200 ms pay (varsayılan 50 ms önce / 80 ms sonra). 8. Sadece kelime seviyesinde transkript. 9. Transkripti cache'le. 10. Birden fazla sahne → paralel alt ajanlar. 11. Onaysız kesim yok. 12. Tüm çıktılar `<proje>/edit/` içinde.

**Türkçe Whisper tuzakları:** filler yutma (script prompt + voiced gap ile yakalar; "voiced gap" görürsen `timeline_view` ile bak) · sessizlikte uydurma ("Altyazı M.K.", "İzlediğiniz için teşekkürler" — son cümleyi kontrol et) · hisse kodları/terimler (THYAO, BIST, VİOP) yanlış yazılabilir → `master.srt`'de düzelt.

**Güvenli alanlar:** Reels — alt %25-30 ve sağ ~140 px şerit Instagram UI; overlay bandı y≈115-540 (başın üstü; kart yüzü kapatmasın); kenarlardan ≥60 px; altyazı MarginV 520. YouTube — alt %10 ve sağ alt köşe boş.

## 8. EDL formatı
```json
{"version": 1, "sources": {"klip": "/abs/klip.mp4"},
 "ranges": [{"source": "klip", "start": 0.0, "end": 3.5, "beat": "HOOK", "quote": "...", "reason": "...", "push": 0.05},
            {"source": "klip", "start": 4.1, "end": 6.0, "beat": "VURGU", "quote": "...", "reason": "...", "zoom": 1.12},
            {"source": "klip", "start": 6.3, "end": 11.0, "beat": "LİSTE", "quote": "...", "reason": "...", "layout": "split"}],
 "grade": "<bronz, parlamasız — §5>", "overlays": [], "total_duration_s": 12.9}
```
Kaynak adı = dosyanın uzantısız adı. `zoom` 1.08-1.18, `push` 0.03-0.06; ikisi birlikte olur. Dikeyde kırpma %35'ten (yüz üstte); kafa kesiliyorsa zoom'u düşür.

## Semih'in kalıcı tercihleri
- **Onaylı standart (18.10.2026, "6 hata" yeniden kurgusu — "bu şekilde devam edelim"):** hook'ta `proof` kartları · her madde = `split` + `prop` fikir animasyonu (dev turuncu numara + başlık), ardından yüz + zoom/push (split'ler arka arkaya gelmez) · zirve cümlede zoom 1.15 + `impact-bass-1` · donmuş kare + `cta` · render öncesi `storyboard.jpg` onayı. Referans proje: `examples/alti_hata/` (plan.py + compose.py).
- Tema: **krem** (15.10.2026) — split/pip paneli ve kartlar krem #EFE8DB, koyu metin, dev turuncu madde numarası, panel videoya degradeyle erir; split altyazısı panelde koyu. Lacivert artık kullanılmıyor (gerekirse `STUDIO_THEME=lacivert`). **Petrol (19.10 seçildi, 20.10 'deneme1' ile test edilip beğenildi → yeni standart):** `STUDIO_THEME=petrol` — panel #E9ECEC, metin #14262B, vurgu #0F7C8C (videoda #35C2D2), soluk #8FA0A3; altyazı vurgusu açık petrol; bant kartları koyu petrol #101E22.
- Altyazı: beyaz Montserrat ExtraBold, normal harf, turuncu anahtar kelimeler, sola hizalı, ~2 satır, alt üçte bir; imza satırı ve "YENİ BÖLÜM" bandı yok.
- Tamamı büyük harf yok (altyazı + kartlar + kapak). Ses orijinal — yankı temizliği yok (açıkça istemedikçe). Ten F grade, doğal sıcak (§5). Kartlar yüzü kapatmaz.
- Format modu her editte önce; efekt dozu moda göre; her efektin konuşmada nedeni var — anlamsız edit yok.
- Uygun an varsa animasyonlu motion graphics (sayaç, mini grafik, ticker/% etiketi, sıralı liste, fikir animasyonu) kullan; statik karta kaçma.
- (20.10.2026) "22 video efekti" referansındaki tüm efektler stüdyoda (`fx.py`); uygun an geldiğinde kullan, efekt göstermek için efekt koyma.
- (20.10.2026) "6 hata" petrol denemesi v2 beğenildi ("güzel, tamamdır"): Reels'te konuşmaya bağlı ~8 fx dozu kabul (`examples/deneme1_petrol/`). Semih ilk sürümde (3 fx) "yeni yeteneklerden çok azını kullanmışsın" dedi — anlamlı yer varsa çekinme, ama vitrin yapma.
- (20.10.2026) Baş üstü bandı varsayılan; yıl için takvim değil `year`; kaynak kartlarını Claude kendisi bulur (gerçek kaynak, birebir metin).
- Hedef seviye: Tasarımcı Dayı "Bu Videoyu Ben Editlemedim!" — tek tasarım sistemi (frame.md), sürekli değişen layout, kaynaklı bilgi sahneleri.
- Planı onaylamadan render yok; onaylarsa sorusuz ilerle. Her şey ücretsiz ve bulutta.

## Anti-pattern'ler
Altyazıyı overlay'den önce basmak · lineer easing · doğrulanmamış web fontu (paket fontlarını kullan) · konuşmayla bağı olmayan efekt · glitch/parlama/sallantı · telifli müzik veya görsel · kaynaksız rakam · kesimde sert ses · onaysız edit · transkripti tekrar almak · her sahneyi sıfırdan HTML yazmak (önce `scene.py`) · söyleneni panelde aynen tekrar yazmak (fikri göster: `prop`) · fx vitrini yapmak (konuşmada karşılığı olmayan fx, aynı fx iki kez) · bütün videoyu maskelemek (sadece fx segmenti) · kaynak kartına uydurma/özetlenmiş metin koymak (birebir alıntı + url) · şirket logosu kullanmak (hisse kodu yaz) · gömülü kelimeyi birden fazla kullanmak · videonun türünü varsaymak — önce bak, sonra sor, en son edit et.