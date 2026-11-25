# Render and Verification

Read this before building and rendering. All commands are examples — adapt filenames to the assets you actually have. Never run a command that depends on a tool you have not checked exists.

## Contents
1. Environment check
2. The render pipeline
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
python3 -c "import skia; print('skia', skia.__version__)"
python3 -c "import faster_whisper; print('word-level ASR: available')" 2>/dev/null || echo "ASR: unavailable (pip install faster-whisper; without it word timing becomes an estimate -- tell the user)"
[ -n "$GEMINI_API_KEY" ] && echo "GEMINI_API_KEY: present" || echo "GEMINI_API_KEY: absent"
which curl yt-dlp           # curl for TTS, yt-dlp for URL references
NC=$(timeout 8 curl -s -o /dev/null -w '%{http_code}' https://generativelanguage.googleapis.com/v1beta/models 2>/dev/null)
case "$NC" in 200|403|404) echo "network: OK (HTTP $NC)";; *) echo "network: PROBLEM (HTTP $NC / timeout)";; esac
```

Network access is often restricted. Fonts come from Google Fonts into `assets/fonts/`; if a download is blocked, say so and ask — never substitute a system font (§1). The ffmpeg version dictates which options are legal (see §6).

### Vision capability (measured, never assumed)

Stages 4 and 7 need the model to open an image. Provider metadata is not evidence: on one measured gateway, 15 of 72 models advertising `vision: true` returned an empty `content` because the router stripped the image. Probe with one real image before relying on it:

```bash
# known-content probe: white 800x400, blue square, red circle, text X7-KILO
python3 - <<'PY'
import os
from PIL import Image, ImageDraw
os.makedirs("work", exist_ok=True)   # work/ may not exist yet at this point
im = Image.new("RGB", (400, 200), "white"); d = ImageDraw.Draw(im)
d.rectangle([20, 20, 120, 120], fill=(0, 0, 255))
d.ellipse([140, 20, 240, 120], fill=(255, 0, 0))
d.text((30, 150), "X7-KILO", fill="black")
im.resize((800, 400), Image.LANCZOS).save("work/vision-probe.png")
PY
```

Then ask the main session to read `work/vision-probe.png` and report the text and both shapes. Pass = it names `X7-KILO`, a blue square, and a red circle. Fail = empty reply, a refusal, or a placeholder such as `[image omitted: ...]`.

- **Pass** → keep every image call in the main session. No subagent.
- **Fail** → delegate the image call to the `vision` subagent, once, and continue in the main session with its text answer. The subagent owns its own failover chain; never build a second one here, never retry the main model, never loop.
- **Both fail** → say so plainly and ask the user for a text description. Do not substitute guesses for what the picture shows.

Batch several images into one delegated call. Timing, scene code, rendering, and every QC number stay in the main session — the subagent returns a description, not a decision. Delete `work/vision-probe.png` with the rest of `work/` at cleanup (§10).

### Fonts — always downloaded into the project

**A font is never read from the machine.** No `~/.local/share/fonts`, no
`fc-list`, no family that merely happens to be installed, no sample font shipped
with this skill. A film that depends on a system font renders differently on
another machine, after a rebuild, or inside a container — and the failure is
silent, because PIL quietly substitutes a fallback.

**One route only: download from Google Fonts, store it in the project.**

```bash
mkdir -p assets/fonts
# one file per family; variable fonts carry every weight
curl -sL -o assets/fonts/Outfit.ttf \
  "https://github.com/google/fonts/raw/main/ofl/outfit/Outfit%5Bwght%5D.ttf"
```

Verify before writing any scene code — a failed download is an HTML error page,
not a font:

```bash
python3 - <<'PY'
from PIL import ImageFont
f = ImageFont.truetype("assets/fonts/Outfit.ttf", 96)
print(f.getname(), f.getbbox("H"))      # real family name and a capital box
PY
```

Under 10 KB on disk, or an exception above, means the download failed: fix the
URL or pick another Google Fonts family. Never fall back to a system font, and
never proceed with a font that renders tofu.

Render only ever points at the project copy:

```python
F_DISPLAY = ImageFont.truetype("assets/fonts/Outfit.ttf", 96)
F_DISPLAY.set_variation_by_axes([700])   # variable files only
```

**Choose the family from the topic, not from what is easy to fetch.** Pick three
roles as a set — display (the keyword), meta (labels, indices), accent (a
handwritten annotation, used sparingly) — and state the reason in one sentence.
Do not let one family carry all three roles; that is what makes a film read as a
template. If a chosen family is not on Google Fonts, choose another that is.

## 2. The render pipeline

Python draws every frame deterministically from `t = frame_index / 30`, then ffmpeg assembles it. That is what makes the frame count exactly duration × 30 and lets animation sync to the timeline.

```bash
pip install pillow numpy skia-python
```

Shapes go through skia, text through PIL — the sync gate (§7) hooks `ImageDraw.ImageDraw.text`, so every text has to be drawn there. Measured at 1080×1920: 2 ms/frame for PIL text, 34 ms for shapes in skia, 38 ms for the hybrid. The frame function in §5 shows the arrangement.

Store frames as `work/frames/00000.png` through `work/frames/01199.png`. To save memory you can pipe straight into ffmpeg (`-f rawvideo -pix_fmt rgb24 -s WxH -r 30 -i -`).

The build script is **`render.py`**. Helper modules (`lib/`, `make_music.py`) are fine as long as `render.py` is the only thing you run end to end.

## 3. Measuring and analysing the voiceover

Duration:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "audio/voiceover.wav"
```

A user recording may already carry its own lead-in. Measure it before trusting the duration:

```bash
python3 - <<'PY'
import wave, numpy as np
w = wave.open("audio/voiceover.wav")
a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
i = int(np.argmax(np.abs(a) > 800))
print(f"lead silence {i / w.getframerate():.2f} s")
PY
```

If it exceeds 0.3 s, trim it to 0.2 s of air and re-measure. `VO_DELAY` stays the single 1 s lead-in; a second lead-in baked into the file is dead air the audio gate does not look for.

Pauses and sentence boundaries (lower `noise` for noisy recordings):

```bash
ffmpeg -i "audio/voiceover.wav" -af silencedetect=noise=-35dB:d=0.25 -f null - 2>&1 | grep silence_
```

Word timing: **use speech recognition first, word-count estimation last.** Words per second exist only to sanity-check script length, never to place text.

Try ASR with per-word timestamps before giving up on estimation. `faster-whisper` is practical and runs on CPU:

```python
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio_array, language=None, word_timestamps=True)
# language=None auto-detects. Pin it (language="id") only when the script is Indonesian
# and detection is unreliable -- forcing the wrong language corrupts every word boundary.
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

Write the result to `audio/words.json` — it is the one artefact every later stage reads (timeline, sync gate, optional subtitle and publish copy), and the one derived file that must survive cleanup:

```python
import json
json.dump({
    "vo_delay": 1.0,          # the same single constant as VO_DELAY -- never re-typed per scene
    "segments": [{"start": s.start, "end": s.end, "text": s.text,
                  "text_display": align_from_script(s),   # script.txt spelling, same sentence
                  "words": [{"word": w.word, "start": w.start, "end": w.end}
                            for w in s.words]} for s in segs]
}, open("audio/words.json", "w"), ensure_ascii=False, indent=1)
```

`text_display` is the sentence as `script.txt` spells it, aligned to the ASR segment (token index is enough; a fuzzy match when ASR splits or merges a word). The ASR `text` stays exactly as recognised because only its boundaries matter — but it must never reach a subtitle or the publish copy.

`audio/`, not `work/`. Re-running ASR after a cleanup produces timestamps that differ by ~±0.1 s from the ones the pictures were synced to, so a rewrite of this file silently desyncs a re-render. Sitting beside `voiceover.wav` makes it a durable project input rather than a disposable intermediate.

Same file also produces a subtitle track for the platform upload, for free:

```python
def ts(t):
    ms = int(round(t * 1000))                 # integer maths: 1.9996 s must not become ",1000"
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

d = json.load(open("audio/words.json"))
off = d["vo_delay"]                            # read the delay, never re-type it
# one cue per sentence, shifted onto the video timeline.
# Use text_display (script spelling), never g['text'] (ASR spelling is kept wrong on purpose).
open("output/<slug>.srt", "w").write("".join(
    f"{i}\n{ts(g['start'] + off)} --> {ts(g['end'] + off)}\n{g['text_display'].strip()}\n\n"
    for i, g in enumerate(d["segments"], 1)))
