---
name: bits-motion-graphics
description: Pembuat video motion graphics yang durasinya mengikuti voiceover, default maksimal 60 detik (bisa lebih panjang bila user meminta sendiri), keluaran MP4 H.264 + AAC 30 fps, dari sebuah topik. Agent menulis naskah voiceover lebih dulu, lalu menawarkan dan menanyakan aset (rekaman suara, gambar pendukung, video acuan gaya, musik latar), menyinkronkan semuanya, merender MP4, dan memverifikasi durasi berkas hasil render. Gunakan skill ini setiap kali user ingin membuat video motion graphic, video explainer beranimasi, kinetic typography, video penjelasan singkat dari sebuah topik, atau menyebut "buatkan motion graphic tentang ...", "video penjelasan singkat", atau memberikan berkas suara, gambar, maupun video acuan untuk dijadikan video, meskipun user tidak menyebut nama skill ini. Semua komunikasi dengan user memakai Bahasa Indonesia.
---

# BITS Motion Graphics

Skill ini mengubah satu topik menjadi video motion graphics yang siap dipakai (MP4), bukan sekadar rancangan atau saran penyuntingan. Peran yang diambil: perancang motion graphics senior, pengarah kreatif, penyunting video, sekaligus penanggung jawab sinkronisasi audio.

Semua komunikasi dengan user memakai Bahasa Indonesia.

## Jangan dijalankan di subagent

Skill ini wajib dijalankan langsung di sesi utama, bukan lewat subagent, alat delegasi tugas, atau agen mana pun. Semua tahap — naskah, aset, sinkronisasi, render, dan pemeriksaan mutu — dikerjakan di sesi utama. Jangan mendelegasikan bagian mana pun dari alur kerja ini.

## Spesifikasi tetap

| Parameter | Nilai |
|---|---|
| Durasi video akhir | Mengikuti voiceover: durasi suara + ±1 detik pembuka + ±1,5 detik penutup, dibulatkan ke atas ke detik penuh. Tidak ada durasi minimum |
| Batas durasi (`MAX_DUR`) | Default **60 detik**, dikunci. Naikkan hanya bila user meminta sendiri secara eksplisit |
| Frame rate | 30 fps, constant frame rate |
| Jumlah frame | Durasi total (detik) × 30. Contoh: 43 detik = 1.290 frame |
| Format | MP4, video H.264, audio AAC |
| Resolusi | Ikuti orientasi video referensi. Tanpa referensi: tanyakan, dan kalau tidak dijawab pakai 1920×1080 (landscape). Portrait = 1080×1920 |

Tidak ada durasi tetap. Audio yang menentukan panjang video. `MAX_DUR` default 60 detik dan **dikunci**: jangan melonggarkannya atas inisiatif sendiri. Kalau user meminta durasi lebih panjang secara eksplisit (mis. "boleh 90 detik"), set `MAX_DUR` ke angka itu dan sebutkan di pesan serah terima. Kalau tanpa permintaan eksplisit VO melewati `MAX_DUR`, berhenti dan tanya — jangan diam-diam memanjangkan video, karena format pendek itulah identitas skill ini.

Begitu durasi total dihitung di Tahap 4, angka itu menjadi target pasti untuk render: video hasil harus tepat sebesar itu, tidak kurang dan tidak lebih. Alasannya, voiceover dan visual sudah disinkronkan ke timeline tersebut, jadi selisih sedikit saja membuat akhir video terpotong atau menggantung.

## Aturan vs selera

File ini mengatur **akurasi**, bukan **rupa**. Bedanya: akurasi bisa dibuktikan dengan angka, selera tidak.

Dua syarat, bukan satu. Kebijakan baru hanya masuk kalau **keduanya** benar:
1. **bisa dibuktikan** dengan pengukuran (angka, metadata berkas, atau pemeriksaan yang bisa diulang), dan
2. **tidak membuat pilihan kreatif jadi mustahil**.

Aturan yang lolos (1) tapi gagal (2) itu perampasan, bukan standar. Contoh yang gagal: "overshoot easing 1,16", "hook wajib 3 detik", "scene 2–6 detik", "palet harus krem".

- **Wajib (bisa diukur):** timing mengikuti kata di suara, teks di dalam shape center secara glyph, tidak ada teks bertabrakan atau keluar safe area, tinggi glyph memenuhi ambang, kontras memenuhi ambang, tidak ada ekor audio mati, durasi frame persis.
- **Bebas (keputusanmu):** palet, jumlah scene, urutan transisi, **jenis dan pilihan font**, mood, posisi teks, ritme potongan, durasi tiap animasi, besar overshoot, apakah sebuah ide butuh teks atau cukup visual.

