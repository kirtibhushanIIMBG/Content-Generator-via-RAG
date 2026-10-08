"""Phase 2 verification. Run: python tests/test_chunks.py

Proves the chunked corpus is safe to index. Regenerate chunks first:
    python -m src.ingest.chunk

Anything that fails here means a citation could be wrong downstream. Do not index.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

ACT = [json.loads(ln) for ln in (PROCESSED / "act_chunks.jsonl").read_text("utf-8").splitlines()]
RULES = [
    json.loads(ln) for ln in (PROCESSED / "rules_chunks.jsonl").read_text("utf-8").splitlines()
]
ALL = ACT + RULES

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
STATUSES = {"in force", "effective 2026-11-13", "effective 2027-05-13"}

# CLAUDE.md §6
CHAPTER_SECTIONS = {
    "I": range(1, 4), "II": range(4, 11), "III": range(11, 16), "IV": range(16, 18),
    "V": range(18, 27), "VI": range(27, 29), "VII": range(29, 33), "VIII": range(33, 35),
    "IX": range(35, 45),
}


def flat(chunks: list[dict]) -> str:
    """Chunk text keeps the PDF's hard line-wraps ('in accordance\\nwith the provisions'),
    so any check for a contiguous phrase has to squeeze whitespace first."""
    return " ".join(" ".join(c["text"] for c in chunks).split())


def sections() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for c in ACT:
        if c["type"] == "section":
            out.setdefault(c["number"], []).append(c)
    return out


def rules() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for c in RULES:
        if c["type"] == "rule":
            out.setdefault(c["number"], []).append(c)
    return out


# ---------------------------------------------------------------- completeness


def test_all_44_sections_present() -> None:
    missing = sorted(set(range(1, 45)) - {int(n) for n in sections()})
    assert not missing, f"Act sections missing: {missing}"


def test_all_23_rules_present() -> None:
    # Rule 17 is the trap: "17.Appointment of..." has NO space after the period
    # (docs/source-verification.md, constraint 1). A naive ^\d+\.\s regex drops it.
    missing = sorted(set(range(1, 24)) - {int(n) for n in rules()})
    assert not missing, f"Rules missing: {missing}"
    assert "17" in rules(), "Rule 17 lost -- the no-space-after-period header trap"


def test_all_schedules_present() -> None:
    got = {(c["schedule"], c["part"]) for c in RULES if c["type"] == "schedule"}
    want = {
        ("First", "A"), ("First", "B"), ("Second", None), ("Third", None),
        ("Fourth", "A"), ("Fourth", "B"), ("Fifth", None), ("Sixth", None),
        ("Seventh", None),
    }
    assert got == want, f"schedule/part mismatch\n  missing: {want - got}\n  extra: {got - want}"
    act_sched = [c for c in ACT if c["type"] == "schedule"]
    assert len(act_sched) == 1, "the Act has exactly one Schedule (penalties, under s.33)"


def test_chapters_match_the_act_structure() -> None:
    for num, chunks in sections().items():
        want = next(ch for ch, rng in CHAPTER_SECTIONS.items() if int(num) in rng)
        got = chunks[0]["chapter"]
        assert got == want, f"s.{num} in chapter {got}, expected {want}"
    titles = {c["chapter"]: c["chapter_title"] for c in ACT if c["chapter"]}
    assert titles["II"] == "Obligations of Data Fiduciary", titles["II"]
    assert titles["V"] == "Data Protection Board of India", titles["V"]


# ---------------------------------------------------------------- metadata


def test_every_chunk_has_citation_source_and_page() -> None:
    # CLAUDE.md §7: a chunk missing any of these must never be indexed.
    for c in ALL:
        where = c.get("citation") or c.get("source_ref")
        assert c["citation"], f"no citation: {c}"
        assert c["source_ref"].endswith(".pdf"), f"bad source_ref: {where}"
        assert isinstance(c["page"], int) and c["page"] >= 1, f"bad page: {where}"
        assert c["text"].strip(), f"empty text: {where}"
    for c in ACT:
        assert 1 <= c["page"] <= 21, f"page out of range for the Act: {c['citation']} p{c['page']}"
    for c in RULES:
        assert 1 <= c["page"] <= 18, f"page out of range for Rules: {c['citation']} p{c['page']}"


def test_every_page_field_points_at_its_own_text() -> None:
    """The page field exists so a human can open the PDF and verify a citation in
    seconds (CLAUDE.md §7). That guarantee must hold for EVERY chunk -- split chunks
    (s.6(9) starts a page after s.6's header) and schedule Parts (Fourth Schedule
    heading p13, Part B p14) inherited their parent's page until this test existed."""
    from pypdf import PdfReader

    # The shared comparison key — see src/ingest/chunk.py::nospace for WHY whitespace must be
    # removed and not collapsed. A second, subtly different copy of this is what made the
    # 2026-07-14 spot-check report a false page mismatch on r.7.
    from src.ingest.chunk import nospace

    readers = {
        "DPDP_Act_2023.pdf": PdfReader(str(ROOT / "data" / "raw" / "DPDP_Act_2023.pdf")),
        "DPDP_Rules_2025.pdf": PdfReader(str(ROOT / "data" / "raw" / "DPDP_Rules_2025.pdf")),
    }

    # Where each Rules schedule's heading is printed, so a Part can be bounded to its OWN
    # schedule. "PART A" alone is not a probe: it is printed on p.9 (First Schedule) AND p.13
    # (Fourth), so a Part that inherited the wrong schedule's page still found its marker there
    # and passed -- the exact mis-citation this test exists to catch. Sixth and Seventh share
    # p.17, so a schedule's span runs up to and INCLUDING the next schedule's heading page.
    # The heading is a STANDALONE LINE, which is how the chunker finds it too (RULES_SCHEDULE).
    # Substring-matching the page text instead finds the rules' own cross-references ("...in
    # accordance with the First Schedule..."), which put "FIRST SCHEDULE" on p.2 — eight pages
    # before the Schedule itself.
    rules = readers["DPDP_Rules_2025.pdf"]
    heading = re.compile(r"^(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH)\s+SCHEDULE$", re.I)
    heading_page: dict[str, int] = {}
    for i, pg in enumerate(rules.pages, start=1):
        for raw in (pg.extract_text() or "").splitlines():
            m = heading.match(" ".join(raw.split()))
            if m:
                heading_page.setdefault(m.group(1).capitalize(), i)
    span_end = {}
    later = sorted(heading_page.items(), key=lambda kv: kv[1])
    for i, (ordinal, first) in enumerate(later):
        span_end[ordinal] = later[i + 1][1] if i + 1 < len(later) else len(rules.pages)

    for c in ALL:
        page = nospace(readers[c["source_ref"]].pages[c["page"] - 1].extract_text() or "")
        if c["type"] == "schedule":
            # tables are re-wrapped, so probe the marker, not the prose
            probe = nospace(f"PART {c['part']}") if c["part"] else nospace(c["text"].splitlines()[0])
        else:
            probe = nospace(c["text"])[:40]
        assert probe in page, (
            f"{c['citation']} claims p.{c['page']}, but that page does not contain the "
            f"chunk's opening text {probe[:40]!r} -- a human following this citation "
            f"lands on the wrong page"
        )
        if c["part"] and c["schedule"] in heading_page:
            lo, hi = heading_page[c["schedule"]], span_end[c["schedule"]]
            assert lo <= c["page"] <= hi, (
                f"{c['citation']} claims p.{c['page']}, which lies outside the "
                f"{c['schedule']} Schedule's own pages ({lo}-{hi}) -- the 'PART {c['part']}' "
                f"marker on that page belongs to a DIFFERENT schedule"
            )