```

If ASR is unavailable or fails: split time by `silencedetect` pauses, distribute words per phrase by syllable count, and **tell the user that word timing is approximate**.

If the voiceover is delayed during mixing (e.g. starting at second 1), every ASR time must be shifted by that delay before use. Keep it as one constant (`VO_DELAY`) and derive all times from it — never add it manually per scene.

Format note: the examples use `audio/voiceover.wav`. Files the user supplies may be .mp3/.wav/.m4a — normalise to `audio/voiceover.wav` (48 kHz mono) before analysis.

If the computed total (voiceover + ~2.5 s) exceeds the cap for that orientation — **60 s portrait, 300 s landscape** — stop and ask (see stage 4 in `SKILL.md`).

The two caps are different products, not a preference: a portrait clip runs in a feed next to other 30–60 s clips, a landscape explainer runs on a platform that expects minutes. A 5-minute portrait video is not "more thorough", it is unwatchable in that context; a 60-second landscape video under-delivers its format. Pick the cap by orientation and hold it.

### When there is no voiceover

1. **Generate with Gemini TTS** (needs a Gemini key). Current models: `gemini-3.8-flash-tts` (best) and `gemini-3.8-flash-lite-tts` (separate quota). If either 404s, check Google's current model list.

   **Keys rotate automatically — never hardcode one key.** Quota is counted per key *per model* (free tier ≈10 TTS requests/day). The shared helper lists every key in priority order — `$GEMINI_API_KEY`, then each `/root/.hermes/keys/*.key`, then `GEMINI_API_KEY` in `/root/.hermes/.env` — and the same set is used by bits-affiliate, bits-motion, bits-hyperframes and bits-bang-motion:

   ```bash
   python3 /root/.hermes/keys/gemini_key.py     # how many keys are ready
   ```

   ```python
   import sys; sys.path.insert(0, "/root/.hermes/keys")
   from gemini_key import keys

   daftar = keys()          # ordered, de-duplicated
   ```

   On a `429` / `RESOURCE_EXHAUSTED` / `API_KEY_INVALID` response, mark that key spent and try the next one before giving up. To add capacity, drop a new file at `/root/.hermes/keys/<name>.key` (chmod 600, contents = the key alone); no code change needed. Never print a key value into logs or reports — `key#N` is enough.

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
# models) decode manually: 24 kHz, mono, s16le. Either path normalises to the
# project format: 48 kHz mono.
if [ -f work/tts.pcm ]; then
  ffmpeg -v error -y -f s16le -ar 24000 -ac 1 -i work/tts.pcm -ar 48000 "audio/voiceover.wav"
else
  ffmpeg -v error -y -i work/tts.wav -ar 48000 -ac 1 "audio/voiceover.wav"
fi
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

The reference comes from the user (file or URL) or is found on Pinterest (subsection below). For a URL from the user, download with `yt-dlp "<url>" -o "assets/reference.mp4"` before analysing. Once the file exists, read it in four steps: a **contact sheet** for the design layers, **motion strips** for the temporal ones, an eight-layer read, and a brief written into the build script. A still cannot show easing, entry duration or text granularity — those only exist in consecutive frames.

```bash
REF="assets/reference.mp4"
ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration -of default=nw=1 "$REF"
```

The reference must match the orientation chosen in stage 1 — a mismatch fails the filter below and never changes `MAX_DUR`.

### Pass 1 — contact sheet over the whole clip

```bash
RDUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$REF")

# ~60 thumbnails across the whole clip, never coarser than one every 2 s
DIMS=$(python3 -c "import math; d=max(float('$RDUR'),1); f=min(2.0, 60/d); c=max(1, round(d*f)); print(f'{f:.3f} {math.ceil(math.sqrt(c))}')")
FPS=${DIMS% *}; GRID=${DIMS#* }

mkdir -p work/ref
ffmpeg -i "$REF" -vf "fps=$FPS,scale=240:-1,tile=${GRID}x${GRID}" -frames:v 1 -update 1 work/ref/contact.png
```

The grid is sized from the clip's duration. A fixed `tile=6x5` at `fps=2` covers the first **15 s** of any clip and then fails on the remaining tiles (`Cannot write more than one file with the same name`), leaving a sheet that shows only the opening — measured on a 60 s reference: 120 frames extracted, 30 cells on the sheet, exit code 234. `-frames:v 1` and `-update 1` are both required: a tile grid is one image written to one filename.

### Pass 2 — motion strips around three cuts

Cut rhythm is measurable — do not rely on impression. Detect the cuts, keep the first, middle and last, then take a strip across each one:

```bash
# scene changes (threshold 0.3 = a real cut, not a fade). No -v flag: showinfo logs at info level.
ffmpeg -i "$REF" -vf "select='gt(scene,0.3)',showinfo" -an -f null - 2>&1 \
  | grep -o "pts_time:[0-9.]*" | cut -d: -f2 > work/ref/cuts.txt

awk 'NR==1{f=$1} {a[NR]=$1; n=NR}
     END{if(!n){print "no cuts found" > "/dev/stderr"; exit}
         printf "%s\n", f
         if(n>2) printf "%s\n", a[int((n+1)/2)]
         if(n>1) printf "%s\n", a[n]}' work/ref/cuts.txt > work/ref/pick.txt

# 0.5 s before each cut, 1.0 s after: 45 frames in a 15x3 tile
while read -r T; do
  S=$(awk -v t="$T" 'BEGIN{x=t-0.5; if(x<0)x=0; printf "%.3f", x}')
  ffmpeg -ss "$S" -i "$REF" -t 1.5 -vf "fps=30,scale=200:-1,tile=15x3" \
    -frames:v 1 -update 1 "work/ref/strip-$T.png"
done < work/ref/pick.txt
```

Average gap plus the shortest and longest gap describe the pace in numbers; that is what you match or deliberately break. From each strip read: how many frames an element takes to land (8 and 20 are different videos), the easing shape, whether text arrives per letter, per word or per line, whether there is overshoot, and whether the frame is already still before the cut.

`showinfo` writes at info level — adding `-v error` silences the very lines this pipeline greps, and an empty `cuts.txt` then reads as "a reference with no cuts".

### Pass 3 — the eight-layer read

Read the sheet and the strips layer by layer. Every layer answers one question and produces one line of code. "Warm palette" is not a reading; "70% near-black, 20% cream, 10% orange, orange on one word per frame" is.

| Layer | What to read | Translation to code |
|---|---|---|
| **Palette** | roles (ground / ink / accent), the share of frame each holds, whether the accent marks one word or a whole field, whether the palette shifts between chapters, texture over the colour | a hex per role, an area budget, a background per section, a grain amount |
| **Typography** | title-to-meta size ratio, families and the axis varied (weight, width, case), tracking on caps, and whether type is used as an image — cropped, stacked, outlined, filled, off-frame | a size table, tracking values, crop masks |
| **Composition** | empty-space ratio, where the mass sits, layer count, full-bleed vs card | margins, anchor points, z-order |
| **Graphic language** | shape vocabulary, corner radius, stroke weight, fill style, icon grid, diagram grammar (bars, arcs, arrows, axis style), illustration register (flat, outline, collage, isometric), texture | `rounded_rectangle(r=16)`, `line(width=3)`, icon grid 24, grain 4% |
| **Motion** | entry duration in frames, easing shape, overshoot, what moves (camera, world, or layers), text granularity, secondary motion, morph/mask, whether motion carries meaning or decorates | an easing constant, a duration in frames, a stagger per word or line |
| **Rhythm** | cut distribution (not just the mean — the shortest and longest gap matter most), event density per second, the energy curve, whether cuts land on speech or on music | expected cut count, where holds go |
| **Sound** | whoosh / impact / riser / tick vocabulary, silence as punctuation, whether music drops under the key line | an SFX plan per transition type |
| **Attention** | what is on screen at 1.5 s and how many elements, the chapter system, withholding (what is held back and when it is released), pattern-interrupt interval, callbacks in the close | hook frame contents, chapter cards, interrupt spacing |

Two closing reads, both required:

- **Signature device.** Name the one or two things that are this reference's fingerprint — text always entering from behind an object, a hairline that grows into a diagram, numbers counting up. Write the principle, not the form, and then use it differently.
- **Weakness.** Name what the reference does badly — too much text, a flat middle, a weak close. That is where the build beats it.

The reference is a **floor, not a ceiling**. At least one decision — a motif, a material, a motion idea from another medium — must come from the topic and be absent from the reference. A build that only matches its reference is a copy with extra steps.

### Pass 4 — write the brief into `render.py`

Ten lines, written before the first scene and kept as the header comment of the build script — not a separate file (`SKILL.md` → *Project layout*: one source of truth). Update a line when a decision changes; stage 7 checks the export against it.

```python
# STYLE BRIEF — reference: <url> (read <date>)
# palette  : ground #0B0B0F 70% | ink #F5F1EA 20% | accent #C6492B 10%, one word per frame
# type     : <display> 900 / <meta> 500; title:meta 6:1; caps tracking 6 px
# layout   : mass left, 55% empty; full-bleed, no cards
# graphics : rounded rect r=16, stroke 2 px, grain 4%, line icons 3 px on a 24 grid
# motion   : entry 8-12 frames ease-out, no overshoot; text per word; camera locked, layers drift
# rhythm   : cuts 0.9-1.4 s, one 2.6 s hold before the close; land on speech, not music
# sound    : whoosh 120 ms on mask transitions; music drops under the verdict line
# attention: hook = one object + one word at frame 0; chapters 01-03; circle callback at the close
# device   : <name> in principle — this build uses it <differently>
# floor    : <the one decision not taken from the reference>
```

A brief that could describe any motion-graphics video has not been read — it is a template. Each line has to be specific enough that another build could not use it.

### Finding a reference on Pinterest (when the user gives none)

If the user supplies no reference file or URL (or asks for everything automatic), searching is **mandatory before self-design** — the budget and failure modes are specified in `SKILL.md` stage 3 and apply here verbatim: ≥5 pin candidates across ≥2 searches as the floor, ~8 as the working target, one download attempt at a time, discard by the filter below, report each failure in one line. Known failure modes measured in the wild: image-only pins (`No video formats found!`), Vimeo-embedded pins (often TLS-blocked per environment), and 4 s loops that fail the minimum-duration filter. Only after the budget is exhausted: design the style yourself and say so, including that the search was attempted.

Search in this order — do not stop at the first failure:

1. **Search with `motion graphics` plus the topic**, e.g. `https://id.pinterest.com/search/pins/?rs=typed&q=motion+graphics+<topik>` (or `pinterest.com pin <topic keywords> motion graphics video` through a web search; Indonesian and English). Collect 5+ candidate pin URLs before downloading.
2. **Judge fit, not just relevance.** Compare each candidate against the topic's character: is the palette right for this subject? Is the typography at the right register (serious, playful, archival, technical)? Is the motion pace suited to the narration? Pick the closest.
3. **If nothing fits well, take something loosely related** — same broad mood or same kind of subject matter, even if the content differs. A calm paper-craft pin is a better style anchor for a serious topic than an energetic neon clip that happens to share keywords.
4. **If even that fails, design the style yourself.** Choose palette, typography, and motion language from the topic and say so in one line, e.g. `Tidak ada acuan yang cocok, jadi saya tentukan sendiri: latar gelap, aksen hangat, tipografi tebal.` A self-designed style is legitimate; an unannounced one is not.

Download candidates one at a time until one works:

```bash
yt-dlp "<pin-url>" -o "assets/reference.mp4"
```

Filter before use — check with `ffprobe` and discard candidates that: run under 5 s or over 180 s (three minutes is enough to read a style; longer only costs analysis time), have the wrong aspect ratio, have no video stream, or are visually unusable. Discarded → try the next.

**Aspect ratio, not resolution.** A reference teaches style — palette, typography, composition, cut rhythm — and every one of those reads perfectly from a smaller frame. 720×1280 is a valid reference for a 1080×1920 build, and 1280×720 for a 1920×1080 build: same orientation, same 9:16 (or 16:9) geometry. What matters when comparing:

- **orientation** must match the planned output (portrait ref → portrait build; landscape ref → landscape build);
- **aspect ratio** within a small tolerance (±2% on the ratio; 720×1280, 1080×1920, 2160×3840 are all exactly 9:16 — a crop that changes the geometry is *not* the same composition and misleads the analysis);
- **resolution is irrelevant** for a reference (it is analysed at reduced scale anyway — contact sheets are drawn at 240–480 px wide), and never a reason to reject.

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
- **Motion is what the encoder can see.** Every second needs at least one element whose **position** actually changes — an idle element can drift or pan instead of pulsing. This is an encoding requirement, not a ban on held frames: a documented hold is a legitimate edit (`GUIDE.md` §3). Keywords and important figures (e.g. "92 juta") take a motion emphasis as the word is spoken — the amount and form is taste (scale pop, colour, weight, position, or a combination). If two words share a line, a scale pop must decay back to 100% before the next one, or they collide; a keyword that owns its frame may hold its scale. Measure each word's width slot with the font actually used (keyword ≠ body); a word appearing twice in one scene needs its own time for each appearance — never map both through one dict entry. Encoder note: element POSITION motion (x/y shift) is more reliable than radius/scale alone — a solid antialias-free circle that merely pulses in radius often changes not a single pixel, and motion under ~10 px can be quantised away at CRF 18+.
- Easing formulas you may use or replace with whatever suits the feel: `easeOutCubic(u) = 1-(1-u)**3`; `easeInOutCubic(u) = u<0.5 ? 4*u**3 : 1-((-2*u+2)**3)/2`; overshoot/back-out: `1 + 2.7*(u-1)**3 + 1.7*(u-1)**2`.

  **No duration or overshoot figure is mandatory.** Entry duration, overshoot size, and rhythm are taste decisions — pick what matches the narration pace and reference mood. Only these invariants are required, because breaking them breaks the result rather than merely changing the feel:
  - a scale pop **decays back to 100%** before the next pop (otherwise words collide);
  - avoid constant speed unless deliberate;
  - idle elements move in **position**, not just radius/scale (see the encoder note above).
- Draw icons and diagrams from code shapes (donut, bar, briefcase, bulb) — never emoji or symbol codepoints, which render as tofu in display faces. Typographic characters the chosen face actually contains (arrows, bullets) are fine. Backgrounds may alternate between scenes (light/dark) with one consistent accent colour as the default.

  Shapes go through skia, text through PIL (§2). One frame:

  ```python
  import skia, numpy as np
  from PIL import Image, ImageDraw, ImageFont

  surf = skia.Surface(W, H)
  c = surf.getCanvas()
  c.clear(skia.Color(*BG))
  c.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Color=skia.Color(*ACCENT)))
  arr = surf.makeImageSnapshot().toarray()          # BGRA
  frame = Image.fromarray(arr[..., :3][..., ::-1])   # -> RGB
  ImageDraw.Draw(frame).text((80, 180), "KATA", font=ImageFont.truetype(FONT, 110), fill=INK)
  ```

  **Sub-pixel drift is why shapes are drawn in skia.** PIL's `ImageDraw` rounds coordinates to whole pixels: a circle moved from x=100.0 to x=100.4 changed **0 pixels**, while skia changed 496. Drift under a pixel is the micro-motion this workflow uses to keep a scene alive, so under PIL it renders as a still frame — and the encoder sees a freeze (§7).
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

Set the cap first, from the orientation — the canonical numbers are in `SKILL.md` → *Fixed specifications*: portrait `1080×1920` → **60 s**; landscape `1920×1080` → **300 s (5 min)**. Raise it only when the user explicitly names a target.

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

**Three steps — never merged into one `filter_complex`.** Combining `loudnorm` with `apad` in one chain kills the audio tail: loudnorm also processes the padding, dropping the tail to −91 dB (measured: `silence_start 40.86` in a 43 s video). So split:

```bash
# 1) normalise the voiceover into its own file
ffmpeg -y -i "audio/voiceover.wav" -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 work/voiceover-norm.wav

# 2) prepare the music in its own file: loop to the full length, level, fade to a
#    floor (never to absolute zero). A fade-in is allowed -- but if the bed is quiet
#    enough that its opening half-second sits under -50 dB, the §7 gate reads that as
#    dead air, so in that case let it enter at full level instead.
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

`FADE_ST` derives from video duration, not music duration: `DUR - 2.5` (the `awk` recipe above already does this). The fade ends near the final second but must not reach absolute zero — `afade=t=out:st=DUR-2.5:d=2.5` ends exactly at zero and leaves the last **0.8 s at −61.7 dB**, which the gate treats as dead air. The expression above fades to a −32 dB floor instead; measured last-0.5-s level **−45 dB with music echoing the tail**, which passes. `-ac 2` matters because a mono voiceover otherwise exports a mono AAC track; measured `channels=1` without it, `channels=2` with it.

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
# black frames -- pix_th=0.02, NOT the 0.10 default. A legitimate dark background
# such as 0x0B0B0F (luma 0.043) is reported as "black" at the default; measured,
# true 0x000000 is still caught at 0.02, so 0.02 catches defects without
# flagging dark design. Use d=0.5 so single transition frames are ignored.
ffmpeg -i output/<slug>.mp4 -vf blackdetect=d=0.5:pix_th=0.02 -an -f null - 2>&1 | grep black_
# frozen frames -- n=0: only truly identical frames count as a freeze.
# `n` is a linear 0-1 ratio (default 0.001, about -60 dB), not a dB value --
# never pass `n=-60dB`. On flat graphics the default already false-positives:
# micro-changes between frames (thousands of pixels, max diff ~220) get reported
# as a freeze on video that clearly moves.
ffmpeg -i output/<slug>.mp4 -vf freezedetect=n=0:d=1.0 -an -f null - 2>&1 | grep freeze_
# raw silence dump and peak level (read it; the pass/fail rule is the windowed
# gate below -- a silent tail is legitimate when the video has no music)
ffmpeg -i output/<slug>.mp4 -af silencedetect=noise=-50dB:d=0.5 -vn -f null - 2>&1 | grep silence_
ffmpeg -i output/<slug>.mp4 -af volumedetect -vn -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

**Motion gate:** `freezedetect=n=0:d=1.0` should come back empty, apart from deliberate, timeline-documented rests. `n` is a linear 0–1 ratio, not a dB value — `n=-60dB` is not a legal argument, and the default `n=0.001` (about −60 dB) false-positives on flat graphics. A freeze means the render is genuinely still — go back to §5, add micro camera motion or element animation, re-render. Report this gate result alongside the duration. The section below sets how many rests are worth an alert, not a pass/fail line.

How many rests are expected scales with length, because a five-minute explainer needs breathing room a 60-second clip does not. Treat the table as an **alert threshold, not a ceiling**: a deliberate hold — comedic timing, a punchline frame, a dramatic pause after a verdict — is a legitimate editing choice when it is written in the timeline with its reason. The gate's job is to count rests and list their positions so a human judges intent; it must never fail a video for holding a frame on purpose. What stays forbidden is the *undocumented* freeze: a scene stalled because nothing was animated.

| Runtime | Expected rests (alert above this) | Each |
|---|---|---|
| ≤60 s | ~1 | ≤1.5 s |
| >60 s | ≤1 per full minute of runtime | ≤2.5 s |

Deliberate holds beyond the threshold are fine when each one is written in the timeline ("hold 1.8 s on the 100% frame for comic timing"). Undocumented freezes are defects. The difference is the timeline entry, not the number.

The lead-in is not covered by this gate: the first `VO_DELAY` (1 s) holds the title/accent and is allowed to sit still, because nothing is being narrated yet. A freeze reported **entirely** inside `0..1 s` is not a defect; a freeze that reaches into speech is.

**Audio gate — windowed, not whole-file.** A whole-file `silencedetect must be empty` contradicts the spec: the tail after speech is ~1.5 s of legitimate silence whenever there is no music, so the plain command can never pass. Two checks, both measured on the export:

```bash
VO_DELAY=$(python3 -c "import json;print(json.load(open('audio/words.json'))['vo_delay'])")  # one source
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 audio/voiceover.wav)
HAS_MUSIC=1             # 0 when the video has no music track
SE=$(awk -v a="$VO_DELAY" -v b="$VO_DUR" 'BEGIN{printf "%.2f", a+b}')

# 1) no dead air inside the speech region, and no over-long lead-in.
#    Pair start/end: a silence that begins at 0 and runs to 1.8 s prints
#    `silence_start: 0`, which a start-only filter silently ignores.
ffmpeg -i output/<slug>.mp4 -af silencedetect=noise=-50dB:d=0.5 -vn -f null - 2>&1 \
  | grep -E "silence_(start|end)" \
  | awk -v s="$VO_DELAY" -v se="$SE" '
      /silence_start/ { st=$NF; next }
      /silence_end/   { en=$NF; if (en > s+0.25 && st < se-0.2) { print "FAIL dead air " st "-" en "s"; bad=1 } }
      END { if (bad) exit 1; print "audio gate 1 OK (speech " s "-" se "s)" }'

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

**Loudness gate.** The voiceover is normalised, but the finished mix is not: quiet music leaves the whole file quiet, and every platform then re-normalises it inconsistently. Measure the export:

```bash
ffmpeg -hide_banner -nostats -i output/<slug>.mp4 -af ebur128=peak=true -f null - 2>&1 \
  | grep -E "^\s+(I|Peak):" | sed 's/^ *//'
