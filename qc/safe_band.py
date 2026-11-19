#!/usr/bin/env python3
"""
Asserts the portrait content box in GUIDE.md §2 / RENDER.md §7. No browser.

    python3 qc/safe_band.py

Organic short-form only. See GUIDE.md §2 for the numbers and the sources.
"""

W, H = 1080, 1920

# Sources, as fractions of the frame: wrapped-video scene-grammar.md (top 12%,
# bottom 18%, sides 5%) and motioner typography.md (top 250 px, bottom 400 px on
# a 1080-wide frame). Top is 13% to clear the taller of the two.
BOX = dict(top=0.13, bottom=0.20, left=0.05, right=0.05, read_bottom=0.28)

# The action rail (like/comment/share/audio) sits down the lower right.
RAIL = dict(from_y=0.55, inset_right=0.12)

EXPECTED = dict(
    x0=54, x1=1026, y0=250, y1=1536, read_y1=1382, rail_y=1056, rail_x=950, area=60
)

x0, x1 = round(W * BOX["left"]), round(W * (1 - BOX["right"]))
y0, y1 = round(H * BOX["top"]), round(H * (1 - BOX["bottom"]))
read_y1 = round(H * (1 - BOX["read_bottom"]))
rail_y = round(H * RAIL["from_y"])
rail_x = round(W * (1 - RAIL["inset_right"]))

for k, v in dict(
    x0=x0, x1=x1, y0=y0, y1=y1, read_y1=read_y1, rail_y=rail_y, rail_x=rail_x
).items():
    assert v == EXPECTED[k], f"{k} drifted: {v} != {EXPECTED[k]}"

# Symmetric sides: the horizontal centre is the frame centre.
assert (x0 + x1) / 2 == W / 2
# The vertical centre sits high, because the platforms stack UI at the bottom.
assert (y0 + y1) / 2 < H / 2
assert H / 2 - (y0 + y1) / 2 == 67

assert BOX["bottom"] > BOX["top"]
assert BOX["read_bottom"] > BOX["bottom"], "read line must sit above the caption stack"

area = round((x1 - x0) * (y1 - y0) / (W * H) * 100)
assert area == EXPECTED["area"], f"area drifted to {area}%"
assert area > 55
assert x1 - x0 > W * 0.85, "the box must span nearly the full width"

print(
    f"safe band OK: x {x0}..{x1}, y {y0}..{y1} ({x1 - x0}x{y1 - y0}, {area}% of frame); "
    f"read line {read_y1}; rail below y {rail_y} pulls right to x {rail_x}"
)