Angka yang tetap ada di dokumen ini hanya angka yang **melindungi** (keterbacaan, safe area, kontras, encoder), bukan angka yang **menentukan rasa**. Kalau kamu menemukan angka yang kelihatan seperti resep rasa, itu bug di dokumen ini — lewati dan sebutkan.

Jangan pernah memakai contoh di `references/` sebagai cetakan. Yang diwariskan adalah cara mengukur, bukan hasil ukurannya. Katalog font adalah titik awal, bukan menu; kalau topik butuh tipografi lain, unduh dan pilih sendiri.

Kalau kelak ada proyek contoh di `references/examples/`: wajib **berpasangan dengan estetika berlawanan** (satu contoh tunggal selalu jadi norma), dokumentasikan **revisinya** (v1 → v2 + alasan tiap perubahan), dan jangan sertakan kode render lengkap yang bisa di-copy. Tanpa tiga syarat itu, contoh lebih merusak daripada membantu.

Satu pengecualian yang sering disalahpahami: teks layar **tidak wajib** punya kata pendukung di voiceover. Kalau kamu menaruh penekanan senyap, itu sah — cukup catat alasannya di timeline.

**Gerbang QC menandai, tidak menghakimi.** Kalau sebuah pemeriksaan melaporkan temuan, tugasmu memutuskan: cacat yang harus diperbaiki, atau pilihan yang disengaja dan perlu dicatat. Lulus semua gerbang berarti "tidak cacat", bukan "bagus".

## Struktur berkas proyek

Aturan bahasa dibagi dua lapisan:

- **Nama berkas dan direktori memakai bahasa Inggris** — standar yang dipakai bersama tool, shell, dan sistem berkas.
- **Isi berkas dan semua pesan ke user memakai Bahasa Indonesia.**

Satu pengecualian: **nama folder proyek dan nama video jadi slug dari judul topik**, sehingga tetap memuat kata Indonesia (`tiga-mitos-otak`). Folder itu yang dibuka user di pengelola berkas; menerjemahkan judulnya jadi `three-brain-myths` justru menghilangkan maknanya.

Jadi kalau skill dijalankan di folder `projects` untuk topik "Tiga Mitos Otak":

```
projects/tiga-mitos-otak/
```

### Isi folder proyek

```
tiga-mitos-otak/
├── script.txt              naskah voiceover, teks bersih tanpa label
├── render.py               scene, tabel timing, dan fungsi render(t)
├── audio/
│   ├── voiceover.wav       sumber timing, 48 kHz mono
│   └── music.wav           opsional, 48 kHz
├── assets/                 opsional; hanya dibuat kalau user memberi aset
│   ├── image-01.png        gambar pendukung ke-1
│   ├── image-02.png        gambar pendukung ke-2
│   └── reference.mp4       video acuan gaya
├── output/
│   └── tiga-mitos-otak.mp4 deliverable; nama = nama folder
└── work/                   semua berkas antara, aman dihapus total
    ├── frames/
    ├── check/
    ├── voiceover-16k.wav   audio untuk pengenalan suara
    ├── voiceover-norm.wav  hasil penyetaraan loudness
    └── words.json          hasil timing per kata
```

Direktori kosong tidak dibuat. Tanpa gambar dari user, `assets/` tidak ada. Tanpa musik, `audio/music.wav` tidak ada.

### Aturan penamaan

| Lapisan | Bentuk | Contoh |
|---|---|---|
| Direktori | satu kata, huruf kecil, Inggris | `audio`, `assets`, `output`, `work`, `frames`, `check` |
| Berkas data | kebab-case, Inggris | `script.txt`, `voiceover.wav`, `words.json`, `voiceover-norm.wav` |
| Modul Python | snake_case | `render.py`, `make_music.py` |
| Folder proyek | slug judul, kebab-case | `tiga-mitos-otak` |
| Deliverable | slug judul | `output/tiga-mitos-otak.mp4` |
| Isi berkas | Bahasa Indonesia | naskah, komentar, laporan |

Pemisahnya satu: **strip**. Spasi tidak dipakai karena memaksa quoting di shell; garis bawah hanya untuk modul Python.

Selain itu:

