# Render dan Verifikasi

Baca dokumen ini sebelum membangun dan merender. Semua perintah di bawah adalah contoh; sesuaikan nama file dengan aset user. Jangan menjalankan perintah yang bergantung pada tool yang belum dicek ada.

## Daftar isi
1. Cek lingkungan
2. Memilih pipeline render
3. Mengukur dan menganalisis voiceover
4. Menganalisis video referensi
5. Menyusun frame secara deterministik
6. Mixing audio dan ekspor
7. Verifikasi berkas hasil ekspor (termasuk gerbang sinkron, geometri, ekor audio)
8. Musik latar buatan sendiri
9. Jebakan umum
10. Bersih-bersih setelah serah terima

## 1. Cek lingkungan

Jalankan dulu, dan sesuaikan rencana dengan hasilnya:

```bash
ffmpeg -version | head -1; ffprobe -version | head -1
ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "(libx264|aac)" || echo "PERINGATAN: encoder libx264/aac tidak ditemukan"
python3 -c "import PIL, numpy; print('PIL+numpy ok')"
python3 -c "import faster_whisper; print('pengenalan suara per kata: ada')" 2>/dev/null || echo "pengenalan suara: tidak tersedia (pip install faster-whisper; kalau gagal, timing per kata jadi perkiraan -- beri tahu user)"
node -v
fc-list | head -20          # font yang tersedia
which espeak-ng pico2wave   # TTS offline (kemungkinan besar tidak ada)
[ -n "$GEMINI_API_KEY" ] && echo "GEMINI_API_KEY: ada" || echo "GEMINI_API_KEY: tidak ada"
which curl yt-dlp           # curl untuk TTS, yt-dlp untuk unduh referensi via URL
NC=$(timeout 8 curl -s -o /dev/null -w '%{http_code}' https://generativelanguage.googleapis.com/v1beta/models 2>/dev/null)
case "$NC" in 200|403|404) echo "jaringan: OK (HTTP $NC)";; *) echo "jaringan: BERMASALAH (HTTP $NC / timeout)";; esac
```

Catatan: jaringan lingkungan kerja bisa dibatasi. Cek dulu apa yang bisa diakses: kalau `pip` dan `npm` jalan, font tambahan bisa lewat paket npm `@fontsource/<nama-font>`; kalau unduhan eksternal diblokir, pakai font yang sudah ada di sistem. Versi ffmpeg memengaruhi opsi yang boleh dipakai (lihat bagian 6).

### Font siap pakai (terpasang di `~/.local/share/fonts/motion/`)

**Katalog ini titik awal, bukan menu.** Kalau topik butuh tipografi yang tidak ada di sini, unduh sendiri (lihat sub-bagian berikut). Memakai font terpasang hanya karena tersedia adalah cara tercepat membuat semua video terasa sama.

Cek cepat: `fc-list | grep -iE "poppins|fredoka|caveat"` — kalau kosong, font belum terpasang (lihat §9 kalau penyebabnya tidak jelas).

Pilih sesuai mood video; satu video maksimal 2–3 family (satu display + satu pendukung, plus handwriting kalau perlu aksen):

| Mood / gaya | Font | Keterangan |
|---|---|---|
| Modern, netral, UI-like | `Poppins` (Regular/SemiBold/Bold), `Inter`, `Montserrat`, `Manrope` | Standar aman untuk narasi dan body text |
| Playful, doodle, bulat ramah | `Baloo 2`, `Fredoka`, `Quicksand`, `Nunito` | Cocok topik ringan, edukasi santai, anak/muda |
| Handwriting, catatan tangan | `Caveat`, `Patrick Hand`, `Indie Flower`, `Kalam` | Aksen anotasi, garis panah, coretan |
| Script elegan/retro | `Pacifico`, `Dancing Script` | Logo kata, judul santai — jangan untuk body text |
| Impact, tipografi kinetis besar | `Bebas Neue`, `Anton`, `Archivo Black`, `Oswald` | Kata kunci besar, hook, angka statistik |
| Editorial/serif tegas | `Fraunces`, `Instrument Serif`, `Libre Caslon Text` | Kutipan, angka besar, topik sejarah/serius — gaya beda dari sans, jangan dicampur berlebihan |
| Teknis/data/mono | `JetBrains Mono`, `Space Mono`, `Space Grotesk` | Label kecil, angka statistik, nuansa data/teknologi |

Cara pakai: di CSS/Remotion pakai nama family persis seperti di `fc-list` (mis. `"Baloo 2"`, `"Bebas Neue"`); di PIL pakai path file TTF langsung (`~/.local/share/fonts/motion/Baloo2.ttf`). Font variable (Inter, Montserrat, Baloo2, Fredoka, Quicksand, Nunito, Caveat, DancingScript) punya semua bobot dalam satu file — di CSS set `font-weight`; di PIL instantiate bobot dengan `ImageFont.truetype(..., size).set_variation_by_axes([weight])`. Poppins tidak variable: pakai file terpisah `Poppins-Regular.ttf`, `Poppins-SemiBold.ttf`, `Poppins-Bold.ttf` (tidak ada `Poppins.ttf`).

### Menambah font baru

Kalau topik butuh tipografi yang belum terpasang, unduh sendiri. Tiga jalur, coba berurutan:

```bash
# 1) Google Fonts lewat repo github/google/fonts — paling andal, file TTF langsung
#    pola path: <lisensi>/<slug>/<NamaFile>.ttf   (lisensi: ofl | apache | ufl)
SLUG=outfit; FILE="Outfit%5Bwght%5D.ttf"     # %5B = [ , %5D = ] untuk font variable
curl -sL -o "/tmp/$SLUG.ttf" "https://github.com/google/fonts/raw/main/ofl/$SLUG/$FILE"

# 2) kalau slug/nama file tidak diketahui, tanya API-nya.
#    Perhatikan: urutan listing sering menaruh file Italic di depan -- filter dulu,
#    dan utamakan yang tidak Italic. Nama file bermuatan [ ] harus di-URL-encode
#    (%5B / %5D) saat diunduh.
SLUG=outfit
curl -s "https://api.github.com/repos/google/fonts/contents/ofl/$SLUG" \
  | python3 -c "
import json, sys, urllib.parse
fs = [f['name'] for f in json.load(sys.stdin) if f['name'].endswith('.ttf')]
plain = [f for f in fs if 'italic' not in f.lower()] or fs
pick = plain[0]
print('pilih:', pick)
print('unduh:', 'https://github.com/google/fonts/raw/main/ofl/$SLUG/' + urllib.parse.quote(pick))
"

# 3) kalau GitHub diblokir: npm @fontsource (kemasannya berisi file woff2 + ttf)
npm pack "@fontsource/$SLUG" --silent && tar -xzf fontsource-$SLUG-*.tgz && \
  find package -name "*.ttf" | head
```

Setelah berkasnya didapat, **wajib diverifikasi sebelum dipakai di scene** — font rusak atau bukan file font akan gagal jauh di tengah render:

```python
from PIL import ImageFont
f = ImageFont.truetype("/tmp/outfit.ttf", 80)
print(f.getname())                       # nama family sebenarnya, bukan nama file
d.textbbox((0, 0), "Baca Tulis", font=f)  # harus mengembalikan kotak, bukan error
f.set_variation_by_axes([700])           # hanya kalau variable font
```

Kalau ukurannya di bawah 10 KB, itu halaman HTML galat, bukan font. Salin ke `~/.local/share/fonts/motion/` dengan nama sesuai family (mis. `Outfit.ttf`), lalu `fc-cache -f` bila memakai nama family di CSS. Untuk PIL, path langsung cukup — tidak perlu fc-cache.

Catatan penting: pilih font yang **layak untuk topiknya**, bukan yang paling mudah diunduh. Kalau unduhan gagal semua, pakai yang terpasang dan katakan ke user bahwa tipografi idealnya belum tercapai — jangan diam-diam turun ke font default yang jelek (lihat §9).

## 2. Memilih pipeline render

Prinsipnya: render setiap frame secara deterministik dari fungsi waktu `t = nomor_frame / 30`, lalu satukan dengan ffmpeg. Cara ini membuat jumlah frame pasti sama dengan durasi total × 30 dan animasi mudah disinkronkan dengan timeline.

| Pipeline | Cocok untuk | Syarat |
|---|---|---|
| Python (Pillow/numpy, opsional cairosvg atau skia-python) | Teks, bentuk, gambar user, mask, parallax | PIL dan numpy |
| HTML/CSS/JS + browser headless (screenshot per frame) | Tipografi kompleks, SVG, CSS blur dan bayangan | Browser headless tersedia dan bisa dijalankan |
| Remotion / Node | Komposisi berbasis React | Node dan browser headless |
| Filtergraph ffmpeg / MoviePy | Komposisi sederhana | ffmpeg |

Pilih pipeline yang paling cocok dengan kebutuhan komposisi timeline, bukan yang kebetulan sudah terpasang. Kalau dependensinya belum ada, install dulu sebelum render:

```bash
pip install pillow numpy cairosvg     # pipeline Python
npx playwright install chromium       # headless browser (HTML/CSS atau Remotion)
npm install                           # dependensi proyek Remotion, lalu render dengan npx remotion render
```

Kalau instalasi gagal (jaringan diblokir, tanpa izin), berhenti dan laporkan ke user beserta alasannya. Jangan diam-diam turun ke pipeline yang lebih sederhana — kualitas visual menurun tanpa user sadar. Lanjut pakai pipeline sederhana hanya kalau user menyetujuinya setelah tahu konsekuensinya. Kalau benar-benar tidak ada yang bisa jalan, ikuti bagian "Kejujuran soal hasil" di SKILL.md.

Simpan frame sebagai `work/frames/00000.png` sampai `work/frames/01199.png`. Untuk mengurangi memori, bisa juga di-pipe langsung ke ffmpeg (`-f rawvideo -pix_fmt rgb24 -s WxH -r 30 -i -`).

## 3. Mengukur dan menganalisis voiceover

Durasi asli:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "audio/voiceover.wav"
```

Jeda dan batas kalimat (turunkan `noise` kalau rekaman bising):

```bash
ffmpeg -i "audio/voiceover.wav" -af silencedetect=noise=-35dB:d=0.25 -f null - 2>&1 | grep silence_
```

Timing per kata: **pakai pengenalan suara otomatis dulu, perkiraan jumlah kata sebagai jalan terakhir.** Hitung kata per detik hanya untuk memeriksa kewajaran panjang naskah, jangan untuk menempatkan teks.

Coba pengenalan suara otomatis (ASR) ber-timestamp per kata sebelum menyerah ke perkiraan. `faster-whisper` praktis dan berjalan di CPU:

```python
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio_array, language="id", word_timestamps=True)
# segs[i].start/.end per kalimat; segs[i].words[j].word/.start/.end per kata
```

Beri `audio_array` numpy float32 16 kHz mono, **bukan path file**: di sebagian lingkungan `av` menolak `metadata_errors` sehingga `transcribe("file.wav")` gagal dengan `TypeError: open() got an unexpected keyword argument 'metadata_errors'`. Decode sendiri:

```bash
ffmpeg -v error -y -i "audio/voiceover.wav" -ar 16000 -ac 1 work/voiceover-16k.wav
```

```python
import wave, numpy as np
w = wave.open("work/voiceover-16k.wav")
a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
```

Pakai hasil ASR apa adanya walau ada salah transkripsi (mis. "berumasuk") — yang dibutuhkan hanya batas waktu katanya, bukan ejaannya. Selisih ASR ±0,1 dtk tidak terlihat; selisih estimasi kata bisa 2 dtk dan itu terlihat jelas.

Kalau pengenalan suara tidak tersedia atau gagal: bagi waktu menurut batas jeda `silencedetect`, distribusikan kata per frasa menurut suku kata, dan **katakan ke user bahwa timing per kata adalah perkiraan**.

Kalau VO di-`adelay` saat mixing (mis. mulai detik 1), semua waktu hasil pengenalan suara harus ditambah delay itu sebelum dipakai di timeline. Tulis sebagai satu konstanta (`VO_DELAY`) dan turunkan semua waktu darinya, jangan tambahkan manual di tiap scene.

Catatan format: contoh di bawah memakai `audio/voiceover.wav`. Berkas yang user berikan boleh .mp3/.wav/.m4a — rapikan ke `audio/voiceover.wav` (48 kHz mono) sebelum dianalisis.

Kalau durasi total hasil hitungan (durasi voiceover + ±2,5 detik) melebihi `MAX_DUR` (default 60 detik), berhenti dan tanya user (lihat Tahap 4 di SKILL.md).

Kalau user tidak punya voiceover, urutan pilihannya:

1. **Generate lewat Gemini TTS** (butuh `GEMINI_API_KEY`; contoh pakai model `gemini-3.8-flash-tts`, kalau 404 cek daftar model TTS yang tersedia di docs Google):

Tulis payload dengan `json.dumps` (JANGAN inline naskah ke curl `-d` — kutip/newline di naskah merusak JSON dan memicu 400 `INVALID_ARGUMENT`):

```bash
# Tulis naskah yang sudah disetujui ke script.txt dulu (boleh multiline, kutip bebas)
# PENTING: buang label struktur seperti [Hook], [Inti 1], [Penutup] dari teks yang
# dikirim ke TTS — model TTS membaca teks verbatim, label bisa ikut terbaca.
# Simpan label di file terpisah sebagai peta timing scene, jangan di script.txt.