```

Target: **I between −17 and −14 LUFS** (a −16 LUFS voiceover with ducked music lands near −16, measured −16.0 on a 28 s build) and **true peak ≤ −1 dBTP**. A build with the voiceover turned down to 15% measured **−32.5 LUFS** — that is the failure this gate exists for. Report both numbers in the delivery message; `max_volume` alone does not describe loudness.

**Write the sync, geometry, and repetition checks yourself when needed.** The rules are complete in prose below and in `GUIDE.md` §2: safe area 4%, two-tier cap height, contrast per role, collision cover, repetition patterns. Translate them into code against the shapes your own scene code draws.

Suggested shape: collect every text bbox during render, then inspect at the end. Two checks are hard requirements — frame contiguity before encoding (§6) and the loudness/tail floor above. Everything in this section is **advice, not PASS/FAIL**: collect findings, print them, and decide. A gate that stops the script on the first finding hides the other four.

```python
findings = []
def check(ok, msg):
    if not ok:
        findings.append(msg)
    return ok

# ... run the checks ...
print("\n".join(findings) if findings else "no findings")
```

How to capture drawn text: wrap `ImageDraw.ImageDraw.text` — every text goes through it.

**Sync gate.** For each key text prove two things: it exists at `word_time + 0.10` and does not exist at `word_time − 0.15` (the window is tunable; what matters is its asymmetry — 0.1 s late beats appearing early). Capture all drawn text by wrapping the text call, then match by text name.

ASR times are **voiceover time**; the renderer draws on **video time**. Add `vo_delay` once, in the gate — never per scene.

```python
seen = []
orig = ImageDraw.ImageDraw.text
def patched(self, xy, s, *a, **kw):
    if kw.get("fill") is not None:
        seen.append(str(s))
    return orig(self, xy, s, *a, **kw)
