---
name: bits-motion-graphics
description: Pembuat video explainer motion graphics yang durasinya menyesuaikan voiceover, default maksimal 60 detik (bisa lebih panjang bila user meminta sendiri), MP4 H.264 + AAC 30 fps, dari sebuah topik. Agent menulis naskah voiceover lebih dulu, lalu menawarkan dan menanyakan aset (suara voiceover, gambar pendukung, video referensi, musik latar), menyinkronkan semuanya, me-render MP4, dan memverifikasi durasi file hasil render. Gunakan skill ini setiap kali user ingin membuat video motion graphic, video explainer animasi, kinetic typography, video penjelasan singkat dari sebuah topik, atau menyebut "buatkan motion graphic tentang ...", "video penjelasan singkat", atau mengunggah file bernama "Referensi - Motion Graphic", "gambar1/gambar2", "Suara Voiceover" untuk dijadikan video, meskipun user tidak menyebut nama skill ini. Seluruh komunikasi dengan user memakai Bahasa Indonesia.
---

# BITS Motion Graphics

Skill ini mengubah satu topik menjadi video explainer motion graphics yang sudah jadi (MP4), bukan sekadar storyboard atau saran editing. Perannya: motion graphics designer senior, creative director, video editor, sekaligus spesialis sinkronisasi audio.

Semua komunikasi dengan user memakai Bahasa Indonesia.

## Jangan dijalankan di subagent

Skill ini wajib dijalankan langsung di sesi utama (main session), bukan lewat subagent, task tool, atau agent apa pun. Semua tahap — naskah, aset, sinkronisasi, render, dan QC — dikerjakan di sesi utama. Jangan mendelegasikan bagian mana pun dari alur kerja ini.

## Spesifikasi tetap

| Parameter | Nilai |
|---|---|
| Durasi file akhir | Mengikuti voiceover: durasi suara + ±1 detik pembuka + ±1,5 detik penutup, dibulatkan ke atas ke detik penuh. Tidak ada durasi minimum |
| Batas durasi (`MAX_DUR`) | Default **60 detik**, dikunci. Naikkan hanya bila user meminta sendiri secara eksplisit |
| Frame rate | 30 fps, constant frame rate |
| Jumlah frame | Durasi total (detik) × 30. Contoh: 43 detik = 1.290 frame |
| Format | MP4, video H.264, audio AAC |
| Resolusi | Ikuti orientasi video referensi. Tanpa referensi: tanyakan, dan kalau tidak dijawab pakai 1920×1080 (landscape). Portrait = 1080×1920 |

Tidak ada durasi tetap. Audio yang menentukan panjang video. `MAX_DUR` default 60 detik dan **dikunci**: jangan melonggarkannya atas inisiatif sendiri. Kalau user meminta durasi lebih panjang secara eksplisit (mis. "boleh 90 detik"), set `MAX_DUR` ke angka itu dan sebutkan di pesan serah terima. Kalau tanpa permintaan eksplisit VO melewati `MAX_DUR`, berhenti dan tanya — jangan diam-diam memanjangkan video, karena format pendek itulah identitas skill ini.

Begitu durasi total dihitung di Tahap 4, angka itu menjadi target pasti untuk render: file hasil harus tepat sebesar itu, tidak kurang dan tidak lebih. Alasannya, voiceover dan visual sudah disinkronkan ke timeline tersebut, jadi selisih sedikit saja membuat akhir video terpotong atau menggantung.

## Aturan vs selera

File ini mengatur **akurasi**, bukan **rupa**. Bedanya: aturan bisa dicek skrip, selera tidak.

Dua syarat, bukan satu. Kebijakan baru hanya masuk kalau **keduanya** benar:
1. **bisa dicek skrip**, dan
2. **tidak membuat pilihan kreatif jadi mustahil**.

Aturan yang lolos (1) tapi gagal (2) itu perampasan, bukan standar. Contoh yang gagal: "overshoot easing 1,16", "hook wajib 3 detik", "scene 2–6 detik", "palet harus krem".

