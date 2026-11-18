# Render and Verification

Read this before building and rendering. All commands are examples — adapt filenames to the assets you actually have. Never run a command that depends on a tool you have not checked exists.

## Contents
1. Environment check
2. Choosing a render pipeline
3. Measuring and analysing the voiceover
4. Analysing a reference video
5. Building frames deterministically
6. Audio mixing and export
7. Verifying the exported file (sync, geometry, audio, loudness)
8. Self-made background music
9. Common traps
10. Cleanup after delivery

## 1. Environment check

Run this first and plan around the result:

```bash
ffmpeg -version | head -1; ffprobe -version | head -1
ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "(libx264|aac)" || echo "WARNING: libx264/aac encoder missing"
python3 -c "import PIL, numpy; print('PIL+numpy ok')"
python3 -c "import faster_whisper; print('word-level ASR: available')" 2>/dev/null || echo "ASR: unavailable (pip install faster-whisper; without it word timing becomes an estimate -- tell the user)"
node -v
fc-list | head -20          # available fonts
[ -n "$GEMINI_API_KEY" ] && echo "GEMINI_API_KEY: present" || echo "GEMINI_API_KEY: absent"
which curl yt-dlp           # curl for TTS, yt-dlp for URL references
NC=$(timeout 8 curl -s -o /dev/null -w '%{http_code}' https://generativelanguage.googleapis.com/v1beta/models 2>/dev/null)
case "$NC" in 200|403|404) echo "network: OK (HTTP $NC)";; *) echo "network: PROBLEM (HTTP $NC / timeout)";; esac
```

Network access is often restricted. Check what actually works: if `pip` and `npm` run, extra fonts can come from `@fontsource/<font-name>`; if external downloads are blocked, use fonts already on the system. The ffmpeg version dictates which options are legal (see §6).

### Fonts ready to use (`~/.local/share/fonts/motion/`)

**This catalogue is a starting point, not a menu.** If the topic needs typography that isn't here, download it (next subsection). Picking an installed font merely because it exists is the fastest route to making every video look the same.

Quick check: `fc-list | grep -iE "poppins|fredoka|caveat"` — empty means not installed (see *Adding a new font* below).

Match to the video's mood; at most 2–3 families per video (one display + one supporting, plus handwriting if it needs an accent):

| Mood / style | Fonts | Notes |
|---|---|---|
| Modern, neutral, UI-like | `Poppins` (Regular/SemiBold/Bold), `Inter`, `Montserrat`, `Manrope`, `DM Sans`, `Figtree` | Safe standard for narration and body text |
| Playful, doodle, rounded | `Baloo 2`, `Fredoka`, `Quicksand`, `Nunito`, `Gochi Hand` | Light topics, informal education, children/youth |
| Handwriting, annotation | `Caveat`, `Patrick Hand`, `Indie Flower`, `Kalam`, `Gochi Hand` | Annotation accents, arrows, scribbles |
| Elegant / retro script | `Pacifico`, `Dancing Script`, `Shrikhand` | Wordmarks, casual headlines — never body text |
| Impact, kinetic type | `Bebas Neue`, `Anton`, `Archivo Black`, `Oswald`, `Archivo`, `Unbounded`, `Syne` | Big keywords, hooks, statistics |
| Editorial / firm serif | `Fraunces`, `Instrument Serif`, `Libre Caslon Text`, `DM Serif Display`, `Newsreader`, `Gloock` | Quotes, large figures, history or serious topics |
| Technical / data / mono | `JetBrains Mono`, `Space Mono`, `Space Grotesk`, `IBM Plex Mono`, `Sora`, `Epilogue` | Small labels, statistics, data and tech feel |
| Expressive / display | `Bricolage Grotesque`, `Shrikhand`, `Unbounded`, `Syne` | Titles that carry personality — use once per video, never for body |

Mix across categories freely, but only 2–3 families per video. The catalogue exists to widen the range of moods available, not to prescribe which one to pick.

Usage: in CSS/Remotion use the family name exactly as `fc-list` reports it (e.g. `"Baloo 2"`, `"Bebas Neue"`); in PIL use the TTF path directly (`~/.local/share/fonts/motion/Baloo2.ttf`). Variable fonts (Inter, Montserrat, Baloo2, Fredoka, Quicksand, Nunito, Caveat, DancingScript) carry every weight in one file — set `font-weight` in CSS, or in PIL call `ImageFont.truetype(..., size).set_variation_by_axes([weight])`. Poppins is not variable: use the separate files `Poppins-Regular.ttf`, `Poppins-SemiBold.ttf`, `Poppins-Bold.ttf` (there is no `Poppins.ttf`).

### Adding a new font

When the topic needs typography that isn't installed, download it. Three routes, in order:

```bash
# 1) Google Fonts via github/google/fonts — most reliable, direct TTF
#    path pattern: <licence>/<slug>/<FileName>.ttf   (licence: ofl | apache | ufl)
SLUG=outfit; FILE="Outfit%5Bwght%5D.ttf"     # %5B = [ , %5D = ] for variable fonts
curl -sL -o "/tmp/$SLUG.ttf" "https://github.com/google/fonts/raw/main/ofl/$SLUG/$FILE"

# 2) if the slug or filename is unknown, ask the API.
#    Note: listings often put the Italic file first -- filter it out.
#    Filenames containing [ ] must be URL-encoded (%5B / %5D) when downloaded.
SLUG=outfit
curl -s "https://api.github.com/repos/google/fonts/contents/ofl/$SLUG" \
  | python3 -c "
import json, sys, urllib.parse
fs = [f['name'] for f in json.load(sys.stdin) if f['name'].endswith('.ttf')]
plain = [f for f in fs if 'italic' not in f.lower()] or fs
pick = plain[0]
print('pick:', pick)
print('url :', 'https://github.com/google/fonts/raw/main/ofl/$SLUG/' + urllib.parse.quote(pick))
"

# 3) if GitHub is blocked: npm @fontsource (the package ships woff2 + ttf)
npm pack "@fontsource/$SLUG" --silent && tar -xzf fontsource-$SLUG-*.tgz && \
  find package -name "*.ttf" | head
```

Once you have the file, **verify before using it in a scene** — a broken file or a non-font failure surfaces deep into a render:

```python
from PIL import ImageFont
f = ImageFont.truetype("/tmp/outfit.ttf", 80)
print(f.getname())                       # the real family name, not the filename
d.textbbox((0, 0), "Baca Tulis", font=f)  # must return a box, not raise
f.set_variation_by_axes([700])           # only for variable fonts
```

Under 10 KB means an HTML error page, not a font. Copy it to `~/.local/share/fonts/motion/` using the family name (e.g. `Outfit.ttf`), then `fc-cache -f` if you reference it by family in CSS. For PIL a direct path is enough — no `fc-cache` needed.

