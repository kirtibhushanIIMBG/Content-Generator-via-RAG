"""Generate the animated SVGs embedded in README.md.

GitHub renders README images through <img>, which runs CSS animations inside an SVG but never
scripts or external resources. So every file here is self-contained: inline <style>, system
fonts, no JS. Each animation loops on one shared cycle per file; timing lives in keyframe
percentages, never in animation-delay, so loops stay in sync forever.

Base (non-animated) styles are the FINISHED state, so prefers-reduced-motion — which switches
every animation off — shows a complete static diagram.

    python3 tools/gen_readme_svgs.py assets/readme

The evaluation numbers in evalchart() are copied from eval/last_run.json (the 22 July 2026
run). Update them there when a new full run is published, then regenerate.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

# ---------------------------------------------------------------- tokens
CARD = "#161b22"      # card surface (validated against: #3987e5 passes all dataviz checks)
INSET = "#0d1117"     # caption bar / sample box
BOX = "#1c2330"       # stage box fill
LINE = "#30363d"      # hairlines, borders
WIRE = "#484f58"      # idle connectors
INK = "#f0f6fc"       # primary text
INK2 = "#c9d1d9"      # secondary text
MUTED = "#8b949e"     # muted text
BLUE = "#3987e5"      # accent / chart series (dataviz dark slot 1)
AQUA = "#199e70"      # second series (dataviz dark slot 3)
YELLOW = "#c98500"    # gate (dataviz dark slot 4)
RED = "#e66767"       # refusal (dataviz dark slot 8)
GOOD = "#0ca30c"      # status: good (always with an icon + label)

SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif'
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'


def f(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


class Anim:
    """Collects keyframes for one SVG; every animation shares the cycle length T."""

    def __init__(self, T: float):
        self.T = T
        self.rules: list[str] = []
        self.n = 0

    def add(self, points: list[tuple[float, str]], extra: str = "", ease: str = "linear") -> str:
        """points: (time_s, css-declarations). Returns a class name to put on the element."""
        pts = sorted(points, key=lambda p: p[0])
        if pts[0][0] > 0:
            pts.insert(0, (0.0, pts[0][1]))
        if pts[-1][0] < self.T:
            pts.append((self.T, pts[-1][1]))
        self.n += 1
        name = f"k{self.n}"
        frames = " ".join(f"{max(0, min(100, t / self.T * 100)):.3f}% {{{d}}}" for t, d in pts)
        self.rules.append(f"@keyframes {name} {{{frames}}}")
        anim = f"{name} {f(self.T)}s {ease} infinite both"
        if extra:
            anim += ", " + extra
        self.rules.append(f".{name} {{animation: {anim};}}")
        return name

    def window(self, on: float, off: float, *, fade: float = 0.25, peak: float = 1,
               after: float = 0, hold_until: float | None = None, reset: float | None = None,
               extra: str = "") -> str:
        """Opacity 0 → peak during [on, off], then `after` until hold_until, then 0 by reset."""
        pts = [(0, "opacity:0"), (on, "opacity:0"), (on + fade, f"opacity:{peak}"), (off, f"opacity:{peak}")]
        if after:
            pts += [(off + 0.3, f"opacity:{after}")]
            if hold_until is not None:
                pts += [(hold_until, f"opacity:{after}"), (reset, "opacity:0")]
        else:
            pts += [(off + fade, "opacity:0")]
        return self.add(pts, extra)

    def css(self) -> str:
        return "\n".join(self.rules)


def svg_open(w: int, h: int, title: str, desc: str, anim: Anim, extra_css: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">
<title id="t">{escape(title)}</title>
<desc id="d">{escape(desc)}</desc>
<style>
text {{ font-family: {SANS}; }}
.mono {{ font-family: {MONO}; }}
.t1 {{ font-size: 22px; font-weight: 600; fill: {INK}; }}
.t2 {{ font-size: 15px; fill: {MUTED}; }}
.bt {{ font-size: 17px; font-weight: 600; fill: {INK}; }}
.bl {{ font-size: 13px; fill: {MUTED}; }}
.num {{ font-size: 13px; font-weight: 700; fill: {INK}; }}
.cap {{ font-size: 15.5px; fill: {INK2}; }}
.tb {{ transform-box: fill-box; }}
@keyframes flow {{ to {{ stroke-dashoffset: -20; }} }}
{extra_css}
%%ANIM%%
@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; }}
  .rm-show {{ opacity: 1 !important; }}
  .rm-hide {{ opacity: 0 !important; }}
}}
</style>
<defs>
<filter id="glow" x="-20%" y="-30%" width="140%" height="160%">
<feGaussianBlur in="SourceGraphic" stdDeviation="5" result="b"/>
<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
</defs>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="{CARD}" stroke="{LINE}"/>
"""


def header(title: str, sub: str) -> str:
    return (f'<text x="40" y="48" class="t1">{escape(title)}</text>\n'
            f'<text x="40" y="74" class="t2">{escape(sub)}</text>\n')


def arrowhead(x: float, y: float, direction: str, color: str) -> str:
    """Triangle whose tip sits at (x, y)."""
    a, b = 9, 5
    pts = {
        "right": [(x, y), (x - a, y - b), (x - a, y + b)],
        "left": [(x, y), (x + a, y - b), (x + a, y + b)],
        "down": [(x, y), (x - b, y - a), (x + b, y - a)],
        "up": [(x, y), (x - b, y + a), (x + b, y + a)],
    }[direction]
    return f'<polygon points="{" ".join(f"{f(px)},{f(py)}" for px, py in pts)}" fill="{color}"/>'


