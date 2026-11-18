# Render and Verification

Read this before building and rendering. All commands are examples — adapt filenames to the assets you actually have. Never run a command that depends on a tool you have not checked exists.

## Contents
1. Environment check
2. Choosing a render pipeline
3. Measuring and analysing the voiceover
4. Analysing a reference video
5. Building frames deterministically
6. Audio mixing and export
7. Verifying the exported file (sync, geometry, audio tail)
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

Quick check: `fc-list | grep -iE "poppins|fredoka|caveat"` — empty means not installed (see §9).

Match to the video's mood; at most 2–3 families per video (one display + one supporting, plus handwriting if it needs an accent):

| Mood / style | Fonts | Notes |
|---|---|---|
| Modern, neutral, UI-like | `Poppins` (Regular/SemiBold/Bold), `Inter`, `Montserrat`, `Manrope` | Safe standard for narration and body text |
| Playful, doodle, rounded | `Baloo 2`, `Fredoka`, `Quicksand`, `Nunito` | Light topics, informal education, children/youth |
| Handwriting, annotation | `Caveat`, `Patrick Hand`, `Indie Flower`, `Kalam` | Annotation accents, arrows, scribbles |
| Elegant / retro script | `Pacifico`, `Dancing Script` | Wordmarks, casual headlines — never body text |
| Impact, kinetic type | `Bebas Neue`, `Anton`, `Archivo Black`, `Oswald` | Big keywords, hooks, statistics |
| Editorial / firm serif | `Fraunces`, `Instrument Serif`, `Libre Caslon Text` | Quotes, large figures, history or serious topics |
| Technical / data / mono | `JetBrains Mono`, `Space Mono`, `Space Grotesk` | Small labels, statistics, data and tech feel |

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

If ASR is unavailable or fails: split time by `silencedetect` pauses, distribute words per phrase by syllable count, and **tell the user that word timing is approximate**.

If the voiceover is delayed during mixing (e.g. starting at second 1), every ASR time must be shifted by that delay before use. Keep it as one constant (`VO_DELAY`) and derive all times from it — never add it manually per scene.

Format note: the examples use `audio/voiceover.wav`. Files the user supplies may be .mp3/.wav/.m4a — normalise to `audio/voiceover.wav` (48 kHz mono) before analysis.

If the computed total (voiceover + ~2.5 s) exceeds `MAX_DUR` (default 60 s), stop and ask (see stage 4 in `SKILL.md`).

### When there is no voiceover

