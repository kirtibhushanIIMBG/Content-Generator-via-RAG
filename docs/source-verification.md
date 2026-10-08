# Source verification — evidence for the Phase 2 chunker

Both CLAUDE.md §3/§4 pre-ingestion gates are **cleared**. This file records the *evidence*, plus
the extraction facts the chunker must respect. Findings are from a read-only `pypdf` probe on
2026-07-13. Re-run the probe if the PDFs are ever replaced.

## Gate 1 — the Rules PDF is the FINAL notified text ✅

Human confirmed, and independently verified from page 1 of `DPDP_Rules_2025.pdf`, which reads:

> `G.S.R. 846(E)` … `New Delhi, the 13th November, 2025`

This is the final Gazette notification, **not** the superseded January 2025 draft `G.S.R. 02(E)`.

## Gate 2 — both PDFs are text-selectable, not scans ✅

| | Act 2023 | Rules 2025 |
|---|---|---|
| Pages | 21 | 18 |
| Extracted chars | 63,713 (~3,033/pg) | 62,748 (~3,486/pg) |
| Near-empty pages | 0 | 0 |

No OCR needed.

## Completeness (probe-level, NOT yet the chunker's guarantee)

- **Act**: sections 1–44 all present. 9 `CHAPTER` headings, 1 `SCHEDULE`, 11 `Illustration`s.
- **Rules**: rules 1–23 all present. All seven Schedules (First–Seventh) found; `Part A` and
  `Part B` both occur.

## ⚠️ Chunker constraints — read before writing the regex

**1. A rule header may have NO space after the period.** Rule 17 is literally:

```
17.Appointment of Chairperson and other Members .— (1) The Central Government shall ...
```

A naive `^\s*(\d{1,2})\.\s` **silently drops Rule 17** — no error, just a missing rule. Do not
require whitespace after the dot. Verify the parsed set is exactly {1..23} and {1..44}, and fail
loudly if not.

**2. Headers carry stray spaces inside words.** e.g. `Search -cum-Selection`, `sub -rules`,
`sub -section`. Normalise whitespace before matching, and do not anchor on exact word spacing.

**3. Body text uses real Unicode punctuation, not ASCII.** U+2014 em-dash (×92), U+201C/201D
smart quotes (×71), U+2019 apostrophe (×12), U+2013 en-dash (×4). Section bodies typically open
`.— (1)` with an em-dash. **These are correct — do not "sanitise" them.** If they render as `?`
in a terminal that is a cp1252 *console* artifact, not a data problem. (Also 5× U+00E8 `è`,
likely a font mis-map — inspect, do not mass-replace.)

**4. Hindi is header-only, not bilingual body text.** Devanagari appears only as 243 chars across
the 9 even-numbered pages of the Rules PDF (2,4,…,18) — the Gazette running header — plus 9 chars
on page 1 of the Act. There is no parallel Hindi body to separate. Strip the running header;
then assert zero Devanagari survives into any chunk.

**5. Rule 17 vs section 17 are different things.** The string `17` also appears inside
cross-references (`section 17 of the Act`), pay-matrix levels (`level 17`), and a citation to the
`Mental Healthcare Act, 2017`. Match headers at line-start only; never substring-match a number.

**6. Commencement is in the text itself.** Rules 1, 2 and 17–21 come into force on publication —
`(2) Rules 1, 2 and 17 to 21 shall come into force on the date of their publication in the
Official Gazette.` Cross-check this against the `authority_status` values in CLAUDE.md §7 when
assigning metadata; do not assign effective dates from memory.

---

## Gate 3 — the Act's commencement dates ✅ (G.S.R. 843(E))

The Act **cannot** date itself: s.1(2) says only *"such date as the Central Government may, by
notification in the Official Gazette, appoint."* So `authority_status` for the 44 sections comes
from a **third** document, obtained 2026-07-13 and stored at `data/raw/DPDP_Act_Commencement_SO.pdf`
(gitignored, build-time only):

> **G.S.R. 843(E)** — Ministry of Electronics and Information Technology, **New Delhi, 13th
> November 2025**. `[F. No. AA-11038/1/2025-CL&ES]`, AJIT KUMAR, Jt. Secy. `CG-DL-E-14112025-267647`.
> Source: [meity.gov.in](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf)
> (403s to most clients; fetched with a browser User-Agent).

