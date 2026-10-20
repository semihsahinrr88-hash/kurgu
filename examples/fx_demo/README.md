# fx demo — 24 efekt
Referans "22 video efekti" Reels'inden çıkarılan efektlerin örnek spec'leri (petrol tema).
`jobs.txt`: efekt + test segmenti (A/B/C = 3 sn'lik konuşan-kafa klipleri, X = ortasında kesim olan klip).
```bash
cat jobs.txt | xargs -P 2 -L 1 sh -c 'python3 ~/studio/fx.py $0.json --in seg$1.mp4 -o out/$0.mp4'
```
Maskeli efektler (orbit, frame_break, green_screen, paper_cut, cover_story, doodle_boil) segmentin yanına
`seg?.subj.mov` maskesini otomatik üretir. Koordinatlar (center, window, shapes, label_xy) klibe göre ayarlanır.
