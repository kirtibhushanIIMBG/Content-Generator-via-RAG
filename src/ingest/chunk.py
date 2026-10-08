"""Legal-aware chunker for the DPDP Act 2023 and DPDP Rules 2025.

Build-time only (CLAUDE.md §3: nothing at runtime may depend on this).

    python -m src.ingest.chunk            # write data/processed/*_chunks.jsonl
    python -m src.ingest.chunk --inspect  # print headers found, write nothing

WHY TWO PDF LIBRARIES (this is not accidental — do not "simplify" it):

* Body text -> pdfminer.six. The Act is a two-column Gazette whose section titles
  live in a MARGIN column ("Short title and commencement."), set in 8pt while the
  body is 10pt. Flat text extraction interleaves those margin words into the middle
  of legal sentences ("...only in accordance PROCESSING with the provisions..."),
  which corrupts the text. pdfminer gives per-line (x0, size), so the margin is
  removed geometrically. It also merges the small-caps chapter titles correctly.

* Schedules -> pypdf extraction_mode="layout". Every Schedule is a TABLE. pypdf's
  default mode emits the Act's penalty table in column order (all 7 breaches, then
  all 7 Sl. Nos, then all 7 penalties), dissociating each breach from its penalty --
  i.e. it will happily attach "250 crore" to the wrong row. Layout mode preserves
  the row alignment verbatim. pdfminer is NOT used here because reading its lines in
  y-order interleaves the columns the same way.

Both claims are reproducible with --inspect. See docs/source-verification.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTChar, LTContainer, LTTextLine
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

ACT_PDF = RAW / "DPDP_Act_2023.pdf"
RULES_PDF = RAW / "DPDP_Rules_2025.pdf"

ACT_DOC = "DPDP Act 2023"
RULES_DOC = "DPDP Rules 2025"

N_SECTIONS = 44  # CLAUDE.md §6
N_RULES = 23
ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh"]

MAX_TOKENS = 1200  # CLAUDE.md §6
OVERLAP_TOKENS = 80

# --- Rules commencement. Derived from Rule 1(2)-(4) IN THE PDF, not from memory.
# Gazette published 13 Nov 2025 -> +1yr = 2026-11-13, +18mo = 2027-05-13.
# Verified by test_chunks.py against the extracted text of Rule 1.
RULE_STATUS: dict[int, str] = {}
for _n in [1, 2, 17, 18, 19, 20, 21]:  # r.1(2) "on the date of their publication"
    RULE_STATUS[_n] = "in force"
RULE_STATUS[4] = "effective 2026-11-13"  # r.1(3) "one year after"
for _n in [3, *range(5, 17), 22, 23]:  # r.1(4) "eighteen months after"
    RULE_STATUS[_n] = "effective 2027-05-13"

# --- Act commencement. The Act's own text fixes NO date (s.1(2): "such date as the
# Central Government may ... appoint"), so its authority_status cannot come from the Act.
# It comes from G.S.R. 843(E) (MeitY, 13 Nov 2025), the commencement notification issued
# under s.1(2). That PDF is a build-time METADATA source only -- it is never chunked, and
# the knowledge base still contains nothing but the two source texts (CLAUDE.md §3).
#
# The gazette publishes on 13 Nov 2025, so its three clauses map to:
#   (a) "date of publication"  -> in force
#   (b) "one year"             -> effective 2026-11-13
#   (c) "eighteen months"      -> effective 2027-05-13
# ...which is exactly the three-bucket scheme in CLAUDE.md §3.
ACT_COMMENCEMENT_SO = RAW / "DPDP_Act_Commencement_SO.pdf"

# The operative clauses, verbatim. commencement_evidence() asserts each one is actually
# present in the PDF (whitespace-insensitively -- the gazette extracts with stray spaces
# inside words, e.g. "sub -section", "sectio n 1"). If the notification is ever amended,
# or the wrong PDF is dropped in, the build STOPS rather than quietly re-dating the law.
SO_CLAUSES = {
    "in force": (
        "sub-section (2) of section 1, section 2, sections 18 to 26 sections 35, 38, 39, "
        "40, 41, 42, 43, and sub-sections (1) and (3) of section 44 of the said Act shall "
        "come into force"
    ),
    "effective 2026-11-13": (
        "sub-section (9) of section 6 and clause (d) of sub-section (1) of section 27 of "
        "the said Act shall come into force"
    ),
    "effective 2027-05-13": (
        "sections 3 to 5, sub-sections (1) to (8) and (10) of section 6,sections 7 to 10, "
        "sections 11 to 17, section 27 except clause (d) of sub-section (1) of the said "
        "section, sections 28 to 34, 36, 37 and sub-section (2) of section 44 of the said "
        "Act shall come into force"
    ),
}

# Sections wholly in force on 13 Nov 2025, per clause (a). s.44 is NOT here: it straddles
# two dates and is handled per sub-section in act_status().
ACT_IN_FORCE = {1, 2, *range(18, 27), 35, *range(38, 44)}


def act_status(number: int, sub: str | None) -> str:
    """authority_status for one Act provision, straight off G.S.R. 843(E).

    Everything not named in clause (a) or (b) falls in clause (c) -- which is the whole of
    the substantive compliance regime (notice, consent, security, children, SDF, penalties).
    None of it is live until 2027-05-13, so content must never present it as a duty today.
    """
    if number == 6:
        # clause (b): only sub-section (9) -- the Consent Manager route -- moves early
        return "effective 2026-11-13" if sub == "9" else "effective 2027-05-13"
    if number == 44:
        # clause (a) takes sub-sections (1) and (3); clause (c) takes (2)
        return "in force" if sub in ("1", "3") else "effective 2027-05-13"
    if number in ACT_IN_FORCE:
        return "in force"
    # s.27 lands here. Strictly, clause (b) moves s.27(1)(d) to 2026-11-13 -- but that is a
    # CLAUSE inside s.27(1), sharing its chapeau with (a)-(c) which are 2027. A chunk carries
    # one status, and severing (d) from its chapeau would leave a fragment that is easy to
    # mis-cite. So s.27 takes the LATER date: it understates clause (d) by six months, and
    # understating is the safe error -- the golden rule forbids implying a duty is live
    # EARLY, not late. s.27 is a Board power, not a Data Fiduciary obligation. (Human
    # decision, 2026-07-13.)
    return "effective 2027-05-13"


def commencement_evidence() -> None:
    """Prove the notification says what act_status() claims. Refuse to build otherwise."""
    if not ACT_COMMENCEMENT_SO.is_file():
        raise SystemExit(
            f"FATAL: missing {ACT_COMMENCEMENT_SO.relative_to(ROOT)}\n"
            "  The Act fixes no commencement date in its own text, so without the gazette\n"
            "  notification every Act chunk's authority_status is unknowable and NOTHING\n"
            "  may be indexed. Supply G.S.R. 843(E) (MeitY, 13 November 2025)."
        )
    pages = PdfReader(str(ACT_COMMENCEMENT_SO)).pages
    packed = re.sub(r"\s+", "", "\n".join(p.extract_text() or "" for p in pages))
    if "G.S.R.843(E)" not in packed:
        raise SystemExit(f"FATAL: {ACT_COMMENCEMENT_SO.name} is not G.S.R. 843(E).")
    for status, clause in SO_CLAUSES.items():
        if re.sub(r"\s+", "", clause) not in packed:
            raise SystemExit(
                f"FATAL: {ACT_COMMENCEMENT_SO.name} does not contain the clause this build\n"
                f"  relies on for authority_status {status!r}:\n    {clause}\n"
                "  Either this is the wrong PDF, or the notification has been amended.\n"
                "  Do NOT edit the table to match -- check the gazette first."
            )

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
BARE_NUMBER = re.compile(r"^\d{1,3}$")

# Running headers, printer colophons, signature block. Matched on squeezed lines.
NOISE = re.compile(
    r"THE\s+GAZETTE\s+OF\s+INDIA"
    r"|^\[?\s*P\s*ART\s+II\b"
    r"|^SEC\.\s*\d+\]"
    r"|^UPLOADED BY THE MANAGER"
    r"|^AND PUBLISHED BY THE CONTROLLER"
    r"|^Uploaded by Dte"
    r"|^and Published by the Controller"
    r"|^MGIPMRND"
    r"|^DR\.\s*REETA"
    r"|^Secretary to the Govt"
    # The RULES gazette's signature block. Everything above is the ACT's colophon; the Rules
    # PDF signs off differently and nothing matched it. Its two lines sit at the bottom of the
    # last page — INSIDE the horizontal span of the Seventh Schedule's third column — so
    # looks_tabular() still held, table_span() ran the table over them, and build_rows() folded
    # them into row 3 as continuation text. The shipped chunk ended:
    #   "...as the Secretary in charge of the said Ministry may designate in this behalf.
    #    [F. No. AA-11038/1/2025-CLandES] AJIT KUMAR, Jt. Secy. |"
    # i.e. a gazette file number and a civil servant's name welded into the "Authorised person"
    # cell of a legal table — quotable, and citable as `DPDP Rules 2025, Seventh Schedule`,
    # which cite_check would pass because the CITATION is real. Same class as the Act colophon,
    # just at the tail instead of the head.
    r"|^\[?\s*F\.\s*No\."
    r"|Jt\.\s*Secy"
    r"|^[-—–_\s]+$",  # rule-off separators e.g. "————"
    re.I,
)

# A section/rule header: number, period, then the body or title. Rule 17 in the Rules
# PDF is literally "17.Appointment of..." with NO space after the dot, so \s* not \s+
# (docs/source-verification.md, constraint 1).
HEADER = re.compile(r"^(\d{1,2})\.\s*(?=\(1\)|[A-Z])")
CHAPTER = re.compile(r"^CHAPTER\s+([IVXL]+)$")
ACT_SCHEDULE = re.compile(r"^THE\s+SCHEDULE$")
RULES_SCHEDULE = re.compile(r"^(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH)\s+SCHEDULE$")
PART = re.compile(r"^PART\s+([AB])$")
# A Note scoped to the WHOLE schedule ("Note: In this Schedule, —"), which therefore belongs to
# every Part of it, not just the last one it happens to be printed under. Deliberately narrow:
# a note scoped to a single Part must NOT be copied onto its siblings, so the "In this Schedule"
# wording is required, not merely a leading "Note:".
SCHEDULE_NOTE = re.compile(r"^Note\s*:\s*In this Schedule", re.I)
SEE_RULE = re.compile(r"\[See rules?\s+(.+?)\]")
SUBSECTION = re.compile(r"^\((\d{1,2})\)\s")
# "6. (1) The consent given by ..." -- sub-section (1) rides on the section header line
HEADER_SUB = re.compile(r"^\d{1,2}\.\s*\((\d{1,2})\)\s")

CHARS_PER_TOKEN = 4  # English prose, GPT-family tokenizers


def ntokens(text: str) -> int:
    """Approximate. Deliberately NOT tiktoken: an exact count would add a build-time
    network fetch of the BPE file, and the 1200-token target is a chunking heuristic,
    not a hard limit -- text-embedding-3-large accepts 8191, so we are 6x clear even
    if this estimate is off by 2x. test_chunks.py asserts the real ceiling in chars."""
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def tail(text: str, tokens: int) -> str:
    """Last ~`tokens` worth of text, snapped forward to a word boundary."""
    chars = tokens * CHARS_PER_TOKEN
    if len(text) <= chars:
        return text
    cut = text[-chars:]
    space = cut.find(" ")
    return cut[space + 1 :] if space != -1 else cut


@dataclass
class Line:
    page: int
    y: float
    x0: float
    size: float
    text: str


@dataclass
class Chunk:
    doc: str
    type: str  # "section" | "rule" | "schedule"
    number: str | None
    sub: str | None
    chapter: str | None
    chapter_title: str | None
    schedule: str | None
    part: str | None
    citation: str
    authority_status: str | None
    source_ref: str
    page: int
    text: str
    # The provision's own heading. For the Act this is the margin side-note, which is NOT in
    # `text` (see act_titles) — without it no Act section states its subject. Rules and
    # Schedules carry their heading inline in `text` already, so this stays None for them and
    # nothing downstream may assume it is populated. Embedding-only: see hybrid.index_text.
    title: str | None = None
    # Not in CLAUDE.md §7's schema, but cheap and it makes retrieval debuggable.
    tokens: int = field(default=0)


def squeeze(s: str) -> str:
    return " ".join(s.split())


def nospace(s: str) -> str:
    """The ONLY correct key for comparing chunk text against PDF page text.

    Whitespace must be REMOVED, not collapsed. The two PDF libraries disagree about spaces:
    for r.7's heading, pypdf extracts "...personal data breach . — (1)" (a stray space before
    the full stop, from glyph spacing in the Gazette's bold heading) where pdfminer — and so
    the chunk — has "...personal data breach. — (1)". Collapsing runs of whitespace PRESERVES
    that stray space and the comparison fails on a chunk that is perfectly correct; removing
    whitespace absorbs it.

    This is not hypothetical: a hand-rolled collapse-based probe reported the r.7 chunk as
    landing on the wrong PDF page during the 2026-07-14 citation spot-check. It was wrong, and
    a verification tool that cries wolf teaches its reader to ignore real flags. Every
    chunk-vs-PDF comparison in this repo imports THIS function — do not re-roll it.
    """
    return re.sub(r"\s+", "", s)


# Chapter headings are typeset in small-caps, so they extract as ALL CAPS. str.title()
# would give "Obligations Of Data Fiduciary"; CLAUDE.md §7 wants "...of...".
MINOR = {"of", "and", "to", "be", "by", "for", "the", "in", "on", "with", "as", "a", "an"}


def titlecase(s: str) -> str:
    words = squeeze(s).lower().split()
    return " ".join(
        w.capitalize() if i == 0 or w not in MINOR else w for i, w in enumerate(words)
    )


# ---------------------------------------------------------------- extraction


def walk(obj) -> "list[LTTextLine]":
    """Depth-first text lines. MUST recurse: page 1 of the Act draws its whole body
    (masthead, long title, CHAPTER I, s.1) inside a Form XObject, which pdfminer
    surfaces as a nested LTFigure. A top-level-only loop silently returns 2 lines for
    that page and loses section 1 -- and one lost section cascades through the
    sequence check into "no sections found at all"."""
    if isinstance(obj, LTTextLine):
        return [obj]
    if isinstance(obj, LTContainer):
        return [ln for child in obj for ln in walk(child)]
    return []


def read_lines(pdf: Path) -> list[Line]:
    """Body lines in reading order, via pdfminer. Noise and margin notes NOT yet removed."""
    lines: list[Line] = []
    # all_texts=True runs layout analysis INSIDE figures too; without it the LTFigure
    # on page 1 yields raw glyphs that never get grouped into lines.
    laparams = LAParams(all_texts=True)
    for page_no, page in enumerate(extract_pages(str(pdf), laparams=laparams), start=1):
        for ln in walk(page):
            text = squeeze(ln.get_text())
            if not text:
                continue
            sizes = [round(c.size, 1) for c in ln if isinstance(c, LTChar)]
            if not sizes:
                continue
            lines.append(
                Line(
                    page=page_no,
                    y=ln.y0,
                    x0=ln.x0,
                    size=max(set(sizes), key=sizes.count),
                    text=text,
                )
            )
    # reading order: page, then top-to-bottom, then left-to-right
    lines.sort(key=lambda ln: (ln.page, -ln.y, ln.x0))
    return lines


def is_act_margin(ln: Line) -> bool:
    """Act side-notes: 8pt, in the margin column. Body is 10pt spanning x0 117.5-477.6.

    Margin sits at x0~57 on even pages and x0~486 on odd (the Gazette alternates the
    side). The chapter titles are ALSO small (7-8pt small-caps) but are centred
    (x0~235), so the x0 test is what keeps them -- do not drop on size alone.
    """
    return ln.size < 9.5 and (ln.x0 < 110 or ln.x0 > 480)


# --- Act section titles ------------------------------------------------------------
# The Act's section titles ("Notice.", "Exemptions.") are printed as 8pt SIDE-NOTES in the
# margin column, and clean() drops that column on purpose — read inline they inject
# themselves into the middle of legal sentences. The cost of dropping them was invisible
# until the RAG eval: the Act's body text contains the word "Notice" ZERO times, "Exemption"
# ZERO times, "Security safeguard" ZERO times. Every one of the 44 sections was indexed with
# no statement of its own subject, while every Rule carries its heading inline — so the Act
# lost topical queries to the Rules (s.17, THE exemptions section, fell out of the top-6 for
# "which processing is exempt", behind r.12/r.16/Fourth Schedule which all say "exemption").
#
# So: capture the side-note, keep it OUT of `text` (which stays pristine statute), and let
# hybrid.index_text() feed it to the embedding only.
#
# A side-note is the run of margin lines that STARTS on the section header's own line and
# continues down at single-line spacing. Anchoring on the header is what separates the title
# from the other thing that lives in this column — statute cross-references ("45 of 1860.",
# "24 of 1997.") — which sit further down. Those also land INSIDE a long title's run
# (s.25 came out "Members and officers to be public 45 of 1860. servants"), so they are
# dropped by shape as well as by position.
XREF_NOTE = re.compile(r"^\d{1,3}\s+of\s+\d{4}\.?$")
TITLE_GAP = 14.0  # pt: consecutive lines of one side-note are ~9-10pt apart
TITLE_ANCHOR = 12.0  # pt: the note's first line sits on the header's own line


def act_titles(lines: list[Line]) -> dict[int, str]:
    """{section number: side-note title}. `lines` must still CONTAIN the margin column."""
    margins = [ln for ln in lines if is_act_margin(ln)]
    titles: dict[int, str] = {}
    expect = 1
    for ln in lines:
        if is_act_margin(ln):
            continue
        m = HEADER.match(ln.text)
        if not (m and int(m.group(1)) == expect):
            continue
        run: list[Line] = []
        for c in sorted(
            (x for x in margins if x.page == ln.page and x.y <= ln.y + TITLE_ANCHOR),
            key=lambda x: -x.y,
        ):
            if not run:
                if c.y < ln.y - TITLE_ANCHOR:
                    break  # nothing on the header's line — this section has no side-note
                run.append(c)
            elif run[-1].y - c.y <= TITLE_GAP:
                run.append(c)
            else:
                break  # gap too big: a separate marginal note, not part of this title
        title = squeeze(" ".join(x.text for x in run if not XREF_NOTE.match(x.text)))
        if title:
            titles[expect] = title.rstrip(".")
        expect += 1
    return titles


def clean(lines: list[Line], drop_margin: bool) -> list[Line]:
    """Strip Gazette furniture, leaving only the law."""
    # The running header is one physical line -- "SEC. 1]  THE GAZETTE OF INDIA
    # EXTRAORDINARY  21" -- but pdfminer emits the page number as its OWN text line
    # (x0~522), so it matches none of the NOISE patterns. Left alone it survives cleaning
    # and gets appended to whichever section happens to straddle the page break, dropping a
    # bare "8" into the middle of s.8. Find the header's y per page and drop bare numbers
    # sitting on that same line.
    header_y: dict[int, float] = {}
    for ln in lines:
        if NOISE.search(ln.text) or DEVANAGARI.search(ln.text):
            header_y[ln.page] = max(header_y.get(ln.page, ln.y), ln.y)  # topmost = header

    out = []
    for ln in lines:
        if NOISE.search(ln.text):
            continue
        if DEVANAGARI.search(ln.text):
            continue  # Gazette running header only; there is no Hindi body text
        if drop_margin and is_act_margin(ln):
            continue
        y = header_y.get(ln.page)
        if BARE_NUMBER.match(ln.text) and y is not None and abs(ln.y - y) < 3:
            continue  # the page number, riding on the running-header line
        out.append(ln)
    return out


def layout_pages(pdf: Path) -> dict[int, list[str]]:
    """Per-page lines in pypdf layout mode -- preserves table row alignment."""
    reader = PdfReader(str(pdf))
    pages: dict[int, list[str]] = {}
    for i, page in enumerate(reader.pages, start=1):
        kept = []
        for raw in page.extract_text(extraction_mode="layout").splitlines():
            if not raw.strip():
                continue
            if NOISE.search(squeeze(raw)) or DEVANAGARI.search(raw):
                continue
            kept.append(raw.rstrip())
        pages[i] = kept
    return pages


# ---------------------------------------------------------------- tables
#
# Every Schedule is a table. Layout mode keeps the rows aligned, but the chunk text is
# what gets EMBEDDED and what goes into the generation prompt -- and read as flat text,
# an aligned table interleaves its columns:
#
#   "1. Breach in observing the obligation of Data Fiduciary to May extend to two
#    take reasonable security safeguards to prevent personal hundred and fifty ..."
#
# ...which silently welds "two hundred and fifty crore" onto the wrong breach. It reads
# plausibly, which is what makes it dangerous. So we rebuild real rows and emit markdown,
# where the cell boundaries survive any downstream whitespace handling.

ROW_MARKER = re.compile(r"^\d{1,2}\.$")
HEADER_SEARCH_LINES = 6  # a schedule's table header sits within a few lines of its caption


def gutters(lines: list[str]) -> list[tuple[int, int]]:
    """Column spans, found from character columns that are blank in EVERY line.

    Splitting on runs of 2+ spaces does NOT work: layout mode justifies cell text
    ("Three  years  from  the  date") and the Act's own header has "of  this Act", so
    intra-cell double spaces are everywhere. A gutter has to be blank down the whole
    table, which is exactly what distinguishes it from a word gap.
    """
    if not lines:
        return []
    width = max(len(ln) for ln in lines)
    padded = [ln.ljust(width) for ln in lines]
    blank = [all(p[i] == " " for p in padded) for i in range(width)]

    spans: list[tuple[int, int]] = []
    start = None
    for i in range(width):
        if not blank[i] and start is None:
            start = i
        elif blank[i] and start is not None:
            # a single blank column is a word gap, not a gutter; require 2+
            run = 0
            while i + run < width and blank[i + run]:
                run += 1
            if run >= 2:
                spans.append((start, i))
                start = None
    if start is not None:
        spans.append((start, width))
    return spans


def build_rows(lines: list[str], spans: list[tuple[int, int]]) -> list[list[str]]:
    """Slice lines into cells, folding each continuation line into the record above it."""
    rows: list[list[str]] = []
    for line in lines:
        cells = [line[a:b].strip() for a, b in spans]
        if not any(cells):
            continue
        # a new record begins at a bare "1." / "2." in the first column; anything else
        # is a continuation of the record above, cell by cell
        if rows and not ROW_MARKER.match(cells[0]):
            for i, part in enumerate(cells):
                if part:
                    rows[-1][i] = (rows[-1][i] + " " + part).strip()
        else:
            rows.append(cells)
    return rows


def as_markdown(lines: list[str]) -> str | None:
    """Render an aligned table as markdown. None if these lines aren't a table."""
    spans = gutters(lines)
    if len(spans) < 2:
        return None
    rows = build_rows(lines, spans)
    if len(rows) < 2:
        return None

    # A real column always has a heading. A span with an EMPTY heading is a false gutter:
    # cell text is justified, and where several rows carry the same wording their word
    # gaps line up into a column that is blank all the way down. The Third Schedule's
    # "Time period" cells are identical across rows and split exactly this way.
    # Merge such a span back into the column on its left -- at SPAN level, not by
    # concatenating the extracted cells, or the stolen words reattach out of order.
    merged: list[tuple[int, int]] = []
    for i, span in enumerate(spans):
        if i and not rows[0][i].strip():
            merged[-1] = (merged[-1][0], span[1])
        else:
            merged.append(span)
    if merged != spans:
        spans = merged
        rows = build_rows(lines, spans)
        if len(rows) < 2 or len(spans) < 2:
            return None

    keep = [i for i in range(len(spans)) if any(r[i].strip() for r in rows)]
    if len(keep) < 2:
        return None
    rows = [[squeeze(r[i]) for i in keep] for r in rows]

    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(keep)]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def looks_tabular(lines: list[str], spans: list[tuple[int, int]]) -> bool:
    """Two or more columns, and a first column that actually holds row numbers.

    The column count alone is not enough: once a prose line runs the full width it
    merges the real columns into one fat span plus a stray, which still counts as
    "2 columns" while being nothing of the kind. Bare "1." / "2." markers in column one
    are what make it a table.
    """
    if len(spans) < 2:
        return False
    a, b = spans[0]
    markers = sum(1 for ln in lines if ROW_MARKER.match(ln[a:b].strip()))
    return markers >= 2