def connector(x1, y1, x2, y2, direction, color, *, dash="", width=2) -> str:
    # stop the line short of the tip so the arrowhead stays crisp
    sx = {"right": -8, "left": 8}.get(direction, 0)
    sy = {"down": -8, "up": 8}.get(direction, 0)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2 + sx)}" y2="{f(y2 + sy)}" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round"{d}/>' + arrowhead(x2, y2, direction, color))


def stage_box(x, y, w, h, num, title, lines, *, title_cls="bt") -> str:
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{BOX}" stroke="{LINE}"/>',
           f'<circle cx="{x + 24}" cy="{y + 26}" r="12" fill="{LINE}"/>',
           f'<text x="{x + 24}" y="{y + 30.5}" class="num" text-anchor="middle">{num}</text>',
           f'<text x="{x + 44}" y="{y + 31}" class="{title_cls}" data-fit="{x},{x + w}">{escape(title)}</text>']
    for i, ln in enumerate(lines):
        out.append(f'<text x="{x + 18}" y="{y + 56 + i * 19}" class="bl" data-fit="{x},{x + w}">{escape(ln)}</text>')
    return "\n".join(out)


def stage_overlay(x, y, w, h, num, color, cls, base=0.45) -> str:
    return (f'<g class="{cls}" opacity="{base}">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{color}" fill-opacity="0.10" '
            f'stroke="{color}" stroke-width="2" filter="url(#glow)"/>'
            f'<circle cx="{x + 24}" cy="{y + 26}" r="12" fill="{color}"/>'
            f'<text x="{x + 24}" y="{y + 30.5}" class="num" text-anchor="middle" fill="#ffffff">{num}</text></g>')


def caption_bar(x, y, w, h) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{INSET}" stroke="{LINE}"/>'


def captions(anim: Anim, texts: list[tuple[float, float, str]], x: float, y: float,
             static_text: str, fit: tuple[int, int]) -> str:
    out = []
    for on, off, txt in texts:
        cls = anim.window(on, off, fade=0.2)
        out.append(f'<text x="{x}" y="{y}" class="cap {cls} rm-hide" opacity="0" data-fit="{fit[0]},{fit[1]}">{escape(txt)}</text>')
    out.append(f'<text x="{x}" y="{y}" class="cap rm-show" opacity="0" data-fit="{fit[0]},{fit[1]}">{escape(static_text)}</text>')
    return "\n".join(out)


def progress(anim: Anim, x, y, w, start, end, hold_until, reset) -> str:
    grow = anim.add([(0, "transform:scaleX(0)"), (start, "transform:scaleX(0)"), (end, "transform:scaleX(1)"),
                     (reset, "transform:scaleX(1)"), (reset + 0.01, "transform:scaleX(0)")])
    fade = anim.add([(0, "opacity:1"), (hold_until, "opacity:1"), (reset, "opacity:0"), (reset + 0.05, "opacity:1")])
    return (f'<rect x="{x}" y="{y}" width="{w}" height="4" rx="2" fill="{LINE}"/>'
            f'<g class="{fade}"><rect x="{x}" y="{y}" width="{w}" height="4" rx="2" fill="{BLUE}" '
            f'class="tb {grow}" style="transform-origin: 0 50%"/></g>')


def check_icon(cx, cy, color=GOOD, r=9) -> str:
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{r}" fill="{color}"/>'
            f'<path d="M{f(cx - 4)},{f(cy + 0.5)} l3,3 l5.5,-6" fill="none" stroke="#ffffff" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')


def cross_icon(cx, cy, color=RED, r=9) -> str:
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{r}" fill="{color}"/>'
            f'<path d="M{f(cx - 3.5)},{f(cy - 3.5)} l7,7 M{f(cx + 3.5)},{f(cy - 3.5)} l-7,7" stroke="#ffffff" '
            f'stroke-width="2" stroke-linecap="round"/>')