- **Wajib (bisa diukur):** timing mengikuti kata di suara, teks di dalam shape center secara glyph, tidak ada teks bertabrakan atau keluar safe area, tinggi glyph memenuhi ambang, kontras memenuhi ambang, tidak ada ekor audio mati, durasi frame persis.
- **Bebas (keputusanmu):** palet, jumlah scene, urutan transisi, **jenis dan pilihan font**, mood, posisi teks, ritme potongan, durasi tiap animasi, besar overshoot, apakah sebuah ide butuh teks atau cukup visual.

Angka yang tetap ada di file ini hanya angka yang **melindungi** (keterbacaan, safe area, kontras, encoder), bukan angka yang **menentukan rasa**. Kalau kamu menemukan angka yang kelihatan seperti resep rasa, itu bug di dokumen ini — lewati dan sebutkan.

Jangan pernah memakai contoh di `references/` sebagai cetakan. Yang diwariskan adalah cara mengukur, bukan hasil ukurannya. Katalog font adalah titik awal, bukan menu; kalau topik butuh tipografi lain, unduh dan pilih sendiri.

Kalau kelak ada proyek contoh di `references/examples/`: wajib **berpasangan dengan estetika berlawanan** (satu contoh tunggal selalu jadi norma), dokumentasikan **revisinya** (v1 → v2 + alasan tiap perubahan), dan jangan sertakan kode render lengkap yang bisa di-copy. Tanpa tiga syarat itu, contoh lebih merusak daripada membantu.

Satu pengecualian yang sering disalahpahami: teks layar **tidak wajib** punya kata pendukung di voiceover. Kalau kamu menaruh penekanan senyap, itu sah — cukup catat alasannya di timeline.

**Gerbang QC menandai, tidak menghakimi.** Kalau sebuah fungsi QC melaporkan temuan, tugasmu memutuskan: cacat yang harus diperbaiki, atau pilihan yang disengaja dan perlu dicatat. Lulus semua gerbang berarti "tidak cacat", bukan "bagus".

## Alur kerja

Ikuti urutan ini. Jangan loncat ke render sebelum tahap 1–3 selesai.

### Tahap 1 — Tulis naskah voiceover

User memberi topik. Tugas pertama adalah menulis naskah narasi, kecuali user sudah membawa naskah atau file voiceover sendiri (kalau begitu pakai punya user dan lanjut ke tahap 2).

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

Di pesan yang sama dengan naskah (atau setelah user menyetujui naskah), tampilkan daftar media di bawah dan tanyakan mana yang mau diberikan (di-upload atau lewat path file). Cukup satu kali bertanya, rinci, jangan berulang-ulang.

| Media | Nama file yang disarankan | Status | Kalau user tidak punya |
|---|---|---|---|
| Suara voiceover (rekaman sendiri atau suara AI dari naskah yang sudah disetujui) | `Suara Voiceover` | Sangat disarankan, karena jadi acuan timing | Lihat bagian "Tanpa voiceover" di bawah |
| Gambar, ilustrasi, ikon pendukung | `gambar1`, `gambar2`, `gambar3`, dst. | Opsional | AI membuat elemen grafis motion graphic sendiri |
| Video referensi gaya | `Referensi - Motion Graphic` | Opsional | AI cari sendiri di Pinterest sesuai topik (lihat `references/RENDER.md` §4); kalau gagal, tanya user |
| Musik latar | `Musik Latar` | Opsional | AI membuat musik latar sederhana, atau render tanpa musik |
| Orientasi layar | — | Tanyakan | Default landscape 1920×1080 |

Tawarkan juga secara eksplisit opsi "serahkan saja ke AI, buat acak/otomatis" untuk user yang tidak mau repot menyiapkan referensi. Tipografi **tidak perlu ditanyakan** — itu keputusanmu di Tahap 4, dan kalau font yang cocok belum ada, kamu yang mengunduhnya.

### Tahap 3 — Cek kesiapan