def table_span(body: list[str]) -> tuple[int, int]:
    """The [start, end) lines of `body` that form the table. (0, 0) if there is none.

    Prose lines span the full width, so they put text in every gutter and collapse the
    column structure of any region they sit in. That cuts BOTH ways:

    * Trailing prose ("Note: In this Schedule, —" and definitions) ends the table, so grow
      the table while it still parses AS a table.
    * LEADING prose ends it too, and this is subtler: the Fourth Schedule's Part A carries a
      full-width caption ("Classes of Data Fiduciaries in respect of whom ... shall not
      apply") ABOVE its table. Growing only from body[0] meant every prefix contained that
      caption, no prefix ever parsed as a table, and the whole Schedule fell back to raw
      layout text -- silently, because the fallback is legal-looking prose. Read line by
      line, that text welds each row's two cells together ("A Data Fiduciary who is an
      individual in | Processing is restricted to tracking..."), which is exactly the
      column interleaving this module exists to prevent.

    So find where the table STARTS as well as where it ends.

    The start must be the HEADER row, not merely the first line where the gutters happen to
    resolve. Captions are CENTRED or indented, so they leave the row-number column blank,
    while every DPDP schedule header opens with it ("S.", "S. no.", "Sl. No.") -- the same
    column `looks_tabular` keys on. Take the first column being filled, by something that is
    not itself a row marker, as the definition of the header. Without it, Part B of the
    Fourth Schedule swallowed its caption into the heading and emitted a TWO-column table,
    fusing every row's Purposes cell onto its Conditions cell.
    """
    # A schedule's table, if it has one, opens right below the caption. Bounding the scan
    # keeps numbered PROSE (First/Second/Fifth/Sixth are "1., 2., 3." lists) from having a
    # spurious table found deep inside it.
    for start in range(min(HEADER_SEARCH_LINES, len(body))):
        n = 0
        for i in range(start + 2, len(body) + 1):
            if looks_tabular(body[start:i], gutters(body[start:i])):
                n = i
            elif n:
                break  # the table ended; the rest is prose
        if not n:
            continue

        # Judge the header against the gutters of the WHOLE table region. A two-line peephole
        # merges every column into one span, under which a centred caption looks like a filled
        # first cell -- which is how "PART B" got taken for a heading.
        spans = gutters(body[start:n])
        if len(spans) < 2:
            continue
        first = body[start][spans[0][0] : spans[0][1]].strip()
        if not first or ROW_MARKER.match(first):
            continue  # caption (row-number column blank) or a data row — not the header
        return start, n
    return 0, 0


