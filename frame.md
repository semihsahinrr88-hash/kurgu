---
version: 1
name: BorsaSemih — Frame
description: >
  BorsaSemih Reels/YouTube görsel sistemi. Koyu lacivert zemin, beyaz metin, TEK vurgu rengi turuncu
  (#FF8C1E, altyazıyla aynı). Yeşil/kırmızı sadece artış/düşüş için. Montserrat (başlık, rakam, gövde)
  + JetBrains Mono (küçük gri üst etiket / kaynak satırı). Tamamı büyük harf YOK — her yerde cümle düzeni.
unit: 1080×1920 (Reels, birincil) · 1920×1080 (YouTube)
principle: atomlar kutsal · yerleşim serbest · rakamlar konuşmadan ve kaynaktan gelir

colors:
  bg: "#08142D"            # zemin, split/pip paneli, B-roll dolgusu (ffmpeg: 0x08142D)
  card: "rgba(8,20,45,0.92)"
  card-solid: "#0E1F42"
  stripe: "#2F80FF"        # kartın sol şeridi, pip çerçevesi
  accent: "#FF8C1E"        # TEK vurgu — kelime, aktif madde, yeni değer
  up: "#2BD47D"            # sadece artış
  down: "#FF5A5F"          # sadece düşüş
  text: "#FFFFFF"
  text-muted: "#A9B4C8"
  text-dim: "#6B7894"
  hairline: "rgba(255,255,255,0.10)"
  grid: "rgba(47,128,255,0.07)"
  scrim: "rgba(0,0,0,0.55)" # büyük soru başlığında konuşanın üstüne perde

radii:
  card: "28px"
  chip: "999px"
  bar: "10px"

typography:
  # Fontlar paketle gelir: fonts/Montserrat-*.ttf, fonts/JetBrainsMono-*.ttf (@font-face ile yükle, web fontuna güvenme)
  # JetBrains Mono'da ₺ yok → mono satırda "TL" yaz; ₺ gerekiyorsa Montserrat kullan.
  eyebrow:  { fontFamily: "JetBrains Mono", px: 30, weight: 500, tracking: "0.02em", color: "text-muted" }   # "BIST · günün özeti", "Kaynak: KAP, 06.10.2026"
  body:     { fontFamily: "Montserrat", px: 44, weight: 600, lineHeight: 1.25, color: "text" }
  label:    { fontFamily: "Montserrat", px: 40, weight: 700, color: "text-muted" }
  h2:       { fontFamily: "Montserrat", px: 72, weight: 800, lineHeight: 1.08, tracking: "-0.01em", color: "text" }
  h1:       { fontFamily: "Montserrat", px: 104, weight: 900, lineHeight: 1.02, tracking: "-0.02em", color: "text" }
  stat:     { fontFamily: "Montserrat", px: 168, weight: 900, lineHeight: 0.95, tracking: "-0.03em", color: "text" }
  stat-unit:{ fontFamily: "Montserrat", px: 64, weight: 700, color: "text-muted" }
  caption:  { fontFamily: "Montserrat ExtraBold", px: 74, weight: 800, color: "text", highlight: "accent" } # make_ass.py üretir
  # YouTube (1920×1080): tüm px değerlerini 0.62 ile çarp; caption 54.

spacing:
  safe-side: "60px"                   # kenarlardan en az
  reels-overlay-band: "y 115–540 px"  # konuşan kafanın üstündeki boş duvar (önce kare alıp başı kontrol et)
  reels-split-panel: "y 0–864 px"     # layout=split üst panel
  reels-ui-dead: "alt %25-30 + sağ 140px şerit" # Instagram arayüzü — önemli bir şey koyma
  caption-band: "MarginV 520 / 1920"
  youtube-dead: "alt %10 + sağ alt köşe (abone/son ekran)"

components:
  card:
    backgroundColor: "{colors.card}"
    rounded: "{radii.card}"
    borderLeft: "14px solid {colors.stripe}"
    padding: "44px 52px"
    shadow: "0 24px 60px rgba(0,0,0,0.35)"
    description: "Her bilgi kartının temeli. Üstte eyebrow, ortada değer/başlık, altta kaynak satırı."
  stat-card:
    typography: "{typography.eyebrow} → {typography.stat} + {typography.stat-unit} → {typography.eyebrow} (kaynak)"
    description: "Count-up sayaç. İniş karesi konuşmadaki rakam kelimesine denk gelir."
  change-chip:
    rounded: "{radii.chip}"
    description: "▲ %3,2 yeşil / ▼ %1,4 kırmızı; zemin renkli %18 opak, metin tam renk."
  compare:
    description: "Eski değer {colors.text-dim} + üstü çizili → yeni değer {colors.accent}; altta fark etiketi."
  list:
    description: "Maddeler konuşmayla tek tek gelir; anlatılan madde accent, geçmişler text-muted; ✓ işaret stripe rengi."
  timeline:
    description: "Yatay 4px hairline + yıl noktaları; anlatılan yıl accent ile yanar."
  ticker:
    description: "Kod (h2) + fiyat (body) + change-chip. Tek satır, kart içinde."
  question-title:
    description: "Konuşan + {colors.scrim}; ortada h1 cümle, tek kelime accent. Soru/tez cümleleri için."
  terminal:
    description: "card-solid zemin, JetBrains Mono, '$ cat not.txt' satırları yazılarak gelir. Kapanış dersi için."
  cta-end:
    description: "Son 2-2.5 sn donmuş kare + kart: soru (h2) + 'Yorumlara yaz ↓' (accent)."
  atmosphere:
    description: "Panel/tam ekran sahnelerde 60px aralıklı {colors.grid} ızgara + köşede küçük eyebrow. Kartın üstünde değil, zeminde."
---

# BorsaSemih — Frame

## Ruh

Borsa anlatan, sakin ama net bir yatırımcı. Görsel dil **"tasarlanmış ama gösterişsiz"**: koyu lacivert,
beyaz, tek turuncu. Hedef referans: Tasarımcı Dayı — "Bu Videoyu Ben Editlemedim!" seviyesi; tek tasarım
sistemi, sürekli değişen yerleşim, kaynaklı bilgi sahneleri.

## Değişmezler (Do)

- Her sahne bu dosyadaki renk/font/kart ailesinden gelir. Yeni renk icat etme.
- Turuncu = dikkat. Bir karede en fazla 1-2 turuncu öğe (altyazı dahil).
- Yeşil/kırmızı yalnızca yön bildirir (artış/düşüş), dekor değildir.
- Rakam büyük ve kalın, birim küçük ve gri. Her rakamlı kartta kaynak satırı (eyebrow).
- Varsayımsal rakamda kartta "Örnek hesaplama" yazar.
- Cümle düzeni: "Faiz kararı ne getirir?" — tamamı büyük harf yok, harf aralığı açma yok.
- Türkçe karakter kontrolü: İ, ı, ş, ğ, ç, ö, ü her render karesinde doğru görünmeli.

## Yasaklar (Don't)

- Glitch, parlama, sallantı, RGB kayması, konfeti — marka dışı.
- Yüzü kapatan kart. Instagram UI bölgesine metin.
- Kaynaksız rakam. Telifli görsel/müzik.
- İki bağımsız bilgiyi aynı anda göstermek.

## Hareket dili

- Giriş 0.30–0.45 sn, `power3.out`; metin soldan 24px kayarak + opaklık. Çıkış daha hızlı (0.25–0.35 sn, `power2.in`).
- Count-up 0.6–0.9 sn, `power2.out`; son rakam iniş karesinde sabitlenir, kart en az 1 sn durur.
- Liste maddeleri arası en az 0.35 sn; madde girişi konuşmadaki kelimeyle eş zamanlı.
- Lineer easing yok. Sahne değişince ses ve altyazı kesilmez; sadece görsel katman değişir.

## Ses dili

- Efekt yalnızca ekrandaki bir olaya bağlı: kart girişi → `pop`/`click-soft`, geçiş → `whoosh-short`,
  sonuç cümlesi → `impact-bass-1` veya `chime` (biri), liste maddesi → `tick`, rakam inişi → `ping`.
- Efektler konuşmanın altında kalır (-14…-22 dB). Glitch sesleri marka dışı.
