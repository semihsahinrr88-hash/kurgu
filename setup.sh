#!/usr/bin/env bash
# BorsaSemih Video Stüdyo — tek komutla kurulum (her yeni bulut oturumunda bir kez, ~3-5 dk).
#   git clone --depth 1 https://github.com/semihsahinrr88-hash/kurgu ~/kurgu && bash ~/kurgu/setup.sh
# Sonuç: ~/studio/ içinde video-use helper'ları (yamalı) + BorsaSemih scriptleri + fontlar + ses kütüphanesi.
set -euo pipefail
CA=/root/.ccr/ca-bundle.crt
[ -f "$CA" ] && export SSL_CERT_FILE=$CA REQUESTS_CA_BUNDLE=$CA NODE_EXTRA_CA_CERTS=$CA
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ST=~/studio; mkdir -p "$ST" && cd "$ST"

echo "1/6 video-use"
test -d video-use || git clone -q --depth 1 https://github.com/browser-use/video-use
cp video-use/helpers/*.py "$ST/"

echo "2/6 python paketleri"
pip install -q --break-system-packages faster-whisper librosa matplotlib pillow numpy fonttools 2>&1 | grep -v -i warning || true
( pip install -q --break-system-packages whisperx >/tmp/whisperx_install.log 2>&1 && echo "whisperx hazır" >>/tmp/whisperx_install.log ) &
WX=$!


echo "3/6 BorsaSemih scriptleri + fontlar + sfx"
cp "$PKG"/scripts/*.py "$ST/"
mkdir -p "$ST/fonts" && cp "$PKG"/fonts/*.ttf "$ST/fonts/"
ln -sfn "$PKG/sfx" "$ST/sfx"
cp "$PKG/frame.md" "$ST/frame.md"; mkdir -p "$ST/templates" && cp "$PKG"/templates/* "$ST/templates/"

echo "4/6 render.py yamaları"
# Yama 1: altyazı varsayılan normal harf; SUB_UPPER=1 ile Türkçe-doğru büyük harf
grep -q SUB_UPPER render.py || {
  sed -i 's/^import json$/import json\nimport os/' render.py
  sed -i 's/            text = text.upper()/            if os.environ.get("SUB_UPPER") == "1":\n                text = text.replace("i", "İ").replace("ı", "I").upper()/' render.py
}
# Yama 2: şeffaf .webm overlay'lerde alfa kanalı (libvpx-vp9 decoder)
python3 - <<'PY'
s=open('render.py').read()
old='        inputs += ["-i", str(ov_path)]'
new='''        dec = ["-c:v", "libvpx-vp9"] if ov_path.suffix.lower() == ".webm" else []
        inputs += [*dec, "-i", str(ov_path)]'''
if 'libvpx-vp9' not in s and old in s: s=s.replace(old,new); open('render.py','w').write(s)
PY
# Yama 3: zoom / push / layout (talk|split|pip)
python3 patch_zoom.py

echo "5/6 HyperFrames (Chrome + skill'ler)"
npx --yes hyperframes browser ensure >/dev/null 2>&1 || echo "UYARI: hyperframes browser ensure başarısız"
npx --yes hyperframes skills update talking-head-recut embedded-captions >/dev/null 2>&1 || echo "UYARI: hyperframes skills update başarısız"

echo "6/6 kontrol"
python3 -m py_compile transcribe_local.py auto_cut.py retime_words.py align_words.py make_ass.py sfx.py scene.py export.py
grep -c SUB_UPPER render.py >/dev/null && grep -q 'r.get("layout"' render.py && grep -q libvpx-vp9 render.py
ls "$ST/sfx/"*.wav | wc -l | xargs -I{} echo "sfx: {} efekt"
ffprobe -version | head -1
wait $WX || true; tail -1 /tmp/whisperx_install.log
python3 -c "import nltk, nltk.pathsec as p; p.ALLOW_PROXIED_FETCH=True; nltk.download('punkt_tab', quiet=True)" >/dev/null 2>&1 || echo "UYARI: nltk punkt_tab indirilemedi (align_words için gerekli)"
echo "HAZIR: ~/studio"