COLON_FUSE = re.compile(r":(?=[A-Z][a-z])")


def unfuse(s: str) -> str:
    """pypdf's layout mode occasionally eats the space after a colon ("Note:In this
    Schedule"). Only ever INSERTS a space -- never alters or drops a character -- and only
    where a colon is immediately followed by a capitalised word. One occurrence corpus-wide
    (the Third Schedule's Note); the test keeps it at zero."""
    return COLON_FUSE.sub(": ", s)


def render_schedule(lines: list[str]) -> str:
    """Heading verbatim, the tabular part as markdown, any trailing prose as prose.

    Several Schedules (First, Second, Fifth, Sixth) are numbered prose with no table at
    all -- table_span returns an empty span for those and they pass through untouched.
    """
    head_end = 0
    for i, raw in enumerate(lines[:6]):
        if re.search(r"\[See (rule|section)", squeeze(raw)):
            head_end = i + 1
            break
    head = [squeeze(x) for x in lines[:head_end] if x.strip()]
    body = [x for x in lines[head_end:] if x.strip()]

    start, n = table_span(body)
    table = as_markdown(body[start:n]) if n - start >= 3 else None  # header + at least 2 rows
    if table is None:
        return unfuse("\n".join(head + [squeeze(x) for x in body]).strip())
    before = [squeeze(x) for x in body[:start]]  # the caption above the table is legal text
    after = [squeeze(x) for x in body[n:]]
    return unfuse("\n".join(head + before + [table] + after).strip())