Choose the font that **suits the topic**, not the one that is easiest to download. If every download fails, use what is installed and tell the user the ideal typography was not reached — never quietly fall back to a bad default (§9).

## 2. Choosing a render pipeline

The principle: render every frame deterministically from time `t = frame_index / 30`, then assemble with ffmpeg. This makes the frame count exactly duration × 30 and makes animation easy to sync to the timeline.

| Pipeline | Good for | Requires |
|---|---|---|
| Python (Pillow/numpy, optionally cairosvg or skia-python) | Text, shapes, user images, masks, parallax | PIL and numpy |
| HTML/CSS/JS + headless browser (screenshot per frame) | Complex typography, SVG, CSS blur and shadows | A working headless browser |
| Remotion / Node | React-based compositions | Node plus headless browser |
| ffmpeg filtergraph / MoviePy | Simple compositions | ffmpeg |

Pick the pipeline that best fits the composition, not the one that happens to be installed. Install missing dependencies before rendering:

```bash
pip install pillow numpy cairosvg     # Python pipeline
npx playwright install chromium       # headless browser (HTML/CSS or Remotion)
npm install                           # Remotion project deps, then npx remotion render
```

If installation fails (blocked network, no permission), stop and report it with the reason. Never silently drop to a simpler pipeline — visual quality degrades without the user knowing. Only continue with a simpler pipeline once the user agrees after hearing the consequences. If nothing runs at all, follow "Honesty about the result" in `SKILL.md`.

Store frames as `work/frames/00000.png` through `work/frames/01199.png`. To save memory you can pipe straight into ffmpeg (`-f rawvideo -pix_fmt rgb24 -s WxH -r 30 -i -`).

The build script is `render.<ext>` — `render.py` for the Python pipeline, `render.mjs` for Remotion, and so on. Same file, extension follows the pipeline; never carry two entry points.

## 3. Measuring and analysing the voiceover

Duration:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "audio/voiceover.wav"
```

Pauses and sentence boundaries (lower `noise` for noisy recordings):

```bash
ffmpeg -i "audio/voiceover.wav" -af silencedetect=noise=-35dB:d=0.25 -f null - 2>&1 | grep silence_
```

Word timing: **use speech recognition first, word-count estimation last.** Words per second exist only to sanity-check script length, never to place text.

Try ASR with per-word timestamps before giving up on estimation. `faster-whisper` is practical and runs on CPU:

```python
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio_array, language="id", word_timestamps=True)
# segs[i].start/.end per sentence; segs[i].words[j].word/.start/.end per word
```

Pass a float32 numpy array at 16 kHz mono, **not a file path**: in some environments `av` rejects `metadata_errors`, so `transcribe("file.wav")` fails with `TypeError: open() got an unexpected keyword argument 'metadata_errors'`. Decode it yourself:

```bash
ffmpeg -v error -y -i "audio/voiceover.wav" -ar 16000 -ac 1 work/voiceover-16k.wav
```

```python
import wave, numpy as np
w = wave.open("work/voiceover-16k.wav")
a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
```

Take ASR output as-is even when the transcription is wrong (e.g. "berumasuk") — you need the word boundaries, not the spelling. ASR error of ±0.1 s is invisible; word-count estimation can be off by 2 s, which is glaring.

Write the result to `work/words.json` — it is the one artefact every later stage reads (timeline, sync gate, and the optional subtitle export):

```python
import json
json.dump({
    "vo_delay": 1.0,
    "segments": [{"start": s.start, "end": s.end, "text": s.text,
                  "words": [{"word": w.word, "start": w.start, "end": w.end}
                            for w in s.words]} for s in segs]
}, open("work/words.json", "w"), ensure_ascii=False, indent=1)
```

Same file also produces a subtitle track for the platform upload, for free:

```python
def ts(t):
    ms = int(round(t * 1000))                 # integer maths: 1.9996 s must not become ",1000"
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

d = json.load(open("work/words.json"))
off = d["vo_delay"]                            # read the delay, never re-type it
# one cue per sentence, shifted onto the video timeline
open("output/<slug>.srt", "w").write("".join(
    f"{i}\n{ts(g['start'] + off)} --> {ts(g['end'] + off)}\n{g['text'].strip()}\n\n"
    for i, g in enumerate(d["segments"], 1)))
```

If ASR is unavailable or fails: split time by `silencedetect` pauses, distribute words per phrase by syllable count, and **tell the user that word timing is approximate**.

If the voiceover is delayed during mixing (e.g. starting at second 1), every ASR time must be shifted by that delay before use. Keep it as one constant (`VO_DELAY`) and derive all times from it — never add it manually per scene.

Format note: the examples use `audio/voiceover.wav`. Files the user supplies may be .mp3/.wav/.m4a — normalise to `audio/voiceover.wav` (48 kHz mono) before analysis.

If the computed total (voiceover + ~2.5 s) exceeds the cap for that orientation — **60 s portrait, 300 s landscape** — stop and ask (see stage 4 in `SKILL.md`).

The two caps are different products, not a preference: a portrait clip runs in a feed next to other 30–60 s clips, a landscape explainer runs on a platform that expects minutes. A 5-minute portrait video is not "more thorough", it is unwatchable in that context; a 60-second landscape video under-delivers its format. Pick the cap by orientation and hold it.

### When there is no voiceover

1. **Generate with Gemini TTS** (needs `GEMINI_API_KEY`). Current models: `gemini-3.8-flash-tts` (best) and `gemini-3.8-flash-lite-tts` (separate quota). If either 404s, check Google's current model list.

The TTS API is the **Interactions** endpoint today: `POST /v1beta/interactions`, style in `input[].content[].annotations[].style`, audio in `steps[].content[].data`. The older `:generateContent` + `inlineData` shape still exists but does not carry `speech_metadata`; use it only as a fallback.

Build the payload with `json.dumps` (never inline the script into a curl `-d` — quotes and newlines corrupt the JSON and trigger 400 `INVALID_ARGUMENT`):

```bash
# Write the approved script to script.txt first (multiline allowed, quoting free)
# IMPORTANT: strip structural labels like [Hook], [Inti 1], [Penutup] from what you
# send to TTS -- the model reads text verbatim and will speak them aloud.