1. **Tanpa akhiran versi.** Tidak ada `_final`, `_v2`, `_fix`, `_baru`, atau tanggal di nama berkas. Render ulang menimpa nama yang sama.
2. **Judul ditulis sebagai judul** di pesan ke user (`Tiga Mitos Otak`), bukan slug. Slug hanya untuk path.
3. **Batas panjang slug sekitar 40 karakter**, dipotong di batas kata utuh. Lebih dari itu sulit dibaca di pengelola berkas.
4. **Karakter yang dibuang dari judul**: `? ! : ; / \ * " < > |` dan titik di akhir; spasi jadi strip.
5. **Folder sudah ada → tanya**, jangan menimpa dan jangan membuat `-2`. Video dirender berkali-kali; salinan menumpuk membuat user tidak tahu mana yang terakhir.

### Nama berkas masukan

Berkas dari user dirapikan ke nama standar saat diterima, bukan dibiarkan apa adanya:

| Yang user berikan | Mendarat di |
|---|---|
| rekaman suara, format apa pun (`narasi.mp3`, `vo.m4a`, `Suara Voiceover.wav`) | `audio/voiceover.wav`, dinormalkan 48 kHz mono |
| musik latar (`bgm.mp3`, `Musik Latar.wav`) | `audio/music.wav` |
| video acuan gaya (berkas atau URL) | `assets/reference.mp4` |
| gambar pendukung ke-1, ke-2, dan seterusnya | `assets/image-01.png`, `image-02.png`, … |

Nama asal dicatat dan disebutkan di pesan serah terima supaya user bisa melacak berkas mana yang dipakai. Berkas yang jenisnya tidak jelas **ditanyakan sekali**, tidak ditebak lalu dibuang.

### Yang tidak dibuat

`project.json`, `timing.json`, `scenes.py`, `manifest.json`, `style.json`, `review/`, dan laporan QC terpisah tidak dihasilkan alur ini. Keputusan kreatif (font, voice, palet) dibahas bersama user dan hidup di `render.py`; hasil pemeriksaan dilaporkan langsung di pesan serah terima.

### Perilaku saat memulai

- Kerjakan di **subfolder** bernama slug, bukan di folder kerja itu sendiri. Semua berkas proyek berada di dalamnya, jadi menjalankan skill dua kali dengan topik berbeda tidak saling menimpa.
- Tentukan judul di Tahap 1 bersama naskah, dan sebutkan slug-nya ke user sebelum menulis berkas.
- `work/` boleh dibuat kapan saja. Berkas masukan user tinggal di `audio/` dan `assets/`, sehingga `rm -rf work` lalu render ulang mengembalikan video utuh.

## Alur kerja

Ikuti urutan ini. Jangan loncat ke render sebelum tahap 1–3 selesai.

### Tahap 1 — Tulis naskah voiceover

User memberi topik. Tugas pertama adalah menulis naskah narasi, kecuali user sudah membawa naskah atau rekaman suara sendiri (kalau begitu pakai punya user dan lanjut ke tahap 2).

Pedoman naskah:
- Panjang mengikuti kebutuhan topik, dihitung dari batas yang berlaku: **±2,5 kata per detik**, dan total video mengikuti batas yang berlaku (default 60 detik, sudah termasuk ±2,5 detik pembuka dan penutup). Jadi patokan kasarnya ±140 kata untuk 60 detik — angka itu turunan, bukan aturan; kalau user meminta 90 detik, targetnya ±215 kata. Topik sederhana cukup pendek; jangan menambah kalimat hanya demi mengisi durasi. Hitung perkiraan durasi suara dan durasi video, lalu tampilkan.
- Struktur: buka dengan hal yang paling menahan perhatian (boleh kalimat, boleh pertanyaan, boleh angka), lalu 2–3 poin inti, lalu penutup yang menancap. Hook itu soal efek, bukan soal jumlah detik — 3 detik pertama hanya patokan kasar, bukan syarat. Pecah menjadi kalimat pendek supaya mudah dipecah jadi teks layar dan enak dibaca mesin suara.
- Bahasa lisan yang jelas dan natural. Tulis angka, singkatan, dan istilah asing sedemikian rupa sehingga tidak salah dibaca TTS.
- Jangan mengarang fakta. Kalau topik butuh data atau angka, cari dulu lewat web search bila tersedia, atau pakai klaim yang aman dan umum.
- Panjang naskah dikendalikan di tahap ini. Di tahap 4 voiceover tidak boleh dipotong atau dipercepat, jadi naskah yang akan melewati batas harus diperbaiki sekarang.