# ---------------------------------------------------------------- splitting


def split_at_subsections(text: str) -> list[tuple[str | None, str]]:
    """Break a section body into (sub_number, text) at '(1)', '(2)', ... line starts.

    Illustrations and clauses (a)/(b) sit *inside* a sub-section block and so stay
    attached to their parent -- which is exactly what CLAUDE.md §6 requires.
    """
    blocks: list[tuple[str | None, list[str]]] = []
    current: tuple[str | None, list[str]] = (None, [])
    for i, line in enumerate(text.splitlines()):
        # An Act section opens "6. (1) The consent given by ...": sub-section (1) shares
        # the header line, so without this it would be filed as an unlabelled preamble and
        # s.6(1) could never be told apart from s.6(9).
        m = HEADER_SUB.match(line) if i == 0 else None
        if not m:
            m = SUBSECTION.match(line)
        if m:
            if current[1]:
                blocks.append(current)
            current = (m.group(1), [line])
        else:
            current[1].append(line)
    if current[1]:
        blocks.append(current)
    return [(sub, "\n".join(body).strip()) for sub, body in blocks if "\n".join(body).strip()]


def label(subs: list[str | None]) -> str | None:
    known = [s for s in subs if s]
    if not known:
        return None
    return known[0] if len(known) == 1 else f"{known[0]}-{known[-1]}"