python3 - <<'PY'
import json
script = open('script.txt').read()
# REQUIRED: `text` is verbatim ONLY, with no instructions. Instructions such as
# "Read this warmly..." placed INSIDE text get read aloud (measured: instruction +
# 3 words = 6.5 s; verbatim 3 words = 2.2 s). Delivery goes in
# annotations[].style, the official channel that stays silent.
payload = {
  "model": "gemini-3.8-flash-tts",
  "input": [{"type": "user_input", "content": [{
      "type": "text",
      "text": script,
      "annotations": [{"type": "speech_metadata", "style": "warm, clear, slightly upbeat"}]
  }]}],
  "response_format": {"type": "audio"},
  "generation_config": {"speech_config": [{"voice": "Kore"}]}
}
json.dump(payload, open('work/tts-request.json','w'), ensure_ascii=False)
PY

curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/interactions" \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d @work/tts-request.json > work/tts-response.json

python3 - <<'PY'
import json, base64, sys
d = json.load(open('work/tts-response.json'))
if 'error' in d:
    sys.exit(f"TTS failed, API response: {json.dumps(d)[:500]}")
# Interactions: last audio block wins; unary responses are complete WAV (RIFF header)
blocks = [c for s in d.get('steps', []) if s.get('type') == 'model_output'
            for c in s.get('content', []) if c.get('type') == 'audio' and c.get('data')]
if blocks:
    open('work/tts.wav','wb').write(base64.b64decode(blocks[-1]['data']))
    print('interactions: wrote work/tts.wav')
else:
    # legacy generateContent fallback
    part = d['candidates'][0]['content']['parts'][0]
    data = base64.b64decode(part['inlineData']['data'])
    mime = part['inlineData'].get('mimeType', '')
    open('work/tts.wav' if 'wav' in mime else 'work/tts.pcm','wb').write(data)
    print('legacy: mimeType', mime)
PY
# Unary requests return complete WAV. For audio/l16 (raw PCM, streaming or older
# models) decode manually: 24 kHz, mono, s16le.
[ -f work/tts.pcm ] && ffmpeg -f s16le -ar 24000 -ac 1 -i work/tts.pcm "audio/voiceover.wav" || cp work/tts.wav "audio/voiceover.wav"
```

**On 400 `INVALID_ARGUMENT`**, read the error in `work/tts-response.json`:
- `No matching speaker voice found for name: X` → wrong voice name. Check the official list: `curl -s -H "x-goog-api-key: $GEMINI_API_KEY" "https://generativelanguage.googleapis.com/v1beta/models"` or the docs at `ai.google.dev/gemini-api/docs/speech-generation#voices` (30 prebuilt voices, all usable).
- `Invalid JSON payload received` → corrupted payload, almost always an inlined script. Use the `json.dumps` pattern above.
- Anything else → inspect `field_violations` in the response and fix the named field.

Pick a voice that fits the topic. Good narration voices: `Kore` (firm), `Puck` (bright/upbeat), `Charon` (informative), `Zephyr` (clear), `Leda` (young/female). Voice names are case-sensitive. When unsure, probe with a short text. Tell the user which voice you used. The result enters the §3 pipeline exactly like a user recording.

**Sanity check after generating.** Compare the resulting duration against the script estimate (~2.5 words/second for Indonesian; ±35% tolerance). A much larger gap usually means non-script text was read aloud (instructions, `[Hook]` labels, placeholders) or the script was truncated: check `work/tts-request.json` — `text` must be the verbatim script only — then regenerate once. If it still makes no sense, tell the user before moving to the timeline.

**Optional per-phrase timing.** When kinetic per-word typography really matters: split the script into phrases, generate one request per phrase, measure each file with `ffprobe` so phrase boundaries are exact, then concatenate in order into `audio/voiceover.wav` (concat text file + `ffmpeg -f concat -i list.txt -c copy`, or re-encode to WAV). Trade-off: free-tier quota is about 10 requests/day per model, so long scripts are unrealistic to split on the free tier. Default stays one complete file.

Free-tier quota: roughly **10 requests/day per model** (not per minute). On HTTP 429 `RESOURCE_EXHAUSTED`, read the message: if it is the daily limit, do not retry that day — fall back to `gemini-3.8-flash-lite-tts` (a separate model with separate quota) and tell the user you switched. If both are exhausted, use option 2.

2. **No API key / failure:** never fabricate a voice. Ask the user to record the approved script and supply the file. If they want a draft without voice, estimated timing may be derived from word count (~2.5 words/second), clearly labelled as a draft and still respecting `MAX_DUR`.

## 4. Analysing a reference video

The reference comes from the user (file or URL) or is found on Pinterest (subsection below). Once `assets/reference.mp4` exists, analyse it:

```bash
ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration -of default=nw=1 "assets/reference.mp4"
mkdir -p work/ref && ffmpeg -i "assets/reference.mp4" -vf "fps=2,scale=480:-1" work/ref/%03d.png

# single-page contact sheet for fast reading
ffmpeg -framerate 2 -i work/ref/%03d.png -vf "scale=320:-1,tile=6x5" work/ref/contact.png
```

Read the extracted frames (a contact sheet works well) for palette, typography, composition, and cut rhythm. Take principles, not copies. The reference's orientation and aspect become the default output orientation.

Cut rhythm is measurable — do not rely on impression. Count the actual cuts and their spacing, then decide whether to sit near or against that rhythm:

```bash
# scene changes (threshold 0.3 = a real cut, not a fade)
ffmpeg -i "assets/reference.mp4" -vf "select='gt(scene,0.3)',showinfo" -an -f null - 2>&1 \
  | grep -o "pts_time:[0-9.]*" | cut -d: -f2 \
  | awk 'NR==1{printf "first cut at %.2fs\n", $1; p=$1; next}
         {printf "cut at %.2fs (gap %.2fs)\n", $1, $1-p; p=$1; g+=$1-p; n++}
         END{if(n) printf "average gap %.2fs over %d gaps\n", g/n, n}'
```

Average gap plus the shortest and longest gap describe the pace in numbers; that is what you match or deliberately break.

For a URL from the user, download with `yt-dlp "<url>" -o "assets/reference.mp4"` before analysing.

### Finding a reference on Pinterest (when the user gives none)

If the user supplies no reference file or URL (or asks for everything automatic), search in this order — do not stop at the first failure:

1. **Search with `motion graphics` plus the topic.** Queries like `pinterest.com pin <topic keywords> motion graphics video` (try Indonesian and English). Collect 3–5 candidate video pins.
2. **Judge fit, not just relevance.** Compare each candidate against the topic's character: is the palette right for this subject? Is the typography at the right register (serious, playful, archival, technical)? Is the motion pace suited to the narration? Pick the closest.
3. **If nothing fits well, take something loosely related** — same broad mood or same kind of subject matter, even if the content differs. A calm paper-craft pin is a better style anchor for a serious topic than an energetic neon clip that happens to share keywords.
4. **If even that fails, design the style yourself.** Choose palette, typography, and motion language from the topic and say so in one line, e.g. `Tidak ada acuan yang cocok, jadi saya tentukan sendiri: latar gelap, aksen hangat, tipografi tebal.` A self-designed style is legitimate; an unannounced one is not.