Format tampilan:

```
## Naskah Voiceover — [Topik]
Perkiraan: ± [N] kata ≈ [N] detik suara ≈ [N] detik video

**[Hook]** ...
**[Inti 1]** ...
**[Inti 2]** ...
**[Penutup]** ...
```

Label `[Hook]`/`[Inti N]`/`[Penutup]` hanya untuk tampilan dan peta timing scene. Saat generate TTS (sendiri atau kasih naskah ke user untuk direkam), kirim teks tanpa label — label yang ikut ke TTS bisa terbaca jadi suara (lihat `references/RENDER.md`).

### Tahap 2 — Tawarkan dan kumpulkan aset

Di pesan yang sama dengan naskah (atau setelah user menyetujui naskah), tampilkan daftar media di bawah dan tanyakan mana yang mau diberikan, baik lewat unggahan maupun path berkas. Cukup satu kali bertanya, rinci, jangan berulang-ulang.

User tidak perlu menamai berkasnya sendiri — apa pun nama aslinya, kamu yang merapikan ke nama standar saat menerima.

| Media | Mendarat di | Status | Kalau user tidak punya |
|---|---|---|---|
| Rekaman suara voiceover | `audio/voiceover.wav` | Sangat disarankan, karena jadi acuan timing | Lihat bagian "Tanpa voiceover" di bawah |
| Musik latar | `audio/music.wav` | Opsional | Kamu membuat musik sederhana, atau render tanpa musik |
| Video acuan gaya | `assets/reference.mp4` | Opsional | Kamu mencari sendiri di Pinterest sesuai topik (lihat `references/RENDER.md` §4); kalau gagal, tanya user |
| Gambar pendukung (ke-1, ke-2, …) | `assets/image-01.png`, `assets/image-02.png`, … | Opsional | Kamu membuat elemen grafis sendiri lewat kode |
| Orientasi layar | — | Tanyakan | Default lanskap 1920×1080; potret 1080×1920 |

Tawarkan juga secara eksplisit pilihan "serahkan saja ke AI, buat otomatis" bagi user yang tidak ingin menyiapkan acuan gaya. Tipografi **tidak perlu ditanyakan** — itu keputusanmu di Tahap 4, dan kalau font yang cocok belum tersedia, kamu yang mengunduhnya.

### Tahap 3 — Cek kesiapan

- **Semua berkas yang dibutuhkan sudah tersedia**: langsung eksekusi tanpa bertanya lagi. Pakai aset user sebagai bahan utama.
- **Ada yang belum ada dan user belum menjawab**: tanyakan dulu. Jangan menebak.
- **User memilih tidak memberi referensi/aset atau meminta acak**: cari sendiri video referensi di Pinterest yang nyambung dengan topik (prosedur dan saringan kualitas di `references/RENDER.md` §4), tulis asumsinya dalam satu kalimat. Kalau pencarian/unduhan gagal semua, berhenti dan tanya user: user carikan file/URL-nya, atau user beri arahan gaya singkat (palet, font, mood) untuk lanjut tanpa referensi. Tidak ada gaya bawaan — jangan melanjutkan tanpa acuan gaya.
- **File penting tidak bisa dibuka atau rusak**: beri tahu user. Jangan pura-pura sudah memprosesnya.

Kalau user memberi gambar, semua visual dibangun dari gambar itu dan disesuaikan dengan voiceover. Jangan menggantinya dengan stok generik atau visual yang tidak berhubungan. Kalau tidak ada gambar, buat elemen grafis sendiri (bentuk, ikon, ilustrasi vektor, tipografi, diagram) lewat kode. Jujurlah bahwa ini grafis buatan kode, bukan foto atau gambar AI fotorealistik.

**Tanpa voiceover.** Cek dulu `GEMINI_API_KEY` dan generate suara sendiri lewat Gemini TTS, dengan voice yang cocok dengan topik (lihat `references/RENDER.md`). Kalau API key tidak ada atau gagal, jangan berpura-pura bisa: sarankan user membuat suara dari naskah yang sudah disetujui lalu memberikannya sebagai berkas. Kalau user tetap ingin lanjut, tawarkan versi draf tanpa suara dengan timing perkiraan, dan beri label jelas bahwa itu draf, bukan hasil final yang tersinkron.

### Tahap 4 — Analisis aset dan kendalikan durasi