def locate_page(chunk_text: str, lines: list[tuple[int, str]], start: int, fallback: int) -> tuple[int, int]:
    """Page where this chunk's text actually begins.

    A split chunk (s.6(9), s.44(2)...) can start pages after its section header, and its
    `page` field must point a human at THAT page, not the section's first. The chunk's
    first line is an exact source line, so find it in the section's (page, text) lines,
    scanning forward from the previous chunk's position so repeated lines cannot rebind
    backwards. Falls back to the section's first page only for a chunk whose first line
    is synthetic (an 80-token overlap tail -- none exist in the current corpus).
    """
    first = chunk_text.split("\n", 1)[0]
    for i in range(start, len(lines)):
        if lines[i][1] == first:
            return lines[i][0], i + 1
    return fallback, start


def pack_act(number: int, text: str) -> list[tuple[str | None, str, str]]:
    """-> [(sub_label, text, authority_status)] for one Act section.

    A chunk carries exactly ONE authority_status, so a section whose sub-sections
    commence on different dates MUST be split along those dates however short it is.
    G.S.R. 843(E) does that to two sections:
        s.6  -- (9) is 2026-11-13, the rest 2027-05-13   -> 3 chunks
        s.44 -- (1) and (3) in force, (2) 2027-05-13     -> 3 chunks
    Every other section has a single status and stays whole (subject to MAX_TOKENS).
    """
    blocks = split_at_subsections(text)
    statuses = {act_status(number, sub) for sub, _ in blocks}

    if len(statuses) == 1:
        status = statuses.pop()
        return [(sub, body, status) for sub, body in pack(text)]

    # group CONSECUTIVE sub-sections that share a status; each group becomes a chunk
    groups: list[tuple[str, list[tuple[str | None, str]]]] = []
    for sub, body in blocks:
        status = act_status(number, sub)
        if groups and groups[-1][0] == status:
            groups[-1][1].append((sub, body))
        else:
            groups.append((status, [(sub, body)]))

    out: list[tuple[str | None, str, str]] = []
    for status, members in groups:
        body = "\n".join(b for _, b in members)
        for sub, part in pack(body):  # honour MAX_TOKENS within the group
            out.append((sub or label([s for s, _ in members]), part, status))
    return out