Download candidates one at a time until one works:

```bash
yt-dlp "<pin-url>" -o "assets/reference.mp4"
```

Filter before use — check with `ffprobe` and discard candidates that: run under 5 s or over 90 s, sit below the planned output resolution, have no video stream, or are visually unusable. Discarded → try the next.

**When the user supplies the Pinterest URL themselves**, skip the search entirely: that URL is the reference. Download it with the same command. If it fails (region block, removed pin, no video stream), say so once, then fall back to the search order above — never silently drop the style anchor.

Self-found quality is uncontrolled. Required: tell the user which reference you picked (URL plus a one-line reason) before analysing, and treat it as inspiration, not a mould.

### Sourcing images

Three sources; choose per scene by whatever communicates fastest.

1. **User images** — always the primary material when supplied.
2. **Images you find and download** — for concrete subjects the script names: a place, an object, a document, a historical photo.
3. **Code-drawn graphics** — shapes, icons, vector illustration, diagrams. Always available, always yours.

Mixing is normal: a downloaded photograph with code-drawn annotations, a code-drawn diagram holding one user image. Never pass a found image off as the user's own.

When downloading, verify before use:

```bash
# resolution must be at least the output resolution after any crop
python3 -c "from PIL import Image; im=Image.open('candidate.png'); print(im.size)"
```

Checklist — discard and search again if any fails:
- **Subject matches** what the script says, not merely the query word.
- **Resolution** at least the output size in the dimension it will occupy. A 600 px image stretched to 1080 px is visibly broken.
- **No watermark, no overlaid text, no visible stock-site branding.**
- **Licence permits use.** Prefer public domain, CC0, or an explicit permissive licence; note the source and licence in the delivery message.
- **No person identifiable in a way the video would misrepresent.** If unsure, choose another image or draw it in code.

Save as `assets/image-01.png`, `image-02.png`, … in the order they enter the video. Record every source URL and hand it to the user in the delivery message.

If nothing suitable exists or the licence is unclear, **draw it in code** rather than ship a wrong or low-resolution asset.

## 5. Building frames deterministically

- Write one `render(t)` function that draws the whole frame from time alone, with no hidden state and no randomness that changes between calls (use a fixed seed).
- Define easing functions (ease-out, ease-in-out, overshoot) and use them throughout. Avoid constant speed unless it is deliberate.
- **Motion is required (QC gate, not optional):** every second of video has at least one moving element. No static slide is allowed. If a scene is "still", apply micro camera motion (zoom drift or a gentle pan across the scene). Keywords and important figures (e.g. "92 juta") must get a motion emphasis right as the word is spoken — the amount and form of that emphasis is taste (scale pop, colour, weight, position, or a combination), and the scale MUST decay back to 100% before the next pop; a persistent overshoot (e.g. a word stuck at 120%) makes it collide with neighbours. Measure each word's width slot with the font actually used (keyword ≠ body); a word appearing twice in one scene needs its own time for each appearance — never map both through one dict entry. Encoder note: element POSITION motion (x/y shift) is more reliable than radius/scale alone — a solid antialias-free circle that merely pulses in radius often changes not a single pixel, and motion under ~10 px can be quantised away at CRF 18+ (§9).
- Easing formulas you may use or replace with whatever suits the feel: `easeOutCubic(u) = 1-(1-u)**3`; `easeInOutCubic(u) = u<0.5 ? 4*u**3 : 1-((-2*u+2)**3)/2`; overshoot/back-out: `1 + 2.7*(u-1)**3 + 1.7*(u-1)**2`.

  **No duration or overshoot figure is mandatory.** Entry duration, overshoot size, and rhythm are taste decisions — pick what matches the narration pace and reference mood. Only these invariants are required, because breaking them breaks the result rather than merely changing the feel:
  - a scale pop **decays back to 100%** before the next pop (otherwise words collide);
  - avoid constant speed unless deliberate;
  - idle elements move in **position**, not just radius/scale (see the encoder note above).
- Draw icons and diagrams from code shapes (donut, bar, briefcase, bulb) — never text or emoji. Backgrounds may alternate between scenes (light/dark) with one consistent accent colour.
- Simulate motion blur by averaging several sub-frames at slightly different times.
- Render in parallel with resume: because frames are deterministic, draw with several workers (`multiprocessing`, 4–8 processes) and skip frames whose PNG already exists and is non-empty. If a render dies, rerun the same script — only missing frames are redrawn.

  **Budget the disk before a long render.** A 300 s landscape video is 9000 PNGs. Measured: 9000 frames at 160×90 came to 21 MB, and 1080×1920 scales that by ~144× — **≈3 GB on disk**, before the MP4. Check free space first and delete `work/frames/` right after the encode:

  ```bash
  df -h . | tail -1
  ls work/frames | wc -l          # expect exactly FRAMES
  ```

  If space is tight, pipe raw frames straight into ffmpeg instead of writing PNGs (`-f rawvideo -pix_fmt rgb24 -s WxH -r 30 -i -`); you lose resume, so only do it once the render is stable.
- Load the stage-5 timeline as data (a list of segments with start/end times) so it is easy to retune.
- **One absolute-time table as the single source.** Every element appearance time (`{label: video_seconds}`) lives in one table, and scenes read from it — scenes never keep their own entry offsets. Scene boundaries derive from ASR sentence boundaries, not typed separately. When each scene carries its own numbers, shifting one sentence means shifting six numbers and the drift returns in the next scene. Never hard-code label times to seconds while beats can still change: use `B_VIDEO[key] - scene_start` computed at render time, not a frozen `0.55`.
- Render frame 0 through (frame count − 1). The final frame must still hold a clear closing visual, never an empty screen.

## 6. Audio mixing and export

Duration follows the voiceover. Compute total duration and frame count first (rules in stage 4 of `SKILL.md`):

Set the cap first, from the orientation. Portrait `1080×1920` → **60 s**; landscape `1920×1080` → **300 s (5 min)**. Raise it only when the user explicitly names a target.

```bash
ORIENT=landscape                # portrait | landscape -- read it from stage 2, never guess
case "$ORIENT" in
  portrait)  MAX_DUR=60 ;;
  landscape) MAX_DUR=300 ;;
esac
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "audio/voiceover.wav")
DUR=$(awk -v v="$VO_DUR" 'BEGIN{t=v+2.5; d=int(t); if (d<t) d++; print d}')
FRAMES=$((DUR*30))
FADE_ST=$(awk -v d="$DUR" 'BEGIN{print d-2.5}')
mkdir -p work
echo "orient=$ORIENT  voiceover=$VO_DUR  total=$DUR s  frames=$FRAMES  cap=$MAX_DUR"
awk -v d="$DUR" -v m="$MAX_DUR" -v o="$ORIENT" \
  'BEGIN{if(d>m) print "OVER CAP "m" S for "o": stop and ask the user"}'
```