- **Semua file yang dibutuhkan sudah ada (di-upload atau path-nya diberikan)**: langsung eksekusi tanpa bertanya lagi. Pakai aset user sebagai bahan utama.
- **Ada yang belum ada dan user belum menjawab**: tanyakan dulu. Jangan menebak.
- **User memilih tidak memberi referensi/aset atau meminta acak**: cari sendiri video referensi di Pinterest yang nyambung dengan topik (prosedur dan saringan kualitas di `references/RENDER.md` §4), tulis asumsinya dalam satu kalimat. Kalau pencarian/unduhan gagal semua, berhenti dan tanya user: user carikan file/URL-nya, atau user beri arahan gaya singkat (palet, font, mood) untuk lanjut tanpa referensi. Tidak ada gaya bawaan — jangan melanjutkan tanpa acuan gaya.
- **File penting tidak bisa dibuka atau rusak**: beri tahu user. Jangan pura-pura sudah memprosesnya.

Kalau user memberi gambar (upload atau path), semua visual dibangun dari gambar itu dan disesuaikan dengan voiceover. Jangan menggantinya dengan stok generik atau visual yang tidak berhubungan. Kalau tidak ada gambar, buat elemen grafis sendiri (bentuk, ikon, ilustrasi vektor, tipografi, diagram) lewat kode. Jujurlah bahwa ini grafis buatan kode, bukan foto atau gambar AI fotorealistik.

**Tanpa voiceover.** Cek dulu `GEMINI_API_KEY` dan generate suara sendiri lewat Gemini TTS, dengan voice yang cocok dengan topik (lihat `references/RENDER.md`). Kalau API key tidak ada atau gagal, jangan berpura-pura bisa: sarankan user membuat suara dari naskah yang sudah disetujui lalu memberikan file hasilnya (upload atau path). Kalau user tetap ingin lanjut, tawarkan versi draf tanpa suara dengan timing perkiraan, dan beri label jelas bahwa itu draf, bukan hasil final yang tersinkron.

### Tahap 4 — Analisis aset dan kendalikan durasi

1. Inventarisasi semua file, pahami fungsi tiap aset terhadap naskah. Ukur resolusi gambar user dengan PIL: gambar yang jauh lebih kecil dari resolusi output akan blur saat di-upscale — beri tahu user, atau rancang komposisinya supaya tetap bagus (misalnya pakai sebagai elemen kecil, bukan layar penuh).
2. Ukur durasi asli voiceover dengan `ffprobe`, jangan menebak dari jumlah kata. Sekalian cek durasi masuk akal dibanding perkiraan naskah (±2,5 kata per detik); selisih jauh berarti suara mungkin terpotong — tangani dulu sebelum lanjut.
3. Cari ritme bicara (jeda, pergantian kalimat, kata yang ditekankan). **Utamakan ASR word-timestamp** (`faster-whisper`, resep lengkap di `references/RENDER.md` §3) — waktu per kata dari suara itu sendiri, bukan dari jumlah kata. Estimasi kata per detik hanya untuk sanity check panjang naskah dan hanya dipakai kalau ASR benar-benar tidak bisa dijalankan; kalau begitu, katakan ke user bahwa timing per kata adalah perkiraan.
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

Timing disimpan sebagai **satu tabel waktu absolut** yang dibaca semua scene (detail bentuknya di `references/RENDER.md` §5); batas scene diturunkan dari batas kalimat hasil ASR. Ini urusan akurasi, bukan gaya — isi kreatif tiap scene tetap keputusanmu.

Ritme dibuat bervariasi: pembuka yang langsung menarik perhatian, bagian tengah yang dinamis, penutup yang memuaskan. Penjelasan penting diberi gerak yang lebih tenang dan terbaca. Timeline ini hanya perencanaan. Lanjut ke produksi, jangan berhenti di sini.

### Tahap 6 — Produksi dan render

Baca dua file referensi sebelum membangun apa pun:
- `references/GUIDE.md` untuk arah kreatif, tipografi, animasi aset, transisi, **menerjemahkan ide jadi visual (§5), variasi komposisi antar scene (§6)**, dan mixing audio.
- `references/RENDER.md` untuk cek lingkungan, pipeline render, perintah ffmpeg, dan cara verifikasi.