def pack(text: str) -> list[tuple[str | None, str]]:
    """Return [(sub_label, text)] honouring MAX_TOKENS.

    Under the limit -> one chunk, sub=None. Over -> greedily group consecutive
    sub-sections, carrying OVERLAP_TOKENS of the previous block for continuity.
    """
    if ntokens(text) <= MAX_TOKENS:
        return [(None, text)]

    blocks = split_at_subsections(text)
    if len(blocks) <= 1:
        return [(None, text)]  # nothing to split on; leave whole rather than cut mid-clause

    out: list[tuple[str | None, str]] = []
    buf: list[tuple[str | None, str]] = []

    def flush() -> None:
        if not buf:
            return
        subs = [s for s, _ in buf if s]
        label = subs[0] if len(subs) == 1 else (f"{subs[0]}-{subs[-1]}" if subs else None)
        body = "\n".join(t for _, t in buf)
        if out:  # 80-token overlap tail of the previous chunk
            body = tail(out[-1][1], OVERLAP_TOKENS) + "\n" + body
        out.append((label, body))
        buf.clear()

    for sub, body in blocks:
        if buf and ntokens("\n".join(t for _, t in buf) + body) > MAX_TOKENS:
            flush()
        buf.append((sub, body))
    flush()
    return out


# ---------------------------------------------------------------- the Act


