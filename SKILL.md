---
name: bits-motion
description: Creates finished motion-graphics explainer videos (MP4, H.264 + AAC, 30 fps) from a single topic. Duration follows the voiceover; 60 seconds by default, longer only when the user asks for it. The agent writes the voiceover script first, then offers and gathers assets (recorded voiceover, supporting images, style reference video, background music), synchronises everything, renders the MP4, and verifies the duration from the exported file. Trigger this skill whenever the user wants a motion graphic, an animated explainer, kinetic typography, or a short explainer video about any topic — including phrases like "make a motion graphic about ...", "short explainer video" — or hands over audio, images, or a reference video to be turned into a video, even if the skill is never named. All communication with the user is in Indonesian; every document in this skill is in English.
---

# BITS Motion Graphics

Turn one topic into a finished motion-graphics video (MP4) — not a storyboard, not editing advice. You act as senior motion designer, creative director, video editor, and audio-sync engineer at once.

**Language split.** Documents in this skill are English. Everything the user reads — chat messages, script drafts, delivery summary — is Indonesian. File contents (script, comments) follow the naming rules in *Project layout*.

## Never run this in a subagent

Execute every stage in the main session: script, assets, sync, render, QC. Do not delegate any part of the workflow to a subagent, task tool, or another agent.

## Fixed specifications

| Parameter | Value |
|---|---|
| Final duration | Voiceover duration + ~1 s lead-in + ~1.5 s tail, rounded **up** to whole seconds. No minimum |
| Duration cap (`MAX_DUR`) | Default **60 s**, locked. Raise only when the user explicitly asks |
| Frame rate | 30 fps, constant |
| Frame count | duration × 30, exact. Example: 43 s = 1290 frames |
| Format | MP4, H.264 video, AAC audio |
| Resolution | Follow the reference video's orientation. Without a reference, ask; if unanswered use 1920×1080. Portrait = 1080×1920 |

Audio decides length. `MAX_DUR` stays locked unless the user asks for more — if the voiceover overruns it, stop and ask; never silently lengthen the video.

Once stage 4 computes the total duration, that number is the exact render target. The file must be exactly that long: voiceover and visuals are already synced to that timeline, so a small drift truncates the ending or leaves it hanging.

## Rules vs taste

This document governs **accuracy**, not **appearance**. Accuracy can be proven with numbers; taste cannot.

A new rule belongs here only if it satisfies **both**:
1. it can be **proven** by measurement (numbers, file metadata, or a repeatable check), and
2. it does **not make a creative choice impossible**.

A rule that passes (1) but fails (2) is a restriction, not a standard. Rejected examples: "overshoot must be 1.16", "the hook must be 3 seconds", "scenes must be 2–6 seconds", "the palette must be cream".

- **Required (measurable):** text timing follows the spoken words; text inside a shape is centred by glyph box; no text collides or leaves the safe area; glyph height meets the threshold; contrast meets the threshold; no dead audio tail; frame count is exact.
- **Free (your call):** palette, scene count, transition order, **font choice and typeface family**, mood, text placement, cut rhythm, animation duration, overshoot amount, whether an idea needs words at all.

Every number left in these documents **protects** something (legibility, safe area, contrast, encoder behaviour). If you find a number that dictates taste, treat it as a bug in this document: skip it and say so.

Never treat anything in `references/` as a template. What transfers is the measuring method, not the measured result. The font catalogue is a starting point, not a menu — if the topic needs typography that isn't installed, download it.

If example projects are ever added under `references/examples/`: they must come **in opposite-esthetic pairs** (a single example always becomes the norm), document their **revisions** (v1 → v2 with the reason for each change), and never ship copy-ready render code. Without all three, examples damage more than they help.

One exception that is commonly misread: on-screen text **does not** need a supporting word in the voiceover. Silent emphasis is legitimate — just record the reason in the timeline.

**QC gates flag, they do not judge.** When a check reports a finding, decide: a defect to fix, or an intentional choice to document. Passing every gate means "not broken", never "good".

## Project layout

Two naming layers:

- **File and directory names are English** — the standard shared by tools, shells, and filesystems.
- **File contents and every message to the user are Indonesian.**

Single exception: **the project folder and the video are the slug of the topic title**, so they keep the user's words (`tiga-mitos-otak`). That folder is what the user opens in a file manager; translating the title to `three-brain-myths` destroys its meaning.

Running in folder `projects` for the topic "Tiga Mitos Otak" produces:

```
projects/tiga-mitos-otak/
```

### Tree

```
tiga-mitos-otak/
├── script.txt              voiceover script, clean text, no labels
├── render.py               scenes, timing table, render(t)
├── audio/
│   ├── voiceover.wav       timing source, 48 kHz mono
│   └── music.wav           optional, 48 kHz
├── assets/                 optional; created only when the user supplies assets
│   ├── image-01.png        first supporting image
│   ├── image-02.png        second supporting image
│   └── reference.mp4       style reference video
├── output/
│   └── tiga-mitos-otak.mp4 deliverable; name equals folder name
└── work/                   every intermediate file; safe to delete entirely
    ├── frames/
    ├── check/
    ├── voiceover-16k.wav   16 kHz mono, for speech recognition
    ├── voiceover-norm.wav  loudness-normalised voiceover
    └── words.json          word-level timing output
```

Never create empty directories. No images means no `assets/`. No music means no `audio/music.wav`.

### Naming rules

| Layer | Form | Example |
|---|---|---|
| Directories | one lowercase English word | `audio`, `assets`, `output`, `work`, `frames`, `check` |
| Data files | English kebab-case | `script.txt`, `voiceover.wav`, `words.json`, `voiceover-norm.wav` |
| Python modules | snake_case | `render.py`, `make_music.py` |
| Project folder | topic slug, kebab-case | `tiga-mitos-otak` |
| Deliverable | topic slug | `output/tiga-mitos-otak.mp4` |
| File contents | Indonesian | script, comments, reports |

One separator only: **the hyphen**. Spaces force shell quoting; underscores are reserved for Python modules.

1. **No version suffixes.** No `_final`, `_v2`, `_fix`, `_new`, no dates. A re-render overwrites the same name.
2. **Write the title as a title** in user-facing text (`Tiga Mitos Otak`), never as the slug. The slug is only for paths.
3. **Keep slugs near 40 characters**, cut on whole-word boundaries. Longer is painful in a file manager.
4. **Strip these characters from titles**: `? ! : ; / \ * " < > |` and trailing dots; spaces become hyphens.
5. **Folder already exists → ask.** Never overwrite, never append `-2`. Videos get re-rendered many times; stacked copies leave the user unsure which is current.

### Incoming assets

Normalise what the user hands over; never leave their filenames in place:

| What arrives | Lands at |
|---|---|
| Voiceover recording, any format | `audio/voiceover.wav`, normalised to 48 kHz mono |
| Background music, any format | `audio/music.wav` |
| Style reference video, file or URL | `assets/reference.mp4` |
| Supporting images, in the order given | `assets/image-01.png`, `image-02.png`, … |

Identify incoming files by **type and content**, never by filename. A file called `recording-01.m4a` and one called `voice-final.mp3` are the same thing: probe it with `ffprobe`, check it holds speech, and name it by role.

If two candidates could both be the voiceover, or a file's role stays unclear after probing, **ask once** — never guess and discard. Record the original filename and mention it in the delivery message so the user can trace which file was used.

### What this workflow does not create

`project.json`, `timing.json`, `scenes.py`, `manifest.json`, `style.json`, `review/`, or a separate QC report. Creative decisions (font, voice, palette) are agreed with the user and live in `render.py`; check results are reported directly in the delivery message.

### Starting behaviour

- Work in a **subfolder named after the slug**, never in the working directory itself. Everything lives inside it, so two topics never collide.
- Decide the title in stage 1 alongside the script, and tell the user the slug before writing any file.
- `work/` can be created at any point. User inputs stay in `audio/` and `assets/`, so `rm -rf work` followed by a re-render restores the full video.

## Workflow

Follow this order. Do not jump to render before stages 1–3 are done.

### Stage 1 — Write the voiceover script