def test_citations_are_wellformed() -> None:
    ok = re.compile(
        r"^(DPDP Act 2023, (s\.\d{1,2}(\(\d{1,2}(-\d{1,2})?\))?|Schedule)"
        r"|DPDP Rules 2025, (r\.\d{1,2}(\(\d{1,2}(-\d{1,2})?\))?"
        r"|(First|Second|Third|Fourth|Fifth|Sixth|Seventh) Schedule(, Part [AB])?))$"
    )
    bad = [c["citation"] for c in ALL if not ok.match(c["citation"])]
    assert not bad, f"malformed citations: {bad}"


def test_rules_authority_status_is_complete_and_correct() -> None:
    # Derived from Rule 1(2)-(4) in the PDF itself, not from memory.
    want = {}
    for n in [1, 2, 17, 18, 19, 20, 21]:
        want[str(n)] = "in force"
    want["4"] = "effective 2026-11-13"
    for n in [3, *range(5, 17), 22, 23]:
        want[str(n)] = "effective 2027-05-13"

    for num, chunks in rules().items():
        for c in chunks:
            assert c["authority_status"] == want[num], (
                f"r.{num}: got {c['authority_status']!r}, expected {want[num]!r}"
            )
    # every rule accounted for, and every status legal
    assert set(want) == set(rules()), "rule status table and parsed rules disagree"
    for c in RULES:
        assert c["authority_status"] in STATUSES, f"illegal status: {c['citation']}"