# ================================================================ 1. hero
def hero() -> str:
    W, H, T = 960, 392, 12.0
    a = Anim(T)
    L1 = "From 13 May 2027, a Data Fiduciary must inform the Board and each affected"
    L2 = "Data Principal of a personal data breach."
    c1w, c2w = 760, 430

    def cover(on, off, w):
        # cover shrinks toward its right edge → text appears left to right; at the end it grows
        # back (right to left) to "erase" before the loop restarts. Base opacity 0 = text shown.
        return a.add([(0, "opacity:1;transform:scaleX(1)"), (on, "opacity:1;transform:scaleX(1)"),
                      (off, "opacity:1;transform:scaleX(0)"), (10.8, "opacity:1;transform:scaleX(0)"),
                      (11.4, "opacity:1;transform:scaleX(1)")])

    def cursor(on, off, dist):
        return a.add([(0, "opacity:0;transform:translateX(0)"), (on - 0.05, "opacity:0;transform:translateX(0)"),
                      (on, "opacity:1;transform:translateX(0)"), (off, f"opacity:1;transform:translateX({dist}px)"),
                      (off + 0.05, f"opacity:0;transform:translateX({dist}px)")])

    def pop(t, until=10.8):
        return a.add([(0, "opacity:0;transform:translateY(6px)"), (t, "opacity:0;transform:translateY(6px)"),
                      (t + 0.35, "opacity:1;transform:translateY(0)"), (until, "opacity:1;transform:translateY(0)"),
                      (until + 0.5, "opacity:0;transform:translateY(0)")], ease="cubic-bezier(.2,.7,.2,1)")

    cv1, cv2 = cover(0.5, 2.6, c1w), cover(2.6, 3.6, c2w)
    cu1, cu2 = cursor(0.5, 2.6, c1w), cursor(2.6, 3.6, c2w)
    chip = pop(3.9)
    ok1, ok2 = pop(4.6), pop(5.2)
    p1, p2, p3 = pop(6.0), pop(6.35), pop(6.7)

    body = [svg_open(W, H, "Content Generator via RAG",
                     "Animated banner. An example sentence is typed out: 'From 13 May 2027, a Data Fiduciary must "
                     "inform the Board and each affected Data Principal of a personal data breach.' A citation "
                     "tag appears beside it: DPDP Act 2023, s.8(6). Two checks follow: the citation matches a "
                     "retrieved provision (Act, page 7), and the duty is dated honestly because it applies from "
                     "13 May 2027. Three labels close it: grounded in the official text, checked by code, "
                     "approved by a person.", a,
                     extra_css=f".hero {{ font-size: 40px; font-weight: 700; fill: {INK}; letter-spacing: -0.5px; }}\n"
                               f".sub {{ font-size: 18px; fill: {INK2}; }}\n"
                               f".eyebrow {{ font-size: 12.5px; font-weight: 600; fill: {MUTED}; letter-spacing: 1.6px; }}\n"
                               f".sample {{ font-size: 16.5px; fill: {INK}; }}\n"
                               f".small {{ font-size: 12px; fill: {MUTED}; }}\n"
                               f".ok {{ font-size: 14px; fill: {INK2}; }}\n"
                               f".pill {{ font-size: 13.5px; fill: {INK}; }}"),
            f'<rect x="48" y="38" width="36" height="4" rx="2" fill="{BLUE}"/>',
            '<text x="48" y="66" class="eyebrow">CITATION-GROUNDED CONTENT GENERATION</text>',
            '<text x="48" y="110" class="hero" data-fit="40,920">Content Generator via RAG</text>',
            '<text x="48" y="142" class="sub" data-fit="40,920">Marketing content grounded in India’s DPDP Act 2023 and DPDP Rules 2025</text>',
            # sample box
            f'<rect x="48" y="164" width="864" height="96" rx="12" fill="{INSET}" stroke="{LINE}"/>',
            '<text x="68" y="188" class="small">EXAMPLE OF A CITED CLAIM</text>',
            f'<text x="68" y="217" class="sample" data-fit="48,{68 + c1w}">{escape(L1)}</text>',
            f'<text x="68" y="244" class="sample" data-fit="48,{68 + c2w}">{escape(L2)}</text>',
            f'<rect x="64" y="200" width="{c1w}" height="24" fill="{INSET}" class="tb {cv1}" style="transform-origin: 100% 50%" opacity="0"/>',
            f'<rect x="64" y="227" width="{c2w}" height="24" fill="{INSET}" class="tb {cv2}" style="transform-origin: 100% 50%" opacity="0"/>',
            f'<rect x="66" y="201" width="2" height="21" fill="{BLUE}" class="{cu1}" opacity="0"/>',
            f'<rect x="66" y="228" width="2" height="21" fill="{BLUE}" class="{cu2}" opacity="0"/>',
            # citation chip
            f'<g class="{chip}"><rect x="672" y="226" width="222" height="26" rx="13" fill="{BLUE}" fill-opacity="0.18" stroke="{BLUE}"/>'
            f'<text x="783" y="244" class="mono" font-size="14" fill="{INK}" text-anchor="middle" data-fit="672,894">DPDP Act 2023, s.8(6)</text></g>',
            # checks
            f'<g class="{ok1}">{check_icon(57, 285)}<text x="74" y="290" class="ok" data-fit="48,912">Citation matches a provision the system retrieved (DPDP_Act_2023.pdf, page 7)</text></g>',
            f'<g class="{ok2}">{check_icon(57, 311)}<text x="74" y="316" class="ok" data-fit="48,912">Dated honestly: this duty applies only from 13 May 2027</text></g>',
        ]
    pills = [("Grounded in the official text", BLUE, p1, 48, 248),
             ("Checked by code", AQUA, p2, 308, 160),
             ("Approved by a person", GOOD, p3, 480, 196)]
    for label, color, cls, x, w in pills:
        body.append(f'<g class="{cls}"><rect x="{x}" y="336" width="{w}" height="32" rx="16" fill="{BOX}" stroke="{LINE}"/>'
                    f'<circle cx="{x + 18}" cy="352" r="5" fill="{color}"/>'
                    f'<text x="{x + 32}" y="357" class="pill" data-fit="{x},{x + w}">{escape(label)}</text></g>')
    body.append("</svg>")
    return "\n".join(body).replace("%%ANIM%%", a.css())


