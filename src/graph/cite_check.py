"""cite_check — machine self-verification of a draft (CLAUDE.md §8, design §5.7).

Pure functions, no API calls: everything here is deterministic and offline, so it can be
argued with, unit-tested for free, and cannot itself hallucinate. It answers three questions
about a Draft, in the order they can kill you:

1. FABRICATED — does it cite a provision it was never shown? (measured, see Draft.fabricated)
2. DATE-LIE — does it cite a not-yet-in-force provision without saying when it starts?
3. TRACEABILITY — what fraction of its legal claims carry a valid citation?

The response to a failure lives in the graph (src/graph/pipeline.py): ONE retry, spent only
on a golden-rule failure (a fabricated citation or a date-lie). A coverage-only miss — low
traceability, nothing invented, dates honest — goes straight to a human at attempt 1 with the
`unsupported` sentences attached. Never auto-pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.generation.generate import CITE, DISCLAIMER, Draft, cite_supported

MIN_TRACEABILITY = 0.9  # design §5.7

# A sentence asserts a LEGAL CLAIM if it uses the language of obligation, permission,
# prohibition, entitlement, time limits or penalties. Narrative connective tissue ("This
# matters for compliance teams.", "Here is what changes.") carries no cue and is not a claim
# — demanding a citation for it would drive retries that cannot succeed.
#
# ponytail: a cue-word list under-detects a claim phrased without one ("Consent is the
# default basis for processing personal data."), which inflates the score. It is a floor, not
# a proof — the human review console (Phase 6) is the backstop, and an LLM claim-extractor
# (eval/run_eval.py already runs a judge) is the upgrade path if the floor proves too low.
CLAIM_CUE = re.compile(
    r"\b(must|shall|may|cannot|can(?:not)? be|require\w*|oblig\w*|prohibit\w*|entitl\w*|"
    r"right to|penalt\w*|fine[sd]?|liable|within \d|no later than|\d+\s*(?:days?|hours?)|"
    r"effective|in force|takes effect|appl(?:ies|y)|provide[sd]|specif\w*|mandat\w*|"
    r"permit\w*|allowed|responsible for)\b",
    re.I,
)

_MASK = "\x00"  # citations are masked out before sentence splitting: "s.8(7)" ends in no dot,
# but "[DPDP Act 2023, s.8]" is full of them and would shred a naive splitter.
# The bracket pattern is generate.CITE — the SAME object the draft's own citations() uses. When
# these two disagree, a citation the checker cannot see still counts as one to the drafter (or
# the reverse), and the gap is exactly where an unverified claim lives.


_BOLD_LINE = re.compile(r"\*\*([^*]+)\*\*:?$")
_BULLET = re.compile(r"^([-*•]|\d+[.)])\s+")


def _is_heading(line: str) -> bool:
    """A section label the model wrote as structure, not as a legal claim: a markdown heading
    ("## Penalties"), a bold label ("**Penalties**"), or a BARE-TEXT label ("Effective date").

    A bold line that ENDS IN A SENTENCE TERMINATOR is a bolded claim, not a label — dropping
    it would exempt "**A Data Fiduciary must notify the Board.**" from scoring altogether,
    which is a hole a draft could hide an uncited claim in. Labels do not end in full stops.

    Bare-text labels are the same problem in a different coat. The drafter writes its section
    headings as plain lines — "Effective date", "Core security obligations", "What the Act
    requires" — NOT as "## ...". They carry claim cue-words but assert nothing, and cost a
    redraft that can never fix them: the model keeps the label and fails again (measured on
    gpt-5-mini — grievance-90-days escalated on "Effective date" alone, at 89% traceability;
    the drafter is gpt-5.6-terra since 2026-07-16, and this guard is NOT model-specific — it
    is prose shape, every drafter does it, do not delete it as obsolete). Kept
    deliberately narrow — short, unterminated, no citation, not a bullet, AND (audit-measured
    holes, both previously machine-passed): no COLON — "The Board must consider the following
    factors:" is an uncited claim STEM, not a label, and dropping it exempted the claim and
    orphaned its bullets — and no DIGIT — "Breach notification deadline: 72 hours" asserts a
    time limit; a number in a short line is a claim wearing a label's clothes. A real claim
    that ends in "." is always scored; an unterminated, digit-free prose claim can still slip
    (documented floor — CLAIM_CUE's own docstring — and human review is the backstop).
    """
    if re.match(r"#{1,6}\s", line):
        return True
    m = _BOLD_LINE.fullmatch(line)
    if m:
        return not m.group(1).rstrip().endswith((".", "!", "?"))
    return (
        len(line.split()) <= 10
        and not line.endswith((".", "!", "?"))
        and ":" not in line
        and not any(ch.isdigit() for ch in line)
        and not CITE.search(line)
        and not _BULLET.match(line)
    )


def _split(line: str) -> list[str]:
    """Sentences within one line. Citations are masked first: "s.8(7)" ends in no dot, but
    "[DPDP Act 2023, s.8]" is full of them and would shred a terminator-based splitter.

    ponytail: splits on terminator-then-capital. Fine for the model's plain business prose;
    it would over-split on an unmasked abbreviation ("e.g. The") if one ever appeared.
    """
    masked = CITE.sub(lambda m: _MASK * len(m.group()), line)
    starts = [0] + [m.end() for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z\"(])", masked)]
    out = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(line)
        if piece := line[s:e].strip():
            out.append(piece)
    return out


def claim_units(text: str) -> list[tuple[str, str]]:
    """The draft body as (sentence, citation_scope) pairs — the unit cite_check scores.

    Structure is not decoration here, it decides what counts as cited:

    * HEADINGS are dropped. "## Penalties apply to a breach" is full of claim cues and would
      be scored as an uncited claim that NO redraft could fix — the model would rewrite the
      body, keep the heading, and fail again. Measured: it did exactly that, three times.
    * A BULLET inherits the citation of the stem that introduces it. The model writes "The
      Board must consider [DPDP Act 2023, s.33]:" and then lists the factors, quoted from the
      source, one per line. The citation governs the whole list; demanding one per bullet
      flags five "uncited claims" that are, in fact, the cited provision's own words.

    Everything else is scored sentence by sentence, on its own citation.
    """
    # Draft.body()'s cut, and it must stay identical to it: the LAST disclaimer (the one the
    # code appended), never the "---" first line, and never the FIRST occurrence — a stray
    # mid-body disclaimer would then hide every sentence after it from scoring while it still
    # shipped in the draft. See Draft.body().
    body = text.rsplit(DISCLAIMER, 1)[0]
    units: list[tuple[str, str]] = []
    stem = ""  # the citation scope a following bullet inherits
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _is_heading(line):
            stem = ""  # a new section: a bullet under it must not inherit the last one's citation
            continue
        if _BULLET.match(line):
            item = _BULLET.sub("", line)
            units += [(s, s + " " + stem) for s in _split(item)]  # bullet + its stem's citations
            continue
        stem = line
        units += [(s, s) for s in _split(line)]
    return units


def sentences(text: str) -> list[str]:
    """The draft's scored sentences (claim_units without their citation scope)."""
    return [s for s, _ in claim_units(text)]


def is_claim(sentence: str) -> bool:
    """Does this sentence assert something about what the law requires?"""
    return bool(CLAIM_CUE.search(sentence))


def date_honest(d: Draft) -> tuple[bool, str]:
    """Every cited not-yet-in-force provision must have its effective YEAR in the draft.

    KNOWN CEILING: this detects the TOTAL ABSENCE of the year, not a date-lie. A draft that
    says "you must notify the Board within 72 hours today" while echoing "[effective
    2027-05-13]" somewhere passes, because the year is present. It is a floor, not a proof.

    Matching is by cite_supported, NOT exact equality — audit-measured: a draft citing the
    refinement [DPDP Rules 2025, r.7(1)] of a future-dated r.7 chunk validated for
    traceability but slipped this gate entirely (exact match saw no "r.7" in the citations),
    machine-passing a draft that implied a 2027 obligation is live today. If a citation rests
    on a hit, it inherits that hit's effective date. Same one-definition rule as fabrication.
    """
    cited = set(d.citations())
    for h in d.hits:
        if h.authority_status.startswith("effective") and any(
            cite_supported(c, [h]) for c in cited
        ):
            year = h.authority_status.split("-")[0].split()[-1]
            if year not in d.text:
                return False, f"cites {h.citation} ({h.authority_status}) but never says {year}"
    return True, ""


@dataclass
class Report:
    traceability_score: float           # supported claims / total claims, in [0, 1]
    fabricated: list[str] = field(default_factory=list)   # cited but never retrieved
    unsupported: list[str] = field(default_factory=list)  # legal claims carrying no valid citation
    claims: int = 0
    date_ok: bool = True
    date_why: str = ""

    @property
    def ok(self) -> bool:
        """A draft passes ONLY if it invents nothing, mis-dates nothing, and traces."""
        return (
            not self.fabricated
            and self.date_ok
            and self.traceability_score >= MIN_TRACEABILITY
        )

    def feedback(self) -> str:
        """What to tell the model on a redraft. Specific failures only — "try harder" is not
        actionable, and a vague retry costs a full generation to change nothing."""
        parts = []
        if self.fabricated:
            parts.append(
                "You cited provisions that are NOT among the sources you were given: "
                + ", ".join(f"[{c}]" for c in self.fabricated)
                + ". Either you invented them, or you merged/altered a real citation (each "
                "bracket holds exactly ONE citation, copied verbatim from a source header). "
                "Remove every claim you cannot support from the sources above, and re-cite "
                "the rest verbatim."
            )
        if not self.date_ok:
            parts.append(
                f"Date honesty failure: {self.date_why}. State plainly, in prose, that the "
                "provision is not yet in force and give the date it takes effect."
            )
        if self.unsupported:
            shown = "\n".join(f"  - {s}" for s in self.unsupported[:5])
            parts.append(
                f"These sentences assert what the law requires but carry no valid citation "
                f"(traceability {self.traceability_score:.0%}, must be "
                f"{MIN_TRACEABILITY:.0%}):\n{shown}\n"
                "Cite each one from the sources, or delete it."
            )
        return "\n\n".join(parts)


def check(d: Draft) -> Report:
    """Verify a grounded draft against the chunks it was actually shown."""
    fabricated = d.fabricated()
    date_ok, date_why = date_honest(d)

    claims = [(s, scope) for s, scope in claim_units(d.text) if is_claim(s)]
    unsupported = [
        s for s, scope in claims
        # `scope` is the sentence plus, for a bullet, the stem that introduced it — a citation
        # anywhere in the scope supports the claim. cite_supported accepts an exact chunk match
        # OR a validated sub-section refinement (s.8(5) off a shown s.8); a fabricated or
        # invented-sub-section citation supports nothing. Same rule as Draft.fabricated().
        if not any(cite_supported(c, d.hits) for c in CITE.findall(scope))
    ]
    # No claims detected is NOT a pass. A grounded draft with no citations anywhere scored a
    # clean 100% on the eval's fabrication gate for exactly this reason (eval/run_eval.py:
    # `uncited`): nothing cited means nothing fabricated. 700 words of confident, sourceless
    # law is the failure, not the absence of one.
    score = 1.0 - len(unsupported) / len(claims) if claims else (1.0 if d.citations() else 0.0)

    return Report(
        traceability_score=score,
        fabricated=fabricated,
        unsupported=unsupported,
        claims=len(claims),
        date_ok=date_ok,
        date_why=date_why,
    )