1. **Generate with Gemini TTS** (needs `GEMINI_API_KEY`; example uses `gemini-3.8-flash-tts` — if it 404s, check Google's current TTS model list):

Build the payload with `json.dumps` (never inline the script into a curl `-d` — quotes and newlines corrupt the JSON and trigger 400 `INVALID_ARGUMENT`):

```bash
# Write the approved script to script.txt first (multiline allowed, quoting free)
# IMPORTANT: strip structural labels like [Hook], [Inti 1], [Penutup] from what you
# send to TTS -- the model reads text verbatim and will speak them aloud.

python3 - <<'PY'
import json
script = open('script.txt').read()
# REQUIRED: text is verbatim ONLY, with no instructions. Instructions such as
# "Read this warmly..." placed INSIDE text get read aloud by the 3.8 model
# (measured: instruction + 3 words = 6.5 s; verbatim 3 words = 2.2 s).
# Delivery goes through speech_metadata.style, the official channel that stays silent.
payload = {
    "contents": [{"parts": [{"text": script,
        "speech_metadata": {"style": "warm, clear, slightly upbeat"}}]}],
    "generationConfig": {
        "responseModalities": ["AUDIO"],
        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}
    }
}
json.dump(payload, open('work/tts-request.json','w'), ensure_ascii=False)
PY

curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d @work/tts-request.json > work/tts-response.json

python3 - <<'PY'
import json, base64, sys
d = json.load(open('work/tts-response.json'))
if 'candidates' not in d:
    sys.exit(f"TTS failed, API response: {json.dumps(d)[:500]}")
part = d['candidates'][0]['content']['parts'][0]
data = base64.b64decode(part['inlineData']['data'])
mime = part['inlineData'].get('mimeType', '')
open('work/tts.wav' if 'wav' in mime else 'work/tts.pcm','wb').write(data)
print('mimeType:', mime)
PY
# 3.8 returns complete audio/wav (RIFF header) — write .wav directly.
# For mimeType audio/l16 (raw PCM, older models), decode manually:
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

For a URL from the user, download with `yt-dlp "<url>" -o "assets/reference.mp4"` before analysing.

### Finding a reference on Pinterest (when the user gives none)

If the user supplies no reference file or URL (or chooses "hand it to the AI"), find a video that fits the topic:

1. Search for candidate video pins using the available web search tool: queries like `pinterest.com pin <topic keywords> video` (try Indonesian and English). Collect 3–5 candidate pin URLs.
2. Download candidates one at a time until one works:

   ```bash
   yt-dlp "<pin-url>" -o "assets/reference.mp4"
   ```

3. Filter before use — check with `ffprobe` and discard candidates that: run under 5 s or over 90 s, sit below the planned output resolution, have no video stream, or are unrelated to the topic. Discarded → try the next.
4. If every candidate fails, do not force it. Tell the user and ask: supply the file or URL themselves, or give a short style direction (palette, font, mood). There is no default style — never proceed without a style anchor.

Self-found quality is uncontrolled. Required: tell the user which reference you picked (URL plus a one-line reason) before analysing, and treat it as inspiration, not a mould.

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
- Load the stage-5 timeline as data (a list of segments with start/end times) so it is easy to retune.
- **One absolute-time table as the single source.** Every element appearance time (`{label: video_seconds}`) lives in one table, and scenes read from it — scenes never keep their own entry offsets. Scene boundaries derive from ASR sentence boundaries, not typed separately. When each scene carries its own numbers, shifting one sentence means shifting six numbers and the drift returns in the next scene. Never hard-code label times to seconds while beats can still change: use `B_VIDEO[key] - scene_start` computed at render time, not a frozen `0.55`.
- Render frame 0 through (frame count − 1). The final frame must still hold a clear closing visual, never an empty screen.

## 6. Audio mixing and export

Duration follows the voiceover. Compute total duration and frame count first (rules in stage 4 of `SKILL.md`):

Set the cap first. `MAX_DUR` defaults to 60; raise it only when the user explicitly asks.

```bash
MAX_DUR=60                      # default cap; change only on user request
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "audio/voiceover.wav")
DUR=$(awk -v v="$VO_DUR" 'BEGIN{t=v+2.5; d=int(t); if (d<t) d++; print d}')
FRAMES=$((DUR*30))
FADE_ST=$(awk -v d="$DUR" 'BEGIN{print d-2.5}')
mkdir -p work
echo "voiceover=$VO_DUR  total=$DUR s  frames=$FRAMES  cap=$MAX_DUR"
awk -v d="$DUR" -v m="$MAX_DUR" 'BEGIN{if(d>m) print "OVER CAP "m" S: stop and ask the user"}'
```

Use those `DUR` and `FRAMES` values for the whole render (frames drawn, timeline, export). The voiceover is delayed to start at second 1 (`adelay`), padded to the end, and the music is looped, trimmed to the video length, lowered in volume, and ducked under speech.

**Three steps — never merged into one `filter_complex`.** Combining `loudnorm` with `apad` in one chain kills the audio tail: loudnorm also processes the padding, dropping the tail to −91 dB (measured on the single-chain example that used to be here: `silence_start 40.86` in a 43 s video). So split:

```bash
# 1) normalise the voiceover into its own file
ffmpeg -y -i "audio/voiceover.wav" -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 work/voiceover-norm.wav

# 2) prepare the music in its own file: level + fade-out. Never add afade=t=in --
#    music starting from silence reads as unintended silence to the §7 gate.
ffmpeg -y -i "audio/music.wav" -af "volume=0.40,afade=t=out:st=$FADE_ST:d=2.5" -ar 48000 work/music-norm.wav

# 3) then combine: adelay + apad + duck + amix
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

`FADE_ST` derives from video duration, not music duration: `DUR - 2.5` (the `awk` recipe above already does this). The fade must finish before the final second, but the music must not touch absolute zero on the last frame — a residual −25 dB tail passes the gate, absolute zero does not.