# ================================================================ 2. build time
def build() -> str:
    W, H, T = 960, 380, 14.0
    a = Anim(T)
    S = [(0.4, 2.2), (2.2, 4.2), (4.2, 7.8), (7.8, 9.8), (9.8, 12.0)]
    HOLD, RESET = 13.3, 13.9

    def lit(i):  # stage overlay: bright while active, dim after, gone at reset
        on, off = S[i]
        return a.window(on, off, after=0.45, hold_until=HOLD, reset=RESET)

    out = [svg_open(W, H, "How the law gets in",
                    "Animated diagram of the one-time build. Two official PDFs, the DPDP Act 2023 (44 sections, "
                    "9 chapters) and the DPDP Rules 2025 (23 rules, 7 schedules), go into a rule-based chunker "
                    "that splits them at every Section, Rule and Schedule. The result is 81 chunks: 49 from the "
                    "Act and 32 from the Rules. Each chunk is embedded by meaning with OpenAI and by exact terms "
                    "with BM25, then stored in Qdrant Cloud.", a),
           header("How the law gets in", "Done once at build time, and again whenever the law is amended.")]

    # documents
    docs = [(40, 100, "DPDP Act 2023", "44 sections · 9 chapters"),
            (40, 180, "DPDP Rules 2025", "23 rules · 7 schedules")]
    doc_cls = lit(0)
    for x, y, t, s in docs:
        w, h, fold = 172, 66, 14
        out.append(f'<path d="M{x},{y + 10} a10,10 0 0 1 10,-10 h{w - 10 - fold} l{fold},{fold} v{h - fold - 10} '
                   f'a10,10 0 0 1 -10,10 h-{w - 20} a10,10 0 0 1 -10,-10 z" fill="{BOX}" stroke="{LINE}"/>')
        out.append(f'<path d="M{x + w - fold},{y} v{fold} h{fold}" fill="none" stroke="{LINE}"/>')
        out.append(f'<text x="{x + 14}" y="{y + 28}" class="bt" font-size="15" data-fit="{x},{x + w}">{t}</text>')
        out.append(f'<text x="{x + 14}" y="{y + 48}" class="bl" font-size="12" data-fit="{x},{x + w}">{s}</text>')
        out.append(f'<path class="{doc_cls}" d="M{x},{y + 10} a10,10 0 0 1 10,-10 h{w - 10 - fold} l{fold},{fold} '
                   f'v{h - fold - 10} a10,10 0 0 1 -10,10 h-{w - 20} a10,10 0 0 1 -10,-10 z" fill="{BLUE}" '
                   f'fill-opacity="0.10" stroke="{BLUE}" stroke-width="2" filter="url(#glow)" opacity="0.45"/>')
    # bracket from both docs into the chunker
    out.append(f'<path d="M212,133 h12 v80 h-12" fill="none" stroke="{WIRE}" stroke-width="2"/>')
    out.append(connector(224, 173, 248, 173, "right", WIRE))

    # chunker
    cx, cy, cw, ch = 248, 110, 156, 126
    out.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="12" fill="{BOX}" stroke="{LINE}"/>')
    out.append(f'<text x="{cx + 16}" y="{cy + 30}" class="bt" font-size="16" data-fit="{cx},{cx + cw}">Chunker</text>')
    for i, ln in enumerate(["splits at every", "Section, Rule and", "Schedule; tables", "stay whole"]):
        out.append(f'<text x="{cx + 16}" y="{cy + 54 + i * 17}" class="bl" font-size="12.5" data-fit="{cx},{cx + cw}">{ln}</text>')
    out.append(stage_overlay_plain(cx, cy, cw, ch, BLUE, lit(1)))
    scan = a.add([(0, "opacity:0;transform:translateY(0)"), (S[1][0], "opacity:0;transform:translateY(0)"),
                  (S[1][0] + 0.1, "opacity:1;transform:translateY(0)"), (S[1][0] + 0.9, f"opacity:1;transform:translateY({ch - 8}px)"),
                  (S[1][0] + 1.0, "opacity:1;transform:translateY(0)"), (S[1][0] + 1.8, f"opacity:1;transform:translateY({ch - 8}px)"),
                  (S[1][0] + 1.9, f"opacity:0;transform:translateY({ch - 8}px)")])
    out.append(f'<rect x="{cx + 6}" y="{cy + 4}" width="{cw - 12}" height="2" rx="1" fill="{BLUE}" class="{scan}" opacity="0"/>')
    out.append(connector(404, 173, 438, 173, "right", WIRE))

    # 81-chunk grid: 49 Act (blue) then 32 Rules (aqua), filled one by one
    gx, gy, sz, gap = 446, 104, 12, 4
    t0, t1 = S[2][0] + 0.1, S[2][1] - 0.5
    step = (t1 - t0) / 81
    for k in range(81):
        r, c = divmod(k, 9)
        color = BLUE if k < 49 else AQUA
        tk = t0 + k * step
        cls = a.add([(0, "opacity:0.12"), (tk, "opacity:0.12"), (tk + 0.12, "opacity:1"),
                     (HOLD, "opacity:1"), (RESET, "opacity:0.12")])
        out.append(f'<rect x="{gx + c * (sz + gap)}" y="{gy + r * (sz + gap)}" width="{sz}" height="{sz}" rx="2" fill="{color}" class="{cls}"/>')
    lab = a.add([(0, "opacity:0"), (S[2][1] - 0.4, "opacity:0"), (S[2][1] - 0.1, "opacity:1"), (HOLD, "opacity:1"), (RESET, "opacity:0")])
    out.append(f'<text x="516" y="266" class="bt {lab}" font-size="15" text-anchor="middle">81 chunks</text>')
    out.append(f'<rect x="450" y="279" width="10" height="10" rx="2" fill="{BLUE}"/>'
               f'<text x="466" y="288" class="bl" font-size="12.5">49 Act</text>'
               f'<rect x="522" y="279" width="10" height="10" rx="2" fill="{AQUA}"/>'
               f'<text x="538" y="288" class="bl" font-size="12.5">32 Rules</text>')
    out.append(connector(592, 173, 630, 173, "right", WIRE))

    # embed
    ex, ew = 630, 158
    out.append(f'<rect x="{ex}" y="{cy}" width="{ew}" height="{ch}" rx="12" fill="{BOX}" stroke="{LINE}"/>')
    out.append(f'<text x="{ex + 16}" y="{cy + 30}" class="bt" font-size="16" data-fit="{ex},{ex + ew}">Embed</text>')
    for i, ln in enumerate(["by meaning:", "OpenAI, 3,072-d", "by exact terms:", "BM25 sparse"]):
        out.append(f'<text x="{ex + 16}" y="{cy + 54 + i * 17}" class="bl" font-size="12.5" data-fit="{ex},{ex + ew}">{ln}</text>')
    out.append(stage_overlay_plain(ex, cy, ew, ch, BLUE, lit(3)))
    out.append(connector(788, 173, 828, 173, "right", WIRE))

    # Qdrant cylinder, filling from the bottom
    qx, qw, top, bot = 836, 90, 122, 222
    rx_, ry_ = qw / 2, 11
    mid = qx + qw / 2
    out.append(f'<clipPath id="cyl"><path d="M{qx},{top} a{rx_},{ry_} 0 0 0 {qw},0 v{bot - top} a{rx_},{ry_} 0 0 1 -{qw},0 z"/></clipPath>')
    out.append(f'<path d="M{qx},{top} v{bot - top} a{rx_},{ry_} 0 0 0 {qw},0 v-{bot - top}" fill="{BOX}" stroke="{LINE}"/>')
    fill = a.add([(0, "transform:scaleY(0)"), (S[4][0], "transform:scaleY(0)"), (S[4][1] - 0.3, "transform:scaleY(1)"),
                  (HOLD, "transform:scaleY(1)"), (RESET, "transform:scaleY(0)")], ease="cubic-bezier(.3,.6,.3,1)")
    out.append(f'<g clip-path="url(#cyl)"><rect x="{qx}" y="{top - ry_}" width="{qw}" height="{bot - top + 2 * ry_}" '
               f'fill="{BLUE}" fill-opacity="0.55" class="tb {fill}" style="transform-origin: 50% 100%"/></g>')
    out.append(f'<ellipse cx="{mid}" cy="{top}" rx="{rx_}" ry="{ry_}" fill="{BOX}" stroke="{LINE}"/>')
    out.append(f'<text x="{mid}" y="252" class="bt" font-size="14" text-anchor="middle" data-fit="820,950">Qdrant Cloud</text>')
    out.append(f'<text x="{mid}" y="270" class="bl" font-size="12" text-anchor="middle" data-fit="820,950">collection “dpdp”</text>')

    # captions + progress
    out.append(caption_bar(40, 304, 880, 46))
    caps = ["Input: the two official Gazette PDFs, the DPDP Act 2023 and the final DPDP Rules 2025.",
            "A rule-based chunker splits them at every Section, Rule and Schedule. Tables stay whole.",
            "Result: 81 chunks, each carrying its citation, PDF page number and in-force date.",
            "Each chunk is indexed twice: by meaning (OpenAI embeddings) and by exact terms (BM25).",
            "Everything lands in Qdrant Cloud. The live app never needs the build machine again."]
    texts = [(on, off, c) for (on, off), c in zip(S, caps)]
    texts.append((S[4][1], RESET - 0.2, "Re-run these steps whenever the law is amended."))
    out.append(captions(a, texts, 60, 332, "PDFs → chunker → 81 chunks → embeddings → Qdrant Cloud", (40, 920)))
    out.append(progress(a, 40, 360, 880, S[0][0], S[4][1], HOLD, RESET))
    out.append("</svg>")
    return "\n".join(out).replace("%%ANIM%%", a.css())