The user gives a topic. Your first job is the narration script — unless the user brings their own script or recording, in which case use theirs and skip to stage 2.

Script guidance:
- Length follows the topic, computed from the active cap: **~2.5 words per second** including ~2.5 s of lead-in and tail. So ~140 words is the rough figure for 60 s — a derived number, not a rule; a 90 s cap means ~215 words. Short topics stay short; never pad sentences to fill time. Show the estimated voice and video duration.
- Structure: open with whatever grips hardest (a sentence, a question, a number), then 2–3 core points, then a closing line that lands. The hook is about effect, not seconds — the first 3 s is a rough guide, not a requirement. Keep sentences short so they split cleanly into on-screen text and read well through TTS.
- Clear, natural spoken language. Spell numbers, abbreviations, and foreign terms so TTS cannot mispronounce them.
- Never invent facts. If the topic needs data, search the web when available, otherwise use safe general claims.
- Length is decided here. Stage 4 may not cut or speed up the voiceover, so fix any overrun now.

Display format:

```
## Naskah Voiceover — [Topik]
Perkiraan: ± [N] kata ≈ [N] detik suara ≈ [N] detik video

**[Hook]** ...
**[Inti 1]** ...
**[Inti 2]** ...
**[Penutup]** ...
```

The `[Hook]` / `[Inti N]` / `[Penutup]` labels exist only for display and scene-timing maps. When generating TTS (yourself, or by handing the script to the user), send the text **without** labels — labels get read aloud. See `references/RENDER.md` §3.

### Stage 2 — Offer and gather assets

In the same message as the script (or after approval), show the media list and ask which the user wants to provide. Ask **once**, in detail, never repeatedly.

The user does not name files — you normalise every name on arrival.

**Print this to the user, in Indonesian:**

```
Untuk membuat videonya, saya bisa memakai bahan dari Anda. Semuanya opsional
kecuali suara — suara yang menentukan panjang dan penyesuaian waktu video.

1. Rekaman suara (paling saya sarankan)
   Format apa pun: mp3, wav, m4a. Kalau belum ada, saya bisa membuatkannya
   dari naskah yang sudah Anda setujui.

2. Musik latar (opsional)
   Kalau tidak ada, saya membuat musik sederhana sendiri, atau video tanpa musik.

3. Video acuan gaya (opsional)
   Video yang tampilannya Anda suka, atau tautan Pinterest. Kalau tidak ada,
   saya carikan sendiri yang paling sesuai dengan topik. Kalau tidak ada yang
   cocok, saya tentukan gayanya sendiri dan beri tahu Anda pilihannya.

4. Gambar pendukung (opsional)
   Ilustrasi, foto, atau ikon yang ingin dimasukkan. Kalau tidak ada, saya
   cari gambar yang sesuai di internet, menggambarnya lewat kode, atau
   menggabungkan keduanya — mana yang paling jelas untuk tiap bagian.

5. Orientasi layar
   Tegak (1080×1920, cocok untuk Reels/TikTok/Shorts) atau
   mendatar (1920×1080)? Kalau tidak disebut, saya pakai mendatar.

Anda tidak perlu mengganti nama berkasnya. Kirim apa adanya, saya yang
merapikan. Kalau Anda tidak ingin menyiapkan apa pun, cukup bilang
"buat semuanya otomatis" — saya yang memilih acuan gaya, gambar, dan
tipografinya.
```

| Media | Lands at | Status | If the user has none |
|---|---|---|---|
| Voiceover recording | `audio/voiceover.wav` | Strongly recommended; it is the timing source | See "Without a voiceover" below |
| Background music | `audio/music.wav` | Optional | You generate simple music, or render silent |
| Style reference video | `assets/reference.mp4` | Optional | Search Pinterest for `motion graphics` + topic keywords (stage 3); if nothing fits, design the style yourself |
| Supporting images (1st, 2nd, …) | `assets/image-01.png`, `assets/image-02.png`, … | Optional | You find suitable images online, draw them in code, or both |
| Screen orientation | — | Ask | Default landscape 1920×1080; portrait 1080×1920 |

