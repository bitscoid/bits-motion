# Panduan Visual dan Kreatif

Baca file ini sebelum membangun scene. Isinya adalah arah eksekusi kreatif (tipografi, animasi, transisi, sinkronisasi, audio); arah gaya visual selalu berasal dari video referensi yang terpilih. Sesuaikan dengan aset user dan topik; jangan memaksakan warna atau layout yang sama di setiap scene.

## Daftar isi
1. Membaca video referensi
2. Tipografi kinetik
3. Menganimasikan aset
4. Transisi
5. Menerjemahkan ide jadi visual
6. Variasi yang menjaga konsistensi
7. Sinkronisasi dengan voiceover
8. Musik dan mixing audio

## 1. Membaca video referensi

Referensi adalah tolok ukur kualitas, bukan cetakan. Yang diambil adalah prinsipnya: kenapa video itu enak dilihat, bukan urutan efeknya.

Perhatikan: palet warna, hierarki tipografi, cara teks dan gambar saling bertumpuk, ritme potongan, jenis transisi, penggunaan bayangan dan kedalaman, serta hubungan gerak dengan suara.

Yang dilarang: menyalin adegan satu per satu, memakai komposisi yang sama persis, menempatkan teks di posisi yang sama, atau meniru urutan animasi dan transisi frame demi frame. Tujuannya video yang orisinal dan terasa lebih rapi dari referensinya.

## 2. Tipografi kinetik

Tipografi adalah elemen bercerita, bukan sekadar subtitle.

Teknik yang bisa dipakai sesuai konteks: teks muncul bersamaan dengan kata yang diucapkan, reveal dengan mask, animasi kata atau huruf bertahap, skala dengan overshoot terkontrol, animasi spasi antar huruf, teks masuk dari balik objek, clipping dan layering kreatif, penekanan lewat ketebalan, warna, atau ukuran.

Aturan:
- Pilih font modern, tebal, dan sangat terbaca. Pakai font asli lewat kode (bukan teks hasil generate gambar), sehingga huruf tidak pernah rusak atau jadi kata palsu.

  **Font bukan menu tetap.** Katalog di `RENDER.md` §"Font siap pakai" adalah contoh yang sudah terpasang, bukan daftar pilihan yang boleh dipakai. Tugasmu: pilih tipografi yang **cocok dengan topik dan mood referensi**, bukan yang paling atas di tabel. Kalau topik butuh sesuatu yang belum ada (mis. topik kuliner butuh slab serif gemuk, topik arsip butuh condensed tebal, topik teknologi butuh grotesk sempit), **unduh sendiri** — jangan turun ke font yang "cukup mirip" hanya karena sudah terpasang. Resep unduh + verifikasi ada di `RENDER.md` §1 "Menambah font baru".

  Batasnya bukan jenis font, tapi jumlah: maksimal 2–3 family per video supaya tetap satu keluarga. Cek dengan `fc-list` atau `fc-query` sebelum dipakai di scene.
- Pertahankan ejaan dan makna teks persis seperti naskah.
- Pecah teks jadi frasa pendek. Jangan menampilkan satu paragraf utuh sekaligus. Sorot hanya kata kunci.
- Pisahkan jelas tingkatan: judul, kata kunci, teks pendukung, label kecil.
- Hindari huruf besar acak, font yang sulit dibaca, dan dekorasi berlebihan.
- Jaga safe area: elemen penting minimal ±4% dari tepi frame. Angka ini satu-satunya angka (gerbang geometri di `RENDER.md` §7 memakai 4%); jangan pakai nilai lain supaya tidak ada dua kebenaran.
- Ukuran teks terkecil tetap terbaca di resolusi output. **Ambangnya tinggi glyph, bukan ukuran font** — glyph kapital hanya sekitar 0,75× ukuran font, jadi `truetype(size=100)` menghasilkan glyph ±75 px. Ukur dengan `textbbox`, jangan dari angka `size`. Dua tingkat:
  - **teks utama / kata kunci**: tinggi glyph ≥ 4% tinggi frame (1920 → 77 px; berarti font ≈ 102 px).
  - **teks pendukung / label / chip kecil**: tinggi glyph ≥ 2,5% tinggi frame (1920 → 48 px; font ≈ 64 px), dan wajib lolos kontras 4,5:1 karena ukurannya kecil.

  Kalau baris pendukung tidak muat di tingkat 2,5% bersama elemen lain, kurangi jumlah kata di baris itu — jangan turunkan ambangnya. Ukur hasilnya, jangan dikira.
- Cek kontras teks vs latarnya di kode, jangan dikira dari nama warna. Ambangnya terukur dan diikat ke **peran teks**, bukan ukuran piksel:
  - **teks utama / kata kunci: 3,0:1**
  - **teks pendukung / label / chip: 4,5:1** — lebih ketat dari WCAG "large text", karena teks kecil yang bergerak cepat terbaca jauh lebih buruk daripada teks diam berukuran sama.

  Hitung dengan rumus WCAG:

```python
def lum(c):  # c = (r, g, b) 0-255
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
```

  Gagal → beri panel solid di belakang teks atau gelapkan areanya, jangan mengandalkan bayangan tipis. Teks di atas gambar user wajib diukur terhadap piksel yang benar-benar di belakangnya (ambil rata-rata area), bukan terhadap warna dominan gambar.
- **Centering diukur, bukan diserahkan ke `anchor`.** `anchor="mm"` memusatkan kotak-em font, bukan bentuk glyph — angka, judul kapital, dan teks dengan descender akan terlihat geser di dalam bentuk. Untuk teks yang duduk di dalam objek (angka di lingkaran, label di kartu, teks di dalam blok warna) geser posisinya dengan selisih bbox glyph:

```python
bb = d.textbbox((px, py), s, font=f, anchor="mm")
dx = (bb[0] + bb[2]) / 2 - px
dy = (bb[1] + bb[3]) / 2 - py
d.text((px - dx, py - dy), s, font=f, anchor="mm", fill=fill)
```

  Terukur: offset 10 px → 0,5 px. Kalau transform kamera dipakai (skala/geser), bagi `dx` dan `dy` dengan skala sebelum dipakai. Kalau teks punya `spacing` (per-huruf), `anchor` tidak berlaku — ukur lebar total dan pusatkan sendiri, jangan campur dua metode.
- **Tumpukan teks diukur, bukan dikira.** Kalau beberapa baris saling menumpuk vertikal (label, judul, subjudul), hitung top/bottom tiap baris dari `textbbox` dan pastikan tidak ada irisan. Urutan baca harus sesuai urutan narasi, dan baris terakhir jangan berdempet dengan objek di bawahnya — sisakan celah minimal ~0,8× tinggi baris.

## 3. Menganimasikan aset

Aset penting jangan dibiarkan diam kecuali memang ada momen jeda yang disengaja. Ini kewajiban, bukan pilihan: di setiap scene minimal satu elemen bergerak setiap saat; kalau tidak ada yang wajar bergerak, pakai gerak kamera mikro (zoom drift ±2–4% atau geser ±10–20 px). Video motion graphic yang statis di scene mana pun dianggap gagal QC (gerbang freezedetect ada di `RENDER.md` §7).

Teknik: scale in/out, gerak terarah dan rotasi halus, parallax dan lapisan kedalaman, reveal dengan mask, zoom kamera terkontrol, cropping kreatif, gerak melayang dan gerak sekunder, motion blur dan bayangan lembut, serta hubungan visual antara aset dan teks.

Variasikan teknik sesuai isi. Gunakan easing profesional (percepatan, perlambatan, overshoot, antisipasi, settling), bukan kecepatan konstan.

Boleh memotong, mengubah ukuran, memposisikan, memasking, dan menumpuk aset user selama makna dan detail pentingnya tidak hilang. Jangan memotong objek penting, jangan meregangkan gambar, jangan biarkan elemen bertabrakan canggung.

Pemotongan latar (cut-out): kalau tool pemotong latar tidak tersedia, pakai masking manual atau framing yang membuat gambar tetap menarik tanpa cut-out, dan jangan menjanjikan hasil cut-out yang tidak bisa dibuat.

## 4. Transisi

Pilihan: match cut, whip, wipe terarah, reveal dengan mask, transisi bentuk, transisi skala, transisi yang digerakkan tipografi, transisi parallax berlapis, transisi motion blur, dan elemen grafis yang berpindah antar scene.

Ini pilihan, bukan daftar centang. Pilih yang cocok dengan isi dan jaga kesatuan gaya. Sebisa mungkin hubungkan elemen visual antar scene supaya tidak terasa terputus.

Ritme ditentukan isi, bukan angka. Patokan "scene inti ±2–6 detik" hanya deskripsi video pendek pada umumnya — kalau sebuah ide butuh 8 detik untuk mendarat, beri 8 detik. Yang tetap dijaga: variasi terbesar ditaruh di pembuka, dan scene di sepertiga akhir jangan terlalu pendek sampai penonton tidak sempat mencerna.

Hindari glitch berlebihan, putaran acak, kilatan tanpa alasan, dan transisi yang menutupi penjelasan. Semua transisi harus muat di dalam durasi total yang sudah dihitung. Durasi video tidak boleh melar karena transisi.

## 5. Menerjemahkan ide jadi visual

Tipografi saja membuat video terasa seperti presentasi teks bergerak. Yang membedakan motion graphic bagus adalah **gagasan visual** — satu cara memandang ide yang bisa digambar.

Sebelum membangun scene, untuk setiap poin inti pilih satu **mekanisme visual**, bukan sekadar kata besar di tengah:

| Mekanisme | Pertanyaan yang dijawab | Contoh bentuk |
|---|---|---|
| Skala/perbandingan | "seberapa besar?" | satu figur kecil di antara ratusan; angka raksasa vs benda mungil |
| Akumulasi | "menumpuk jadi apa?" | benda bertambah sampai memenuhi frame (kewajiban, tuntutan, jam) |
| Transformasi | "berubah jadi apa?" | satu bentuk berubah jadi bentuk lain (mainan → meja belajar) |
| Pemisahan/belah | "apa yang terpisah?" | satu bentuk terbelah, satu bagian menjauh (anak vs tuntutan) |
| Jalur/gerak | "ke mana arahnya?" | garis waktu, panah, jalur yang bercabang |
| Wadah/kapasitas | "muat atau tidak?" | gelas meluap, kotak sesak, kapasitas terisi penuh |
| Kontras berdampingan | "beda di mana?" | dua keadaan bersebelahan, bukan berurutan |
| Siklus | "berulang bagaimana?" | lingkaran yang berputar, hari yang sama terulang |

Aturan mainnya:
- Satu scene cukup satu mekanisme utama. Dua mekanisme bersamaan saling melemahkan.
- Boleh meminjam idiom visual (grafik batang, jam, tumpukan) tapi jangan membiarkannya jadi ikon generik tanpa arti khusus untuk topik itu.
- Kalau ide tidak bisa digambar tanpa teks, itu tanda ide belum visual — ganti mekanismenya, jangan menambah teks.
- Mekanisme boleh berulang sebagai motif antar scene (mis. akumulasi dipakai dua kali), asalkan bentuknya berkembang.

Ini bukan daftar wajib. Kalau ide punya bentuk yang lebih baik di luar tabel, pakai itu.

## 6. Variasi yang menjaga konsistensi

Video pendek dengan belasan scene mudah jatuh jadi "slide yang sama, kata berbeda". Cara menghindarinya tanpa kehilangan kesatuan:

- **Variasikan komposisi**, bukan cuma isi: teks kiri + gambar kanan, teks tengah polos, teks menempel tepi, teks bertumpuk objek, teks sangat kecil di ruang luas.
- **Variasikan kepadatan**: scene penuh (banyak elemen) diselingi scene lapang (satu elemen, banyak ruang kosong). Kepadatan seragam melelahkan.
- **Variasikan latar**: terang/gelap boleh bergantian, tapi satu warna aksen tetap dipegang sepanjang video supaya terasa satu keluarga.
- **Variasikan skala**: satu scene dengan elemen raksasa yang memotong frame akan membuat scene lain terasa lapang, meski ukurannya biasa.
- **Jaga satu hal tetap**: satu warna aksen, satu font display, satu jenis gerak dominan. Yang tetap itulah yang membuat variasi terasa disengaja, bukan acak.

Periksa hasilnya dengan contact sheet (`ffmpeg ... tile`) sebelum ekspor: kalau 14 thumbnail terlihat seperti template yang sama, variasinya belum cukup.

## 7. Sinkronisasi dengan voiceover

Voiceover adalah acuan timing utama, sedangkan durasi total video ditetapkan di Tahap 4 SKILL.md (durasi suara + pembuka dan penutup, dibatasi `MAX_DUR` yang default-nya 60 detik).

Timing per kata diambil dari suara itu sendiri lewat ASR word-timestamp, bukan dari jumlah kata (`RENDER.md` §3). Semua kemunculan teks dibaca dari satu tabel waktu absolut (`RENDER.md` §5), dan hasilnya dibuktikan gerbang sinkron (`RENDER.md` §7): teks tidak boleh muncul sebelum katanya.

Untuk setiap frasa penting: tampilkan teks saat kata itu diucapkan, munculkan aset saat relevan, tekankan kata kunci lewat skala/warna/bobot/posisi/gerak, berikan jeda visual singkat ketika penonton butuh waktu mencerna, dan sesuaikan kecepatan animasi dengan ritme pembicara.

Gerak harus terasa merespons suara, bukan berputar acak. Efek visual tidak boleh mengalihkan perhatian dari informasi yang dijelaskan.

Teks tanpa kata pendukung di voiceover tetap sah (penekanan senyap) — cukup catat alasannya di timeline, jangan dihapus hanya karena gerbang sinkron tidak bisa memverifikasinya.

## 8. Musik dan mixing audio

- Voiceover harus tetap jelas dan dominan. Turunkan musik di bawah suara (ducking) terutama saat informasi penting.
- Selaraskan beberapa transisi atau aksen animasi dengan beat bila memang pas dengan narasi.
- Efek suara dipakai hemat dan tidak bersaing dengan suara narator.
- Jangan mempercepat suara atau memotong kata demi mengejar durasi. Pertahankan ritme dan jeda asli.
- Musik fade-out halus di akhir, dan audio berakhir tepat di detik terakhir video tanpa ekor suara atau terpotong mendadak.
- Cegah clipping, distorsi, perubahan volume mendadak, dan keheningan yang tidak disengaja.

Kalau user tidak punya musik: buat musik latar sederhana yang cocok dengan gaya visual (lihat `RENDER.md`), dan katakan terus terang bahwa itu musik sintetis sederhana. Alternatifnya render tanpa musik dan sarankan user menambahkan musik bebas royalti.
