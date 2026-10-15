set -e
export SSL_CERT_FILE=/root/.ccr/ca-bundle.crt NODE_EXTRA_CA_CERTS=/root/.ccr/ca-bundle.crt
cd ~/studio/reels1/edit
echo "[1] sahneler"; for k in s1 s2 s3 s4 s5 s6 cta; do python3 ~/studio/scene.py specs/$k.json -o animations/$k 2>&1 | tail -1; done
echo "[2] base"; (cd ~/studio && python3 render.py reels1/edit/edl_base.json -o reels1/edit/base.mp4 --no-subtitles --no-loudnorm 2>&1 | tail -1)
echo "[3] offsets"; cp offs.json offs_prev.json; python3 ~/studio/frame_offsets.py . --fps 60 | head -1; cmp -s offs.json offs_prev.json && echo "offs aynı" || echo "OFFS DEĞİŞTİ"
echo "[4] altyazı"; cp edl.json edl_orig.json; cp edl_adj.json edl.json; (cd ~/studio && python3 make_ass.py reels1/edit --hl "kaybed,kaybet,planla,sessiz,yığma,kira,taksit,borç,tavşan,kaydet,uzman"); cp edl_orig.json edl.json
echo "[5] gömülü kelime"; cd embed; ffmpeg -loglevel error -y -ss 52.1333 -t 3.2 -i ../base.mp4 -vf fps=30 -c:v libx264 -crf 12 -an seg.mp4
npx --yes hyperframes remove-background seg.mp4 -o subj.webm --quality best 2>&1 | tr '\r' '\n' | grep -E "Removed|rror" | tail -1
ffmpeg -loglevel error -y -i seg.mp4 -loop 1 -t 3.2 -framerate 30 -i word.png -c:v libvpx-vp9 -i subj.webm -filter_complex "[1:v]format=rgba,fade=t=in:st=0.45:d=0.3:alpha=1,fade=t=out:st=2.75:d=0.3:alpha=1[w];[0:v][w]overlay=0:0[a];[a][2:v]overlay=0:0:shortest=1,format=yuv420p" -c:v libx264 -crf 14 -r 30 embed.mp4; cd ..
echo "[6] birleştirme + ses + export"; bash finish.sh
python3 ~/studio/export.py teslim final.mp4 borsada_6_hata_reels_ig.mp4
python3 ~/studio/export.py cover base.mp4 kapak.jpg --t 1.0 --title "Borsada sürekli *kaybediyorsan*"
echo TAMAM
