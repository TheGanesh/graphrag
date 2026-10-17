"""Tiny SVG toolkit used to draw every figure in this guide.

Design goals: one consistent "notebook" look (warm paper, dark ink,
handwritten annotations, sticky notes), legible on GitHub in both light
and dark themes (each figure carries its own paper background), and no
external dependencies.
"""
from __future__ import annotations

import math
import re
from xml.sax.saxutils import escape

INK = "#1f2933"
MUTED = "#5b6670"
PAPER = "#fffdf6"
PAPER_EDGE = "#e3d9c6"
RED = "#c0392b"

KINDS = {
    # name: (fill, stroke)
    "db": ("#e8f4dc", "#4c8a1d"),      # ArangoDB / storage (avocado green)
    "llm": ("#efe8fb", "#6847c0"),     # language models
    "search": ("#e4effb", "#2b67ad"),  # retrieval / search
    "doc": ("#fff3d4", "#a87500"),     # documents, text, data
    "user": ("#fde7e1", "#c4462a"),    # people, questions, answers
    "plain": ("#ffffff", "#3d4852"),
    "gray": ("#f2efe8", "#8b8578"),
    "ok": ("#e3f5ea", "#1e8449"),
    "warn": ("#fdeaea", "#c0392b"),
    "note": ("#fff6b3", "#d8bd3a"),    # sticky note
}

SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
HAND = "'Comic Neue', 'Comic Sans MS', 'Chalkboard SE', 'Marker Felt', 'Segoe Print', cursive"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace"

AQL_KEYWORDS = {
    "FOR", "IN", "RETURN", "FILTER", "SORT", "LIMIT", "LET", "COLLECT", "INTO", "WITH",
    "COUNT", "AGGREGATE", "INSERT", "UPDATE", "UPSERT", "REPLACE", "REMOVE", "SEARCH",
    "OUTBOUND", "INBOUND", "ANY", "GRAPH", "DESC", "ASC", "DISTINCT", "OPTIONS", "AND",
    "OR", "NOT", "NULL", "TRUE", "FALSE", "PRUNE", "KEEP", "LIKE",
    # Cypher, for side-by-side comparisons
    "MATCH", "WHERE", "MERGE", "CALL", "YIELD", "UNWIND", "ORDER", "BY", "CREATE", "SET",
    "OPTIONAL", "AS",
}


def esc(s: str) -> str:
    return escape(str(s), {'"': "&quot;"})


def text_width(s: str, size: float, font: str = "sans") -> float:
    """Rough width estimate used for layout (verified by rendering)."""
    factor = {"sans": 0.56, "hand": 0.58, "mono": 0.61, "bold": 0.6}[font]
    return len(s) * size * factor