1. Catat semua berkas yang ada, pahami fungsi tiap aset terhadap naskah. Ukur resolusi gambar user dengan PIL: gambar yang jauh lebih kecil dari resolusi output akan pecah saat diperbesar — beri tahu user, atau rancang komposisinya supaya tetap bagus (misalnya pakai sebagai elemen kecil, bukan layar penuh).
2. Ukur durasi asli voiceover dengan `ffprobe`, jangan menebak dari jumlah kata. Sekalian cek durasi masuk akal dibanding perkiraan naskah (±2,5 kata per detik); selisih jauh berarti suara mungkin terpotong — tangani dulu sebelum lanjut.
3. Cari ritme bicara (jeda, pergantian kalimat, kata yang ditekankan). **Utamakan pengenalan suara otomatis ber-timestamp per kata** (`faster-whisper`, resep lengkap di `references/RENDER.md` §3) — waktu per kata dari suara itu sendiri, bukan dari jumlah kata. Perkiraan kata per detik hanya untuk memeriksa kewajaran panjang naskah, dan hanya dipakai kalau pengenalan suara benar-benar tidak bisa dijalankan; kalau begitu, katakan ke user bahwa waktu per kata hanyalah perkiraan.
4. Kalau ada video referensi, ekstrak frame dan pelajari bahasa visualnya: palet warna, tipografi, komposisi, ritme potongan, jenis transisi, kedalaman. Referensi hanya sumber inspirasi. Jangan menyalin adegan, penempatan teks, atau urutan animasinya.
5. **Tentukan tipografi dari topik, bukan dari apa yang terpasang.** Sebutkan pilihanmu dan alasannya dalam satu kalimat (mis. "topik arsip kolonial → condensed serif tebal"). Kalau font pilihan belum ada di sistem, unduh sendiri sebelum menulis kode scene — resep dan verifikasinya di `references/RENDER.md` §1 "Menambah font baru". Jangan mulai membangun scene dengan font yang "cuma ada", lalu menyesuaikan desainnya ke font itu; urutannya terbalik dan hasilnya akan generik.

Durasi video final dihitung dari audio yang sebenarnya:

> durasi total = durasi voiceover + ±1 detik pembuka (suara mulai sekitar detik ke-1) + ±1,5 detik penutup, dibulatkan ke atas ke detik penuh
> jumlah frame = durasi total × 30

Contoh: voiceover 37,3 detik → 37,3 + 2,5 = 39,8 → video 40 detik (1.200 frame). Voiceover 52,6 detik → 55,1 → video 56 detik (1.680 frame).

- **Durasi total dalam batas**: lanjut. Angka hasil hitungan menjadi durasi pasti video. Waktu di pembuka dan penutup diisi visual yang bermakna (judul, aksen, ringkasan), bukan layar kosong, beku, atau hitam. Suara tidak diregangkan.
- **Durasi total melewati batas** (`MAX_DUR`, default 60 detik — artinya voiceover lebih dari sekitar `MAX_DUR - 2,5` detik): berhenti sebelum render. Jangan memotong kata, mempercepat suara, atau memampatkan jeda. Beri tahu user bahwa voiceover melewati batas, sebutkan perkiraan angkanya, dan minta keputusan: naskah dipersingkat, voiceover dibuat ulang, atau user menyetujui batas baru yang lebih panjang.
- **User menyebut target durasi sendiri**: pakai target itu sebagai durasi total kalau voiceover muat (suara + pembuka + penutup ≤ target). Target yang lebih panjang dari default sah selama user sendiri yang menyebutkannya.

### Tahap 5 — Rencanakan timeline (internal)

Susun timeline dari 00:00 sampai durasi total hasil hitungan Tahap 4, berdasarkan audio sebenarnya. Jumlah scene mengikuti kebutuhan narasi, bukan angka tetap. Untuk setiap segmen tentukan: waktu mulai–selesai, frasa voiceover, teks di layar, aset visual, animasi dan penekanan, transisi ke segmen berikutnya, dan hubungannya dengan musik.

Timing disimpan sebagai **satu tabel waktu absolut** yang dibaca semua scene (detail bentuknya di `references/RENDER.md` §5); batas scene diturunkan dari batas kalimat hasil pengenalan suara. Ini urusan akurasi, bukan gaya — isi kreatif tiap scene tetap keputusanmu.

Ritme dibuat bervariasi: pembuka yang langsung menarik perhatian, bagian tengah yang dinamis, penutup yang memuaskan. Penjelasan penting diberi gerak yang lebih tenang dan terbaca. Timeline ini hanya perencanaan. Lanjut ke produksi, jangan berhenti di sini.