Operative text, verbatim — *"the Central Government hereby appoints —"*

| clause | when | Act provisions |
|---|---|---|
| (a) | date of publication → **in force** | s.1(2), s.2, ss.18–26, ss.35, 38, 39, 40, 41, 42, 43, s.44(1) & (3) |
| (b) | one year → **2026-11-13** | s.6(9), s.27(1)(d) |
| (c) | eighteen months → **2027-05-13** | ss.3–5, s.6(1)–(8) & (10), ss.7–10, ss.11–17, s.27 *except* (1)(d), ss.28–34, 36, 37, s.44(2) |

**This is a metadata source, NOT a corpus document.** It is never chunked; the knowledge base
still contains only the Act and the Rules (golden rule, CLAUDE.md §3).

Consequences the content pipeline must respect:
- **The substantive regime is not live.** Notice (s.5), consent (s.6), security safeguards (s.8),
  children (s.9), SDF (s.10), cross-border (s.16/17) all bite on **2027-05-13** — the same day as
  the Rules that operationalise them. Never write "you must comply today".
- **The penalties are not enforceable yet.** ss.33–34 and the Schedule are clause (c) →
  2027-05-13. Any "up to ₹250 crore" line must be dated.
- **What IS live** is the Data Protection Board (ss.18–26) and the definitions (s.2).
- **s.6(9) and Rule 4 commence together** (2026-11-13) — both are the Consent Manager machinery.
  `test_sections_split_only_where_the_commencement_date_changes` pins that pairing; if it ever
  breaks, the mapping has drifted.

Two consequences for chunking:
1. **ss.6 and 44 are split at sub-section level** — not for length, but because their sub-sections
   commence on *different dates* and a chunk carries exactly one `authority_status`.
2. **s.27 is deliberately NOT split.** Its early provision is *clause (d) of sub-section (1)* — a
   clause, sharing a chapeau with (a)–(c). Isolating it would leave a fragment that is easy to
   mis-cite, so s.27 takes the **later** date (2027-05-13). This understates clause (d) by six
   months, which is the safe direction: the golden rule forbids implying a duty is live *early*,
   not late. (Human decision, 2026-07-13.)

`commencement_evidence()` asserts all three clauses are present in the PDF, whitespace-insensitively
(the gazette extracts with stray spaces inside words: `sub -section`, `sectio n 1`). A missing or
wrong PDF **exits 1** — the mapping can never silently drift from the gazette.

---

## Extraction findings (Phase 2 — added 2026-07-13, learned the hard way)

These cost real debugging time. Read them before touching `src/ingest/chunk.py`.

**7. The Act needs TWO pdf libraries, and so does the corpus.** Neither pypdf nor pdfminer
gets everything right:

| | body text | Schedules (tables) |
|---|---|---|
| pdfminer.six | ✅ used | ❌ reads columns in y-order → interleaves cells |
| pypdf `layout` | ❌ inlines margin notes into sentences | ✅ used |

**8. The Act's section titles live in an 8pt MARGIN column, not inline.** "Short title and
commencement.", "Notice.", "Consent." are side-notes. Flat extraction drops them into the
middle of the body: `...only in accordance PROCESSING with the provisions...`. That is silent
corruption of legal text. They are removed geometrically: `size < 9.5 AND (x0 < 110 OR x0 > 480)`.
The margin **alternates sides by page parity** (x0≈57 on even pages, x0≈486 on odd). Body spans
x0 117.5–477.6. Do NOT filter on font size alone — chapter titles are 7–8pt small-caps too, but
they are centred (x0≈235), so the x0 test is the only thing keeping them.

**9. Act page 1 is inside a Form XObject.** pdfminer returns **2 lines** for page 1 unless you
(a) recurse into `LTFigure` and (b) pass `LAParams(all_texts=True)`. Without both, section 1 and
CHAPTER I vanish — and because the parser only accepts the *next expected* number, one lost
section cascades into "0 sections found". This same nesting is why pypdf reports negative `y`
coordinates on page 21.

