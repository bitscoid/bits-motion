"""Gerbang QC untuk bits-motion. Pustaka pengukur, bukan wasit.

Prinsip: fungsi di sini MENGUKUR dan MENYARANKAN. Tidak ada yang memutuskan
"video ini bagus". Lulus semua fungsi di sini berarti "tidak cacat", dan
"tidak cacat" bukan "bagus" — rasa tetap keputusan perancang.

Pakai dari skrip render sendiri:

    from gates import safe_area, glyph_size, overlaps, contrast, repeated_pattern

    for t in teks_yang_digambar:
        safe_area(t.bbox, W, H)      # -> list saran, kosong = aman
        glyph_size(t.bbox, H, main=False)
    contrast(fill_rgb, bg_rgb, main=True)

Semua fungsi mengembalikan daftar temuan (string). Kosong = lolos.

Yang TIDAK dilakukan pustaka ini: memilih font, memilih palet, menentukan
jumlah scene, menilai apakah videonya menarik. Itu semua keputusan perancang.
"""

from __future__ import annotations

# --------------------------------------------------------------------- konstanta
# Satu sumber angka. Kalau nilai ini diubah, ubah juga GUIDE.md §2.
SAFE = 0.04  # margin tepi frame
GLYPH_MAIN = 0.04  # tinggi glyph minimum teks utama (% tinggi frame)
GLYPH_SUP = 0.025  # tinggi glyph minimum teks pendukung
CONTRAST_SMALL = 4.5  # WCAG AA teks kecil
CONTRAST_LARGE = 3.0  # WCAG AA teks besar


def _pct(x: float) -> str:
    return f"{x * 100:.2f}%"


# ----------------------------------------------------------------------- geometri
def safe_area(bbox, frame_w: int, frame_h: int, label: str = "") -> list[str]:
    """bbox = (x0, y0, x1, y1) dalam piksel. Kembalikan saran, bukan larangan."""
    x0, y0, x1, y1 = bbox
    mx, my = frame_w * SAFE, frame_h * SAFE
    out = []
    if x0 < mx:
        out.append(f"{label} kurang {mx - x0:.0f}px dari tepi kiri (min {mx:.0f}px)")
    if x1 > frame_w - mx:
        out.append(f"{label} lebih {x1 - (frame_w - mx):.0f}px ke tepi kanan")
    if y0 < my:
        out.append(f"{label} kurang {my - y0:.0f}px dari tepi atas (min {my:.0f}px)")
    if y1 > frame_h - my:
        out.append(f"{label} lebih {y1 - (frame_h - my):.0f}px ke tepi bawah")
    return out


def glyph_size(bbox, frame_h: int, main: bool = True, label: str = "") -> list[str]:
    """Tinggi GLYPH, bukan ukuran font. Glyph kapital ~0,75x ukuran font.

    main=False untuk teks pendukung/label/chip.
    """
    need = GLYPH_MAIN if main else GLYPH_SUP
    h = bbox[3] - bbox[1]
    if h < need * frame_h:
        kind = "utama" if main else "pendukung"
        return [
            f"{label} tinggi glyph {h:.0f}px = {_pct(h / frame_h)}, "
            f"minimum {kind} {_pct(need)} ({need * frame_h:.0f}px). "
            f"Naikkan ukuran font ~{need * frame_h * 1.33:.0f}px atau pendekkan barisnya."
        ]
    return []


def overlaps(bboxes, threshold: float = 0.16):
    """bboxes = [(bbox, label), ...]. Kembalikan pasangan yang bertabrakan."""

    def iou(a, b):
        x0, y0 = max(a[0], b[0]), max(a[1], b[1])
        x1, y1 = min(a[2], b[2]), min(a[3], b[3])
        if x1 <= x0 or y1 <= y0:
            return 0.0
        inter = (x1 - x0) * (y1 - y0)
        union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
        return inter / union

    out = []
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            a, la = bboxes[i]
            b, lb = bboxes[j]
            if la == lb:
                continue  # teks sama digambar dua kali (teks di atas blok sorot), disengaja
            v = iou(a, b)
            if v > threshold:
                out.append(f"'{la}' dan '{lb}' bertabrakan (IoU {v:.2f})")
    return out


# ------------------------------------------------------------------------ kontras
def _lum(c) -> float:
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (f(x) for x in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg, main: bool = True, label: str = "") -> list[str]:
    """Rasio kontras WCAG. fg/bg = (r, g, b) 0-255.

    Ambang diikat ke PERAN teks, bukan ukuran piksel:
      - teks utama    : 3,0:1
      - teks pendukung: 4,5:1 — lebih ketat dari WCAG "large text", karena teks
                        kecil yang bergerak cepat terbaca jauh lebih buruk
                        daripada teks diam berukuran sama.
    """
    la, lb = sorted((_lum(fg), _lum(bg)), reverse=True)
    ratio = (la + 0.05) / (lb + 0.05)
    need = CONTRAST_LARGE if main else CONTRAST_SMALL
    if ratio < need:
        kind = "utama" if main else "pendukung"
        return [
            f"{label} kontras {ratio:.2f}:1, butuh {need:.1f}:1 untuk teks {kind}. "
            f"Beri panel solid, gelapkan area di belakangnya, atau ganti warnanya."
        ]
    return []


# ------------------------------------------------------------------ pola berulang
def repeated_pattern(frames_per_scene, labels=None) -> list[str]:
    """Tandai scene berurutan yang strukturnya sama. TIDAK menolak, hanya menandai.

    frames_per_scene = list PIL.Image, satu frame tengah per scene.
    """

    def sig(img):
        g = img.convert("L")
        w, h = g.size
        px = g.load()
        ink_x = ink_y = n = 0
        dark_bg = True
        total = 0
        step = max(1, (w * h) // 20000)  # sampling supaya cepat
        for y in range(0, h, step):
            for x in range(0, w, step):
                v = px[x, y]
                total += v
                if v < 110:
                    ink_x += x
                    ink_y += y
                    n += 1
        if n < 50:
            return ("kosong",)
        return (
            round(ink_x / n / w, 1),
            round(ink_y / n / h, 1),
            round(n / max(1, total and (w * h / step / step)), 2),
            "gelap" if (total / max(1, (w // step) * (h // step))) < 100 else "terang",
        )

    sigs = [sig(f) for f in frames_per_scene]
    out = []
    for i in range(1, len(sigs)):
        if sigs[i] == sigs[i - 1] and sigs[i] != ("kosong",):
            a = labels[i - 1] if labels else i - 1
            b = labels[i] if labels else i
            out.append(
                f"scene {a} dan {b} berpola sama {sigs[i]} — sengaja diulang atau kebetulan? "
                f"Tulis alasan di timeline."
            )
    return out


# ------------------------------------------------------------------------- rekap
def report(findings: dict[str, list[str]]) -> str:
    """findings = {'nama gerbang': [temuan, ...]}. Cetak ringkas, tanpa keputusan."""
    lines = []
    total = 0
    for name, items in findings.items():
        total += len(items)
        lines.append(f"== {name}: {len(items)} temuan")
        for it in items[:20]:
            lines.append(f"   {it}")
    lines.append("")
    lines.append(f"total temuan: {total}")
    lines.append(
        "Ingat: 0 temuan berarti tidak cacat, bukan berarti bagus. "
        "Rasa dan variasi tetap keputusan perancang."
    )
    return "\n".join(lines)