ImageDraw.ImageDraw.text = patched

def at(t):
    seen.clear(); render_frame(int(round(t * 30))); return list(dict.fromkeys(seen))

VO_DELAY = json.load(open("audio/words.json"))["vo_delay"]   # read it, never re-type it
for text, t_vo in checks:          # rendered string + ASR word time, in voiceover seconds
    t = VO_DELAY + t_vo            # convert to video time before sampling
    check(text in at(t + 0.10), f"late or missing: {text} @ {t:.2f}s")
    check(text not in at(t - 0.15), f"appears too early: {text} @ {t:.2f}s")
```

Match by **time**, not by spelling: `t_vo` comes from the ASR token index while `text` comes from the script, because the ASR spelling is deliberately kept as-is (§3). A gate that string-matches ASR text to drawn text can never pass.

On failure, fix the time table — never nudge numbers inside a scene (§5).

**Geometry gate.** Three checks, all using the font metrics actually in play:

```python
# 1) safe area: no glyph crosses 4% of the frame edge (same value as GUIDE.md §2).
#    textbbox is in canvas coordinates with the default anchor AND with anchor="mm"
#    (measured: drawing "92" at (200,100) returns (200,116,311,176)); pass the SAME
#    anchor you draw with, and the comparison holds either way.
bb = d.textbbox((px, py), s, font=f, anchor="mm")
check(bb[0] > W * 0.04 and bb[2] < W * 0.96, f"crosses side safe area: {s}")
check(bb[1] > H * 0.04 and bb[3] < H * 0.96, f"crosses top/bottom safe area: {s}")

# 1b) legibility: CAP height, not the full box.
#     bb[3]-bb[1] over-measures mixed case (descenders) and badly under-measures a
#     lowercase-only line: at size 60 on DejaVu Sans Bold, "KATA" measures 44px but
#     "sun" measures 35px, against a 43px threshold on a 1080 short side.
#     Cap height is measured once per face and does not depend on the string.
#     Two tiers per GUIDE.md §2, against the SHORT side so portrait and landscape
#     share one number: short side 1920 -> primary 77px, supporting 48px;
#     short side 1080 -> primary 43px, supporting 27px.
S = min(W, H)
cap = f.getbbox("H")
cap_h = cap[3] - cap[1]
check(cap_h >= S * (0.04 if is_main else 0.025), f"text too small: {s} (cap {cap_h}px)")

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
    check(cover(bb_a, bb_b) < 0.02, f"text overlaps: {s}")