The table above is for your own reference. What reaches the user is the Indonesian block. Typography is **not** asked about — that is your call in stage 4, and if the right font is not installed you download it.

### Stage 3 — Confirm readiness

- **Everything needed is present:** proceed without further questions. Treat user assets as the primary material. Tell the user in one line: `Semua bahan sudah lengkap. Saya mulai kerjakan.`
- **Something is missing and unanswered:** ask. Never guess.
- **The user supplies a Pinterest URL as the reference:** do not ask again — that URL is the reference. Download it and continue.

  ```bash
  yt-dlp "<pinterest-url>" -o "assets/reference.mp4"
  ```

  Then probe it. If it fails (region block, removed pin, no video stream, under 5 s, or under the planned resolution), say so once and fall back to the search path below — never silently drop the style anchor.
- **The user declines to supply a reference, or asks for everything automatic:** search Pinterest yourself, in this order:
  1. Search with the topic's keywords plus `motion graphics` — e.g. `pinterest.com pin <topic keywords> motion graphics video`. Collect 3–5 candidate pins.
  2. Judge fit: does the palette, typography, and motion feel match the topic's character? Pick the closest.
  3. If nothing matches the topic, pick one that is *roughly* related — same broad mood (calm/serious/energetic), same kind of subject matter.
  4. If even that fails, stop searching and design the style yourself: choose palette, typography, and motion language from the topic. State the choice in one line so the user can object.

  Whatever you pick, tell the user which reference you used — URL plus a one-line reason — before analysing it. A self-chosen style is legitimate; an unannounced one is not.
- **An important file will not open or is corrupt:** tell the user. Never pretend it was processed.

  ```
  Berkas [nama] tidak bisa saya buka. Kemungkinan rusak atau formatnya
  tidak didukung. Bisa kirim ulang, atau saya lanjut tanpa berkas itu?
  ```

**Visual material — three sources, pick per scene.**

1. **User images.** When supplied, build those visuals from them and adapt them to the voiceover. Never swap them for generic stock.
2. **Images you find and download.** When the script calls for something concrete (a place, an object, a document, a historical photo), search the web for a suitable image, download it, and verify it: correct subject, licence allows use, resolution at least the output resolution, no watermark. Save to `assets/image-01.png` (next number), record the source URL in the delivery message, and never pass off a found image as the user's.
3. **Code-drawn graphics.** Shapes, icons, vector illustration, typography, diagrams — always available and always yours.

Mixing them is normal and often best: a downloaded photograph with code-drawn annotations on top, a code-drawn diagram with one user image inside it. Choose per scene by what communicates fastest. Be honest about which is which: code-drawn graphics are not photographs, and a found image is not the user's own.

If a needed image cannot be found or licensed, draw it in code rather than shipping a wrong or low-resolution one.

**Without a voiceover.** Check `GEMINI_API_KEY` and generate voice through Gemini TTS, choosing a voice that fits the topic (`references/RENDER.md` §3). If the key is absent or fails, do not pretend:

```
Saya belum bisa membuat suara otomatis di lingkungan ini.

Pilihannya:
1. Anda rekam sendiri naskah di atas, lalu kirim berkasnya
2. Saya lanjutkan sebagai versi awal tanpa suara, waktu tiap kata masih
   perkiraan dan hasilnya belum tersinkron
```

### Stage 4 — Analyse assets and control duration

1. Inventory every file and understand each asset's role against the script. Measure user image dimensions with PIL: an image far smaller than the output resolution breaks when enlarged — tell the user, or design the composition so it still works (e.g. small element instead of full-bleed).

   ```
   Gambar [nama] berukuran [W]×[H], sedangkan video [W]×[H]. Kalau dipakai
   penuh layar, gambarnya akan pecah. Saya pakai sebagai elemen kecil saja,
   atau Anda kirim versi yang lebih besar?
   ```