def test_rule_1_actually_says_what_the_status_table_claims() -> None:
    """The status table above is only trustworthy if the source text supports it.
    This pins RULE_STATUS to the PDF, so a re-ingest of a different PDF fails loudly."""
    r1 = flat(rules()["1"])
    assert "Rules 1, 2 and 17 to 21 shall come into force on the date of their publication" in r1
    assert "Rule 4 shall come into force one year after" in r1
    assert "Rules 3, 5 to 16, 22 and 23 shall come into force eighteen months after" in r1


def test_schedule_status_inherits_from_parent_rule() -> None:
    want = {
        ("First", "A"): "effective 2026-11-13",   # [See rule 4]
        ("First", "B"): "effective 2026-11-13",
        ("Second", None): "effective 2027-05-13",  # [See rules 5(1) and 16]
        ("Third", None): "effective 2027-05-13",   # [See rule 8(1)]
        ("Fourth", "A"): "effective 2027-05-13",   # [See rule 12]
        ("Fourth", "B"): "effective 2027-05-13",
        ("Fifth", None): "in force",               # [See rule 18]
        ("Sixth", None): "in force",               # [See rule 21(2)]
        ("Seventh", None): "effective 2027-05-13",  # [See rules 23(1) and 8(3)]
    }
    for c in RULES:
        if c["type"] != "schedule":
            continue
        key = (c["schedule"], c["part"])
        assert c["authority_status"] == want[key], (
            f"{c['citation']}: got {c['authority_status']!r}, expected {want[key]!r}"
        )


def act_status_of(number: int, sub: str | None) -> str:
    """Expected status, transcribed from G.S.R. 843(E) independently of chunk.py."""
    if number == 6:
        return "effective 2026-11-13" if sub == "9" else "effective 2027-05-13"
    if number == 44:
        return "in force" if sub in ("1", "3") else "effective 2027-05-13"
    if number in {1, 2, *range(18, 27), 35, *range(38, 44)}:
        return "in force"
    return "effective 2027-05-13"  # incl. s.27 -- see act_status() in chunk.py


def test_act_authority_status_is_complete_and_correct() -> None:
    """Every Act chunk carries a status, and it is the one G.S.R. 843(E) appoints.

    A chunk with no authority_status must never be indexed (CLAUDE.md §7).
    """
    for c in ACT:
        assert c["authority_status"] in STATUSES, f"illegal status: {c['citation']}"
    for num, chunks in sections().items():
        for c in chunks:
            want = act_status_of(int(num), c["sub"])
            assert c["authority_status"] == want, (
                f"{c['citation']}: got {c['authority_status']!r}, expected {want!r}"
            )
    sched = next(c for c in ACT if c["type"] == "schedule")
    assert sched["authority_status"] == "effective 2027-05-13", (
        "the Schedule is made under s.33, which G.S.R. 843(E) puts at 2027-05-13 -- the "
        "penalties are NOT yet enforceable"
    )