# 3) contrast: WCAG ratio, threshold tied to the text ROLE (GUIDE.md §2),
#    not to pixel size -- small moving text reads worse than static text
check(ratio(fill, bg_color) >= (3.0 if is_main else 4.5), f"contrast too low: {s}")
```

A label sitting inside a title block legitimately scores cover 1.0 — that is why the identical-box exclusion exists and why this is advice to read, not a hard fail. What it must catch: two independent lines that share any real band of pixels.

For a **portrait** export, run the content box as a second check on top of the 4% gate (`GUIDE.md` §2). One box, symmetric sides:

```python
S = min(W, H)
BOX  = dict(top=0.13, bottom=0.20, left=0.05, right=0.05, read=0.28)
RAIL = dict(from_y=0.55, inset_right=0.12)   # like/comment/share sit lower-right

if PORTRAIT:                       # 1080x1920 -> x 54..1026, y 250..1536
    check(bb[0] > W * BOX["left"], f"crosses left margin: {s}")
    check(bb[2] < W * (1 - BOX["right"]), f"crosses right margin: {s}")
    check(bb[1] > H * BOX["top"], f"crosses top band: {s}")
    check(bb[3] < H * (1 - BOX["bottom"]), f"crosses caption stack: {s}")
    # the rail exists only below the line: above it the full width is usable
    if bb[3] > H * RAIL["from_y"]:
        check(bb[2] < W * (1 - RAIL["inset_right"]), f"crosses the action rail: {s}")
    if is_readable:                # anything that must be read
        check(bb[3] < H * (1 - BOX["read"]), f"below the read line: {s}")
elif is_readable or is_caption:    # landscape: title-safe, no box
    # 1920x1080 -> x 192..1728, y 108..972. A caption at the usual 80-120 px
    # floor lands at y 960..1000 and crosses y 972 — put it inside the box.
    check(bb[3] < H * 0.90 and bb[1] > H * 0.10 and
          bb[0] > W * 0.10 and bb[2] < W * 0.90, f"outside title-safe: {s}")
```

The box covers **60% of the frame** and its horizontal centre is the frame centre, so ordinary centring works; only the vertical centre sits 67 px high. The bottom margin (20%) is the largest because every vertical platform stacks its UI there, while the top carries only a header. Sources for these numbers: `~/.agents/skills/iart-wrapped-video/references/scene-grammar.md` (top 12%, bottom 18%, sides 5%) and `~/.agents/skills/motioner/references/typography.md` (top 250 px, bottom 400 px on a 1080-wide frame); top is 13% to clear the taller of the two.

These numbers are organic short-form, not an ad spec (`GUIDE.md` §2). This skill never runs `hyperframes check`, so the ad box those guides define is not consulted here at all.

The box binds **content**. Backgrounds, gradients, grain and shapes with no meaning may bleed past it, but still obey the 4% edge.

Landscape has no box, but it does have a rule for readable text and captions: **10% title-safe** on all four sides. Treat a burned-in caption as readable — it is the accessibility layer.

**Contrast gate** uses the same WCAG formula as `GUIDE.md` §2, with the threshold tied to the text's role: **3.0:1** for primary text, **4.5:1** for supporting text. Measured pairs, reproducible with the formula above:

| Foreground | Background | Ratio | Verdict |
|---|---|---|---|
| `(166, 82, 70)` darkened accent | `(245, 241, 234)` cream | **4.76:1** | passes supporting |
| `(166, 82, 70)` | `(250, 246, 238)` cream | **4.97:1** | passes supporting |
| `(238, 150, 130)` light salmon | `(245, 241, 234)` cream | **2.00:1** | hard fail |
| `(20, 20, 20)` ink | `(250, 244, 232)` cream | **16.8:1** | passes everything |

An accent below 3:1 fails for primary text, and below 4.5:1 it fails for supporting text; the fix is to move the accent until the measured ratio clears, not to lower the threshold. When this gate rejects, change the colour, move the text onto a dark background, or place a solid panel behind it. On a dark palette the accent usually needs **lightening** — `fit_accent` in `GUIDE.md` §2 searches both directions for that reason.

### Text inside a frame — centring gate

A chip, badge, tag, button, sticker or card holds its text **centred both ways**:
horizontally *and* vertically against its frame. Horizontal-only centring leaves
the text floating high or low and reads as misplacement, however good the copy is.

- **Browser (DOM/HTML):** let the frame centre its own content —
  `display:flex; align-items:center; justify-content:center` — instead of nudging
  the text with `transform`, `padding-top` or a hand-tuned offset. Then prove it:
  `Range.getClientRects()` for the line count (one rect = one line) plus
  `getBoundingClientRect()` of frame and text; centre-to-centre gap ≤ 2 px, and
  top/bottom gaps equal within 3 px.
- **PIL/skia (`render.py`):** never place text with a fixed nudge such as
  `y + font.size * 0.34` — it is a guess that breaks at every new size or family.
  Size the frame from the **glyph ink box** and centre the ink itself:

  ```python
  def ink_box(font, s, tracking=0.0):
      """Real ink box of a string, relative to a text drawn at anchor 'lm'."""
      x, xs, ys = 0.0, [], []
      for ch in s:
          b = font.getbbox(ch, anchor="lm")
          xs += [x + b[0], x + b[2]]
          ys += [b[1], b[3]]
          x += font.getlength(ch) + tracking
      return min(xs), min(ys), max(xs), max(ys)

  ix0, iy0, ix1, iy1 = ink_box(font, label, tracking)
  w = (ix1 - ix0) + 2 * pad_x          # frame from ink + symmetric padding
  h = (iy1 - iy0) + 2 * pad_y
  d.text((cx - (ix0 + ix1) / 2, cy - (iy0 + iy1) / 2),
         label, font=font, anchor="lm")   # centre of ink on centre of frame
  ```

- **Prove it from pixels, not from the code that drew it.** Record each frame box
  as it is drawn, then measure the rendered frame: ink bbox against frame bbox,
  centre-to-centre ≤ 2 px and left/right, top/bottom gaps equal within 4 px.
  Drop the rounded corners and a 4 px border before measuring, otherwise the
  outline itself is counted as ink and every chip looks off-centre. Vision is not
  a substitute — it calls a 12 px misalignment "centred".
- A finding here is a defect, not taste: fix the geometry and re-render.

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

Vary composition on purpose, and record it: keep a small per-scene vector (composition zone, density, scale, background). **Three consecutive scenes** on the same vector is a flag, not a verdict — keep it only with a written reason. Two in a row can be a deliberate pair; three is the "same layout, different words" failure `GUIDE.md` §6 warns about.

If two consecutive scenes share a pattern, **do not change them automatically**. Write one sentence in the timeline:

- "the motif is deliberate — these two scenes are a pair" → leave it
- "coincidence, no other idea" → change composition, density, or scale

Deliberate repetition is often good and always legitimate. What must surface is repetition born of no decision. The gate forces that decision to be written down; it never homogenises the output.

The same text drawn twice at the same position (e.g. text over a highlight block) is IoU 1.0 — deliberate; exclude identical pairs. Run every gate before export, not after; re-rendering one scene is cheaper than re-rendering a video.

`max_volume` touching 0 dB means clipping risk — and if `alimiter` is installed yet max is still 0 dB, the cause is almost certainly its default `level` option (§9).

Visual check: extract frames at key points (start, each scene change, end) and look for yourself at legibility, spelling, cropping, and collisions.

```bash
mkdir -p work/check          # ffmpeg will not create it -- "Could not open file" otherwise
ffmpeg -i output/<slug>.mp4 -vf "fps=1/2,scale=640:-1" work/check/%02d.png
ffmpeg -ss $(awk -v d="$DUR" 'BEGIN{print d-0.1}') -i output/<slug>.mp4 -frames:v 1 work/check/last.png
```

The grid must cover the whole video, and a landscape video can run 300 s. `fps=1` at `8x8` stops at 64 s, so a 5-minute video silently loses its last four minutes. Size both the interval and the grid from `DUR`:

```bash
CELLS=$(( (DUR + 2) / 3 ))                       # one thumbnail per 3 s
GRID=$(python3 -c "import math; print(max(1, math.ceil(math.sqrt($CELLS))))")
ffmpeg -i output/<slug>.mp4 -vf "fps=1/3,scale=240:-1,tile=${GRID}x${GRID}" \
  -frames:v 1 work/check/sheet.png