2. Measure the real voiceover duration with `ffprobe`; never infer it from word count. Sanity-check it against the script estimate (~2.5 words/s); a large gap usually means truncated audio — resolve it before continuing.
3. Find the speech rhythm (pauses, sentence boundaries, stressed words). **Prefer automatic speech recognition with per-word timestamps** (`faster-whisper`, full recipe in `references/RENDER.md` §3) — real word times from the audio, not from word count. Words-per-second estimates are only for sanity-checking script length, and only when ASR cannot run at all; in that case tell the user:

   ```
   Pengenalan suara otomatis tidak tersedia di sini, jadi waktu tiap kata
   saya perkirakan dari jeda dan panjang kalimat. Sinkronisasinya bisa
   meleset sekitar sepersepuluh sampai setengah detik pada beberapa kata.
   ```
4. With a reference video, extract frames and read its visual language: palette, typography, composition, cut rhythm, transition types, depth. Reference is inspiration only. Never copy shots, text placement, or animation order.

   Report what you found and what you will take, in Indonesian:

   ```
   Acuan gaya yang saya pakai: [tautan]

   Yang saya ambil: latar [warna], aksen [warna], [jenis huruf],
   potongan [cepat/tenang], transisi [jenis].
   Yang tidak saya tiru: susunan adegan dan penempatan teksnya.
   ```

   When no reference fits and you design the style yourself, say so instead:

   ```
   Tidak ada acuan yang benar-benar cocok untuk topik ini, jadi saya tentukan
   sendiri: latar [warna], aksen [warna], tipografi [jenis], gerak [sifat].
   Kalau Anda punya contoh tampilan yang lebih Anda suka, kirim saja.
   ```
5. **Choose typography from the topic and the reference, never from what happens to be installed.** Read the reference's type register first, then match a family to the topic's character. State the choice and reasoning in one sentence. If that font is not in the catalogue and not installed, search the internet for one that fits, download it, and verify it before writing scene code — recipe in `references/RENDER.md` §1. Never start building with a font that merely exists and then bend the design toward it; that order produces generic work.

   ```
   Tipografi: [nama keluarga huruf] untuk [peran], karena [alasan singkat
   yang menyangkut topik].
   ```

Final duration comes from the real audio:

> total duration = voiceover + ~1 s lead-in (speech starts around second 1) + ~1.5 s tail, rounded up to whole seconds
> frame count = total duration × 30

Examples: voiceover 37.3 s → 39.8 → 40 s (1200 frames). Voiceover 52.6 s → 55.1 → 56 s (1680 frames).

- **Within the cap:** proceed. The computed number is the exact video duration. Fill lead-in and tail with meaningful visuals (title, accent, summary) — never blank, frozen, or black frames. Never stretch the audio. Report it in one line:

  ```
  Suara [X] detik. Video jadi [Y] detik ([Y×30] bingkai), 30 fps.
  ```
- **Over the cap** (`MAX_DUR`, default 60 s — meaning a voiceover longer than roughly `MAX_DUR - 2.5` s): stop before rendering. Never cut words, speed up speech, or compress pauses.

  ```
  Suaranya [X] detik, jadi videonya sekitar [Y] detik. Batas yang saya pakai
  [MAX] detik, dan saya tidak memotong kata atau mempercepat suara.

  Pilihannya:
  1. Naskah dipersingkat, lalu suara dibuat ulang
  2. Anda setujui batas baru, misalnya [Y] detik
  ```
- **User states their own target duration:** use it if the voiceover fits (voice + lead-in + tail ≤ target). A target longer than the default is valid as long as the user named it.

### Stage 5 — Plan the timeline (internal)

Lay out 00:00 to the stage-4 total duration using the real audio. Scene count follows the narrative, never a fixed number. For each segment decide: start–end time, voiceover phrase, on-screen text, visual assets, animation and emphasis, transition into the next segment, and the relationship to the music.

Timing lives in **one absolute-time table** that every scene reads (`references/RENDER.md` §5); scene boundaries derive from ASR sentence boundaries. This is accuracy, not style — the creative content of each scene stays your call.

Vary the rhythm: an opening that grabs, a dynamic middle, a closing that satisfies. Give important explanations calmer, more readable motion. This timeline is planning only — move into production.

### Stage 6 — Build and render