Pemeriksaan QC **kamu tulis sendiri** saat dibutuhkan. Aturannya sudah lengkap dalam prosa: safe area, tinggi glyph dua tingkat, kontras WCAG, tabrakan teks (IoU), dan pola berulang — semuanya di `GUIDE.md` §2 dan `RENDER.md` §7. Terjemahkan ke kode sesuai renderer yang kamu pakai. Jangan cari perpustakaan bersama; tiap proyek punya struktur data sendiri, dan aturan yang jelas cukup dibaca.

Sebelum menulis kode scene, pastikan setiap poin inti punya satu mekanisme visual yang bisa digambar (`GUIDE.md` §5). Kalau rencananya masih berupa "tampilkan kata besar di tengah" untuk semua scene, gagasannya belum jadi.

### Tahap 7 — Kontrol kualitas dan serah terima

Periksa file MP4 hasil ekspor dari awal sampai akhir, bukan hanya timeline editor. Yang diverifikasi:

1. Gaya terinspirasi referensi tetapi tidak menyalin shot per shot.
2. Teks terbaca, ejaan benar, dan sinkron dengan narasi.
3. Aset muncul di momen yang relevan, tidak terpotong, tidak terdistorsi.
4. Transisi halus, bervariasi, dan punya tujuan.
5. Musik mendukung dan suara tetap dominan.
6. Tidak ada frame hitam, frame beku, glitch, atau audio cacat yang tidak disengaja.
7. MP4 bisa diputar. Durasi aktual sama dengan durasi total yang dihitung di Tahap 4 (tidak melebihi batas yang berlaku), jumlah frame = durasi × 30, 30 fps, codec dan resolusi sesuai spesifikasi, tidak ada konten setelah detik terakhir, dan batas durasi yang dipakai disebutkan (default 60 detik atau angka yang user setujui). Semuanya dibuktikan dari metadata file hasil ekspor.
8. Tiga gerbang di `references/RENDER.md` §7 lulus: sinkron (tidak ada teks yang muncul sebelum katanya), geometri (safe area, keterbacaan ukuran, tabrakan, kontras), dan ekor audio (tidak ada keheningan tak sengaja sampai detik terakhir). Gerbang keempat (pola berulang) hanya menandai, keputusanmu. Buktikan hasilnya dengan angka, sebutkan di pesan serah terima.

Cek kreatifnya juga, tapi dengan mata, bukan skrip: buka contact sheet hasil ekspor (`ffmpeg -i output.mp4 -vf "fps=1,scale=300:-1,tile=6x8" sheet.png`). Kalau semua thumbnail terlihat seperti satu template dengan kata berbeda, variasi komposisi belum cukup (`GUIDE.md` §6) — perbaiki sebelum serah terima.

Perbaiki masalah yang ditemukan sebelum menyerahkan file. Serahkan MP4 sesuai lingkungan: pakai mekanisme serah file yang tersedia (tool khusus bila ada) atau langsung kasih path file. File proyek/sumber boleh disertakan sebagai tambahan, tetapi MP4 wajib ada.

Pesan serah terima singkat: hasil verifikasi (durasi, frame, resolusi, codec), aset user mana yang dipakai, apa yang dibuat otomatis, dan keterbatasan yang relevan (misalnya musik sintetis atau timing perkiraan).

## Kejujuran soal hasil

- Jangan menyatakan video selesai kalau MP4 belum benar-benar dibuat dan diperiksa.
- Jangan menyatakan durasi terverifikasi kalau tidak diukur dari file hasil ekspor.
- Kalau lingkungan tidak bisa menjamin durasi atau tidak bisa me-render sama sekali, jelaskan keterbatasannya apa adanya, lalu serahkan apa yang memang sudah jadi (naskah, timeline, kode sumber) dengan label yang jelas.
- Jangan mengubah isi naskah user, menambah fakta, atau memutar makna.