Notes:
- `loudnorm` equalises voiceover loudness (target I=-16 LUFS, TP=-1.5) so user recordings and TTS results sit at the same level. It works internally at 192 kHz; `-ar 48000` in step 1 restores the sample rate.
- `normalize=0` needs ffmpeg 7.0+. On 6.x drop `normalize=0` and use `volume=2` — measured identical on 7.1 (−18.5 dB both ways). Never combine them: `normalize=0` + `volume=2` reaches max 0.0 dB, i.e. clipping.
- Without music: skip step 2, and in step 3 use only `[1:a]adelay=1000:all=1,apad=whole_dur=$DUR,atrim=0:$DUR,asetpts=PTS-STARTPTS,afade=t=out:st=<DUR-0.5>:d=0.5[aout]` (compute `DUR-0.5` with `awk` like `FADE_ST`).
- Without voiceover (draft): use music only, and label it a draft.
- If the input is raw video rather than an image sequence, still force `-r 30` and `-frames:v $FRAMES`.
- If the user sets their own target duration, replace `DUR` with it (as long as the voiceover fits), set `MAX_DUR` at least to that target, and recompute `FRAMES` and `FADE_ST` with the same formulas.

## 7. Verifying the exported file

Never trust the duration shown by an editor or a script. Measure the MP4 itself:

```bash
# container duration, codec, resolution, fps, frame count
ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,duration,nb_frames -of default=nw=1 output/<slug>.mp4

# count frames actually decoded (must equal $FRAMES)
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 output/<slug>.mp4
```

Target: container ≈ `DUR` seconds (to three decimals), `FRAMES` video frames, 30 fps, H.264 + AAC, resolution as planned. The AAC encoder adds slight padding so the audio stream duration can differ by milliseconds; the container duration and video frame count are the evidence. Report the real numbers. If they miss, fix and re-export — never round the report.

Detect unintended problems:

```bash
# black frames
ffmpeg -i output/<slug>.mp4 -vf blackdetect=d=0.1:pix_th=0.05 -an -f null - 2>&1 | grep black_
# frozen frames — n=0: only truly identical frames count as a freeze.
# NEVER use n=-60dB: on flat graphics, micro-changes between frames (thousands of
# pixels, max diff ~220) still get reported as a freeze -> false positives on video
# that clearly moves.
ffmpeg -i output/<slug>.mp4 -vf freezedetect=n=0:d=1.0 -an -f null - 2>&1 | grep freeze_
# unintended silence and loudness
ffmpeg -i output/<slug>.mp4 -af silencedetect=noise=-50dB:d=0.5 -vn -f null - 2>&1 | grep silence_
ffmpeg -i output/<slug>.mp4 -af volumedetect -vn -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

**Motion gate:** `freezedetect=n=0:d=1.0` must come back empty, except for a deliberate, timeline-documented rest (at most one, ≤1.5 s, near the close). A freeze means the render is genuinely still — go back to §5, add micro camera motion or element animation, re-render. Report this gate result alongside the duration.

**Audio tail gate:** `silencedetect` on the final file must be empty all the way to the last second, not merely in the middle. Music dying before the video ends shows up as `silence_start` in the final seconds and is a defect, not a choice. The most common cause is `loudnorm` placed inline with `apad` in one `filter_complex` (measured: −91 dB over the last 2.1 s while the source was −15 dB). Normalise the voiceover into its own file first, then mix.

**Write the sync, geometry, and repetition checks yourself when needed.** The rules are complete in prose below and in `GUIDE.md` §2: safe area 4%, two-tier glyph height, contrast per role, collision IoU, repetition patterns. Translate them into code against your renderer's data structures.

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
# 1) safe area: no glyph crosses 4% of the frame edge (same value as GUIDE.md §2)
bb = d.textbbox((px, py), s, font=f, anchor=anchor)
assert bb[0] > W * 0.04 and bb[2] < W * 0.96
assert bb[1] > H * 0.04 and bb[3] < H * 0.96

# 1b) legibility: GLYPH height, not font size (capital glyphs ~0.75x font).
#     two tiers per GUIDE.md §2: primary >=4%H, supporting >=2.5%H
gh = bb[3] - bb[1]
assert gh >= H * (0.04 if is_main else 0.025), f"text too small: {s} ({gh}px)"

# 2) text collision: IoU of glyph boxes
def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    return inter / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter)

assert iou(bb_a, bb_b) < 0.16

# 3) contrast: WCAG ratio, threshold tied to the text ROLE (GUIDE.md §2),
#    not to pixel size -- small moving text reads worse than static text
assert ratio(fill, bg_color) >= (3.0 if is_main else 4.5), f"contrast too low: {s}"
```