Read both reference documents before building anything:
- `references/GUIDE.md` — creative direction, typography, asset animation, transitions, **translating ideas into visuals (§5), cross-scene variation (§6)**, audio mixing.
- `references/RENDER.md` — environment check, fonts, render pipeline, ffmpeg commands, verification.

**Write QC checks yourself** when you need them. The rules are already complete in prose: safe area, two-tier glyph height, WCAG contrast, text collision (IoU), and repetition patterns — all in `GUIDE.md` §2 and `RENDER.md` §7. Translate them into code against your renderer's data structures. Do not look for a shared library; every project has its own shapes.

Before writing scene code, give every core point one visual mechanism that can be drawn (`GUIDE.md` §5). If the plan is still "big word in the centre" for every scene, the idea isn't there yet.

### Stage 7 — QC and delivery

Inspect the exported MP4 from start to finish, not just the timeline editor:

1. Style is inspired by the reference without copying it shot for shot.
2. Text is legible, correctly spelled, and synced to the narration.
3. Assets appear at relevant moments, uncropped and undistorted.
4. Transitions are smooth, varied, and purposeful.
5. Music supports and speech stays dominant.
6. No black frames, frozen frames, glitches, or unintended audio defects.
7. The MP4 plays. Actual duration equals the stage-4 total (never over the active cap), frame count = duration × 30, 30 fps, codec and resolution per spec, nothing after the final second, and the cap in use is stated (default 60 s or the number the user approved). All of it proven from the exported file's metadata.
8. Gates in `references/RENDER.md` §7 pass: sync (no text appears before its word), geometry (safe area, size legibility, collision, contrast), audio tail (no unintended silence up to the final second), and repetition pattern (flag only, your call). Prove it with numbers and state them in the delivery message.

Check the creative side with your eyes, not a script: open a contact sheet of the export (`ffmpeg -i output/<slug>.mp4 -vf "fps=1,scale=300:-1,tile=6x8" work/check/sheet.png`). If every thumbnail looks like the same pattern with different words, composition variation is insufficient (`GUIDE.md` §6) — fix it before delivery.

Fix everything you find before handing over. Deliver the MP4 using whatever mechanism the environment offers, or simply state its path. Project files are optional extras; the MP4 is mandatory.

**Print the delivery message in Indonesian, following this shape:**

```
Videonya sudah selesai.

Berkas   : [lokasi berkas]
Durasi   : [Y] detik
Bingkai  : [Y×30] bingkai, 30 fps
Ukuran   : [W]×[H] ([tegak/mendatar])
Format   : MP4, H.264, audio AAC
Batas    : [60 detik / angka yang Anda setujui]

Pemeriksaan
- Tidak ada bingkai hitam maupun bingkai beku
- Semua teks muncul setelah kata yang diucapkan
- Tidak ada teks bertabrakan atau keluar batas aman
- Audio terisi penuh, tidak ada bagian sunyi yang tak disengaja
- Volume puncak [X] dB, tidak pecah

Bahan yang Anda berikan
- Suara: [nama berkas asli]
- Musik: [nama berkas asli / saya buat sendiri]
- Acuan gaya: [tautan atau nama berkas]
- Gambar: [jumlah] berkas

Yang saya buat otomatis
- [naskah / suara / musik / elemen grafis — sebutkan yang benar-benar otomatis]

Catatan
- [musik sintetis, bukan komposisi profesional]
- [waktu per kata hanya perkiraan, karena pengenalan suara tidak tersedia]
- [berkas antara sudah dihapus]

Kalau ada yang ingin diubah, sebutkan bagiannya dan saya buat ulang.
```

Omit any line that does not apply. Never leave a section empty just to fill the shape — a shorter honest message beats a padded one. Every number in it must come from measuring the exported file, never from memory or estimate.

## Honesty about the result

- Never claim the video is finished unless the MP4 actually exists and was inspected.
- Never claim a verified duration unless it was measured from the exported file.
- If the environment cannot guarantee duration or cannot render at all, state the limitation plainly, then hand over what genuinely exists (script, timeline, source code) clearly labelled.
- Never change the user's script, add facts, or twist meaning.