```

Measured: 60 s → 20 cells in 5×5; 300 s → 100 cells in 10×10. Never hand-tile a fixed grid for a duration that can reach five minutes.

## 8. Self-made background music

Only when the user supplies none. Use the bundled generator — a single held pad is what made every film from these skills sound the same:

```bash
python3 <skill>/scripts/make_music.py --duration 52 --out audio/music.wav \
    --brief "pasar subuh, hangat, akustik, tenang, sedikit melankolis"
```

**Write the brief from the topic — never reuse the previous film's brief.** The brief decides
scale, chord progression, timbre family, bass motion, arpeggio density, texture and tempo,
and seeds the randomness.

`<skill>` is this skill's own directory; the generator ships with the skill, so the
project folder stays free of build tooling. Run it from the project folder.

It writes 48 kHz stereo 16-bit WAV at exactly `--duration` (so the bed never needs looping), peak −6 dBFS, 1.2 s fade-in, and a fade-out that lands on a floor instead of absolute zero.

**Generate the bed longer than the video** — `--duration` ≈ video duration + 13 s, then `-t $DUR` in step 2. A bed written to the exact video length carries its own fade-out into the film's last second: measured, a 59 s bed on a 59 s video plus the mixing fade left the final 0.5 s at **−52.9 dB** and failed the tail floor; the same brief at 72 s measured **−30.1 dB**.

The bed is a four-chord progression (two bars per chord): each chord gets a detuned two-voice pad, a root bass on beats 1 and 3, a plucked arpeggio on eighths that alternates pan, and a soft noise breath at each chord change.

| Flag | Values | Choose by |
|---|---|---|
| `--brief` | free text (required) | the topic's mood and material — this is the creative decision, write it fresh per film |
| `--tempo` | 60–120 | the film's cut rhythm; omit to let the brief decide |
| `--seed` | integer | force a different take from the same brief |

Each film gets its own brief. Reusing one bed, or one brief, across a series is what made
every film sound alike. If a scene change deserves an accent, place it in the mix rather
than bending the bed's tempo.

Tell the user plainly that this is synthesised music — a progression and a pulse generated in code, not a composed track — and suggest royalty-free music when they want more.

Optional, sparing synthetic SFX for transitions — a whoosh, for example:

```bash
ffmpeg -f lavfi -i "anoisesrc=d=0.4:c=pink:a=0.5" -af "afade=t=in:d=0.1,afade=t=out:st=0.2:d=0.2,volume=0.3" -ar 48000 work/whoosh.wav
```

Use at most a few per video, always below the voiceover level, and tell the user the SFX is synthetic.

## 9. Common traps

- **VFR (variable frame rate):** force CFR with `-r 30`. Verify `r_frame_rate` and `avg_frame_rate` both read 30/1.
- **Duration off by a frame:** usually the drawn frame count differs from `DUR × 30`. Recount before encoding.
- **Audio longer than video** (or the reverse): use `apad=whole_dur=$DUR` and `atrim=0:$DUR` as in the example, plus `-t $DUR`.
- **Font not found:** the path you passed is not the one in the project. Fonts live in `assets/fonts/` (§1); re-download it there — never fall back to a system font or an ugly default.
- **Indonesian text clipped at the edge:** measure width with the font's own measuring function, never by eye.
- **File very large:** raise CRF (e.g. 20–22); never lower the resolution.
- **`alimiter` installed yet `max_volume` stays 0 dB:** alimiter's default `level` is 1 (auto-level) — after limiting, the signal is normalised BACK to 0 dBFS. Use `alimiter=limit=0.85:level=0`. Measured: `limit=0.79` alone still yields max 0.0 dB; with `level=0` it yields −1.3 dB.
- **`amix` + `volume` — never use both.** Measured on ffmpeg 7.1 with a `loudnorm`-processed voiceover (−17.0 dB mean, −1.5 max): `amix` default `normalize=1` → −24.5 dB; `amix` default + `volume=2` → −18.5 dB; `amix normalize=0` → −18.5 dB (**identical**); `normalize=0` + `volume=2` → −12.5 dB, max **0.0 dB (clipping)**.

  Conclusion: `volume=2` with the default `normalize` equals `normalize=0`, so the §6 example is safe on both 6.x and 7.x. The danger is combining them. Pick one, then measure with `volumedetect` — never trust the formula, because `amix` defaults change between versions. If `max_volume` hits 0.0 dB despite `alimiter`, check whether `volume` and `normalize=0` are both applied, then check alimiter's `level` option.
- **`loudnorm` inline + `apad` = dead audio tail:** never combine them in one `filter_complex`. Normalise the voiceover into a separate file first (three-step recipe in §6, gate in §7). Measured: one chain → `silence_start 40.86` in a 43 s video, tail −91 dB; three steps → tail −25 to −33 dB, no dead air inside the speech region.
- **A quiet music bed plus `afade=t=in` can trip the audio gate:** silence is only reported when the opening actually sits under −50 dB for 0.5 s. Measured: a 0.53 s fade-in on a normally-levelled bed produced no `silence_start` at all and passed. Check the level, not the fade — if the bed is quiet enough to fall under −50 dB at the start, let it enter at full level instead.
- **`afade=t=out` ending exactly at the last frame is silence, not a fade-out:** measured, `st=DUR-2.5:d=2.5` on a 28 s video left the final **0.8 s at −61.7 dB** — indistinguishable from the music having stopped. Fade to a floor with a `volume` expression (§6), or stop the fade earlier.
- **Music shorter than the video:** without `-stream_loop -1` the track simply ends and the rest is dead air (measured: 10 s track on a 28 s video → `silence_start 26.0`). The pipeline promises the music is looped; loop it in step 2.
- **Mono output from a mono voiceover:** `-ac 2` on export. Measured `channels=1` without it; platforms accept mono but stereo costs nothing.
- **`silencedetect` `$3` is not the timestamp.** The logger writes `[silencedetect @ 0x…] silence_start: 12.34`, so the time is the **last** field (`$NF`). Filtering on `$3` silently matches nothing and every gate appears to pass.
- **`textbbox` with `anchor` is not the glyph shape:** treating bb[1]/bb[3] as symmetric around the anchor point is wrong for numerals and capital text. Always compute the bbox centre offset from the anchor before placing inside a shape (see `GUIDE.md` §2). Pass the **same anchor** you draw with: the box is in canvas coordinates either way (measured: drawing "92" at (200,100) returns (200,116,311,176) at the default anchor), so the safe-area comparison is valid — but bb[1] is offset from the draw point, which matters for centring.
- **Glyph height taken from `textbbox` is not cap height:** mixed case adds descenders, and a lowercase-only line returns x-height. Measured on DejaVu Sans Bold at size 60: `"KATA"` = 44 px, `"sun"` = 35 px, against a 43 px threshold on a 1080 short side. Using `bb[3]-bb[1]` fails correct type (and passes small type). Measure `font.getbbox("H")` once per face.
- **`blackdetect` default `pix_th=0.1` flags legitimate dark design:** a `0x0B0B0F` background (luma 0.043) is reported as black from `pix_th=0.05` upward; at `0.02` it is clean while true `0x000000` is still caught. Use `pix_th=0.02`.
- **`tile` without `-frames:v 1`** writes the grid once per input frame and fails on the second (`Cannot write more than one file with the same name`, exit −22). Also make sure the tile grid has room: a fixed `8x8` at `fps=1` covers only 64 s, so a 300 s landscape video shows its first minute and silently drops the other four. Size interval and grid from `DUR` (§7).
- **Missing frames mid-sequence truncate the encode:** `-i work/frames/%05d.png` stops at the first gap, and `-pattern_type glob` reorders but does not fill. Measured: a 5-file sequence with `00002.png` missing encoded 2 frames. Assert contiguity before encoding (§6).
- **SRT timestamps from float seconds misformat:** `int(round((s % 1) * 1000))` yields `",1000"` for 1.9996 s, which players reject. Convert to integer milliseconds first, then `divmod` (recipe in §3).
- **`textbbox` with `anchor="mm"` at the origin returns HALF widths:** `bbox[2]` is the right edge measured from a centred origin, so using it as a word's width makes every following word overlap the previous one (measured: adjacent words scored 0.43–1.00 coverage and read as double-printed). Always take `b[2] - b[0]` for advances, totals, and tracking — per character as well.
- **skia-python 144.1 API names differ from older examples:** `skia.RRect` has no `MakeLTRB` (use `skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(...), rx, ry)`), and `Canvas` has no `clipCircle`/`clipRRect` (build a `skia.Path`, `addCircle`/`addRRect` it, then `clipPath`). Probe with `dir()` in a scratch script before writing scene code instead of fixing it after the first crashed frame.
- **A shape drawn as bare lines does not read as its object:** a brush head rendered as ~30 stroked curves reads to a viewer as a porcupine or a broom. Draw the silhouette first — a filled, gradient-shaded mass with a rounded/dome tip — then the hairs on top at low alpha. Measured: it took two visual QC rounds to fix a brush that had only hairs.
- **Missing glyphs render as tofu, not as nothing:** the ⚡ character does not exist in Archivo Black and rendered as a placeholder box mid-video (measured on an otherwise passing gate run — the pixel gates do not catch it). Draw symbols (lightning, arrows, badges) as polygons/paths in code; never put emoji or symbol codepoints through a display font.
- **Decorations must never cross a text band:** a charging cable drawn straight through a centred label, and a connector plug landing on a chip, both measured. When a diagram needs a line where text sits, move the label (e.g. split it into two left-anchored lines beside the line's axis), never layer text over the stroke.
- **Chips and badges: build the box from the measured content, not the reverse:** box = padding + icon + gap + text width, the whole group centred on its anchor. Hand-placing the box and the text separately measured off-centre by tens of pixels. Also: a keyword inside a chip is a *badge*, not primary text — set it in the supporting tier (≥2.5% cap height), not the primary tier, or it dwarfs the card around it.
- **ASR homographs break keyword lookup:** matching the word `jadi` by first occurrence grabbed an earlier sentence's token (and an empty ASR artifact split one word into two), silently collapsing a scene range and leaving an 11-second stretch drawing only the closing scene — which no pixel gate flagged as wrong. Index repeated words from the END (`occ=-1`) for closings/verdicts, and after building the timeline, assert scene ranges are increasing (`a < b` for every consecutive pair).
- **Word-level width math is the collision gate's blind spot's twin:** the geometry gate only fires on the frames you sample. Run the coverage check on frames at *every* sentence midpoint, not just the sync-check moments, or an overlap that appears only while words are mid-pop stays invisible.

## 10. Cleanup after delivery

`work/` holds every intermediate file: `frames/`, `ref/`, `check/`, `voiceover-16k.wav`, `voiceover-norm.wav`, `music-norm.wav`, TTS payloads. It can reach hundreds of megabytes and the user does not need it. Once the video is verified and delivered, delete the whole `work/`.

**Keep — everything a later revision needs:**

| Path | Why it must survive |
|---|---|
| `script.txt` | the narration source; re-generating TTS or re-cutting the script starts here |
| `render.py` | the whole visual design lives in this one file |
| `audio/voiceover.wav` | timing source; re-running ASR or re-mixing needs it |
| `audio/words.json` | **the only non-reproducible derived file** — re-running ASR returns ±0.1 s different timestamps and desyncs a re-render |
| `audio/music.wav` | re-mix without regenerating music |
| `assets/` | user-supplied images and the style reference |
| `output/<slug>.mp4` | the deliverable |
| `output/<slug>.srt` | subtitle track, when generated |
| `output/publish.txt` | caption, description, hashtags for upload |

Before deleting, confirm the required checks passed — duration, frame count, loudness, tail floor, black/freeze — measured from the exported MP4, never from the timeline. Advisory findings (sync, geometry, repetition) are recorded with the decision you took on each.

**Verify the kept set is self-sufficient, not just present.** One command proves a revision is possible after cleanup:

```bash
# every input the build script reads must still exist
grep -oE '(audio|assets|output)/[A-Za-z0-9_.-]+' render.py | sort -u | while read p; do
  [ -e "$p" ] || echo "MISSING for re-render: $p"
done
```

An empty result means `rm -rf work` cost nothing that matters: frames rebuild in one command, and `voiceover-norm.wav` / `music-norm.wav` are two ffmpeg lines that reproduce bit-comparable output from unchanged inputs.

Mention in the delivery message that intermediates were cleaned up, and that the video can be re-rendered from the kept files without re-recording anything.