python3 - <<'PY'
import json
naskah = open('script.txt').read()
# WAJIB: text = verbatim SAJA, tanpa instruksi apa pun. Instruksi ala "Bacakan dengan
# nada hangat..." DI DALAM text akan DIBACA KERAS-KERAS oleh model 3.8 (terbukti:
# instruksi+3 kata = 6,5 dtk; verbatim 3 kata = 2,2 dtk). Nada/delivery lewat
# speech_metadata.style — kanal resmi yang tidak ikut terbaca.
payload = {
    "contents": [{"parts": [{"text": naskah,
        "speech_metadata": {"style": "hangat, jelas, dan sedikit bersemangat"}}]}],
    "generationConfig": {
        "responseModalities": ["AUDIO"],
        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}
    }
}
json.dump(payload, open('vo_req.json','w'), ensure_ascii=False)
PY

curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d @vo_req.json > vo.json

python3 - <<'PY'
import json, base64, sys
d = json.load(open('vo.json'))
if 'candidates' not in d:
    sys.exit(f"TTS gagal, respons API: {json.dumps(d)[:500]}")
part = d['candidates'][0]['content']['parts'][0]
data = base64.b64decode(part['inlineData']['data'])
mime = part['inlineData'].get('mimeType', '')
open('work/voiceover.wav' if mime == 'audio/wav' else 'work/voiceover.pcm','wb').write(data)
print('mimeType:', mime)
PY
# 3.8 mengembalikan audio/wav lengkap (RIFF header) — tulis langsung .wav.
# Kalau mimeType audio/l16 (PCM mentah, model lama), baru decode manual:
[ -f work/voiceover.pcm ] && ffmpeg -f s16le -ar 24000 -ac 1 -i work/voiceover.pcm "audio/voiceover.wav" || cp work/voiceover.wav "audio/voiceover.wav"
```

**Kalau dapat 400 `INVALID_ARGUMENT`**, baca pesan errornya di `vo.json`:- `No matching speaker voice found for name: X` → nama voice salah. Cek daftar voice resmi: `curl -s -H "x-goog-api-key: $GEMINI_API_KEY" "https://generativelanguage.googleapis.com/v1beta/models"` atau docs `ai.google.dev/gemini-api/docs/speech-generation#voices` (30 voice prebuilt, semua boleh dipakai).
- `Invalid JSON payload received` → payload rusak, hampir pasti karena naskah di-inline ke string curl. Pakai pola `json.dumps` di atas.
- Selain itu → cek `field_violations` di respons, perbaiki field yang disebut.

Pilih voice sesuai topik. Beberapa voice yang bagus untuk narasi: `Kore` (tegas), `Puck` (ceria/upbeat), `Charon` (informatif), `Zephyr` (terang), `Leda` (muda/wanita). Tersedia 30 voice prebuilt (termasuk `Orus`, `Aoede`, `Enceladus`, dll — docs lama yang bilang tidak ada sudah basi). Nama voice case-sensitive. Kalau ragu, probe satu request dengan teks pendek. Sebutkan ke user voice apa yang dipakai. Hasilnya langsung masuk pipeline bagian 3 seperti rekaman user.

**Sanity check setelah generate.** Bandingkan durasi hasil dengan perkiraan naskah (patokan ±2,5 kata/detik untuk Bahasa Indonesia, ambang ±35%). Selisih jauh lebih besar biasanya berarti ada teks non-naskah yang ikut dibacakan (instruksi, label `[Hook]`, placeholder) atau naskah terpotong: periksa `vo_req.json` — `text` harus berisi verbatim naskah saja — lalu regenerate sekali. Kalau tetap tidak masuk akal, beri tahu user sebelum lanjut ke timeline.

**Mode opsional untuk timing presisi (per-frasa).** Kalau tipografi kinetik per kata sangat penting: pecah naskah jadi frasa, generate satu request per frasa, ukur tiap file dengan `ffprobe` sehingga batas waktu tiap frasa eksak, lalu gabungkan berurutan menjadi satu `audio/voiceover.wav` (file teks concat + `ffmpeg -f concat -i list.txt -c copy` atau re-encode ke WAV). Trade-off: kuota free tier per model cuma 10 request/hari (terhitung per model, per project) — naskah panjang tidak realistis dipecah per frasa di free tier. Default tetap satu file utuh.