def parse_act(inspect: bool = False) -> list[Chunk]:
    commencement_evidence()  # no gazette, no statuses, no build
    raw = read_lines(ACT_PDF)
    titles = act_titles(raw)  # BEFORE clean() — it is clean() that discards the margin
    lines = clean(raw, drop_margin=True)
    layout = layout_pages(ACT_PDF)

    missing_titles = sorted(set(range(1, N_SECTIONS + 1)) - set(titles))
    if missing_titles:
        raise SystemExit(
            f"FATAL: no side-note title found for Act sections {missing_titles}.\n"
            "  Every section has one in the Gazette. A missing title means the margin geometry\n"
            "  changed (is_act_margin / TITLE_GAP) — re-check with --inspect before indexing:\n"
            "  an untitled section states its subject nowhere and retrieves badly."
        )
    if inspect:
        print("  section titles (side-notes; embedded, never in the chunk text):")
        for n, t in sorted(titles.items()):
            print(f"    s.{n:<2d} {t}")

    chapter = chapter_title = None
    chapters: dict[str, str] = {}
    sections: dict[int, dict] = {}
    current: int | None = None
    expect = 1

    i = 0
    while i < len(lines):
        ln = lines[i]

        if ACT_SCHEDULE.match(ln.text):
            break  # Schedule is a table; handled from the layout text below

        m = CHAPTER.match(ln.text)
        if m:
            chapter = m.group(1)
            chapter_title = titlecase(lines[i + 1].text) if i + 1 < len(lines) else None
            chapters[chapter] = chapter_title or ""
            i += 2
            continue

        m = HEADER.match(ln.text)
        # Accept a header ONLY if it is the number we are expecting. A bare "17." can
        # also appear inside a cross-reference or a pay-matrix level, and substring
        # matching a number is how you silently lose a section
        # (docs/source-verification.md, constraint 5).
        if m and int(m.group(1)) == expect:
            current = expect
            sections[current] = {
                "page": ln.page,
                "chapter": chapter,
                "chapter_title": chapter_title,
                "lines": [(ln.page, ln.text)],  # keep the page per line: split chunks
                # (s.6(9), s.44(2)...) need THEIR page, not the section's first page
            }
            expect += 1
            i += 1
            continue

        if current is not None:
            sections[current]["lines"].append((ln.page, ln.text))
        i += 1

    if inspect:
        print(f"  chapters found: {len(chapters)} -> {chapters}")
        print(f"  sections found: {len(sections)}")

    missing = sorted(set(range(1, N_SECTIONS + 1)) - set(sections))
    if missing:
        raise SystemExit(f"FATAL: Act sections not found: {missing}")

    chunks: list[Chunk] = []
    for n, sec in sorted(sections.items()):
        body = "\n".join(t for _, t in sec["lines"])
        cursor = 0
        for sub, text, status in pack_act(n, body):
            page, cursor = locate_page(text, sec["lines"], cursor, sec["page"])
            cite = f"{ACT_DOC}, s.{n}" + (f"({sub})" if sub else "")
            chunks.append(
                Chunk(
                    doc=ACT_DOC,
                    type="section",
                    number=str(n),
                    sub=sub,
                    chapter=sec["chapter"],
                    chapter_title=sec["chapter_title"],
                    schedule=None,
                    part=None,
                    citation=cite,
                    authority_status=status,
                    source_ref=ACT_PDF.name,
                    page=page,
                    text=text,
                    title=titles[n],
                    tokens=ntokens(text),
                )
            )

    chunks.append(act_schedule(layout))
    return chunks


def act_schedule(layout: dict[int, list[str]]) -> Chunk:
    """The Schedule of penalties (under s.33). A 3-column table -- keep it aligned."""
    for page_no, page_lines in layout.items():
        for idx, raw in enumerate(page_lines):
            if ACT_SCHEDULE.match(squeeze(raw)):
                text = render_schedule(page_lines[idx:])
                return Chunk(
                    doc=ACT_DOC,
                    type="schedule",
                    number=None,
                    sub=None,
                    chapter=None,
                    chapter_title=None,
                    schedule="The Schedule",
                    part=None,
                    citation=f"{ACT_DOC}, Schedule",
                    # The Schedule is made under s.33 ("[See section 33 (1)]"), so it bites
                    # when s.33 does -- G.S.R. 843(E) clause (c), 2027-05-13. The penalties
                    # are therefore NOT yet enforceable, and content quoting the 250-crore
                    # cap must say so.
                    authority_status=act_status(33, None),
                    source_ref=ACT_PDF.name,
                    page=page_no,
                    text=text,
                    tokens=ntokens(text),
                )
    raise SystemExit("FATAL: 'THE SCHEDULE' heading not found in the Act")


# ---------------------------------------------------------------- the Rules


def schedule_status(see_rule: str) -> str:
    """A Schedule bites when its parent rule does. If parents disagree, take the LATEST
    date -- never let a chunk imply an obligation is live earlier than it is."""
    refs = [int(n) for n in re.findall(r"\b(\d{1,2})\b(?!\))", see_rule)]
    refs = [n for n in refs if n in RULE_STATUS]
    if not refs:
        raise SystemExit(f"FATAL: no parent rule parsed from '[See rule {see_rule}]'")
    order = {"in force": 0, "effective 2026-11-13": 1, "effective 2027-05-13": 2}
    return max((RULE_STATUS[n] for n in refs), key=lambda s: order[s])


def parse_rules(inspect: bool = False) -> list[Chunk]:
    lines = clean(read_lines(RULES_PDF), drop_margin=False)  # Rules have no side-notes
    layout = layout_pages(RULES_PDF)

    rules: dict[int, dict] = {}
    current: int | None = None
    expect = 1

    for ln in lines:
        if RULES_SCHEDULE.match(ln.text):
            break  # schedules are tables; taken from the layout text below

        m = HEADER.match(ln.text)
        if m and int(m.group(1)) == expect:
            current = expect
            # Page per LINE, exactly as parse_act does. A rule long enough to split would
            # otherwise hand every one of its chunks the page where the RULE began, so
            # `r.N(5-9)` would point a reviewer a page or two early — and `page` exists for
            # precisely one purpose: opening the PDF and verifying the citation in seconds
            # (CLAUDE.md §7). No rule reaches MAX_TOKENS today (the largest is r.10 at ~993),
            # so this changes no current chunk; it is wrong code waiting for an amended Rules
            # PDF, and that is the worst kind, because nothing would fail loudly.
            rules[current] = {"page": ln.page, "lines": [(ln.page, ln.text)]}
            expect += 1
            continue

        if current is not None:
            rules[current]["lines"].append((ln.page, ln.text))

    if inspect:
        print(f"  rules found: {len(rules)}")

    missing = sorted(set(range(1, N_RULES + 1)) - set(rules))
    if missing:
        raise SystemExit(f"FATAL: Rules not found: {missing}")

    chunks: list[Chunk] = []
    for n, rule in sorted(rules.items()):
        body = "\n".join(t for _, t in rule["lines"])
        cursor = 0
        for sub, text in pack(body):
            page, cursor = locate_page(text, rule["lines"], cursor, rule["page"])
            cite = f"{RULES_DOC}, r.{n}" + (f"({sub})" if sub else "")
            chunks.append(
                Chunk(
                    doc=RULES_DOC,
                    type="rule",
                    number=str(n),
                    sub=sub,
                    chapter=None,
                    chapter_title=None,
                    schedule=None,
                    part=None,
                    citation=cite,
                    authority_status=RULE_STATUS[n],
                    source_ref=RULES_PDF.name,
                    page=page,
                    text=text,
                    tokens=ntokens(text),
                )
            )

    chunks.extend(rules_schedules(layout, inspect))
    return chunks