An explicit user target replaces `MAX_DUR` for that run instead of the `case` result — set `MAX_DUR` to the target and recompute.

A 5-minute landscape video is 9000 frames, not 1800. Plan for it: render with the resume worker (§5), and give the contact sheet three seconds per cell (§7) so it still fits one image.

Use those `DUR` and `FRAMES` values for the whole render (frames drawn, timeline, export). The voiceover is delayed to start at second 1 (`adelay`), padded to the end, and the music is looped, trimmed to the video length, lowered in volume, and ducked under speech.

**Check the frame sequence is contiguous before encoding.** Resume-skipping leaves holes when a worker dies, and `%05d` input silently stops at the first missing index — a 5-frame sequence with frame 00002 missing encoded only 2 frames. Measure:

```python
import os
FRAMES = 840
missing = [i for i in range(FRAMES) if not os.path.exists(f"work/frames/{i:05d}.png")]
assert not missing, f"{len(missing)} frames missing, first: {missing[:3]}"
```

**Three steps — never merged into one `filter_complex`.** Combining `loudnorm` with `apad` in one chain kills the audio tail: loudnorm also processes the padding, dropping the tail to −91 dB (measured on the single-chain example that used to be here: `silence_start 40.86` in a 43 s video). So split:

```bash
# 1) normalise the voiceover into its own file
ffmpeg -y -i "audio/voiceover.wav" -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 work/voiceover-norm.wav

# 2) prepare the music in its own file: loop to the full length, level, fade to a
#    floor (never to absolute zero). Never add afade=t=in -- music starting from
#    silence reads as unintended silence to the §7 gate.
#    -stream_loop -1 is what makes "loop the music" true: a 10 s track on a 28 s
#    video without it leaves 18 s of dead air (measured).
ffmpeg -y -stream_loop -1 -i "audio/music.wav" \
  -af "volume='0.40*(1-0.94*min(max(0,(t-$FADE_ST)/2.5),1))':eval=frame" \
  -ar 48000 -t $DUR work/music-norm.wav

# 3) then combine: adelay + apad + duck + amix
ffmpeg -y -framerate 30 -start_number 0 -i work/frames/%05d.png \
  -i work/voiceover-norm.wav -i work/music-norm.wav \
  -filter_complex "\
[1:a]adelay=1000:all=1,apad=whole_dur=$DUR,atrim=0:$DUR,asetpts=PTS-STARTPTS,asplit=2[vo1][vo2];\
[2:a]atrim=0:$DUR,asetpts=PTS-STARTPTS[bg];\
[bg][vo1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[duck];\
[duck][vo2]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,alimiter=limit=0.85:level=0[aout]" \
  -map 0:v -map "[aout]" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -profile:v high -g 60 -r 30 -frames:v $FRAMES \
  -c:a aac -b:a 192k -ac 2 -ar 48000 -t $DUR \
  -movflags +faststart "output/<slug>.mp4"
```

`FADE_ST` derives from video duration, not music duration: `DUR - 2.5` (the `awk` recipe above already does this). The fade ends near the final second but must not reach absolute zero — measured, the old `afade=t=out:st=DUR-2.5:d=2.5` ended exactly at zero and left the last **0.8 s at −61.7 dB**, which the gate treats as dead air. The expression above fades to a −32 dB floor instead; measured last-0.5-s level **−45 dB with music echoing the tail**, which passes. `-ac 2` matters because a mono voiceover otherwise exports a mono AAC track; measured `channels=1` without it, `channels=2` with it.

Notes:
- `loudnorm` equalises voiceover loudness (target I=-16 LUFS, TP=-1.5) so user recordings and TTS results sit at the same level. It works internally at 192 kHz; `-ar 48000` in step 1 restores the sample rate.
- `amix`'s `normalize` option predates 7.0 (it exists in 5.1). What is version-sensitive is only the *result* of combining options — so keep exactly one loudness correction in the chain and confirm with `volumedetect`/`ebur128` instead of trusting the formula.
- Without music: skip step 2, and in step 3 use only `[1:a]adelay=1000:all=1,apad=whole_dur=$DUR,atrim=0:$DUR,asetpts=PTS-STARTPTS[aout]`. Do **not** add a closing `afade`: `apad` already fills the tail with digital zero and an extra fade changes nothing except the chance of masking a real defect. Without music the tail is silent by definition — the gate in §7 allows it (it measures the floor only when music is present).
- Without voiceover (draft): use music only, and label it a draft.
- If the input is raw video rather than an image sequence, still force `-r 30` and `-frames:v $FRAMES`.
- If the user sets their own target duration, replace `DUR` with it (as long as the voiceover fits), set `MAX_DUR` at least to that target, and recompute `FRAMES` and `FADE_ST` with the same formulas.
- `-g 60` (2 s GOP) plus `-profile:v high` keeps seeking responsive and the file playable on every platform that accepts H.264; `+faststart` moves the index to the front.

## 7. Verifying the exported file

Never trust the duration shown by an editor or a script. Measure the MP4 itself:

```bash
# container duration, codec, resolution, fps, frame count
ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,duration,nb_frames -of default=nw=1 output/<slug>.mp4

# count frames actually decoded (must equal $FRAMES)
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 output/<slug>.mp4
```

Target: container ≈ `DUR` seconds (to three decimals), `FRAMES` video frames, 30 fps, H.264 + AAC, resolution as planned, and `DUR` inside the cap for the orientation (60 s portrait / 300 s landscape). The AAC encoder adds slight padding so the audio stream duration can differ by milliseconds; the container duration and video frame count are the evidence. Report the real numbers. If they miss, fix and re-export — never round the report.

Detect unintended problems:

```bash
# black frames -- pix_th=0.02, NOT 0.05. A legitimate dark background such as
# 0x0B0B0F (luma 0.043) is reported as "black" at the 0.05 default; measured,
# true 0x000000 is still caught at 0.02, so 0.02 catches defects without
# flagging dark design. Use d=0.5 so single transition frames are ignored.
ffmpeg -i output/<slug>.mp4 -vf blackdetect=d=0.5:pix_th=0.02 -an -f null - 2>&1 | grep black_
# frozen frames — n=0: only truly identical frames count as a freeze.
# NEVER use n=-60dB: on flat graphics, micro-changes between frames (thousands of
# pixels, max diff ~220) still get reported as a freeze -> false positives on video
# that clearly moves.
ffmpeg -i output/<slug>.mp4 -vf freezedetect=n=0:d=1.0 -an -f null - 2>&1 | grep freeze_
# raw silence dump and peak level (read it; the pass/fail rule is the windowed
# gate below -- a silent tail is legitimate when the video has no music)
ffmpeg -i output/<slug>.mp4 -af silencedetect=noise=-50dB:d=0.5 -vn -f null - 2>&1 | grep silence_
ffmpeg -i output/<slug>.mp4 -af volumedetect -vn -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

**Motion gate:** `freezedetect=n=0:d=1.0` must come back empty, except for deliberate, timeline-documented rests. A freeze means the render is genuinely still — go back to §5, add micro camera motion or element animation, re-render. Report this gate result alongside the duration.

How many rests are allowed scales with length, because a five-minute explainer needs breathing room a 60-second clip does not. The gate is measurable either way — it just counts longer videos differently:

| Runtime | Allowed rests | Each |
|---|---|---|
| ≤60 s | 1 | ≤1.5 s |
| >60 s | ≤1 per full minute of runtime | ≤2.5 s |

Where they go is your call. A rest is a beat of calm after a point lands, never a stalled scene in the middle of an explanation, and every rest is written in the timeline with its reason — the gate stays a gate, it just knows the video is longer now.

The lead-in is not covered by this gate: the first `VO_DELAY` (1 s) holds the title/accent and is allowed to sit still, because nothing is being narrated yet. A freeze reported **entirely** inside `0..1 s` is not a defect; a freeze that reaches into speech is.

**Audio gate — windowed, not whole-file.** A whole-file `silencedetect must be empty` contradicts the spec: the tail after speech is ~1.5 s of legitimate silence whenever there is no music, so the plain command can never pass. Two checks, both measured on the export:

```bash
VO_DELAY=1              # speech starts here
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 audio/voiceover.wav)
HAS_MUSIC=1             # 0 when the video has no music track
SE=$(awk -v a=$VO_DELAY -v b="$VO_DUR" 'BEGIN{printf "%.2f", a+b}')

# 1) no dead air inside the speech region
ffmpeg -i output/<slug>.mp4 -af silencedetect=noise=-50dB:d=0.5 -vn -f null - 2>&1 \
  | grep silence_start \
  | awk -v se="$SE" '$NF>0.1 && $NF<se-0.2 {print "FAIL dead air at " $NF "s"; bad=1} END{exit bad}'

# 2) with music, the tail must still carry sound (music died early = defect)
if [ "$HAS_MUSIC" = 1 ]; then
  T=$(ffmpeg -hide_banner -sseof -0.5 -i output/<slug>.mp4 -af volumedetect -vn -f null - 2>&1 \
      | sed -n 's/.*mean_volume: \(-\?[0-9.]*\) dB/\1/p')
  awk -v t="$T" 'BEGIN{if(t<-50) {print "FAIL tail floor "t" dB (music died early)";exit 1}
    print "tail floor "t" dB OK"}'
fi
```

Verified on real builds: a music track that stops 1 s early reads **−61.7 dB** in the last half second and fails; the same video with music carried to the end reads **−45 dB** and passes; a 0.8 s hole inside narration is caught by check 1; a video with no music passes both because the silent tail is expected.

`silence_start` prints the time as the last field, so use `$NF` — the logger prefix `[silencedetect @ 0x…]` shifts every other column.

The historical −91 dB tail (from `loudnorm` inline with `apad`) is still the most common cause of check 2 failing when music is present. Normalise the voiceover into its own file first, then mix (§6).

**Loudness gate.** The voiceover is normalised, but the finished mix is not: quiet music leaves the whole file quiet, and every platform then re-normalises it inconsistently. Measure the export:

```bash
ffmpeg -hide_banner -nostats -i output/<slug>.mp4 -af ebur128=peak=true -f null - 2>&1 \
  | grep -E "^\s+(I|Peak):" | sed 's/^ *//'
```

Target: **I between −17 and −14 LUFS** (a −16 LUFS voiceover with ducked music lands near −16, measured −16.0 on a 28 s build) and **true peak ≤ −1 dBTP**. A build with the voiceover turned down to 15% measured **−32.5 LUFS** — that is the failure this gate exists for. Report both numbers in the delivery message; `max_volume` alone does not describe loudness.

**Write the sync, geometry, and repetition checks yourself when needed.** The rules are complete in prose below and in `GUIDE.md` §2: safe area 4%, two-tier glyph height, contrast per role, collision cover, repetition patterns. Translate them into code against your renderer's data structures.

Suggested shape: collect every text bbox during render, then inspect at the end. What matters is that the output is **advice, not PASS/FAIL** — the decision stays yours.

How to capture drawn text, by pipeline:

| Pipeline | Capture text | Capture frames |
|---|---|---|
| Python/PIL | wrap the text-drawing method | call the render function directly |
| HTML/Playwright | `page.evaluate` enumerating text elements' `innerText` | screenshot per `t` |
| Remotion/Node | collect from `useCurrentFrame` → record elements in components | `renderStill` per `t` |
| Canvas/JS | wrap `ctx.fillText` | `toDataURL` per `t` |

If a pipeline cannot record which text was drawn, the sync gate cannot run — in that case verify timing from the **time table** the renderer uses (find values satisfying `text_time >= word_time`) and tell the user the check was table-based, not pixel-based.

**Sync gate.** For each key text prove two things: it exists at `word_time + 0.10` and does not exist at `word_time − 0.15` (the window is tunable; what matters is its asymmetry — 0.1 s late beats appearing early). Capture all drawn text by wrapping the text call, then match by text name:

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

for word_time, text in checks:
    assert text in at(word_time + 0.10), f"late or missing: {text} @ {word_time}"
    assert text not in at(word_time - 0.15), f"appears too early: {text} @ {word_time}"
```

On failure, fix the time table — never nudge numbers inside a scene (§5).

**Geometry gate.** Three checks, all using the font metrics actually in play:

```python
# 1) safe area: no glyph crosses 4% of the frame edge (same value as GUIDE.md §2).
#    Use textbbox with the SAME anchor you draw with. Without anchor="mm" the box is
#    relative to the top-left origin (measured: drawing "92" at (200,100) returns
#    (200,111,284,157) at the default anchor), so the comparison is meaningless.
bb = d.textbbox((px, py), s, font=f, anchor="mm")
assert bb[0] > W * 0.04 and bb[2] < W * 0.96, f"crosses side safe area: {s}"
assert bb[1] > H * 0.04 and bb[3] < H * 0.96, f"crosses top/bottom safe area: {s}"

# 1b) legibility: GLYPH height from the measured box, not the size argument.
#     Two tiers per GUIDE.md §2, against the SHORT side so portrait and landscape
#     share one number: short side 1920 -> primary 77px, supporting 48px;
#     short side 1080 -> primary 43px, supporting 27px.
S = min(W, H)
gh = bb[3] - bb[1]
assert gh >= S * (0.04 if is_main else 0.025), f"text too small: {s} ({gh}px)"

# 2) text collision: coverage, not IoU.
#    IoU < 0.16 is too loose: two 100px-tall lines overlapping by 20px score 0.111
#    and pass while visibly colliding. Measure how much of the SMALLER box is
#    covered instead -- same pair scores 0.20, and a 5px overlap still scores 0.05.
def cover(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    return inter / min((a[2]-a[0])*(a[3]-a[1]), (b[2]-b[0])*(b[3]-b[1]))

# identical boxes are a deliberate re-draw (text over its own highlight) -- skip.
# Only glyph boxes are compared against each other, never against the panel or card
# behind them, so a label sitting on a card is not a collision.
if bb_a != bb_b:
    assert cover(bb_a, bb_b) < 0.02, f"text overlaps: {s}"

# 3) contrast: WCAG ratio, threshold tied to the text ROLE (GUIDE.md §2),
#    not to pixel size -- small moving text reads worse than static text
assert ratio(fill, bg_color) >= (3.0 if is_main else 4.5), f"contrast too low: {s}"
```

A label sitting inside a title block legitimately scores cover 1.0 — that is why the identical-box exclusion exists and why this is advice to read, not a hard fail. What it must catch: two independent lines that share any real band of pixels.

**Contrast gate** uses the same WCAG formula as `GUIDE.md` §2, with the threshold tied to the text's role: **3.0:1** for primary text, **4.5:1** for supporting text. Measured pairs, reproducible with the formula above:

| Foreground | Background | Ratio | Verdict |
|---|---|---|---|
| `(166, 82, 70)` darkened accent | `(245, 241, 234)` cream | **4.76:1** | passes supporting |
| `(166, 82, 70)` | `(250, 246, 238)` cream | **4.97:1** | passes supporting |
| `(238, 150, 130)` light salmon | `(245, 241, 234)` cream | **2.00:1** | hard fail |
| `(20, 20, 20)` ink | `(250, 244, 232)` cream | **16.8:1** | passes everything |

Any accent below ~3:1 on cream fails for text of any role; the fix is to darken the accent until the measured ratio clears, not to lower the threshold. When this gate rejects, change the colour, move the text onto a dark background, or place a solid panel behind it.

### Third gate: repetition pattern (flags, never rejects)

This gate **does not judge**. It surfaces scenes with the same structure; you decide.

```python
# for each scene, take a structural signature (not content):
#   mass_position : where the ink centroid sits (left/centre/right, top/middle/bottom)
#   density       : ratio of inked pixels
#   background    : light / dark
#
# "ink" must mean "differs from the background", not "darker than 110". On a dark
# background with light text, `g < 110` selects the BACKGROUND and every scene
# returns the same centroid (measured: 0.5, 0.5 on two completely different
# layouts). Compare against the frame's own modal luma instead.
def signature(frame_rgb):
    g = np.array(frame_rgb.convert("L")).astype(int)
    bg = np.bincount(g.ravel()).argmax()          # modal value = background
    ink = np.abs(g - bg) > 40                      # anything that is not background
    if ink.sum() < 500:
        return ("empty",)
    ys, xs = np.nonzero(ink)
    h, w = g.shape
    return (
        round(xs.mean() / w, 1),                   # 0.0 left .. 1.0 right
        round(ys.mean() / h, 1),
        round(ink.mean(), 2),
        "dark" if bg < 100 else "light",
    )

sigs = [signature(f) for f in mid_frame_of_each_scene]
for i in range(1, len(sigs)):
    if sigs[i] == sigs[i - 1]:
        print(f"scenes {i} and {i+1} share a pattern: {sigs[i]}")
```

Vary composition on purpose, and record it: keep a small per-scene vector (composition zone, density, scale, background) and refuse to leave **three consecutive scenes** on the same vector. Two in a row can be a deliberate pair; three is the "same layout, different words" failure `GUIDE.md` §6 warns about.

If two consecutive scenes share a pattern, **do not change them automatically**. Write one sentence in the timeline:

- "the motif is deliberate — these two scenes are a pair" → leave it
- "coincidence, no other idea" → change composition, density, or scale

Deliberate repetition is often good and always legitimate. What must surface is repetition born of no decision. The gate forces that decision to be written down; it never homogenises the output.

The same text drawn twice at the same position (e.g. text over a highlight block) is IoU 1.0 — deliberate; exclude identical pairs. Run every gate before export, not after; re-rendering one scene is cheaper than re-rendering a video.

Two things that make these gates mislead:
- `freezedetect` with `n=-60dB` (the default) FALSE POSITIVES on motion graphics: decoded frames inside the "frozen" range can change thousands of pixels per frame (idle elements, breathing dots) yet the filter still reports a freeze because the threshold is too high for flat graphics. Always use `n=0`.
- Source frames move but the MP4 reports a freeze at the same point? That is the encoder: small elements (radius <15 px, motion <10 px/frame) in a large flat area can be quantised away at CRF 18+. Enlarge the idle element or drop CRF to 16 — do not add new motion.

`max_volume` touching 0 dB means clipping risk — and if `alimiter` is installed yet max is still 0 dB, the cause is almost certainly its default `level` option (§9).

Visual check: extract frames at key points (start, each scene change, end) and look for yourself at legibility, spelling, cropping, and collisions.

```bash
mkdir -p work/check          # ffmpeg will not create it -- "Could not open file" otherwise
ffmpeg -i output/<slug>.mp4 -vf "fps=1/2,scale=640:-1" work/check/%02d.png
ffmpeg -ss $(awk -v d="$DUR" 'BEGIN{print d-0.1}') -i output/<slug>.mp4 -frames:v 1 work/check/last.png
```

The contact sheet needs `-frames:v 1`: a `tile` grid is one image, and without it ffmpeg tries to write that image once per input frame and dies at the second one (`Cannot write more than one file with the same name`, exit −22).

The grid must also cover the whole video, and the cap is now 300 s for landscape — 5× the old 60 s. `fps=1` at `8x8` stops at 64 s, so a 5-minute video silently loses its last four minutes. Size both the interval and the grid from `DUR`:

```bash
CELLS=$(( (DUR + 2) / 3 ))                       # one thumbnail per 3 s
GRID=$(python3 -c "import math; print(max(1, math.ceil(math.sqrt($CELLS))))")
ffmpeg -i output/<slug>.mp4 -vf "fps=1/3,scale=240:-1,tile=${GRID}x${GRID}" \
  -frames:v 1 work/check/sheet.png
```