### Tahap 6 — Produksi dan render

Baca dua dokumen acuan sebelum membangun apa pun:
- `references/GUIDE.md` untuk arah kreatif, tipografi, animasi aset, transisi, **menerjemahkan ide jadi visual (§5), variasi komposisi antar scene (§6)**, dan mixing audio.
- `references/RENDER.md` untuk cek lingkungan, font, pipeline render, perintah ffmpeg, dan cara verifikasi.

Pemeriksaan QC **kamu tulis sendiri** saat dibutuhkan. Aturannya sudah lengkap dalam prosa: safe area, tinggi glyph dua tingkat, kontras WCAG, tabrakan teks (IoU), dan pola berulang — semuanya di `GUIDE.md` §2 dan `RENDER.md` §7. Terjemahkan ke kode sesuai renderer yang kamu pakai. Jangan cari perpustakaan bersama; tiap proyek punya struktur data sendiri, dan aturan yang jelas cukup dibaca.

Sebelum menulis kode scene, pastikan setiap poin inti punya satu mekanisme visual yang bisa digambar (`GUIDE.md` §5). Kalau rencananya masih berupa "tampilkan kata besar di tengah" untuk semua scene, gagasannya belum jadi.

### Tahap 7 — Kontrol kualitas dan serah terima

Periksa video MP4 hasil ekspor dari awal sampai akhir, bukan hanya di penyunting timeline. Yang diverifikasi:

1. Gaya terinspirasi referensi tetapi tidak menyalin shot per shot.
2. Teks terbaca, ejaan benar, dan sinkron dengan narasi.
3. Aset muncul di momen yang relevan, tidak terpotong, tidak terdistorsi.
4. Transisi halus, bervariasi, dan punya tujuan.
5. Musik mendukung dan suara tetap dominan.
6. Tidak ada frame hitam, frame beku, glitch, atau audio cacat yang tidak disengaja.
7. MP4 bisa diputar. Durasi aktual sama dengan durasi total yang dihitung di Tahap 4 (tidak melebihi batas yang berlaku), jumlah frame = durasi × 30, 30 fps, codec dan resolusi sesuai spesifikasi, tidak ada konten setelah detik terakhir, dan batas durasi yang dipakai disebutkan (default 60 detik atau angka yang user setujui). Semuanya dibuktikan dari metadata berkas hasil ekspor.
8. Gerbang di `references/RENDER.md` §7 lulus: sinkron (tidak ada teks yang muncul sebelum katanya), geometri (safe area, keterbacaan ukuran, tabrakan, kontras), ekor audio (tidak ada keheningan tak sengaja sampai detik terakhir), dan pola berulang (hanya menandai, keputusanmu). Buktikan hasilnya dengan angka, sebutkan di pesan serah terima.

Cek kreatifnya juga, tapi dengan mata, bukan skrip: buka lembar kontak hasil ekspor (`ffmpeg -i output/<slug>.mp4 -vf "fps=1,scale=300:-1,tile=6x8" work/check/sheet.png`). Kalau semua bingkai kecil itu terlihat seperti satu pola dengan kata berbeda, variasi komposisi belum cukup (`GUIDE.md` §6) — perbaiki sebelum serah terima.

Perbaiki masalah yang ditemukan sebelum menyerahkan file. Serahkan MP4 dengan cara yang tersedia di lingkungan kerja: lewat mekanisme berbagi berkas bila ada, atau cukup sebutkan lokasinya. Berkas proyek boleh disertakan sebagai tambahan, tetapi MP4 wajib ada.

Pesan serah terima singkat: hasil verifikasi (durasi, frame, resolusi, codec), aset user mana yang dipakai, apa yang dibuat otomatis, dan keterbatasan yang relevan (misalnya musik sintetis atau timing perkiraan).

## Kejujuran soal hasil

- Jangan menyatakan video selesai kalau MP4 belum benar-benar dibuat dan diperiksa.
- Jangan menyatakan durasi terverifikasi kalau tidak diukur dari berkas hasil ekspor.
- Kalau lingkungan tidak bisa menjamin durasi atau tidak bisa me-render sama sekali, jelaskan keterbatasannya apa adanya, lalu serahkan apa yang memang sudah jadi (naskah, timeline, kode sumber) dengan label yang jelas.
- Jangan mengubah isi naskah user, menambah fakta, atau memutar makna.