def stage_overlay_plain(x, y, w, h, color, cls) -> str:
    return (f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{color}" fill-opacity="0.10" '
            f'stroke="{color}" stroke-width="2" filter="url(#glow)" opacity="0.45"/>')


# ================================================================ 3. run-time pipeline
def pipeline() -> str:
    W, H, T = 960, 560, 18.0
    a = Anim(T)
    D = 1.9
    s = [0.4 + i * D for i in range(8)]
    END, HOLD, RESET = s[7] + D, 17.2, 17.8
    bw, bh = 190, 88
    xs = [40, 270, 500, 730]
    y1, y2 = 104, 330
    c1, c2 = y1 + bh / 2, y2 + bh / 2
    stages = [
        (xs[0], y1, "Topic", ["what to write about", "app or n8n form"], BLUE),
        (xs[1], y1, "Retrieve", ["dense + BM25 search", "6 best provisions"], BLUE),
        (xs[2], y1, "Relevance gate", ["best match ≥ 0.25?", "if not, refuse"], YELLOW),
        (xs[3], y1, "Draft", ["GPT-5.6 Terra writes", "backup: Claude Sonnet 5"], BLUE),
        (xs[3], y2, "cite_check", ["citations and dates", "checked by plain code"], BLUE),
        (xs[2], y2, "Human review", ["approve · edit · reject", "a person decides"], BLUE),
        (xs[1], y2, "Approved", ["only approved drafts", "can leave the system"], GOOD),
        (xs[0], y2, "Delivered", [".md file or Google Doc", "disclaimer included"], GOOD),
    ]
    out = [svg_open(W, H, "How a draft is made",
                    "Animated pipeline in eight steps, highlighted one at a time with a caption. 1 Topic. "
                    "2 Retrieve: hybrid dense and BM25 search returns the 6 best provisions. 3 Relevance gate: "
                    "if the best match scores below 0.25 the system refuses with 'no grounded source' before "
                    "calling any AI model. 4 Draft: GPT-5.6 Terra writes from those provisions, with Claude "
                    "Sonnet 5 as backup. 5 cite_check: plain code verifies every citation and date; an invented "
                    "citation or wrong date gets one retry. 6 Human review: approve, edit or reject. "
                    "7 Approved: only approved drafts can leave. 8 Delivered as a .md file or Google Doc with "
                    "the disclaimer.", a),
           header("How a draft is made", "Every request takes this path. A person signs off before anything leaves.")]

    # idle connectors
    conns = [  # (x1, y1, x2, y2, dir, into-stage index)
        (xs[0] + bw, c1, xs[1], c1, "right", 1), (xs[1] + bw, c1, xs[2], c1, "right", 2),
        (xs[2] + bw, c1, xs[3], c1, "right", 3), (795, y1 + bh, 795, y2, "down", 4),
        (xs[3], c2, xs[2] + bw, c2, "left", 5), (xs[2], c2, xs[1] + bw, c2, "left", 6),
        (xs[1], c2, xs[0] + bw, c2, "left", 7),
    ]
    for x1, yy1, x2, yy2, d, _ in conns:
        out.append(connector(x1, yy1, x2, yy2, d, WIRE))
    # side paths: refusal under the gate, retry beside cite_check
    gx = xs[2] + bw / 2
    out.append(connector(gx, y1 + bh, gx, 234, "down", WIRE, dash="4 4"))
    out.append(f'<rect x="465" y="234" width="260" height="38" rx="19" fill="{BOX}" stroke="{LINE}"/>')
    out.append(cross_icon(487, 253, color="#6e3a3a"))
    out.append(f'<text x="504" y="258" font-size="14" fill="{INK2}" data-fit="465,725">Refused: “no grounded source”</text>')
    out.append(connector(885, y2, 885, y1 + bh, "up", WIRE, dash="4 4"))
    out.append(f'<text x="876" y="266" font-size="13" fill="{MUTED}" text-anchor="end" data-fit="800,885">1 retry</text>')

    for i, (x, y, title, lines, color) in enumerate(stages):
        out.append(stage_box(x, y, bw, bh, i + 1, title, lines,
                             title_cls="bt mono" if title == "cite_check" else "bt"))

    # active highlights (drawn above the boxes)
    for i, (x, y, title, lines, color) in enumerate(stages):
        cls = a.window(s[i], s[i] + D, after=0.45, hold_until=HOLD, reset=RESET)
        out.append(stage_overlay(x, y, bw, bh, i + 1, color, cls))
    for x1, yy1, x2, yy2, d, into in conns:
        color = stages[into][4]
        cls = a.window(s[into] - 0.35, s[into] + D, after=0.45, hold_until=HOLD, reset=RESET,
                       extra="flow 1s linear infinite")
        out.append(f'<g class="{cls}" opacity="0.45">{connector(x1, yy1, x2, yy2, d, color, dash="6 4")}</g>')
    # side-path highlights: refusal during the gate step, retry during cite_check
    r = a.window(s[2] + 0.5, s[2] + D - 0.1, extra="flow 1s linear infinite")
    out.append(f'<g class="{r}" opacity="0">{connector(gx, y1 + bh, gx, 234, "down", RED, dash="6 4")}'
               f'<rect x="465" y="234" width="260" height="38" rx="19" fill="none" stroke="{RED}" stroke-width="2"/>'
               f'{cross_icon(487, 253)}</g>')
    rt = a.window(s[4] + 0.5, s[4] + D - 0.1, extra="flow 1s linear infinite")
    out.append(f'<g class="{rt}" opacity="0">{connector(885, y2, 885, y1 + bh, "up", YELLOW, dash="6 4")}</g>')

    out.append(caption_bar(40, 452, 880, 64))
    caps = [
        "A topic comes in, typed into the web app or sent by the n8n form through the API.",
        "Hybrid search finds the 6 most relevant provisions, by meaning and by exact terms like “Section 8(7)”.",
        "If nothing scores at least 0.25, the system refuses here, before any AI model is called.",
        "The model writes only from those 6 provisions and cites each claim. If OpenAI fails, Claude takes over.",
        "Plain code checks every citation and date. An invented citation or a wrong date earns one redraft.",
        "A person approves, edits or rejects. Approving a draft that failed the checks needs a written reason.",
        "Only an approved draft can be downloaded or used. Rejected drafts never leave.",
        "Out it goes as a .md file or a Google Doc, always carrying the not-legal-advice disclaimer.",
    ]
    texts = [(s[i], s[i] + D, c) for i, c in enumerate(caps)]
    texts.append((END, RESET - 0.2, "Every draft: grounded in the law, checked by code, approved by a person."))
    out.append(captions(a, texts, 62, 490, "Topic → retrieve → gate → draft → cite_check → human review → approved → delivered",
                        (40, 920)))
    out.append(progress(a, 40, 532, 880, s[0], END, HOLD, RESET))
    out.append("</svg>")
    return "\n".join(out).replace("%%ANIM%%", a.css())