def test_the_substantive_obligations_are_not_yet_in_force() -> None:
    """The whole point of authority_status. If any of these ever reads 'in force', the
    system can tell Certinal's audience they must comply today -- when in fact none of
    these duties bite until 2027-05-13. This is the golden rule, as a test."""
    for n in ("3", "4", "5", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17"):
        for c in sections()[n]:
            assert c["authority_status"] == "effective 2027-05-13", (
                f"s.{n} is marked {c['authority_status']!r} -- content could imply a "
                f"Data Fiduciary must comply NOW. G.S.R. 843(E)(c) says 2027-05-13."
            )
    # ...while the Board really is standing (that is what makes the distinction matter)
    for n in ("18", "19", "20", "21", "22", "23", "24", "25", "26"):
        for c in sections()[n]:
            assert c["authority_status"] == "in force", f"s.{n} should be in force"


def test_commencement_notification_says_what_the_status_table_claims() -> None:
    """Pins the Act's statuses to the gazette, exactly as rule 1 pins the Rules'.
    Without this, act_status() is just my typing."""
    sys.path.insert(0, str(ROOT))
    from src.ingest.chunk import commencement_evidence

    commencement_evidence()  # raises SystemExit if the PDF is absent or does not match


def test_sections_split_only_where_the_commencement_date_changes() -> None:
    """G.S.R. 843(E) splits exactly two sections across dates. A chunk carries ONE
    status, so those two must be split -- and nothing else should be."""
    split = {n for n, cs in sections().items() if len(cs) > 1}
    assert split == {"6", "44"}, f"expected only ss.6 and 44 to be split, got {sorted(split)}"

    got = {c["citation"]: c["authority_status"] for c in ACT if c["number"] in ("6", "44")}
    assert got == {
        "DPDP Act 2023, s.6(1-8)": "effective 2027-05-13",
        "DPDP Act 2023, s.6(9)": "effective 2026-11-13",  # Consent Manager, with Rule 4
        "DPDP Act 2023, s.6(10)": "effective 2027-05-13",
        "DPDP Act 2023, s.44(1)": "in force",
        "DPDP Act 2023, s.44(2)": "effective 2027-05-13",
        "DPDP Act 2023, s.44(3)": "in force",
    }, got

    # s.6(9) is the Consent Manager route, and it commences with Rule 4. If that pairing
    # ever breaks, the mapping has drifted.
    s69 = next(c for c in ACT if c["citation"] == "DPDP Act 2023, s.6(9)")
    assert "Consent Manager" in s69["text"]
    r4 = rules()["4"][0]
    assert s69["authority_status"] == r4["authority_status"] == "effective 2026-11-13"


# ---------------------------------------------------------------- text integrity


def test_no_hindi_bleedthrough() -> None:
    bad = [c["citation"] for c in ALL if DEVANAGARI.search(c["text"])]
    assert not bad, f"Devanagari survived into: {bad}"


def test_no_gazette_page_numbers_in_any_chunk() -> None:
    """pdfminer emits the running header's PAGE NUMBER as its own text line (x0~522), so
    it matches none of the header patterns. Left alone it survives cleaning and is appended
    to whichever provision straddles the page break -- dropping a bare "8" into the middle
    of s.8, and "25" into r.3. 28 of them were doing exactly that until the y-band filter."""
    stray = [
        (c["citation"], line.strip())
        for c in ALL
        for line in c["text"].splitlines()
        if re.fullmatch(r"\d{1,3}", line.strip())
    ]
    assert not stray, f"gazette page numbers leaked into the legal text: {stray[:8]}"


def test_no_fused_words_from_layout_mode() -> None:
    # pypdf's layout mode can eat the space after a colon ("Note:In this Schedule").
    fused = [
        (c["citation"], m.group(0))
        for c in ALL
        for m in re.finditer(r"[a-z]:[A-Z][a-z]", c["text"])
    ]
    assert not fused, f"layout mode fused a colon to the next word: {fused}"


def test_no_gazette_furniture_in_any_chunk() -> None:
    # running headers, printer colophons, and the page-1 masthead (which extracts as
    # latin gibberish because it is Devanagari in a legacy 8-bit font)
    junk = [
        "THE GAZETTE OF INDIA", "MGIPMRND", "xxxGID", "vlk/kkj.k", "izkf/kdkj",
        "UPLOADED BY THE MANAGER", "Uploaded by Dte",
    ]
    for c in ALL:
        for j in junk:
            assert j not in c["text"], f"{j!r} leaked into {c['citation']}"


def test_act_margin_notes_did_not_corrupt_the_body() -> None:
    """The Act's section titles sit in an 8pt margin column. Flat extraction injects
    them INTO the sentences ('...only in accordance PROCESSING with the provisions...').
    These two sentences are the ones that break first if the margin filter regresses."""
    s4 = flat(sections()["4"])
    assert (
        "only in accordance with the provisions of this Act and for a lawful purpose" in s4
    ), "s.4 corrupted -- margin note 'Grounds for processing personal data.' bled into the body"

    s5 = flat(sections()["5"])
    assert (
        "shall be accompanied or preceded by a notice given by the Data Fiduciary" in s5
    ), "s.5 corrupted -- margin note 'Notice.' bled into the body"


def test_illustrations_stay_with_their_parent_section() -> None:
    # CLAUDE.md §6: Illustrations (ss.5-8) must stay attached to their parent.
    for n in ("5", "6", "7", "8"):
        assert "Illustration" in flat(sections()[n]), f"s.{n} lost its Illustration(s)"
    total = sum(c["text"].count("Illustration") for c in ACT)
    assert total >= 11, f"expected >=11 Illustrations across the Act, found {total}"


def test_chunks_fit_the_embedding_model() -> None:
    # text-embedding-3-large caps at 8191 tokens. Schedules are tables and are NEVER
    # split (they must stay intact), so they are the long ones -- prove they still fit.
    for c in ALL:
        assert len(c["text"]) < 8191 * 3, f"{c['citation']} too long: {len(c['text'])} chars"


# ---------------------------------------------------------------- the penalty table


def table(chunk: dict) -> list[list[str]]:
    """Data rows of the markdown table in a schedule chunk (header excluded)."""
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in chunk["text"].splitlines()
        if line.startswith("|") and "---" not in line
    ]
    assert rows, f"{chunk['citation']} is not rendered as a table"
    return rows[1:]


