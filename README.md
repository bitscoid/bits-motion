<div align="center">

# 🎬 BITS Motion

**Turn a single topic into a finished motion-graphics video.**

No storyboard. No editing advice. A rendered MP4 you can publish.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Format](https://img.shields.io/badge/output-MP4%20H.264%20%2B%20AAC-blue)
![Frame rate](https://img.shields.io/badge/fps-30%20CFR-informational)
![Duration](https://img.shields.io/badge/duration-follows%20voiceover-brightgreen)
![Docs](https://img.shields.io/badge/docs-English%20only-lightgrey)

</div>

---

## ✨ What it does

Give it a topic. It writes the voiceover script, gathers your assets, syncs every word to the picture, renders the video, and proves the result with real numbers.

```
topic ──► script ──► voice ──► word timing ──► scenes ──► MP4 ──► verified
```

The output is an **MP4 (H.264 + AAC, 30 fps, constant frame rate)** whose length is derived from the voiceover — 60 seconds by default, longer only when you ask.

Resolution follows the reference video's orientation. Without a reference it asks, and falls back to **1920×1080** landscape or **1080×1920** portrait.

---

## 🚀 Quick start

```bash
# 1. install into your agent's skill directory
git clone https://github.com/bitscoid/bits-motion.git \
  ~/.config/opencode/skills/bits-motion

# 2. check the toolchain (ffmpeg, ffprobe, PIL, numpy)
ffmpeg -version | head -1
python3 -c "import PIL, numpy; print('PIL+numpy ok')"

# 3. ask for a video
"buatkan motion graphic tentang kenapa kopi bikin ngantuk"
```

That's the whole interface. No config file, no CLI flags, no build step. The full environment probe — ASR, fonts, network, API key — is `references/RENDER.md` §1.

---

## 🧠 Design philosophy

This skill is **rules, not a template.**

| Layer | Divided how |
|---|---|
| 🎯 **Accuracy** | Measurable, must pass — timing follows the spoken word, text stays in the safe area, glyph height meets threshold, contrast meets WCAG, no dead air inside the narration, mix loudness in band, frame count is exact |
| 🎨 **Taste** | Entirely yours — palette, scene count, transitions, typeface, mood, motion rhythm |

The test applied to every rule before it entered these documents:

> **① Can it be proven by measurement?** &nbsp;and&nbsp; **② Does it leave creative choice alive?**

A rule that passes ① but fails ② is a restriction, not a standard. Rejected examples that live on as warnings in the docs: *"overshoot must be 1.16"*, *"the hook must be 3 seconds"*, *"scenes must be 2–6 seconds"*.

**One skill, no shared library.** The agent writes the render code and the QC checks per project. Every video gets code shaped to its own content instead of being squeezed into a shared engine.

---

## 🎯 What it actually enforces

<details open>
<summary><b>⏱ Timing</b></summary>

Word timing comes from **automatic speech recognition with per-word timestamps**, not from counting words. Every text appearance reads from one absolute-time table, and a sync gate proves no text appears before its word.

Word-count estimation is the documented fallback, clearly labelled as approximate.

</details>

<details open>
<summary><b>📐 Typography geometry</b></summary>

- Safe area: **4%** from every edge — and for portrait short-form, **10% bottom / 12% right**, because the platform UI covers that band
- Glyph height, not font size: **4%** of the short side for primary text, **2.5%** for supporting text (1080p landscape → 43 px / 27 px)
- Centring is measured from the glyph box, never delegated blindly to `anchor="mm"`
- Text collision checked by **coverage of the smaller box (< 0.02)**, not IoU — IoU 0.16 lets a 20% line overlap pass

</details>

<details open>
<summary><b>🌗 Contrast</b></summary>

Thresholds are tied to the text's **role**, not its pixel size — small moving text reads far worse than static text of the same size.

- Primary text: **3.0:1**
- Supporting text: **4.5:1**

Measured with the WCAG formula: a light salmon `(238,150,130)` on cream `(245,241,234)` reaches only **2.00:1** — a hard fail; darkening the accent to `(166,82,70)` reaches **4.76:1** and passes for supporting text. The docs ship a `fit_accent()` helper that walks lightness until the ratio clears, so the palette is chosen by measurement rather than by eye.

</details>

<details open>
<summary><b>🔊 Audio</b></summary>

- Voiceover normalised to −16 LUFS, true peak −1.5 dB, in its own file
- Music **looped to the video length** (`-stream_loop -1`), ducked under speech, faded to a floor — never to absolute zero
- Audio gate is **windowed**: no dead air inside the speech region, and with music the tail must still carry sound
- Finished mix measured: **I ∈ [−17, −14] LUFS**, true peak ≤ −1 dBTP

Measured traps that produced these rules: `loudnorm` inline with `apad` drops the tail to **−91 dB**; `afade=t=out` ending on the last frame leaves the final 0.8 s at **−61.7 dB**; a 10 s music bed on a 28 s video without looping leaves **18 s of silence**.

</details>

<details open>
<summary><b>🎞 Motion</b></summary>

Every second of video keeps at least one element moving. Verified with `freezedetect=n=0` — never the default `n=-60dB`, which false-positives on flat graphics. The 1 s lead-in before speech is exempt.

Frame contiguity is asserted before encoding: a missing PNG mid-sequence silently truncates the MP4 (`%05d` input stops at the gap).

The lower bound is the encoder, not taste: motion under ~10 px can be quantised away at CRF 18+, leaving identical frames.

</details>

<details>
<summary><b>🔁 Repetition gate (flags, never judges)</b></summary>

Scenes with the same structural signature get flagged so you can decide: *deliberate motif* or *coincidence to fix*. The gate forces that decision to be written down; it never homogenises the output.

Signatures compare ink against each frame's own modal luma, so a dark theme with light text works — the old `luma < 110` rule measured the background and returned an identical centroid for every scene.

</details>

---

## 📁 Project output

Each video becomes a self-contained folder:

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
│   ├── tiga-mitos-otak.mp4 deliverable; name equals folder name
│   └── tiga-mitos-otak.srt subtitle track, optional
└── work/                   every intermediate file; safe to delete entirely
    ├── frames/
    ├── check/
    ├── voiceover-16k.wav   16 kHz mono, for speech recognition
    ├── voiceover-norm.wav  loudness-normalised voiceover
    ├── music-norm.wav      looped + ducked-ready music
    └── words.json          word-level timing; every later stage reads it
```

`render.py` is the Python pipeline's name; the build script is always a single entry point, `render.<ext>`.
**Naming rule:** file and directory names are English kebab-case; file contents and every message to the user are Indonesian. The project folder and the video carry the topic slug so they stay meaningful in a file manager.

`rm -rf work` then re-render restores the whole video.

---

## 🛠 Requirements

| Need | Why |
|---|---|
| `ffmpeg` + `ffprobe` | rendering, measuring, verification |
| `python3` + PIL + numpy | frame generation and asset measurement |
| `faster-whisper` | word-level timing (optional, degrades to estimate) |
| `GEMINI_API_KEY` | optional TTS when you have no recording (Interactions endpoint) |
| `yt-dlp` | optional, downloading style references |

Verified on ffmpeg 7.1. Every ffmpeg behaviour cited in the docs was measured on a real render, not copied from documentation.

---

## 🧩 How the documents fit together

| File | Role |
|---|---|
| **`SKILL.md`** | the workflow — 7 stages, decision tables, ready-to-print user messages |
| **`references/GUIDE.md`** | creative direction — typography, animation, transitions, turning ideas into visuals |
| **`references/RENDER.md`** | engineering — environment, fonts, ffmpeg, and the QC gates |

Every measured number lives in `RENDER.md`. Every creative freedom lives in `GUIDE.md`. Neither pretends to be the other.

---

## 🎨 Fonts

The catalogue ships **38 families across 8 registers** as a starting point, never a menu. If the topic needs typography that isn't there, the skill downloads it:

```bash
curl -sL -o /tmp/font.ttf \
  "https://github.com/google/fonts/raw/main/ofl/outfit/Outfit%5Bwght%5D.ttf"
```

Then verifies it before use — under 10 KB means an HTML error page, not a font.

---

## ⚠️ Honest limits

- Music is **synthesised** unless you supply your own — simple chords, not a composition
- Word timing is **approximate** when ASR is unavailable, and the delivery message says so
- The agent cannot watch the video; visual QC relies on extracted frames, contact sheets, and measured numbers
- Maximum 60 seconds by default — this is a short-form explainer, not a documentary tool
- Captions are **offered, not assumed**; burned-in captions are a separate style decision from kinetic typography
- Loudness of the finished mix is verified, but creative judgements (does the beat land, does the hook grip) stay yours

---

## 📄 License

[MIT](LICENSE) — use it, fork it, ship it.

<div align="center">

**BITS Creative** · built for agents that render, not just describe.

</div>