Batas kuota free tier TTS: sekitar **10 request/hari per model** (bukan per menit). Kalau dapat HTTP 429 `RESOURCE_EXHAUSTED`, cek pesannya: kalau limit harian, jangan diulang hari itu — langsung fallback ke `gemini-3.8-flash-lite-tts` (model terpisah, kuota harian terpisah), sebutkan ke user kalau pakai fallback. Kalau kedua model habis, lanjut opsi 2 di bawah.

2. **Tanpa API key / gagal**: jangan mengarang suara. Sarankan user membuat suara dari naskah lalu memberikannya sebagai berkas. Kalau user minta draf tanpa suara, timing perkiraan boleh dihitung dari jumlah kata (sekitar 2,5 kata per detik), dengan label draf dan tetap menghormati `MAX_DUR`.

## 4. Menganalisis video referensi

Referensi datang dari user (file atau URL) atau dicari sendiri di Pinterest (sub-bagian di bawah). Setelah file `assets/reference.mp4` ada, analisis:

```bash
ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration -of default=nw=1 "assets/reference.mp4"
mkdir -p work/ref && ffmpeg -i "assets/reference.mp4" -vf "fps=2,scale=480:-1" work/ref/%03d.png

# Contact sheet satu halaman untuk dibaca cepat
ffmpeg -framerate 2 -i work/ref/%03d.png -vf "scale=320:-1,tile=6x5" work/ref/contact_sheet.png
```

Lihat bingkai hasil ekstrak (bisa disusun jadi lembar kontak) untuk membaca palet, tipografi, komposisi, dan ritme potongan. Ambil prinsipnya, bukan salinannya. Orientasi dan rasio layar referensi menjadi default orientasi output.

Kalau referensi berupa URL dari user, unduh dengan `yt-dlp "<url>" -o "assets/reference.mp4"` sebelum analisis.

### Mencari referensi sendiri di Pinterest (kalau user tidak memberi)

Kalau user tidak memberi file/URL referensi (atau memilih "serahkan ke AI"), cari sendiri video yang nyambung dengan topik:

1. Cari kandidat pin video yang relevan dengan topik: pakai tool pencarian web yang tersedia dengan kueri seperti `pinterest.com pin <kata kunci topik> video` (coba bahasa Indonesia dan Inggris). Ambil 3–5 kandidat URL pin.
2. Unduh kandidat satu per satu sampai ada yang berhasil:

   ```bash
   yt-dlp "<url-pin>" -o "assets/reference.mp4"
   ```

3. Saring sebelum dipakai — cek dengan `ffprobe`, buang kandidat yang: durasi < 5 detik atau > 90 detik, resolusi di bawah resolusi output yang direncanakan, tidak punya stream video, atau isinya tidak berhubungan dengan topik. Kandidat gugur → lanjut ke berikutnya.
4. Semua kandidat gagal → jangan mati-matian. Katakan pada user, lalu tanya: user carikan file/URL-nya sendiri, atau user beri arahan gaya singkat (palet, font, mood) untuk lanjut tanpa referensi. Tidak ada gaya bawaan — jangan melanjutkan tanpa acuan gaya.

Kualitas hasil cari sendiri tidak terkontrol. Wajib: sebut ke user video referensi apa yang terpilih (URL dan alasan singkat) sebelum masuk analisis, dan jadikan inspirasi bukan cetakan sesuai aturan di atas.

## 5. Menyusun frame secara deterministik

- Tulis satu fungsi `render(t)` yang menggambar seluruh frame dari waktu saja, tanpa state tersembunyi atau angka acak yang berubah tiap panggilan (pakai seed tetap).
- Definisikan fungsi easing (ease-out, ease-in-out, overshoot) dan pakai di semua animasi. Hindari gerak linear kecuali memang disengaja.
- **Kewajiban gerak (gerbang QC, bukan pilihan):** di SETIAP detik video ada minimal satu elemen yang bergerak. Tidak boleh ada slide statis. Jika scene "diam", pakai kamera mikro (zoom drift atau geser halus sepanjang scene). Kata kunci dan angka penting (mis. "92 juta") wajib diberi penekanan gerak tepat saat kata diucapkan — besar dan bentuk penekanannya keputusan rasa (pop skala, warna, bobot, posisi, atau kombinasi), dan skala WAJIB decay kembali ke 100% sebelum pop berikutnya — nilai overshoot yang menetap (mis. kata terus memakai skala 120%) membuat kata menimpa tetangganya. Slot lebar tiap kata diukur dengan font yang benar-benar dipakai (keyword ≠ body), dan kata yang muncul dua kali dalam satu scene punya waktu masing-masing — jangan dipetakan lewat dict per kata. Catatan encoder: gerak POSISI elemen (geser x/y) lebih andal daripada perubahan radius/skala saja — lingkaran solid tanpa antialias yang hanya berdenyut radius sering tidak mengubah satu piksel pun, dan gerakan di bawah ±10 px bisa ter-quantize hilang di CRF 18+ (lihat §9).
- Rumus easing siap pakai (boleh dipakai, boleh diganti rumus lain sesuai rasa): `easeOutCubic(u) = 1-(1-u)**3`; `easeInOutCubic(u) = u<0.5 ? 4*u**3 : 1-((-2*u+2)**3)/2`; overshoot/back-out: `1 + 2.7*(u-1)**3 + 1.7*(u-1)**2`.

  **Tidak ada angka durasi atau overshoot yang diwajibkan.** Durasi masuk, besar overshoot, dan ritme adalah keputusan rasa — pilih yang cocok dengan tempo narasi dan mood referensi. Yang wajib hanyalah invarian berikut, karena kalau dilanggar hasilnya rusak, bukan cuma berbeda rasa:
  - skala pop **decay balik ke 100%** sebelum pop berikutnya (kalau tidak, kata menimpa tetangganya);
  - hindari kecepatan konstan kecuali memang disengaja;
  - elemen idle bergerak **posisi**, bukan cuma radius/skala (lihat catatan encoder di atas).