**Contrast gate** uses the same WCAG formula as `GUIDE.md` §2. Measured on palettes in common use: ink-on-cream and cream-on-dark pass well above 4.5:1, but a light salmon accent on cream reaches only **1.85:1** — a hard fail for any text. When this gate rejects, do not lower the threshold: change the colour, move the text onto a dark background, or place a solid panel behind it.

### Third gate: repetition pattern (flags, never rejects)

This gate **does not judge**. It surfaces scenes with the same structure; you decide.

```python
# for each scene, take a structural signature (not content):
#   mass_position : where the ink centroid sits (left/centre/right, top/middle/bottom)
#   density       : ratio of inked pixels
#   background    : light / dark
def signature(frame_rgb):
    g = np.array(frame_rgb.convert("L"))
    ink = g < 110
    if ink.sum() < 500:
        return ("empty",)
    ys, xs = np.nonzero(ink)
    return (
        round(xs.mean() / g.shape[1], 1),   # 0.0 left .. 1.0 right
        round(ys.mean() / g.shape[0], 1),
        round(ink.mean(), 2),
        "dark" if g.mean() < 100 else "light",
    )

sigs = [signature(f) for f in mid_frame_of_each_scene]
for i in range(1, len(sigs)):
    if sigs[i] == sigs[i - 1]:
        print(f"scenes {i} and {i+1} share a pattern: {sigs[i]}")
```

If two consecutive scenes share a pattern, **do not change them automatically**. Write one sentence in the timeline:

- "the motif is deliberate — these two scenes are a pair" → leave it
- "coincidence, no other idea" → change composition, density, or scale

Deliberate repetition is often good and always legitimate. What must surface is repetition born of no decision. The gate forces that decision to be written down; it never homogenises the output.

The same text drawn twice at the same position (e.g. text over a highlight block) is IoU 1.0 — deliberate; exclude identical pairs. Run all four gates before export, not after; re-rendering one scene is cheaper than re-rendering a video.

Two things that make these gates mislead:
- `freezedetect` with `n=-60dB` (the default) FALSE POSITIVES on motion graphics: decoded frames inside the "frozen" range can change thousands of pixels per frame (idle elements, breathing dots) yet the filter still reports a freeze because the threshold is too high for flat graphics. Always use `n=0`.
- Source frames move but the MP4 reports a freeze at the same point? That is the encoder: small elements (radius <15 px, motion <10 px/frame) in a large flat area can be quantised away at CRF 18+. Enlarge the idle element or drop CRF to 16 — do not add new motion.

`max_volume` touching 0 dB means clipping risk — and if `alimiter` is installed yet max is still 0 dB, the cause is almost certainly its default `level` option (§9).

Visual check: extract frames at key points (start, each scene change, end) and look for yourself at legibility, spelling, cropping, and collisions.

```bash
ffmpeg -i output/<slug>.mp4 -vf "fps=1/2,scale=640:-1" work/check/%02d.png
ffmpeg -ss $(awk -v d="$DUR" 'BEGIN{print d-0.1}') -i output/<slug>.mp4 -frames:v 1 work/check/last.png
```

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
- **`loudnorm` inline + `apad` = dead audio tail:** never combine them in one `filter_complex`. Normalise the voiceover into a separate file first (three-step recipe in §6, gate in §7). Measured: one chain → `silence_start 40.86` in a 43 s video, tail −91 dB; three steps → tail −25 to −33 dB, `silencedetect` empty.
- **`afade=t=in` on music trips the audio tail gate:** music starting from silence reads as unintended silence (measured: `silence_start 0`, 0.53 s). Let music enter at full level; fade only at the end.
- **`textbbox` with `anchor` is not the glyph shape:** treating bb[1]/bb[3] as symmetric around the anchor point is wrong for numerals and capital text. Always compute the bbox centre offset from the anchor before placing inside a shape (see `GUIDE.md` §2).
- **Small idle elements quantised by the encoder:** dots/particles under ~15 px radius that merely pulse in a large flat area can vanish after encoding (CRF 18+), leaving identical decoded frames → a real freeze in the MP4 even though the renderer drew motion. Enlarge the element and move its position, not just its radius (a solid antialias-free circle changing radius often alters no pixel at all).

## 10. Cleanup after delivery

`work/` holds every intermediate file: `frames/`, `ref/`, `check/`, normalised audio, and timing JSON. It can reach hundreds of megabytes and the user does not need it. Once the video is verified and delivered, delete the whole `work/`; keep only `script.txt`, `render.py`, `audio/`, `assets/`, and `output/`. Mention in the delivery message that intermediates were cleaned up.