# Ses temizliği (VARSAYILAN KAPALI)

Semih yankıyı çekimde engelliyor. Sadece Semih açıkça "yankıyı/gürültüyü temizle" derse aşağıdaki tarifi kullan:
```bash
curl -sSL -o ~/studio/deep-filter https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep-filter-0.5.6-x86_64-unknown-linux-musl && chmod +x ~/studio/deep-filter
ffmpeg -y -i <video> -vn -ac 1 -ar 48000 -c:a pcm_s16le src48.wav
mkdir -p df && ~/studio/deep-filter -D --pf -o df src48.wav          # -D: gecikme telafisi (senkron bozulmaz)
ffmpeg -y -i df/src48.wav -af "highpass=f=80,equalizer=f=320:t=q:w=1.2:g=-3,agate=threshold=0.015:ratio=2:attack=5:release=110:range=0.3:knee=3" clean.wav
ffmpeg -y -i <video> -i clean.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest <ad>_clean.mp4
```
EDL `sources` yolunu `<ad>_clean.mp4` yap (anahtar adı aynı kalsın → transkript eşleşir). Ölçüm: kelime sonrası 150 ms yankı kuyruğu orijinalde ~-24 dB, temizde ~-37 dB (konuşmaya göre). Sesi dinleyemezsin: kullanıcıya 7 sn önce / 0.8 sn sessizlik / 7 sn sonra karşılaştırma .m4a'sı gönder. Metalik/aşırı işlenmiş derse `range=0.4` ve `--pf`'siz dene.