- Ikon dan diagram digambar dari bentuk kode (donut, bar, briefcase, bohlam) — bukan teks atau emoji. Latar boleh bergantian antar scene (mis. terang/gelap) dengan satu warna aksen konsisten.
- Motion blur bisa disimulasikan dengan merata-ratakan beberapa sub-frame pada waktu yang sedikit berbeda.
- Render paralel dan bisa resume: karena frame deterministik, gambar dengan beberapa worker (mis. `multiprocessing`, 4–8 proses) dan lewati frame yang file PNG-nya sudah ada dan tidak kosong. Kalau render mati di tengah, jalankan ulang skrip yang sama — hanya frame yang hilang yang digambar ulang.
- Pasang timeline dari tahap 5 sebagai data (daftar segmen dengan waktu mulai/selesai) supaya mudah disetel ulang.
- **Satu tabel waktu absolut sebagai sumber tunggal.** Semua waktu kemunculan elemen (`{label: detik_video}`) tinggal di satu tabel, dan scene membaca dari tabel itu — scene tidak menyimpan offset masuk sendiri. Batas scene diturunkan dari batas kalimat hasil pengenalan suara, bukan diketik terpisah. Kalau tiap scene punya angka kirimannya sendiri, menggeser satu kalimat berarti menggeser enam angka dan drift balik lagi di scene berikutnya. Label waktu juga jangan di-hardcode ke detik saat beat-nya masih bisa berubah: pakai `B_VIDEO[key] - scene_start` dihitung saat render, jangan `0.55` yang dibekukan.
- Render frame 0 sampai (jumlah frame − 1). Frame terakhir harus tetap berisi visual penutup yang jelas, bukan layar kosong.

## 6. Mixing audio dan ekspor

Durasi video mengikuti voiceover. Hitung dulu durasi total dan jumlah frame (aturannya ada di Tahap 4 SKILL.md: suara + ±1 detik pembuka + ±1,5 detik penutup, dibulatkan ke atas ke detik penuh):

TENTUKAN dulu batasnya. `MAX_DUR` default 60; naikkan hanya kalau user meminta sendiri secara eksplisit.

```bash
MAX_DUR=60                      # batas default; ganti hanya atas permintaan user
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "audio/voiceover.wav")
DUR=$(awk -v v="$VO_DUR" 'BEGIN{t=v+2.5; d=int(t); if (d<t) d++; print d}')
FRAMES=$((DUR*30))
FADE_ST=$(awk -v d="$DUR" 'BEGIN{print d-2.5}')
echo "voiceover=$VO_DUR  total=$DUR detik  frame=$FRAMES  batas=$MAX_DUR"
awk -v d="$DUR" -v m="$MAX_DUR" 'BEGIN{if(d>m) print "MELEBIHI BATAS "m" DETIK: berhenti dan tanya user"}'
```

Pakai `$DUR` dan `$FRAMES` itu untuk seluruh render (jumlah frame yang digambar, timeline, dan ekspor). Voiceover digeser mulai di detik ke-1 (`adelay`), di-pad sampai akhir video, dan musik diloop lalu dipotong sepanjang video, diturunkan volumenya, di-duck saat ada suara.

**Tiga langkah, jangan digabung jadi satu `filter_complex`.** Menggabungkan `loudnorm` bersama `apad` dalam satu rantai membuat ekor audio mati: filter loudnorm ikut memproses bagian padding sehingga ekornya jatuh ke −91 dB (terukur pada contoh satu-rantai yang dulu ada di sini: `silence_start 40,86` di video 43 dtk). Karena itu pisahkan:

```bash
# 1) normalisasi voiceover ke file sendiri
ffmpeg -y -i "audio/voiceover.wav" -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 work/voiceover-norm.wav

# 2) rapikan musik di file sendiri: level + fade-out. Jangan beri afade=t=in —
#    musik mulai dari senyap akan terbaca sebagai keheningan tak sengaja oleh gerbang §7.
ffmpeg -y -i "audio/music.wav" -af "volume=0.40,afade=t=out:st=$FADE_ST:d=2.5" -ar 48000 work/music-norm.wav

# 3) baru gabungkan: adelay + apad + duck + amix
ffmpeg -y -framerate 30 -i work/frames/%05d.png -i work/voiceover-norm.wav -i work/music-norm.wav \
  -filter_complex "\
[1:a]adelay=1000:all=1,apad=whole_dur=$DUR,atrim=0:$DUR,asetpts=PTS-STARTPTS,asplit=2[vo1][vo2];\
[2:a]atrim=0:$DUR,asetpts=PTS-STARTPTS[bg];\
[bg][vo1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[duck];\
[duck][vo2]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,alimiter=limit=0.85:level=0[aout]" \
  -map 0:v -map "[aout]" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -r 30 -frames:v $FRAMES \
  -c:a aac -b:a 192k -ar 48000 -t $DUR \
  -movflags +faststart "output/<slug>.mp4"
```

`FADE_ST` dihitung dari durasi video, bukan dari durasi musik: `$FADE_ST` = `DUR - 2.5` (resep `awk` di atas sudah begitu). Fade harus selesai sebelum detik terakhir, tapi jangan sampai musik menyentuh nol persis di frame terakhir — sisa −25 dB di ekor masih lolos gerbang, nol persis tidak.