def rules_schedules(layout: dict[int, list[str]], inspect: bool = False) -> list[Chunk]:
    """One chunk per Schedule, and per Part where a Schedule splits into Part A/B."""
    flat: list[tuple[int, str]] = [(p, ln) for p in sorted(layout) for ln in layout[p]]

    # locate the seven schedule headings
    starts: list[tuple[int, int, str]] = []  # (flat index, page, ordinal)
    for idx, (page_no, raw) in enumerate(flat):
        m = RULES_SCHEDULE.match(squeeze(raw))
        if m:
            starts.append((idx, page_no, m.group(1).capitalize()))

    found = [name for _, _, name in starts]
    if inspect:
        print(f"  schedules found: {found}")
    if found != ORDINALS:
        raise SystemExit(f"FATAL: expected {ORDINALS}, found {found}")

    chunks: list[Chunk] = []
    for i, (idx, page_no, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(flat)
        body = flat[idx:end]

        see = ""
        for _, raw in body[:4]:
            m = SEE_RULE.search(squeeze(raw))
            if m:
                see = m.group(1)
                break
        if not see:
            raise SystemExit(f"FATAL: no '[See rule ...]' under {name} Schedule")
        status = schedule_status(see)
        if inspect:
            print(f"    {name:8s} p{page_no:2d}  [See rule {see}]  -> {status}")

        # split into Parts if the schedule is parted
        cuts = [j for j, (_, raw) in enumerate(body) if PART.match(squeeze(raw))]
        segments: list[tuple[str | None, list[tuple[int, str]], int]]
        if cuts:
            segments = []
            head = body[: cuts[0]]
            # A Note that says "In this Schedule" governs EVERY Part, but it is printed once, at
            # the very end — so cutting the Parts at their markers dropped it wholly into the
            # LAST one. The Fourth Schedule's Note defines "clinical establishment", "educational
            # institution", "healthcare professional", "health services", "allied healthcare
            # professional" and "mental health establishment" — the six terms PART A's rows are
            # built from — and it was landing entirely in Part B. Part A named those classes and
            # defined none of them, so a chunk retrieved for "which healthcare providers are
            # exempt from child-consent rules" arrived without its own definitions. (It also
            # defines "advertisement", which only Part B uses — which is why the Note is
            # DUPLICATED onto every Part rather than moved to Part A: the statute scopes it to
            # the Schedule, so each Part carries every definition its rows rely on. Human's
            # decision, 2026-07-15.)
            tail: list[tuple[int, str]] = []
            for j in range(cuts[-1], len(body)):
                if SCHEDULE_NOTE.match(squeeze(body[j][1])):
                    tail = body[j:]
                    body = body[:j]  # ...and it is no longer the last Part's private property
                    break
            for k, c in enumerate(cuts):
                stop = cuts[k + 1] if k + 1 < len(cuts) else len(body)
                part = PART.match(squeeze(body[c][1])).group(1)
                # repeat the schedule heading on each Part so the chunk is self-describing,
                # but the page is the PART marker's own page -- Part B can start pages
                # after the heading (Fourth Schedule: heading p13, Part B p14)
                segments.append((part, head + body[c:stop] + tail, body[c][0]))
        else:
            segments = [(None, body, body[0][0])]

        for part, seg, seg_page in segments:
            text = render_schedule([raw for _, raw in seg])
            cite = f"{RULES_DOC}, {name} Schedule" + (f", Part {part}" if part else "")
            chunks.append(
                Chunk(
                    doc=RULES_DOC,
                    type="schedule",
                    number=None,
                    sub=None,
                    chapter=None,
                    chapter_title=None,
                    schedule=name,
                    part=part,
                    citation=cite,
                    authority_status=status,
                    source_ref=RULES_PDF.name,
                    page=seg_page,
                    text=text,
                    tokens=ntokens(text),
                )
            )
    return chunks


# ---------------------------------------------------------------- main


def write(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inspect", action="store_true", help="print what was parsed, write nothing")
    args = ap.parse_args()

    for pdf in (ACT_PDF, RULES_PDF):
        if not pdf.is_file():
            raise SystemExit(f"FATAL: missing source PDF {pdf}")

    print(f"Act   ({ACT_PDF.name})")
    act = parse_act(args.inspect)
    print(f"Rules ({RULES_PDF.name})")
    rules = parse_rules(args.inspect)

    oversize = [c for c in act + rules if c.tokens > MAX_TOKENS]
    for c in oversize:
        print(f"  note: {c.citation} is {c.tokens} tokens (no sub-section to split on)")

    if args.inspect:
        print("\n--inspect: nothing written.")
        return 0

    write(act, OUT / "act_chunks.jsonl")
    write(rules, OUT / "rules_chunks.jsonl")
    print(f"\nwrote {len(act):3d} chunks -> data/processed/act_chunks.jsonl")
    print(f"wrote {len(rules):3d} chunks -> data/processed/rules_chunks.jsonl")

    tally: dict[str, int] = {}
    for c in act + rules:
        tally[str(c.authority_status)] = tally.get(str(c.authority_status), 0) + 1
    print("\nauthority_status:")
    for status in ("in force", "effective 2026-11-13", "effective 2027-05-13", "None"):
        if status in tally:
            print(f"  {status:22s} {tally[status]:3d} chunks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