def test_penalty_table_rows_are_intact() -> None:
    """THE most dangerous chunk in the corpus. Extracted naively this table comes out in
    COLUMN order (all 7 breaches, then all 7 Sl.Nos, then all 7 penalties), dissociating
    every breach from its penalty -- it reads plausibly while welding '250 crore' onto
    the wrong row. This pins each breach to its own penalty.

    Verify by hand against DPDP_Act_2023.pdf, page 21.
    """
    rows = table(next(c for c in ACT if c["type"] == "schedule"))
    assert len(rows) == 7, f"expected 7 penalty rows, got {len(rows)}"

    expected = [
        ("reasonable security safeguards", "two hundred and fifty crore rupees"),
        ("notice of a personal data breach", "two hundred crore rupees"),
        ("children under section 9", "two hundred crore rupees"),
        ("Significant Data Fiduciary under section 10", "one hundred and fifty crore rupees"),
        ("duties under section 15", "ten thousand rupees"),
        ("voluntary undertaking", "Up to the extent applicable"),
        ("any other provision", "fifty crore rupees"),
    ]
    for i, (breach, penalty) in enumerate(expected):
        sl, got_breach, got_penalty = rows[i][0], rows[i][1], rows[i][2]
        assert sl == f"{i + 1}.", f"row {i + 1} has Sl. No. {sl!r}"
        assert breach in got_breach, f"row {i + 1}: expected breach {breach!r}, got {got_breach!r}"
        assert penalty in got_penalty, (
            f"Schedule row {i + 1} ({breach}) carries the WRONG penalty.\n"
            f"    expected: {penalty!r}\n"
            f"    got:      {got_penalty!r}\n"
            f"  The penalty column has come unstuck from the breach column."
        )


def test_third_schedule_retention_table_is_intact() -> None:
    """Same failure mode, Rules side: each class of Data Fiduciary must keep its own
    retention period. Verify against DPDP_Rules_2025.pdf, page 12."""
    rows = table(next(c for c in RULES if c["schedule"] == "Third"))
    assert len(rows) == 3, f"expected 3 retention rows, got {len(rows)}"

    expected = [
        ("e-commerce entity", "two crore registered users"),
        ("online gaming intermediary", "fifty lakh registered users"),
        ("social media intermediary", "two crore registered users"),
    ]
    for i, (cls, threshold) in enumerate(expected):
        _, got_class, _, period = rows[i]
        assert cls in got_class, f"row {i + 1}: expected {cls!r}, got {got_class!r}"
        assert threshold in got_class, f"row {i + 1}: user threshold came unstuck: {got_class!r}"
        assert "Three years from the date on which the Data Principal last" in period, (
            f"row {i + 1} ({cls}) lost its retention period: {period!r}"
        )


# ---------------------------------------------------------------- sub-section splitting