Catatan:
- `loudnorm` menyetaraan loudness voiceover (target I=-16 LUFS, TP=-1,5) supaya level rekaman user dan hasil TTS konsisten. Filter ini bekerja pada 192 kHz secara internal; `-ar 48000` pada langkah 1 sudah mengembalikan sample rate.
- `normalize=0` butuh ffmpeg 7.0+. Di 6.x hapus `normalize=0` dan pakai `volume=2` — hasilnya setara (terukur identik di 7.1: −18,5 dB keduanya). Jangan pasang keduanya sekaligus: `normalize=0` + `volume=2` menghasilkan max 0,0 dB alias clipping.
- Tanpa musik: lewati langkah 2, dan di langkah 3 cukup `[1:a]adelay=1000:all=1,apad=whole_dur=$DUR,atrim=0:$DUR,asetpts=PTS-STARTPTS,afade=t=out:st=<DUR-0.5>:d=0.5[aout]` (hitung `DUR-0.5` dengan `awk` seperti `FADE_ST`).
- Tanpa voiceover (draf): gunakan hanya musik, dan beri label draf.
- Kalau yang diinput video mentah dan bukan urutan gambar, tetap paksa `-r 30` dan `-frames:v $FRAMES`.
- Kalau user menentukan target durasi sendiri, ganti `DUR` dengan target itu (selama voiceover muat) dan set `MAX_DUR` minimal sebesar target itu, lalu hitung `FRAMES` dan `FADE_ST` dengan rumus yang sama.

## 7. Verifikasi file hasil ekspor

Jangan mengandalkan durasi yang tampil di penyunting atau di skrip. Ukur MP4-nya langsung:

```bash
# durasi container, codec, resolusi, fps, jumlah frame
ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,duration,nb_frames -of default=nw=1 output/<slug>.mp4

# hitung frame yang benar-benar terbaca (harus sama dengan $FRAMES)
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 output/<slug>.mp4
```

Target: container ≈ `$DUR` detik (tepat sampai tiga angka desimal), `$FRAMES` frame video, 30 fps, H.264 + AAC, resolusi sesuai rencana. Encoder AAC menambah sedikit padding sehingga durasi stream audio bisa berbeda beberapa milidetik; yang dipakai sebagai bukti adalah durasi container dan jumlah frame video. Laporkan angka sebenarnya ke user. Kalau meleset, perbaiki dan ekspor ulang, jangan dibulatkan di laporan.

Deteksi masalah yang tidak disengaja:

```bash
# frame hitam
ffmpeg -i output/<slug>.mp4 -vf blackdetect=d=0.1:pix_th=0.05 -an -f null - 2>&1 | grep black_
# frame beku — ambang n=0: hanya frame benar-benar identik yang dihitung freeze.
# JANGAN pakai n=-60dB: di grafis flat, perubahan mikro antar frame (ribuan piksel,
# max diff ~220) tetap dilaporkan sebagai freeze → false positive pada video yang jelas bergerak.
ffmpeg -i output/<slug>.mp4 -vf freezedetect=n=0:d=1.0 -an -f null - 2>&1 | grep freeze_
# keheningan tak disengaja dan level volume
ffmpeg -i output/<slug>.mp4 -af silencedetect=noise=-50dB:d=0.5 -vn -f null - 2>&1 | grep silence_
ffmpeg -i output/<slug>.mp4 -af volumedetect -vn -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

**Gerbang QC gerak:** hasil `freezedetect=n=0:d=1.0` harus kosong, kecuali jeda statis yang sengaja dan tercatat di timeline (maksimal 1 jeda, ≤1,5 dtk, di penutup). Kalau ada freeze berarti render benar-benar diam — kembali ke §5, tambahkan kamera mikro atau animasi elemen, render ulang. Lapor hasil gerbang ini ke user bersama angka durasi.

**Gerbang ekor audio:** `silencedetect` di file final harus kosong sampai detik terakhir, bukan cuma di tengah. Musik yang mati sebelum video habis terdeteksi sebagai `silence_start` di beberapa detik terakhir dan itu cacat, bukan pilihan. Penyebab paling sering: `loudnorm` dipasang inline bersama `apad` dalam satu `filter_complex` — padding jadi ikut masuk rantai loudnorm dan ekornya mati (terukur: −91 dB pada 2,1 dtk terakhir, sementara sumbernya −15 dB). Normalisasi VO ke file sendiri dulu, baru mix:

```bash
ffmpeg -y -i "audio/voiceover.wav" -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 work/voiceover-norm.wav
```

Kalau musik tetap ingin punya fade-out, buat fade di file musiknya sendiri dan pastikan ujungnya tidak menyentuh nol persis di detik terakhir.

### Dua gerbang tambahan: sinkron dan geometri

Keduanya skrip, jalan di atas frame hasil render, dan menangkap kelas cacat yang tidak terlihat saat menonton sekali jalan.

**Tulis sendiri saat dibutuhkan.** Aturannya sudah lengkap dalam prosa di bawah dan di `GUIDE.md` §2: safe area 4%, tinggi glyph dua tingkat, kontras per peran, tabrakan IoU, pola berulang. Terjemahkan ke kode mengikuti struktur data renderer-mu.

Bentuk yang saya sarankan: kumpulkan bbox setiap teks saat render, lalu periksa di akhir. Yang penting hasilnya **saran, bukan LULUS/GAGAL** — keputusan tetap milikmu.

Snippet di bawah menunjukkan **prinsipnya** (memakai API contoh `Cam`); kalau pipeline-mu beda, padanan cara menangkap teks ada di tabel berikut. Yang wajib ada di pipeline mana pun:

| Pipeline | Cara menangkap teks | Cara mengambil frame |
|---|---|---|
| Python/PIL | bungkus method gambar teks | panggil fungsi render langsung |
| HTML/Playwright | `page.evaluate` enumerasi `innerText` elemen teks | screenshot per `t` |
| Remotion/Node | koleksi `useCurrentFrame` → catat elemen di komponen | `renderStill` per `t` |
| Canvas/JS | bungkus `ctx.fillText` | `toDataURL` per `t` |

Kalau pipeline tidak bisa mencatat teks yang tergambar, gerbang sinkron tidak bisa dijalankan — dalam kasus itu ukur timing dari **tabel waktu** yang dipakai renderer (cari nilai yang memenuhi `t_teks >= t_kata`), dan katakan ke user bahwa verifikasinya lewat tabel, bukan lewat piksel.

**Gerbang sinkron.** Untuk setiap teks kunci, buktikan dua hal: teks sudah ada di `t_kata + 0,10` dan belum ada di `t_kata − 0,15` (jendela bisa disetel, yang penting asimetris — lebih baik telat 0,1 dtk daripada muncul sebelum kata). Tangkap semua teks yang tergambar dengan membungkus pemanggil teks, lalu cocokkan nama teksnya:

```python
seen = []
orig = Cam.text
def patched(self, x, y, s, size, fill, **kw):
    if kw.get("alpha", 255) > 40 and size > 20:
        seen.append(str(s))
    return orig(self, x, y, s, size, fill, **kw)