# ================================================================ 4. n8n flow
def n8n() -> str:
    W, H, T = 960, 568, 17.0
    a = Anim(T)
    D = 2.1
    s = [0.4 + i * D for i in range(6)]
    END, HOLD, RESET = s[5] + D, 15.6, 16.3
    bw, bh = 250, 86
    xs = [40, 355, 670]
    y1, y2 = 104, 330
    c1, c2 = y1 + bh / 2, y2 + bh / 2
    stages = [
        (xs[0], y1, "Form", ["topic, link, word limit,", "format, use current news?"]),
        (xs[1], y1, "Relevance check", ["POST /relevance", "is the topic in the DPDP texts?"]),
        (xs[2], y1, "Ideas (optional)", ["Claude reads trending news", "or the reference article"]),
        (xs[2], y2, "Pick an idea", ["the user chooses", "what to write about"]),
        (xs[1], y2, "Generate", ["POST /generate, once", "per chosen format"]),
        (xs[0], y2, "Google Docs", ["one Doc per format,", "saved to Drive for review"]),
    ]
    out = [svg_open(W, H, "The n8n automation",
                    "Animated flow of the n8n workflow in six steps. 1 Form: topic, optional link, word limit, "
                    "format and whether to use current news. 2 Relevance check through the API; off-topic "
                    "subjects let the user tie them to DPDP, go general, or stop. 3 Optional ideas: Claude "
                    "reads trending news or the reference article. 4 The user picks an idea. 5 The API "
                    "generates once per chosen format. 6 Each draft is saved as a Google Doc in Drive for "
                    "human review: blog, LinkedIn long, LinkedIn short, newsletter.", a),
           header("The n8n automation", "Form in, Google Docs out. Import n8n/DPDP Content W.json to run it.")]
    conns = [(xs[0] + bw, c1, xs[1], c1, "right", 1), (xs[1] + bw, c1, xs[2], c1, "right", 2),
             (795, y1 + bh, 795, y2, "down", 3), (xs[2], c2, xs[1] + bw, c2, "left", 4),
             (xs[1], c2, xs[0] + bw, c2, "left", 5)]
    for x1, yy1, x2, yy2, d, _ in conns:
        out.append(connector(x1, yy1, x2, yy2, d, WIRE))
    # off-topic branch under the relevance check
    ox = xs[1] + bw / 2
    out.append(connector(ox, y1 + bh, ox, 230, "down", WIRE, dash="4 4"))
    out.append(f'<rect x="250" y="230" width="460" height="36" rx="18" fill="{BOX}" stroke="{LINE}"/>')
    out.append(f'<text x="480" y="253" font-size="14" fill="{INK2}" text-anchor="middle" data-fit="250,710">'
               f'Off-topic? The user can tie it to DPDP, go general, or stop</text>')
    for i, (x, y, title, lines) in enumerate(stages):
        out.append(stage_box(x, y, bw, bh, i + 1, title, lines))
    for i, (x, y, *_r) in enumerate(stages):
        cls = a.window(s[i], s[i] + D, after=0.45, hold_until=HOLD, reset=RESET)
        out.append(stage_overlay(x, y, bw, bh, i + 1, GOOD if i == 5 else BLUE, cls))
    for x1, yy1, x2, yy2, d, into in conns:
        cls = a.window(s[into] - 0.35, s[into] + D, after=0.45, hold_until=HOLD, reset=RESET,
                       extra="flow 1s linear infinite")
        out.append(f'<g class="{cls}" opacity="0.45">{connector(x1, yy1, x2, yy2, d, BLUE, dash="6 4")}</g>')
    ot = a.window(s[1] + 0.5, s[1] + D - 0.1, extra="flow 1s linear infinite")
    out.append(f'<g class="{ot}" opacity="0">{connector(ox, y1 + bh, ox, 230, "down", YELLOW, dash="6 4")}'
               f'<rect x="250" y="230" width="460" height="36" rx="18" fill="none" stroke="{YELLOW}" stroke-width="2"/></g>')
    # the four format Docs fan out under the Google Docs step
    chips = [("Blog", 64), ("LinkedIn long", 124), ("LinkedIn short", 130), ("Newsletter", 104)]
    x = 40
    for k, (label, w) in enumerate(chips):
        t = s[5] + 0.3 + k * 0.22
        cls = a.add([(0, "opacity:0;transform:translateY(8px)"), (t, "opacity:0;transform:translateY(8px)"),
                     (t + 0.35, "opacity:1;transform:translateY(0)"), (HOLD, "opacity:1;transform:translateY(0)"),
                     (RESET, "opacity:0;transform:translateY(0)")], ease="cubic-bezier(.2,.7,.2,1)")
        out.append(f'<g class="{cls}"><rect x="{x}" y="430" width="{w}" height="28" rx="8" fill="{BOX}" stroke="{GOOD}"/>'
                   f'<path d="M{x + 12},{437} h8 l4,4 v10 h-12 z" fill="none" stroke="{INK2}" stroke-width="1.4" stroke-linejoin="round"/>'
                   f'<text x="{x + 32}" y="449" font-size="13" fill="{INK}" data-fit="{x},{x + w}">{label}</text></g>')
        x += w + 8
    out.append(caption_bar(40, 474, 880, 50))
    caps = [
        "A person fills in the form: topic, optional link, word limit, format, and whether to use current news.",
        "n8n asks the API whether the DPDP texts cover the topic. If not, the user decides what happens next.",
        "If asked, Claude turns trending news (NewsData, NewsAPI) or the linked article into content ideas.",
        "The user picks the idea to write about. Without news or a link, the topic goes straight to drafting.",
        "The API drafts it once per chosen format, with the same grounding and cite_check as the app.",
        "Each draft becomes a Google Doc in Drive, where a person reviews it before anything is published.",
    ]
    texts = [(s[i], s[i] + D, c) for i, c in enumerate(caps)]
    texts.append((END, RESET - 0.2, "Each Doc shows the machine’s verdict and numbered citations, and still needs a person’s sign-off."))
    out.append(captions(a, texts, 62, 505, "Form → relevance check → ideas → pick → generate → Google Docs", (40, 920)))
    out.append(progress(a, 40, 540, 880, s[0], END, HOLD, RESET))
    out.append("</svg>")
    return "\n".join(out).replace("%%ANIM%%", a.css())