def test_oversize_sections_split_at_subsection_boundaries() -> None:
    """No section or rule in the CURRENT corpus exceeds 1200 tokens, so this path never
    runs on real data -- which is exactly why it needs a test. It arms itself the day an
    amendment lengthens a section, and a bad split would mislabel `sub` and so mis-cite.
    """
    sys.path.insert(0, str(ROOT))
    from src.ingest.chunk import MAX_TOKENS, ntokens, pack

    body = "8. (1) Opening words.\n" + "\n".join(
        f"({i}) " + " ".join(["obligation of the Data Fiduciary"] * 90) for i in range(2, 9)
    )
    assert ntokens(body) > MAX_TOKENS, "fixture is not actually oversize"

    parts = pack(body)
    assert len(parts) > 1, "an oversize section was not split at all"

    labels = [sub for sub, _ in parts]
    assert all(labels), f"a split chunk has no sub-section label: {labels}"
    # labels are single "(5)" or ranges "(5-7)", strictly ascending, none repeated
    firsts = [int(str(s).split("-")[0]) for s in labels]
    assert firsts == sorted(firsts) and len(set(firsts)) == len(firsts), labels

    # every sub-section survives somewhere, and the 80-token overlap is real
    joined = " ".join(t for _, t in parts)
    for i in range(2, 9):
        assert f"({i})" in joined, f"sub-section ({i}) lost in the split"
    assert sum(ntokens(t) for _, t in parts) > ntokens(body), "no overlap was carried"


def test_schedules_are_never_split() -> None:
    # CLAUDE.md §6: each Schedule is its own chunk with its table intact. Three of them
    # exceed 1200 tokens; splitting a table would sever rows from their headers.
    for c in ALL:
        if c["type"] == "schedule":
            assert c["sub"] is None, f"{c['citation']} was split -- schedules must stay whole"


# Every Schedule that IS a table, and the columns it must have. The rest (First A/B, Second,
# Fifth, Sixth) are numbered prose and must stay prose -- turning those into a table would be
# just as wrong as failing to table these.
TABLE_SCHEDULES = {
    "DPDP Act 2023, Schedule": ["Sl. No.", "Breach", "Penalty"],
    "DPDP Rules 2025, Third Schedule": ["S. no.", "Class of Data Fiduciaries", "Purposes", "Time period"],
    "DPDP Rules 2025, Fourth Schedule, Part A": ["S. No.", "Class of Data Fiduciaries", "Conditions"],
    "DPDP Rules 2025, Fourth Schedule, Part B": ["S. No.", "Purposes", "Conditions"],
    "DPDP Rules 2025, Seventh Schedule": ["S. no.", "Purpose", "Authorised person"],
}


def test_table_schedules_are_markdown_with_the_right_columns() -> None:
    """Read as flat text, an aligned table interleaves its columns and welds each row's cells
    onto its neighbour's ("A Data Fiduciary who is an individual in | Processing is restricted
    to..."). It reads plausibly, which is what makes it dangerous. Two Schedules shipped broken:
    Fourth Part A was never detected as a table at all, and Fourth Part B emitted a TWO-column
    table with its caption welded into the heading, fusing Purposes onto Conditions in every row.
    Both were caused by the caption above the table, which is why the header row is pinned here.
    """
    by_cite = {c["citation"]: c for c in ALL}
    for cite, columns in TABLE_SCHEDULES.items():
        text = by_cite[cite]["text"]
        header = next((ln for ln in text.splitlines() if ln.startswith("|")), None)
        assert header, f"{cite}: no markdown table -- it fell back to column-interleaved text"

        cells = [c.strip() for c in header.strip("|").split("|")]
        assert len(cells) == len(columns), f"{cite}: {len(cells)} columns, expected {len(columns)}: {cells}"
        for cell, want in zip(cells, columns):
            assert want.lower() in cell.lower(), f"{cite}: column {cell!r} should contain {want!r}"

        # the caption belongs ABOVE the table, never inside a heading cell
        assert "PART" not in header, f"{cite}: caption welded into the header: {header}"
        assert "shall not apply" not in header, f"{cite}: caption welded into the header: {header}"


def test_prose_schedules_stay_prose() -> None:
    prose = {c["citation"] for c in ALL if c["type"] == "schedule"} - set(TABLE_SCHEDULES)
    by_cite = {c["citation"]: c for c in ALL}
    for cite in prose:
        assert "|---" not in by_cite[cite]["text"], f"{cite}: numbered prose was mangled into a table"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        # SystemExit too: chunk.commencement_evidence() RAISES it (not AssertionError) when the
        # gazette PDF is missing or wrong. Caught only as AssertionError, that killed the run
        # from inside this loop — the ~14 tests after it never ran and no summary ever printed.
        except (AssertionError, SystemExit) as e:
            failed += 1
            print(f"FAIL  {t.__name__}:\n      {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