Cam.text = patched

def at(t):
    seen.clear(); render_frame(int(round(t * 30))); return list(dict.fromkeys(seen))

for t_kata, teks in checks:
    assert teks in at(t_kata + 0.10), f"telat/hilang: {teks} @ {t_kata}"
    assert teks not in at(t_kata - 0.15), f"muncul terlalu awal: {teks} @ {t_kata}"
```

Kalau gagal, perbaiki tabel waktu — jangan geser angka di dalam scene (lihat §5).

**Gerbang geometri.** Dua cek, keduanya pakai metrik font yang benar-benar dipakai, bukan tebakan:

```python
# 1) safe area: tidak ada glyph keluar 4% tepi frame (nilai sama dengan GUIDE.md §2)
bb = d.textbbox((px, py), s, font=f, anchor=anchor)
assert bb[0] > W * 0.04 and bb[2] < W * 0.96
assert bb[1] > H * 0.04 and bb[3] < H * 0.96

# 1b) keterbacaan: tinggi GLYPH, bukan ukuran font (glyph kapital ~0,75x font).
#     dua tingkat sesuai GUIDE.md §2: utama >=4%H, pendukung >=2.5%H
gh = bb[3] - bb[1]
assert gh >= H * (0.04 if is_main else 0.025), f"teks terlalu kecil: {s} ({gh}px)"

# 2) tabrakan antar teks: IoU kotak glyph
def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    return inter / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter)

assert iou(bb_a, bb_b) < 0.16

# 3) kontras: rasio WCAG, ambang diikat ke PERAN teks (GUIDE.md §2),
#    bukan ke ukuran px — teks kecil yang bergerak terbaca lebih buruk
assert ratio(fill, bg_color) >= (3.0 if is_main else 4.5), f"kontras kurang: {s}"
```

**Gerbang kontras** memakai rumus WCAG yang sama dengan `GUIDE.md` §2. Terukur pada palet yang sering dipakai: pasangan tinta-di-krem dan krem-di-gelap lolos jauh di atas 4,5:1, tapi aksen salmon muda di atas krem hanya **1,85:1** — gagal telak untuk teks apa pun. Kalau gerbang ini menolak, jangan turunkan ambangnya: ganti warnanya, atau taruh teks itu di latar gelap, atau beri panel solid di belakang.

### Gerbang ketiga: pola berulang (menandai, tidak menolak)

Gerbang ini **tidak menghakimi**. Ia hanya menunjukkan scene yang strukturnya sama, lalu kamu yang memutuskan.

```python
# untuk setiap scene, ambil sidik struktur (bukan isi):
#   posisi_massa : di mana pusat tinta berada  (kiri/tengah/kanan, atas/tengah/bawah)
#   kepadatan    : rasio piksel bertinta
#   latar        : terang / gelap
def signature(frame_rgb):
    g = np.array(frame_rgb.convert("L"))
    ink = g < 110
    if ink.sum() < 500:
        return ("kosong",)
    ys, xs = np.nonzero(ink)
    return (
        round(xs.mean() / g.shape[1], 1),   # 0.0 kiri .. 1.0 kanan
        round(ys.mean() / g.shape[0], 1),
        round(ink.mean(), 2),
        "gelap" if g.mean() < 100 else "terang",
    )

sigs = [signature(f) for f in frames_tengah_tiap_scene]
for i in range(1, len(sigs)):
    if sigs[i] == sigs[i - 1]:
        print(f"scene {i} dan {i+1} berpola sama: {sigs[i]}")
