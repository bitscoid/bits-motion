# Visual and Creative Direction

Read this before building any scene. It covers execution — typography, asset animation, transitions, sync, audio. **Visual style always comes from the chosen reference video**; adapt to the user's assets and topic rather than imposing one palette or layout everywhere.

## Contents
1. Reading a reference video
2. Kinetic typography
3. Animating assets
4. Transitions
5. Turning ideas into visuals
6. Variation that keeps a system
7. Sync with the voiceover
8. Music and audio mixing

## 1. Reading a reference video

A reference is a quality bar, not a mould. What transfers is the principle — why the video feels good, not the order of its effects.

Look at: palette, typographic hierarchy, how text and image stack, cut rhythm, transition types, use of shadow and depth, and how motion relates to sound.

Forbidden: copying shots one by one, reusing the exact composition, placing text in the same positions, or reproducing the animation and transition order frame by frame. The goal is work that is original and tighter than its reference.

## 2. Kinetic typography

Typography is a storytelling element, not a subtitle layer.

Techniques, chosen by context: text appearing with the spoken word, mask reveals, staged word or letter reveals, controlled overshoot scaling, letter-spacing animation, text emerging from behind objects, creative clipping and layering, emphasis through weight, colour, or size.

Rules:
- Choose fonts that are modern, heavy, and highly legible. Use real fonts through code (never text rendered by an image generator) so letters never break or turn into fake words.

  **The font catalogue is not a menu.** The list in `RENDER.md` §"Fonts ready to use" is what happens to be installed, not the set of allowed choices. Your job is to pick typography that **fits the topic and the reference mood**, not the first row of the table. If the topic needs something missing (a food topic wanting a fat slab serif, an archive topic wanting a heavy condensed face, a tech topic wanting a narrow grotesk), **download it** — never settle for "close enough" just because it's installed. The download recipe and verification are in `RENDER.md` §1.

  The limit is quantity, not typeface: at most 2–3 families per video so it stays one system. Verify with `fc-list` or `fc-query` before using it in a scene.
- Preserve spelling and meaning exactly as scripted.
- Break copy into short phrases. Never show a whole paragraph at once. Highlight keywords only.
- Keep clear levels: title, keyword, supporting line, small label.
- Avoid random capitals, hard-to-read faces, and decorative excess.
- Respect the safe area: important elements stay at least **4%** from the frame edge — one number, so there is never a second truth about it (the geometry gate in `RENDER.md` §7 uses 4%).

  **Short-form platforms need more.** 4% is the floor for the file itself; on Reels, TikTok, Shorts and Stories the platform UI covers roughly the bottom 12–15% and the right 10–12% with captions, buttons and progress. For a **portrait** export (`1080×1920`), keep primary text inside **10% from the bottom and 12% from the right**, and say in the delivery message which zone you used. Landscape/YouTube keeps the plain 4%. This is a platform constraint, not taste — measure it, and never let a keyword land in the covered band. The 4% gate still runs on everything; the platform band is a second, stricter margin applied on top for portrait.
- The smallest text must stay legible at output resolution. **The threshold is glyph height, not font size.** Two tiers, measured as a fraction of the **short side** so portrait and landscape share one number:

  | Tier | Glyph height | Short side 1920 | Short side 1080 |
  |---|---|---|---|
  | primary / keywords | ≥ 4% | 77 px | 43 px |
  | supporting / labels / chips | ≥ 2.5% | 48 px | 27 px |

  Font size to reach that height depends on the face: measured on DejaVu Sans Bold, capitals are **0.73× the size**. So on a 1080 short side, primary needs **size ≈ 60** and supporting **≈ 37**; on 1920, **≈ 105** and **≈ 66**. A condensed or display face has a different ratio — measure `textbbox` once for the font you chose and solve for the size; never assume 0.75 or copy a number from a table for a different face.

  Writing only the 1920 figures is what makes a landscape video ship with text half the intended size. Measure the result; don't estimate.

  If a supporting line will not fit at 2.5% alongside other elements, cut words from that line — never lower the threshold.
- Check text-against-background contrast in code, never by judging colour names. Thresholds are measurable and tied to the text's **role**, not its pixel size:
  - **primary text / keywords: 3.0:1**
  - **supporting text / labels / chips: 4.5:1** — stricter than WCAG "large text", because small moving text reads far worse than static text of the same size.

  Compute with the WCAG formula:

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

  On failure: place a solid panel behind the text or darken the area — never rely on a thin drop shadow. Text over user images must be measured against the pixels actually behind it (sample the region), not the image's dominant colour.

  **Pick the accent by measurement, not by eye.** A palette pass that removes the whole failure class: choose the topic's hue, then walk its lightness until the measured ratio clears the threshold for the role it will carry.

```python
import colorsys
def fit_accent(rgb, bg, target):
    """Darken/lighten `rgb` in HSL until it clears `target` against `bg`."""
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    for _ in range(60):
        cand = tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, l, s))
        if ratio(cand, bg) >= target:
            return cand
        l = max(0.0, l - 0.012)
    return (0, 0, 0)                     # fall back to ink, never to a failing colour
```