def wrap(s: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    for para in str(s).split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= max_chars:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


class Fig:
    def __init__(self, w: int, h: int, title: str = "", subtitle: str = "", desc: str = ""):
        self.w, self.h = w, h
        self.title, self.subtitle = title, subtitle
        self.desc = desc or title
        self.items: list[str] = []
        self.markers: dict[str, str] = {}

    # ------------------------------------------------------------------ core
    def raw(self, s: str) -> None:
        self.items.append(s)

    def marker(self, color: str) -> str:
        mid = "ah" + color.strip("#")
        if mid not in self.markers:
            self.markers[mid] = (
                f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" '
                f'markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse">'
                f'<path d="M0,0.8 L10,5 L0,9.2 z" fill="{color}"/></marker>'
            )
        return mid

    def text(self, x, y, s, size=15, color=INK, anchor="start", weight="normal",
             font="sans", italic=False, lh=None, rotate=0, halo=False, opacity=1.0):
        fam = {"sans": SANS, "hand": HAND, "mono": MONO}[font]
        lines = str(s).split("\n")
        lh = lh or size * 1.28
        y0 = y - (len(lines) - 1) * lh / 2 if anchor == "middle-v" else y
        anchor_attr = "middle" if anchor in ("middle", "middle-v") else anchor
        style = ' font-style="italic"' if italic else ""
        tr = f' transform="rotate({rotate} {x} {y})"' if rotate else ""
        hal = (f' stroke="{PAPER}" stroke-width="5" stroke-linejoin="round" paint-order="stroke"'
               if halo else "")
        op = f' opacity="{opacity}"' if opacity != 1.0 else ""
        spans = "".join(
            f'<tspan x="{x}" dy="{0 if i == 0 else lh}">{esc(line)}</tspan>'
            for i, line in enumerate(lines)
        )
        self.raw(
            f'<text x="{x}" y="{y0}" font-family="{fam}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor_attr}" font-weight="{weight}"{style}{tr}{hal}{op}>{spans}</text>'
        )

    # ---------------------------------------------------------------- shapes
    def box(self, x, y, w, h, label="", sub="", kind="plain", size=16, sub_size=13,
            radius=12, dashed=False, sub_chars=None, label_color=None, bold=True, stroke_w=2):
        fill, stroke = KINDS[kind]
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        self.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{stroke_w}"{dash}/>')
        cx = x + w / 2
        sub_lines = wrap(sub, sub_chars or max(8, int(w / (sub_size * 0.55)))) if sub else []
        n_label = len(label.split("\n")) if label else 0
        total = n_label * size * 1.2 + len(sub_lines) * sub_size * 1.25 + (4 if sub_lines and label else 0)
        ty = y + h / 2 - total / 2 + size * 0.95
        if label:
            self.text(cx, ty, label, size=size, anchor="middle", weight="bold" if bold else "normal",
                      color=label_color or INK, lh=size * 1.2)
            ty += n_label * size * 1.2 + 4
        if sub_lines:
            self.text(cx, ty + sub_size * 0.05 - (size * 0.15 if label else 0), "\n".join(sub_lines),
                      size=sub_size, anchor="middle", color=MUTED, lh=sub_size * 1.25)
        return (x, y, w, h)

    def cylinder(self, x, y, w, h, label="", sub="", kind="db", size=16, sub_size=13):
        fill, stroke = KINDS[kind]
        rx, ry = w / 2, min(13, h * 0.16)
        body = (f"M{x},{y + ry} L{x},{y + h - ry} A{rx},{ry} 0 0,0 {x + w},{y + h - ry} "
                f"L{x + w},{y + ry}")
        self.raw(f'<path d="{body}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        self.raw(f'<ellipse cx="{x + rx}" cy="{y + ry}" rx="{rx}" ry="{ry}" fill="#ffffff" '
                 f'stroke="{stroke}" stroke-width="2"/>')
        inner = (x, y + 2 * ry, w, h - 2 * ry)
        cx = x + w / 2
        sub_lines = wrap(sub, max(8, int(w / (sub_size * 0.55)))) if sub else []
        total = size * 1.2 + len(sub_lines) * sub_size * 1.25
        ty = inner[1] + inner[3] / 2 - total / 2 + size * 0.9
        if label:
            self.text(cx, ty, label, size=size, anchor="middle", weight="bold")
        if sub_lines:
            self.text(cx, ty + size * 1.15, "\n".join(sub_lines), size=sub_size, anchor="middle",
                      color=MUTED, lh=sub_size * 1.25)
        return (x, y, w, h)

    def doc(self, x, y, w=54, h=66, kind="doc", lines=4, label=""):
        fill, stroke = KINDS[kind]
        f = 14
        d = f"M{x},{y} L{x + w - f},{y} L{x + w},{y + f} L{x + w},{y + h} L{x},{y + h} z"
        self.raw(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="2" stroke-linejoin="round"/>')
        self.raw(f'<path d="M{x + w - f},{y} L{x + w - f},{y + f} L{x + w},{y + f}" fill="none" '
                 f'stroke="{stroke}" stroke-width="2" stroke-linejoin="round"/>')
        for i in range(lines):
            yy = y + 22 + i * 10
            if yy > y + h - 8:
                break
            self.raw(f'<line x1="{x + 9}" y1="{yy}" x2="{x + w - 10 - (i % 2) * 10}" y2="{yy}" '
                     f'stroke="{stroke}" stroke-width="2" stroke-linecap="round" opacity="0.55"/>')
        if label:
            self.text(x + w / 2, y + h + 18, label, size=13, anchor="middle", color=MUTED)

    def person(self, x, y, s=1.0, kind="user", label=""):
        fill, stroke = KINDS[kind]
        self.raw(f'<circle cx="{x}" cy="{y}" r="{11 * s}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        self.raw(f'<path d="M{x - 19 * s},{y + 38 * s} Q{x - 19 * s},{y + 15 * s} {x},{y + 15 * s} '
                 f'Q{x + 19 * s},{y + 15 * s} {x + 19 * s},{y + 38 * s} z" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2" stroke-linejoin="round"/>')
        if label:
            self.text(x, y + 56 * s, label, size=14, anchor="middle", weight="bold")

    def llm(self, x, y, w=120, h=70, label="LLM", sub=""):
        """Language model drawn as a chip with pins."""
        fill, stroke = KINDS["llm"]
        for i in range(4):
            px = x + 18 + i * (w - 36) / 3
            self.raw(f'<line x1="{px}" y1="{y - 7}" x2="{px}" y2="{y}" stroke="{stroke}" stroke-width="3" stroke-linecap="round"/>')
            self.raw(f'<line x1="{px}" y1="{y + h}" x2="{px}" y2="{y + h + 7}" stroke="{stroke}" stroke-width="3" stroke-linecap="round"/>')
        self.box(x, y, w, h, label, sub, kind="llm")
        self.raw(f'<path d="M{x + w - 16},{y + 9} l2.5,6 6,2.5 -6,2.5 -2.5,6 -2.5,-6 -6,-2.5 6,-2.5 z" '
                 f'fill="{stroke}" opacity="0.8"/>')

    def node(self, x, y, r=24, label="", kind="db", size=13, label_pos="below", sub=""):
        fill, stroke = KINDS[kind]
        self.raw(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        if label:
            if label_pos == "inside":
                self.text(x, y + size * 0.35, label, size=size, anchor="middle", weight="bold")
            else:
                self.text(x, y + r + size + 3, label, size=size, anchor="middle", weight="bold")
        if sub:
            self.text(x, y + r + size * 2 + 6, sub, size=size - 1, anchor="middle", color=MUTED)
        return (x, y, r)

    def edge(self, a, b, label="", color=INK, curve=0.0, dashed=False, width=2, size=13,
             label_dx=0, label_dy=0, both=False):
        """Arrow between two circles a=(x,y,r) and b=(x,y,r)."""
        (x1, y1, r1), (x2, y2, r2) = a, b
        ang = math.atan2(y2 - y1, x2 - x1)
        if curve:
            ang1 = ang - curve * 0.6
            ang2 = ang + math.pi + curve * 0.6
        else:
            ang1, ang2 = ang, ang + math.pi
        sx, sy = x1 + r1 * math.cos(ang1), y1 + r1 * math.sin(ang1)
        ex, ey = x2 + (r2 + 2) * math.cos(ang2), y2 + (r2 + 2) * math.sin(ang2)
        self.arrow(sx, sy, ex, ey, label=label, color=color, curve=curve * 80, dashed=dashed,
                   width=width, size=size, label_dx=label_dx, label_dy=label_dy, both=both)

    def arrow(self, x1, y1, x2, y2, label="", color=INK, curve=0.0, dashed=False, width=2,
              size=13, label_dx=0, label_dy=0, both=False, hand=False, label_color=None):
        mid = self.marker(color)
        dash = ' stroke-dasharray="7 6"' if dashed else ""
        start = f' marker-start="url(#{mid})"' if both else ""
        if curve:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            ln = math.hypot(dx, dy) or 1
            cx, cy = mx - dy / ln * curve, my + dx / ln * curve
            d = f"M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}"
            lx, ly = 0.25 * x1 + 0.5 * cx + 0.25 * x2, 0.25 * y1 + 0.5 * cy + 0.25 * y2
        else:
            d = f"M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
        self.raw(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
                 f'stroke-linecap="round"{dash} marker-end="url(#{mid})"{start}/>')
        if label:
            self.text(lx + label_dx, ly + label_dy + size * 0.35, label, size=size, anchor="middle",
                      color=label_color or (MUTED if color == INK else color), italic=not hand,
                      font="hand" if hand else "sans", halo=True)

    def poly(self, pts, label="", color=INK, dashed=False, width=2, size=13, label_at=None,
             label_dx=0, label_dy=-6, hand=False):
        mid = self.marker(color)
        dash = ' stroke-dasharray="7 6"' if dashed else ""
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.raw(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
                 f'stroke-linejoin="round" stroke-linecap="round"{dash} marker-end="url(#{mid})"/>')
        if label:
            i = label_at if label_at is not None else len(pts) // 2 - 1
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            self.text((ax + bx) / 2 + label_dx, (ay + by) / 2 + label_dy, label, size=size,
                      anchor="middle", color=MUTED if color == INK else color, italic=not hand,
                      font="hand" if hand else "sans", halo=True)

    def note(self, x, y, s, w=190, size=14, rot=-2.0, kind="note", chars=None, color=INK):
        """Sticky note with handwritten text."""
        fill, stroke = KINDS[kind]
        lines = wrap(s, chars or max(10, int((w - 20) / (size * 0.56))))
        h = 18 + len(lines) * size * 1.3
        cx, cy = x + w / 2, y + h / 2
        self.raw(f'<g transform="rotate({rot} {cx} {cy})">'
                 f'<rect x="{x + 3}" y="{y + 4}" width="{w}" height="{h}" fill="#000" opacity="0.06" rx="3"/>'
                 f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" '
                 f'stroke-width="1.5" rx="3"/>')
        self.text(x + 10, y + 10 + size, "\n".join(lines), size=size, font="hand", color=color,
                  lh=size * 1.3)
        self.raw("</g>")
        return h

    def hand(self, x, y, s, size=15, color=RED, anchor="start", rotate=0):
        """Handwritten annotation."""
        self.text(x, y, s, size=size, font="hand", color=color, anchor=anchor, rotate=rotate,
                  lh=size * 1.25)

    def scribble_arrow(self, x1, y1, x2, y2, color=RED, curve=30):
        self.arrow(x1, y1, x2, y2, color=color, curve=curve, width=1.8)

    def code(self, x, y, w, lines, size=13, title="", lh=None, pad=12, dark=True, hl=True):
        """Code card with very small AQL/Cypher highlighting."""
        lh = lh or size * 1.45
        h = pad * 2 + len(lines) * lh + (22 if title else 0)
        bg, fg = ("#1f2933", "#e8edf2") if dark else ("#ffffff", INK)
        self.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{bg}" '
                 f'stroke="{"#1f2933" if dark else "#b9b2a2"}" stroke-width="1.5"/>')
        ty = y + pad + size
        if title:
            self.text(x + pad, y + pad + 11, title, size=12, color="#9fb3c8" if dark else MUTED,
                      font="sans", weight="bold")
            ty += 22
        for line in lines:
            self.raw(self._code_line(x + pad, ty, line, size, fg, hl and dark))
            ty += lh
        return h

    def _code_line(self, x, y, line, size, fg, hl):
        if not hl:
            return (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" fill="{fg}" '
                    f'xml:space="preserve">{esc(line)}</text>')
        parts = []
        for tok in re.findall(r"//.*$|'[^']*'|\"[^\"]*\"|@@?\w+|\w+|\s+|.", line):
            color = fg
            if tok.startswith("//"):
                color = "#8b9aa8"
            elif tok[:1] in "'\"":
                color = "#a8d8a0"
            elif tok.startswith("@"):
                color = "#8fb8ff"
            elif tok.upper() in AQL_KEYWORDS and tok.isupper():
                color = "#ffc66d"
            elif re.fullmatch(r"[A-Z_][A-Z0-9_]*", tok) and len(tok) > 2:
                color = "#f0a6ca"  # FUNCTION_NAMES
            parts.append(f'<tspan fill="{color}">{esc(tok)}</tspan>')
        return (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" '
                f'xml:space="preserve">{"".join(parts)}</text>')

    def pill(self, x, y, s, kind="gray", size=12, pad=8, anchor="start"):
        fill, stroke = KINDS[kind]
        w = text_width(s, size) + pad * 2
        x0 = x - w / 2 if anchor == "middle" else x
        self.raw(f'<rect x="{x0}" y="{y - size - 3}" width="{w}" height="{size + 10}" rx="{(size + 10) / 2}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        self.text(x0 + w / 2, y + 1, s, size=size, anchor="middle", color=INK)
        return w

    def badge(self, x, y, n, kind="user", r=13):
        fill, stroke = KINDS[kind]
        self.raw(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{stroke}"/>')
        self.text(x, y + 5, str(n), size=14, anchor="middle", color="#ffffff", weight="bold")

    def brain(self, x, y, s=1.0, color=KINDS["user"][1]):
        """Small doodle used for 'think about it' moments."""
        p = (f"M{x},{y} c{-14*s},{-2*s} {-20*s},{-16*s} {-8*s},{-24*s} c{0},{-12*s} {16*s},{-16*s} {22*s},{-8*s} "
             f"c{8*s},{-8*s} {26*s},{-4*s} {24*s},{8*s} c{12*s},{6*s} {8*s},{24*s} {-6*s},{26*s} "
             f"c{-6*s},{6*s} {-24*s},{6*s} {-32*s},{-2*s} z")
        self.raw(f'<path d="{p}" fill="#fde7e1" stroke="{color}" stroke-width="2"/>')
        self.raw(f'<path d="M{x + 6*s},{y - 26*s} q{4*s},{8*s} {-2*s},{14*s} M{x + 18*s},{y - 18*s} '
                 f'q{-6*s},{6*s} {2*s},{12*s}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>')

    # ---------------------------------------------------------------- output
    def svg(self) -> str:
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
            f'width="{self.w}" height="{self.h}" role="img" aria-labelledby="t d">'
            f'<title id="t">{esc(self.title)}</title><desc id="d">{esc(self.desc)}</desc>'
            f'<defs>{"".join(self.markers.values())}</defs>'
            f'<rect x="1" y="1" width="{self.w - 2}" height="{self.h - 2}" rx="18" fill="{PAPER}" '
            f'stroke="{PAPER_EDGE}" stroke-width="2"/>'
        )
        title = ""
        if self.title:
            title += (f'<text x="28" y="44" font-family="{SANS}" font-size="23" font-weight="bold" '
                      f'fill="{INK}">{esc(self.title)}</text>')
        if self.subtitle:
            title += (f'<text x="28" y="70" font-family="{HAND}" font-size="16" fill="{MUTED}">'
                      f'{esc(self.subtitle)}</text>')
        return head + title + "".join(self.items) + "</svg>\n"

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.svg())