Measured: 60 s → 20 cells in 5×5; 300 s → 100 cells in 10×10. Never hand-tile a fixed grid for a duration that can now reach five minutes.

## 8. Self-made background music

Only when the user supplies none. Build a simple ambient pad with numpy or ffmpeg's `aevalsrc`/`sine`: several chord tones layered at low volume, plus a light pulse whose tempo suits the visual rhythm (choose it yourself; if you want a beat accent, align it with scene changes). Export as 48 kHz WAV, then feed it into the mix above.

Tell the user plainly that this is simple synthesised music, not a professional composition, and suggest royalty-free music for a richer result.

Optional, sparing synthetic SFX for transitions — a whoosh, for example:

```bash
ffmpeg -f lavfi -i "anoisesrc=d=0.4:c=pink:a=0.5" -af "afade=t=in:d=0.1,afade=t=out:st=0.2:d=0.2,volume=0.3" -ar 48000 work/whoosh.wav
```

Use at most a few per video, always below the voiceover level, and tell the user the SFX is synthetic.

## 9. Common traps

- **VFR (variable frame rate):** force CFR with `-r 30`. Verify `r_frame_rate` and `avg_frame_rate` both read 30/1.
- **Duration off by a frame:** usually the drawn frame count differs from `DUR × 30`. Recount before encoding.
- **Audio longer than video** (or the reverse): use `apad=whole_dur=$DUR` and `atrim=0:$DUR` as in the example, plus `-t $DUR`.
- **Font not found:** check `fc-list`, or download through `npm` — never silently fall back to an ugly default.
- **Indonesian text clipped at the edge:** measure width with the font's own measuring function, never by eye.
- **File very large:** raise CRF (e.g. 20–22); never lower the resolution.
- **`alimiter` installed yet `max_volume` stays 0 dB:** alimiter's default `level` is 1 (auto-level) — after limiting, the signal is normalised BACK to 0 dBFS. Use `alimiter=limit=0.85:level=0`. Measured: `limit=0.79` alone still yields max 0.0 dB; with `level=0` it yields −1.3 dB.
- **`amix` + `volume` — never use both.** Measured on ffmpeg 7.1 with a `loudnorm`-processed voiceover (−17.0 dB mean, −1.5 max): `amix` default `normalize=1` → −24.5 dB; `amix` default + `volume=2` → −18.5 dB; `amix normalize=0` → −18.5 dB (**identical**); `normalize=0` + `volume=2` → −12.5 dB, max **0.0 dB (clipping)**.

  Conclusion: `volume=2` with the default `normalize` equals `normalize=0`, so the §6 example is safe on both 6.x and 7.x. The danger is combining them. Pick one, then measure with `volumedetect` — never trust the formula, because `amix` defaults change between versions. If `max_volume` hits 0.0 dB despite `alimiter`, check whether `volume` and `normalize=0` are both applied, then check alimiter's `level` option.
- **`loudnorm` inline + `apad` = dead audio tail:** never combine them in one `filter_complex`. Normalise the voiceover into a separate file first (three-step recipe in §6, gate in §7). Measured: one chain → `silence_start 40.86` in a 43 s video, tail −91 dB; three steps → tail −25 to −33 dB, no dead air inside the speech region.
- **`afade=t=in` on music trips the audio tail gate:** music starting from silence reads as unintended silence (measured: `silence_start 0`, 0.53 s). Let music enter at full level; fade only at the end.
- **`afade=t=out` ending exactly at the last frame is silence, not a fade-out:** measured, `st=DUR-2.5:d=2.5` on a 28 s video left the final **0.8 s at −61.7 dB** — indistinguishable from the music having stopped. Fade to a floor with a `volume` expression (§6), or stop the fade earlier.
- **Music shorter than the video:** without `-stream_loop -1` the track simply ends and the rest is dead air (measured: 10 s track on a 28 s video → `silence_start 26.0`). The pipeline promises the music is looped; loop it in step 2.
- **Mono output from a mono voiceover:** `-ac 2` on export. Measured `channels=1` without it; platforms accept mono but stereo costs nothing.
- **`silencedetect` `$3` is not the timestamp.** The logger writes `[silencedetect @ 0x…] silence_start: 12.34`, so the time is the **last** field (`$NF`). Filtering on `$3` silently matches nothing and every gate appears to pass.
- **`textbbox` with `anchor` is not the glyph shape:** treating bb[1]/bb[3] as symmetric around the anchor point is wrong for numerals and capital text. Always compute the bbox centre offset from the anchor before placing inside a shape (see `GUIDE.md` §2). And always pass the **same anchor** you draw with — at the default anchor the returned box is relative to the draw origin, not the canvas, so `assert bb[0] > W*0.04` compares an x-offset to a canvas margin.
- **`blackdetect` default `pix_th=0.1` flags legitimate dark design:** a `0x0B0B0F` background (luma 0.043) is reported as black from `pix_th=0.05` upward; at `0.02` it is clean while true `0x000000` is still caught. Use `pix_th=0.02`.
- **`tile` without `-frames:v 1`** writes the grid once per input frame and fails on the second (`Cannot write more than one file with the same name`, exit −22). Also make sure the tile grid has room: a fixed `8x8` at `fps=1` covers only 64 s, so a 300 s landscape video shows its first minute and silently drops the other four. Size interval and grid from `DUR` (§7).
- **Missing frames mid-sequence truncate the encode:** `-i work/frames/%05d.png` stops at the first gap, and `-pattern_type glob` reorders but does not fill. Measured: a 5-file sequence with `00002.png` missing encoded 2 frames. Assert contiguity before encoding (§6).
- **SRT timestamps from float seconds misformat:** `int(round((s % 1) * 1000))` yields `",1000"` for 1.9996 s, which players reject. Convert to integer milliseconds first, then `divmod` (recipe in §3).
- **Small idle elements quantised by the encoder:** dots/particles under ~15 px radius that merely pulse in a large flat area can vanish after encoding (CRF 18+), leaving identical decoded frames → a real freeze in the MP4 even though the renderer drew motion. Enlarge the element and move its position, not just its radius (a solid antialias-free circle changing radius often alters no pixel at all).

## 10. Cleanup after delivery

`work/` holds every intermediate file: `frames/`, `ref/`, `check/`, normalised audio, and timing JSON. It can reach hundreds of megabytes and the user does not need it. Once the video is verified and delivered, delete the whole `work/`; keep only `script.txt`, `render.<ext>`, `audio/`, `assets/`, and `output/` (plus `output/<slug>.srt` when you generated subtitles). Mention in the delivery message that intermediates were cleaned up.