Run it once per role (primary 3.0, supporting 4.5) and use the result everywhere the accent carries text. The accent then stays one colour across the video — `§6`'s "hold one thing constant" — while never shipping an unreadable pair.
- **Centring is measured, not delegated to `anchor`.** `anchor="mm"` centres the font's em box, not the glyph shape — numerals, capital titles, and text with descenders visibly drift inside a shape. For text sitting inside an object (a numeral in a circle, a label on a card, text in a colour block), offset by the glyph bbox:

```python
bb = d.textbbox((px, py), s, font=f, anchor="mm")
dx = (bb[0] + bb[2]) / 2 - px
dy = (bb[1] + bb[3]) / 2 - py
d.text((px - dx, py - dy), s, font=f, anchor="mm", fill=fill)
```

  Measured: offset 10 px → 0.5 px. If a camera transform is active (scale/shift), divide `dx` and `dy` by the scale before applying. If the text uses per-letter `spacing`, `anchor` no longer applies — measure total width and centre it manually; never mix the two methods.
- **Text stacks are measured, not assumed.** When several lines stack vertically (label, title, subtitle), compute each line's top/bottom from `textbbox` and confirm there is no intersection. Reading order must match narrative order, and the last line must not crowd the object below it — leave at least ~0.8× line height.

## 3. Animating assets

Important assets must not sit still unless there is a deliberate beat of rest. This is a requirement, not an option: every scene keeps at least one element moving at all times; if nothing would naturally move, use micro camera motion (slow zoom drift or a gentle pan across the scene). A motion graphic that is static in any scene fails QC (the freezedetect gate is in `RENDER.md` §7).

The lower bound is not taste, it is the encoder: motion that is too small (radius <15 px, shift <10 px) can be quantised away at CRF 18+, leaving identical frames. Measure the motion; don't assume.

Techniques: scale in/out, directional motion and gentle rotation, parallax and depth layers, mask reveals, controlled camera zoom, creative cropping, floating motion and secondary motion, motion blur and soft shadows, and visual relationships between assets and text.

Vary techniques with content. Use professional easing (acceleration, deceleration, overshoot, anticipation, settling) rather than constant speed.

You may crop, resize, position, mask, and layer user assets as long as meaning and important detail survive. Never cut through a key subject, never stretch an image, never leave elements colliding awkwardly.

Background removal: if no cut-out tool exists, use manual masking or framing that looks good without a cut-out — and never promise a cut-out you cannot produce.

## 4. Transitions

Options: match cut, whip, directional wipe, mask reveal, shape transition, scale transition, typography-driven transition, layered parallax transition, motion-blur transition, and graphic elements that carry across scenes.

These are options, not a checklist. Pick what fits the content and keep the system coherent. Where possible, connect visual elements across scenes so nothing feels severed.

Rhythm comes from content, not numbers. The "core scenes run a few seconds" note merely describes short video in general — if an idea needs 8 seconds to land, give it 8. What still holds: put the biggest variation in the opening, and never make late-third scenes so short the viewer cannot absorb them.

Avoid excessive glitch, random spins, unmotivated flashes, and transitions that mask the explanation. Every transition must fit inside the computed total duration. The video never grows because of a transition.

## 5. Turning ideas into visuals

Typography alone makes a video feel like a moving-text presentation. What separates strong motion graphics is a **visual idea** — one way of seeing the concept that can be drawn.

Before building scenes, give each core point one **visual mechanism**, not just a big word in the centre:

| Mechanism | Question it answers | Example form |
|---|---|---|
| Scale / ratio | "how big is it?" | one small figure among hundreds; a huge number against a tiny object |
| Accumulation | "what does it pile into?" | objects multiplying until they fill the frame (obligations, demands, hours) |
| Transformation | "what does it become?" | one shape turning into another (toy → study desk) |
| Splitting | "what is coming apart?" | one shape cleaving, a piece drifting away (child vs demands) |
| Path / motion | "where is it heading?" | timeline, arrow, forking route |
| Container / capacity | "does it fit?" | a glass overflowing, a box crammed, capacity filled |
| Side-by-side contrast | "what is the difference?" | two states adjacent, not sequential |
| Cycle | "how does it repeat?" | a rotating loop, the same day recurring |

Working rules:
- One main mechanism per scene. Two at once weaken each other.
- Borrowing visual idioms (bar chart, clock, stack) is fine, but never let them stay generic icons with no meaning specific to this topic.
- If an idea cannot be drawn without text, the idea isn't visual yet — change the mechanism instead of adding words.
- A mechanism may recur as a motif across scenes (accumulation used twice) as long as its form evolves.

This is not a required list. If an idea has a better shape outside the table, use it.

## 6. Variation that keeps a system

A short video with a dozen scenes slides easily into "same layout, different words". How to avoid it without losing coherence:

- **Vary composition**, not just content: text left + image right, plain centred text, text hugging an edge, text layered behind an object, very small text in a wide space.
- **Vary density**: dense scenes (many elements) alternating with airy ones (one element, lots of space). Uniform density exhausts the viewer.
- **Vary background**: light/dark may alternate, but hold one accent colour across the whole video so it reads as one family.
- **Vary scale**: one scene with an oversized element bleeding off-frame makes the rest feel airy even at normal size.
- **Hold one thing constant**: one accent colour, one display face, one dominant motion type. That constant is what makes the variation feel intentional rather than random.

Check the result with a contact sheet (`ffmpeg ... tile`) before export: if every thumbnail follows the same pattern, variation is insufficient.

**Make the check quantitative.** Rate each scene on four axes and keep the vector beside the timeline; three consecutive scenes on the same vector is the failure, not two.

```python
scene["vary"] = dict(
    zone   = "left | centre | right | edge | full",   # where the mass sits
    density= "airy | medium | dense",
    scale  = "small | normal | oversized",            # oversized = bleeds off-frame
    bg     = "light | dark",
)
```

Two identical neighbours can be a deliberate pair (a before/after, a repeat motif). Three is the signature of a template. `RENDER.md` §7's repetition gate measures the same thing from the rendered pixels and prints it; this vector is what you consult while planning, before any frame is drawn.

## 7. Sync with the voiceover

The voiceover is the primary timing source; total duration is set in stage 4 of `SKILL.md` (voice + lead-in + tail, capped by `MAX_DUR`, default 60 s).

Word timing comes from the audio itself through speech recognition with per-word timestamps, not from word count (`RENDER.md` §3). Every text appearance reads from one absolute-time table (`RENDER.md` §5), and the result is proven by the sync gate (`RENDER.md` §7): text may never appear before its word.

For each key phrase: show the text as the word is spoken, reveal assets when relevant, emphasise keywords through scale/colour/weight/position/motion, allow a brief visual pause when the viewer needs to absorb, and match animation speed to the speaker's pace.

Motion must feel like a response to the voice, not random spinning. Visual effects never pull attention away from the information being explained.

Text without a supporting word in the voiceover remains legitimate (silent emphasis) — record the reason in the timeline; do not delete it merely because the sync gate cannot verify it.

**Captions are a second, separate layer.** Kinetic typography is the design; burned-in captions are the accessibility and retention baseline every short-form platform expects. If the user wants them, they come from the same `work/words.json` (`RENDER.md` §3) and never replace the kinetic type — style them small, low, and steady, in the covering safe zone (`§2`), with at most 3 words per cue. A subtitle file (`output/<slug>.srt`) is free from the same data; offer it whenever the video is going to a platform.

## 8. Music and audio mixing

- The voiceover stays clear and dominant. Duck the music under speech, especially during important information.
- Align some transitions or animation accents to the beat when it genuinely suits the narration.
- Use sound effects sparingly; they never compete with the narrator.
- Never speed up speech or cut words to hit a duration. Preserve natural rhythm and pauses.
- Fade music out smoothly and end audio exactly on the final second — no tail, no abrupt cut. Fade **to a floor, not to absolute zero**: measured, ending the fade exactly on the last frame leaves the final 0.8 s at −61.7 dB, which is indistinguishable from the music having died. The recipe in `RENDER.md` §6 does this with a `volume` expression.
- Prevent clipping, distortion, sudden level changes, and unintended silence. Measure the finished mix: **I between −17 and −14 LUFS, true peak ≤ −1 dBTP** (`RENDER.md` §7). A quiet mix passes every other gate and still plays badly on every platform.
- Music must be **looped to the video length**, not played once (`-stream_loop -1`). A 10 s track on a 28 s video otherwise leaves 18 s of silence.
- If the video is a beat-driven piece, derive the beat grid from the music instead of guessing: a tempo estimate plus the scene-change times is enough to snap transitions to the pulse. Keep it subtle — the narration leads, the beat supports.

Tempo from the music itself — onset strength, then the median gap between onsets:

```python
import wave, numpy as np
w = wave.open("audio/music.wav"); sr = w.getframerate()
a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
hop = int(sr * 0.01)                                  # 10 ms resolution
env = np.array([np.abs(a[i:i+hop]).max() for i in range(0, len(a) - hop, hop)])
d = np.diff(env)
peaks = [i for i in range(1, len(d)) if d[i] > 0.15 and d[i] >= d[i - 1]]
onsets, last = [], None
for p in peaks:                                       # collapse a hit into one onset
    if last is None or p - last > 10:
        onsets.append(p); last = p
gap = np.median(np.diff(onsets)) * 0.01               # seconds per beat
bpm, beat = 60 / gap, gap
```

Measured on a synthetic 120 BPM click: median gap 0.500 s → 120 BPM, 31 onsets over 16 s. Treat the result as a grid to snap optional accents onto, never as a requirement that scenes start on beats.

If the user has no music: build simple background music that fits the visual style (`RENDER.md` §8) and say plainly that it is synthesised music. Alternatively render silent and suggest the user add royalty-free music.