# ================================================================ 5. evaluation chart
def evalchart() -> str:
    W, H, T = 960, 640, 14.0
    a = Anim(T)
    x0, scale, th = 230, 6.0, 18
    retrieval = [("Recall@6", 100.0, 80), ("MRR", 88.0, 70), ("NDCG@6", 88.1, 75)]
    generation = [("Faithfulness", 99.4, 85), ("Correctness", 98.9, 85), ("Relevance", 100.0, 85),
                  ("Coherence", 91.7, 80), ("Conciseness", 85.0, 75)]
    gates = ["Answered", "Citation validity", "Date honesty", "Off-topic refused", "No false assertion",
             "No contradiction"]
    FADE0, FADE1 = 12.6, 13.2
    out = [svg_open(W, H, "Evaluation results",
                    "Animated bar chart of the last full evaluation run, 22 July 2026, 18 questions, scored 0 to "
                    "100 with a pass mark per metric. Retrieval: Recall@6 100 (pass 80), MRR 88.0 (pass 70), "
                    "NDCG@6 88.1 (pass 75). Generation, judged by GPT-4o mini: Faithfulness 99.4 (pass 85), "
                    "Correctness 98.9 (pass 85), Relevance 100 (pass 85), Coherence 91.7 (pass 80), "
                    "Conciseness 85.0 (pass 75). Golden-rule gates, each at 100 percent: answered, citation "
                    "validity, date honesty, off-topic refused, no false assertion, no contradiction.", a,
                    extra_css=f".lab {{ font-size: 15px; fill: {INK2}; }}\n.val {{ font-size: 14px; font-weight: 600; fill: {INK}; }}\n"
                              f".grp {{ font-size: 13.5px; font-weight: 600; fill: {MUTED}; }}\n"
                              f".ax {{ font-size: 12px; fill: {MUTED}; font-variant-numeric: tabular-nums; }}"),
           header("Evaluation results", "Last full run, 22 July 2026: 18 questions with expert answers, scored 0–100.")]
    # key for the pass-mark tick (single series → no legend box; the title names it)
    out.append(f'<line x1="846" y1="34" x2="846" y2="52" stroke="{INK}" stroke-width="2"/>'
               f'<text x="856" y="48" class="ax" font-size="13">pass mark</text>')
    # gridlines + axis
    top, bottom = 136, 432
    for v in (0, 25, 50, 75, 100):
        x = x0 + v * scale
        out.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{bottom}" stroke="{LINE}" stroke-width="1"/>')
        out.append(f'<text x="{x}" y="452" class="ax" text-anchor="middle">{v}</text>')
    data_fade = a.add([(0, "opacity:1"), (FADE0, "opacity:1"), (FADE1, "opacity:0"), (T - 0.15, "opacity:0"), (T, "opacity:1")])
    out.append(f'<g class="{data_fade}">')
    rows = [("Retrieval", 128, retrieval, 156), ("Generation, judged by GPT-4o mini", 262, generation, 290)]
    k = 0
    for gname, gy, items, first in rows:
        out.append(f'<text x="40" y="{gy}" class="grp">{gname}</text>')
        for j, (name, v, p) in enumerate(items):
            cy = first + j * 32
            w = v * scale
            start = 0.5 + k * 0.12
            grow = a.add([(0, "transform:scaleX(0)"), (start, "transform:scaleX(0)"), (start + 1.1, "transform:scaleX(1)"),
                          (FADE1, "transform:scaleX(1)"), (FADE1 + 0.05, "transform:scaleX(0)")], ease="cubic-bezier(.2,.7,.2,1)")
            fadein = a.add([(0, "opacity:0"), (start + 0.9, "opacity:0"), (start + 1.2, "opacity:1")])
            y = cy - th / 2
            # 4px rounded data end, square at the baseline
            out.append(f'<text x="214" y="{cy + 5}" class="lab" text-anchor="end" data-fit="40,222">{name}</text>')
            out.append(f'<path d="M{x0},{y} h{f(w - 4)} a4,4 0 0 1 4,4 v{th - 8} a4,4 0 0 1 -4,4 h-{f(w - 4)} z" '
                       f'fill="{BLUE}" class="tb {grow}" style="transform-origin: 0 50%"/>')
            out.append(f'<line x1="{x0 + p * scale}" y1="{cy - 13}" x2="{x0 + p * scale}" y2="{cy + 13}" stroke="{INK}" stroke-width="2"/>')
            label = "100" if v == 100 else f"{v:.1f}"
            out.append(f'<text x="{f(x0 + w + 10)}" y="{cy + 5}" class="val {fadein}" data-fit="230,950">{label}</text>')
            k += 1
    out.append('</g>')
    # golden-rule gates: identical 100% results read better as checks than as six full bars
    out.append(f'<text x="40" y="494" class="grp">Golden-rule gates: one failure fails the whole run</text>')
    for j, g in enumerate(gates):
        r, c = divmod(j, 3)
        x, y = 40 + c * 298, 508 + r * 44
        t = 2.0 + j * 0.15
        cls = a.add([(0, "opacity:0;transform:translateY(6px)"), (t, "opacity:0;transform:translateY(6px)"),
                     (t + 0.35, "opacity:1;transform:translateY(0)"), (FADE0, "opacity:1;transform:translateY(0)"),
                     (FADE1, "opacity:0;transform:translateY(0)")], ease="cubic-bezier(.2,.7,.2,1)")
        out.append(f'<g class="{cls}"><rect x="{x}" y="{y}" width="284" height="34" rx="10" fill="{BOX}" stroke="{LINE}"/>'
                   f'{check_icon(x + 20, y + 17)}'
                   f'<text x="{x + 38}" y="{y + 22}" font-size="14.5" fill="{INK}" data-fit="{x},{x + 230}">{g}</text>'
                   f'<text x="{x + 270}" y="{y + 22}" font-size="14" font-weight="600" fill="{INK2}" text-anchor="end">100%</text></g>')
    out.append(f'<text x="40" y="618" font-size="13" fill="{MUTED}" data-fit="40,920">Also reported, not graded: '
               f'3 of 18 drafts passed cite_check without needing a person. Every draft gets human review anyway.</text>')
    out.append("</svg>")
    return "\n".join(out).replace("%%ANIM%%", a.css())


if __name__ == "__main__":
    dest = Path(sys.argv[1])
    dest.mkdir(parents=True, exist_ok=True)
    for name, fn in [("hero", hero), ("build", build), ("pipeline", pipeline), ("n8n", n8n), ("eval", evalchart)]:
        svg = re.sub(r'(<text[^>]*?) font-size="([\d.]+)"', r'\1 style="font-size:\2px"', fn())
        assert svg.count("<text") == len(re.findall(r"<text[^>]*>", svg))
        assert not re.search(r'<text[^>]*style="[^"]*"[^>]*style=', svg), "duplicate style attribute"
        (dest / f"{name}.svg").write_text(svg, encoding="utf-8")
        print(f"{name}.svg  {len(svg.encode()) / 1024:.1f} KB")
