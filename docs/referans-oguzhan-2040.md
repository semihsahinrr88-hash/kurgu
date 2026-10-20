# Referans analiz — "OpenAI susturmak istedi, 2040'ı açıkladı" (oguzhan.guzelkaralar, 20.10.2026)

Semih: "Bu adamın tarzı neredeyse benim tarzımla birebir aynı." 147 sn dikey Reels, tek çekim konuşan kafa, ~400 kelime (2,7 kelime/sn — çok sıkı tempo).
Etkileşim (ekranda): 13B beğeni · 459 yorum · 403 paylaşım · **27,8B kaydetme** → içerik "kaydedilecek referans" olarak kurgulanmış.

## 1. Anlatım yapısı (saniye)
| sn | blok | teknik |
|---|---|---|
| 0–10 | **Hook**: "OpenAI bir çalışanına 17 milyon dolar teklif etti. Tek şartla: konuşma. Adam reddetti ve 2040'a kadar olacakları yazdı." | rakam + gizem + çatışma; ilk cümlede para |
| 10–28 | **Otorite**: Time 100, "2021'de ChatGPT'yi tarif etti", "bu yaz kaçtı", "her şey erkenden gerçekleşti" | kanıt zinciri, her iddiaya ekran görüntüsü |
| 28–33 | **Vaat + açık döngü**: "Paranın akacağı 5 sektörü tek tek anlatıyorum" | kilitli/bulanık 5'li liste (sona kadar izlet) |
| 33–94 | **Zaman çizelgesi**: 2025 → 2026 → 2027 → 2028 → 2031 → 2032 → 2033 → 2036 → 2040 | her yıl = takvim yaprağı geçişi; her yılda 1 çarpıcı rakam |
| 94–105 | **İtiraz kırma**: "Diyeceksin ki çok uzak… daha 2026'dayız, uzaya çıktılar bile" | itirazı izleyicinin ağzından söyle, güncel kanıtla çürüt |
| 105–139 | **Payoff**: 5 sektör (çip, enerji, robot, siber güvenlik, uzay) — her biri 1 cümle gerekçe + 3 şirket logosu | kilitli liste tek tek açılır |
| 139–147 | **Kapanış**: "Bu sektör ve şirketleri kaydet" + "yatırım tavsiyesi değil" + soru ("hangisini seçerdin?") + "fikirlerini yorumlara yaz" + "takip etmeyi unutma" | kaydet + yorum + takip, üçü birden |

Dil: kısa cümle, şimdiki zaman ("2032, Amerikan ekonomisi yılda %50 büyüyor"), izleyiciye "sen" ("ve yanlış duymadın: %50"), karşılaştırma ile ölçek ("dünyanın en büyük ordusunun 2 katı"), soru köprüleri ("Peki 2031'de ne oluyor?", "Peki bu büyüme kimin cebine giriyor?", "Peki kim yönetiyor?").

## 2. Kurgu dili
- **Tek çekim, görünür jump cut yok.** Duraklamalar alınmış (5'ten az ≥0,25 sn boşluk). Zoom/punch-in neredeyse yok — hareketi grafikler sağlıyor.
- **Grafik bandı = başın üstü (üst ~%35).** Split panel YOK; kartlar kitaplığın üstünde yüzer. Konuşan hep tam ekran kalır.
- **Tam ekran** sadece 4-5 kez: AI üretimi B-roll (veri merkezi, robot fabrikası, dünya/uydu) + üstünde makale kartı; büyük karşılaştırma grafiği; açık-döngü listesi.
- Görsel değişim ~2-4 sn'de bir; 11. saniyeden sonra ekranda neredeyse hep bir katman var.
- **Renk:** koyu (#111-#1A1A1A) kartlar + tek vurgu turuncu-kırmızı (#FF5A1F civarı) + beyaz. Mono font küçük etiketlerde ("SEKTÖR 01", "YILLIK BÜYÜME", "ai-2027.com").
- **Ses:** -14 LUFS; duraklamalarda ~-20 dB alt zemin (hafif müzik yatağı ya da oda), efektler çok az.

## 3. Bileşen kataloğu (bizde karşılığı)
| # | Bileşen | Ne yapıyor | Stüdyoda |
|---|---|---|---|
| 1 | Hook başlığı | 3 satır dev yoğun yazı, son satır sarı bant üstünde (tamamı büyük harf) | `fx hook_stack` var — biz normal harf + vurgu bandı ekleriz |
| 2 | Takvim yaprağı | yıl değişince yaprak çevrilir (2024→2025), üstte ay/"Senaryo"/"Tahmin" etiketi | **YOK → eklenmeli** (`scene: calendar`) |
| 3 | Kaynak kartı + el çizimi | ekran görüntüsü kartı, kırmızı daire/alt çizgi kendini çizer, fare imleci gezer | kısmen (`proof`, `doodle`) → **`scene: source` eklenmeli** |
| 4 | Kilitli liste (açık döngü) | "Para nereye akacak?" 5 madde bulanık + kilit; anlatıldıkça kilit açılır, isim belirir | **YOK → eklenmeli** (`scene: locked_list`) — maddeli videolar için birebir |
| 5 | Yatay kıyas çubukları | koyu kart, mono etiket: "2024 · 4 DK" küçük gri çubuk → "BUGÜN · 16 SAAT" uzun turuncu çubuk + rozet "1 YIL ERKEN" | kısmen (`compare`) → **`scene: bars` eklenmeli** |
| 6 | Dikey kıyas (tam ekran) | ABD devleti (gri, simge) vs YZ şirketleri (turuncu) büyür + "ŞİRKETLER > DEVLET" damgası | `fx chart_grow` yakın → **`scene: versus` eklenmeli** |
| 7 | Sektör kartı | "SEKTÖR 01 · ÇİP" + 3 şirket logosu kartı + köşede rozet ("ŞEBEKE BEKLEME 7-12 YIL") | **YOK → eklenmeli** (`scene: sector`, logo yerine hisse kodu/BIST logosu) |
| 8 | Tam ekran B-roll + makale kartı | AI görseli tam ekran, altta yarı saydam makale kartı, cümle vurgusu | B-roll (§4b) var; makale kartı `source` ile |
| 9 | Altyazı | beyaz kalın, ORTALI, 2 satır, **aktif kelime yarı saydam beyaz kutu içinde** (karaoke) | bizde sola hizalı + renkli kelime → **`make_ass --karaoke` seçeneği eklenmeli** |
| 10 | Kapanış | sadece sözlü: kaydet + tavsiye değil + soru + yorum + takip | `save_cta` var; sözlü kapanış metne yazılmalı |

## 4. Semih için çıkarımlar
- Bizim "6 hata"daki split panel yerine **başın üstü bandı + tek tam ekran anlar** bu referansın dili. Petrol tema bunu koyu kart + petrol vurgu ile karşılar.
- Uzun (90-150 sn) "zaman çizelgesi / liste" videolarında: kilitli liste + takvim + sektör kartı üçlüsü izlenme süresini taşır.
- Senaryo tarafı: hook'ta rakam+çatışma, otorite zinciri, itiraz kırma, soru köprüleri, "kaydet + yorum + takip" kapanışı → senaryo şablonuna eklenecek.
- Tamamı büyük harf başlık ve kırmızı-turuncu vurgu bu hesabın kimliği; Semih büyük harf istemiyor ve petrol'e geçti — dili alıyoruz, kimliği kopyalamıyoruz.
