set -e
python3 compose.py
python3 ~/studio/sfx.py mix stage2.mp4 sfx_cues.json stage3.mp4
C="acompressor=threshold=-26dB:ratio=3:attack=5:release=90:makeup=8"
J=$(ffmpeg -hide_banner -i stage3.mp4 -af "$C,loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 | sed -n '/{/,/}/p')
MI=$(echo "$J"|python3 -c "import json,sys;d=json.load(sys.stdin);print(f\"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}\")")
ffmpeg -loglevel error -y -i stage3.mp4 -af "$C,loudnorm=I=-14:TP=-1.5:LRA=11:$MI:linear=true,aresample=48000" -c:v copy -c:a aac -b:a 256k final.mp4
python3 ~/studio/export.py reels final.mp4 borsada_6_hata_reels.mp4
ffmpeg -hide_banner -i borsada_6_hata_reels.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:" | tail -2
echo BITTI