```

Kalau dua scene berurutan berpola sama, **jangan otomatis diubah**. Tulis satu kalimat di timeline:

- "motif sengaja diulang — dua scene ini memang sepasang" → biarkan
- "kebetulan, tidak ada ide lain" → ubah komposisi, kepadatan, atau skala

Pengulangan yang disengaja sering bagus dan itu sah. Yang harus ketahuan adalah pengulangan karena tidak ada keputusan. Gerbang ini memaksa keputusan itu ditulis, bukan menyeragamkan hasil.

Teks yang sama digambar dua kali di posisi sama (mis. teks di atas blok sorot) memang IoU 1,0 — itu disengaja, kecualikan pasangan identik. Jalankan keempat gerbang sebelum ekspor, bukan setelah; lebih murah render ulang satu scene daripada satu video.

Dua hal yang bikin gerbang ini salah kepikiran:
- `freezedetect` dengan `n=-60dB` (nilai default) FALSE POSITIVE di motion graphic: decoded frame di rentang "freeze" bisa berubah ribuan piksel per frame (elemen idle, dot napas) tapi filter tetap bilang freeze karena ambangnya terlalu tinggi untuk grafis flat. Selalu pakai `n=0`.
- Frame sumber bergerak tapi MP4 terdeteksi freeze di titik yang sama? Itu encoder: elemen kecil (radius <15 px, gerak <10 px/frame) di area flat besar bisa ter-quantize hilang di CRF 18+. Perbesar elemen idle atau turunkan CRF ke 16, bukan tambah gerakan baru.

`max_volume` yang menyentuh 0 dB berarti risiko clipping — dan kalau `alimiter` sudah dipasang tapi max tetap 0 dB, penyebabnya hampir pasti opsi `level` bawaan (lihat §9).

Cek visual: ekstrak frame di titik-titik kunci (awal, tiap pergantian scene, akhir) dan lihat sendiri apakah teks terbaca, ejaan benar, aset tidak terpotong, dan tidak ada elemen bertabrakan.

```bash
ffmpeg -i output/<slug>.mp4 -vf "fps=1/2,scale=640:-1" work/check/%02d.png
ffmpeg -ss $(awk -v d="$DUR" 'BEGIN{print d-0.1}') -i output/<slug>.mp4 -frames:v 1 work/check/last.png
```

## 8. Musik latar buatan sendiri

Hanya kalau user tidak menyediakan musik. Buat pad ambient sederhana dengan numpy atau `aevalsrc`/`sine` dari ffmpeg: beberapa nada akor bertumpuk dengan volume pelan, ditambah denyut ringan yang **tempo-nya cocok dengan ritme visual** (pilih sendiri; kalau ingin aksen beat, sejajarkan dengan pergantian scene). Ekspor sebagai WAV 48 kHz, lalu masukkan ke mix di atas.

Katakan terus terang ke user bahwa ini musik sintetis sederhana, bukan komposisi profesional, dan sarankan musik bebas royalti bila ingin hasil lebih kaya.

Opsional, efek suara sintetis hemat untuk transisi, misalnya whoosh:

```bash
ffmpeg -f lavfi -i "anoisesrc=d=0.4:c=pink:a=0.5" -af "afade=t=in:d=0.1,afade=t=out:st=0.2:d=0.2,volume=0.3" -ar 48000 whoosh.wav
```

Pakai maksimal beberapa kali per video, volumenya selalu di bawah voiceover, dan sebutkan ke user bahwa ini SFX sintetis.

## 9. Jebakan umum

- **VFR (variable frame rate)**: paksa CFR dengan `-r 30`. Cek `r_frame_rate` dan `avg_frame_rate` sama-sama 30/1.
- **Durasi kurang atau lebih satu frame**: biasanya karena jumlah frame yang dirender tidak sama dengan `DUR × 30`. Hitung ulang sebelum encode.
- **Audio lebih panjang dari video** (atau sebaliknya): pakai `apad=whole_dur=$DUR` dan `atrim=0:$DUR` seperti di contoh, plus `-t $DUR`.
- **Font tidak ditemukan**: cek `fc-list`, atau unduh lewat `npm`, jangan diam-diam jatuh ke font bawaan yang jelek.
- **Teks Bahasa Indonesia terpotong di tepi**: ukur lebar teks dengan fungsi pengukur font, bukan menebak.
- **File sangat besar**: naikkan CRF (misalnya 20–22), jangan menurunkan resolusi.
- **`alimiter` dipasang tapi `max_volume` tetap 0 dB**: opsi `level` bawaan alimiter adalah 1 (auto-level) — setelah membatasi, sinyal dinormalisasi BALIK ke 0 dBFS. Wajib `alimiter=limit=0.85:level=0`. Terbukti: `limit=0.79` saja tetap menghasilkan max 0,0 dB; dengan `level=0` hasilnya -1,3 dB.
- **`amix` + `volume` — jangan pakai keduanya sekaligus.** Diukur di ffmpeg 7.1 dengan VO hasil `loudnorm` (−17,0 dB mean, −1,5 max): `amix` default `normalize=1` → −24,5 dB; `amix` default + `volume=2` → −18,5 dB; `amix normalize=0` → −18,5 dB (**identik**); `normalize=0` + `volume=2` → −12,5 dB, max **0,0 dB (clipping)**.

  Kesimpulannya: `volume=2` dengan `normalize` default setara dengan `normalize=0`, jadi contoh di §6 aman di 6.x maupun 7.x. Bahayanya justru menggabungkan keduanya. Pilih satu, lalu ukur dengan `volumedetect` — jangan percaya rumus, karena perilaku default `amix` berubah antar versi. Kalau `max_volume` menyentuh 0,0 dB padahal `alimiter` sudah dipasang, periksa apakah `volume` dan `normalize=0` terpasang bersamaan, lalu cek opsi `level` alimiter (lihat butir di atas).
- **`loudnorm` inline + `apad` = ekor audio mati**: jangan campur keduanya dalam satu `filter_complex`. Normalisasi VO ke file terpisah lebih dulu (resep tiga langkah di §6, gerbang di §7). Terukur: satu rantai → `silence_start 40,86` di video 43 dtk, ekor −91 dB; tiga langkah → ekor −25 s/d −33 dB, `silencedetect` kosong.
- **`afade=t=in` di awal musik kena gerbang ekor audio**: musik yang mulai dari senyap terbaca sebagai keheningan tak sengaja (terukur: `silence_start 0`, durasi 0,53 dtk). Biarkan musik masuk di level penuh, fade hanya di akhir.
- **`textbbox` dengan `anchor` tidak sama dengan bentuk glyph**: melihat bb[1]/bb[3] sebagai simetris terhadap titik anchor akan salah untuk angka dan teks kapital. Selalu hitung selisih pusat bbox terhadap titik anchor sebelum menempatkan di dalam bentuk (lihat GUIDE.md §2).
- **Elemen idle kecil kena quantize encoder**: dot/particle radius <15 px yang cuma berdenyut di area flat besar bisa hilang setelah encode (CRF 18+), sehingga frame decoded jadi identik → freeze nyata di MP4 padahal renderer menggambar gerakan. Perbesar elemen (radius ≥14 px, amplitudo geser ≥10 px), dan gerak posisinya, bukan cuma radius-only (perubahan radius lingkaran solid tanpa antialias sering tidak mengubah piksel mana pun).

## 10. Bersih-bersih setelah serah terima

`work/` berisi semua berkas antara: `frames/`, `ref/`, `check/`, audio hasil penyetaraan, dan JSON timing. Ukurannya bisa sampai ratusan megabita dan tidak dibutuhkan user. Setelah video terverifikasi dan diserahkan, hapus seluruh `work/`; simpan hanya `script.txt`, `render.py`, `audio/`, `assets/`, dan `output/`. Sebutkan di pesan serah terima bahwa berkas antara sudah dibersihkan.