**10. The Act's penalty Schedule is the most dangerous chunk in the corpus.** Extracted naively
it comes out in COLUMN order — all 7 breaches, then all 7 Sl. Nos, then all 7 penalties — so
every penalty is dissociated from its breach. It still *reads* plausibly, which is what makes it
lethal: nothing stops "₹250 crore" being welded to the wrong row. Schedules are therefore rebuilt
into real markdown tables, and `test_penalty_table_rows_are_intact` pins each breach to its own
penalty. **Verify against p.21 by hand if you ever change the chunker.**

**11. Table columns are found from blank "gutters", with two traps.** Splitting on runs of 2+
spaces does NOT work — layout mode justifies cell text (`Three  years  from  the  date`) and the
Act's own header contains `of  this Act`. A gutter must be blank down the *whole* table. Two
follow-on traps: (a) a Schedule is usually a table FOLLOWED by a prose "Note:" block whose
full-width lines collapse every gutter — so grow the table only while the row structure survives;
(b) where several rows carry identical wording, their justification gaps line up and open a
*false* gutter mid-cell (this splits a phantom column containing the word "the" out of the Third
Schedule). A real column always has a heading, so a headerless span is merged back left.

**12. The page number is its own text line, and it lands *inside* the law.** pdfminer emits the
running header as several lines — `SEC. 1]`, `THE GAZETTE OF INDIA EXTRAORDINARY`, and the bare
page number `21` (x0≈522) — so the page number matches **none** of the header patterns. Left
alone it survives cleaning and gets appended to whichever provision straddles the page break: a
bare `8` inside s.8, a `25` inside r.3. **28 of them were doing exactly that** until `clean()`
started locating the header's y per page and dropping bare numbers on that same line.
`test_no_gazette_page_numbers_in_any_chunk` keeps it at zero.

**13. A split chunk's `page` is not its section's page.** s.6 starts on p.5 but s.6(9) lives on
p.6; s.44 starts on p.19 but s.44(2)/(3) are on p.20; the Fourth Schedule heading is on p.13 but
Part B starts on p.14. Five chunks pointed a human reviewer at the wrong page until pages were
threaded per-line through the splitter (`locate_page()`) and parted schedules took the PART
marker's page. `test_every_page_field_points_at_its_own_text` now checks all 81 chunks, including
splits and Parts — the earlier check skipped exactly those.

**14. Known cosmetic artifact (not a bug — do not "fix" it).**
- `17.Appointment` in r.17 — the source PDF genuinely has no space after the period (see 1).
  (`Note:In` in the Third Schedule *was* a layout-mode defect and is now repaired by `unfuse()`,
  which only ever inserts a space after a colon — it never alters a character.)

---

## Verification: what actually proves the corpus is sound

Beyond `tests/test_chunks.py` (24 checks), the chunked corpus was reconciled against the source:

| check | result |
|---|---|
| **Exact assembly** — chunk text concatenated vs cleaned source lines concatenated | **character-identical**: Act 48,145 = 48,145; Rules 25,412 = 25,412. Nothing dropped, duplicated or reordered. |
| Line reconciliation — every cleaned line lands in exactly one chunk | zero body lines lost. The only unchunked lines are the 8 CHAPTER headings (consumed as `chapter`/`chapter_title` metadata) and the front matter before the first provision. |
| Word completeness on Schedules (the reconstructed tables) | Act Schedule 184 words in → 184 out. Rules Schedules: zero missing words. |
| Citations unique · no boundary bleed · `page` really contains the provision's opening words | all clean |

**A warning for whoever re-verifies this.** Do NOT use raw `pypdf` output as the oracle: for the
Act it is contaminated with exactly the furniture the chunker removes. pypdf's page 19 ends
`...shall be substituted, namely:—` followed by *"Laying of / rules and / certain / notifications.
/ Power to / amend / Schedule. / ... / 24 of 1997."* — the 8pt margin side-notes, dumped at the
end of the page. Diff against that and every page-straddling chunk looks corrupt when it is in
fact correct. Use the exact-assembly reconciliation above instead.

**Deliberately not chunked** (and therefore uncitable): the Act's long title and enacting formula
("An Act to provide for the processing of digital personal data..."), and the Rules' notification
recitals. Both are front matter; CLAUDE.md §6 makes section/rule/schedule the only base units, and
§7 offers no `type` for a preamble. Raise it with the human if marketing ever wants to quote the
long title.
