"""Phase 3 verification — hybrid retrieval must find the RIGHT provision.

Hits the live Qdrant Cloud collection and the OpenAI embeddings API, so it needs
QDRANT_* + OPENAI_API_KEY, and it costs a fraction of a cent per run.

    python tests/test_retrieval.py

On a Zscaler/corporate-MITM machine the OpenAI call needs a CA bundle that includes the
corporate root (see docs/system-design.md §5.4 note):
    SSL_CERT_FILE=~/.certs/ca-bundle.pem python tests/test_retrieval.py

Each case is a query a marketer would actually ask, plus the citation that MUST be in the
top-k. These are the real gate: green tests on the chunker prove nothing about whether the
retriever surfaces s.8 when someone asks about breaches.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingest.index_qdrant import load_chunks  # noqa: E402
from src.retrieval.hybrid import (  # noqa: E402
    COLLECTION,
    MIN_RELEVANCE,
    TOP_K,
    Hit,
    _catalog,
    _referenced_handles,
    expand_query,
    is_grounded,
    merge_hits,
    provision_terms,
    qdrant,
    search,
)

# Questions a COMMON PERSON asks that the DPDP texts genuinely answer...
LAY_GROUNDED = [
    "Can I ask a company to delete my data?",
    "How do I take back my consent?",
    "My kid wants an Instagram account. Is that allowed?",
    "A company leaked my personal information. Who do I complain to?",
    "What are my rights under this law?",
]
# ...and questions that they do NOT. Retrieval still returns 6 chunks for these — it always
# does — so without a relevance gate, generation would confidently write law that isn't there.
# "Can I get compensation?" is the dangerous one: the DPDP Act grants no compensation right.
UNGROUNDED = [
    "best biryani recipe in Hyderabad",
    "how do I fix my car engine",
    "what is the capital of France",
    "python list comprehension tutorial",
]

# (query, citation that must appear in top-6, why it is the right answer)
CASES = [
    ("Section 8(7)", "DPDP Act 2023, s.8", "exact-term lookup — the sparse/BM25 side"),
    ("Rule 7", "DPDP Rules 2025, r.7", "exact-term lookup of a Rule number"),
    (
        "What must a notice to the Data Principal contain?",
        "DPDP Rules 2025, r.3",
        "paraphrase — the dense side; r.3 prescribes notice content",
    ),
    (
        "What information must a Data Fiduciary give when a personal data breach happens?",
        "DPDP Rules 2025, r.7",
        "breach intimation is r.7",
    ),
    (
        "How much can a company be fined for failing to protect personal data?",
        "DPDP Act 2023, Schedule",
        "penalties live in the Schedule (a markdown table) — it must be retrievable",
    ),
    (
        "Can personal data be transferred outside India?",
        "DPDP Rules 2025, r.15",
        "cross-border transfer is r.15",
    ),
    (
        "How long does a Data Fiduciary have to respond to a Data Principal's request?",
        "DPDP Rules 2025, r.14",
        "r.14 sets the response period",
    ),
    (
        "What consent is needed to process a child's personal data?",
        "DPDP Act 2023, s.9",
        "s.9 governs children's data (r.10 is also acceptable context)",
    ),
    (
        "Schedule III of the DPDP Rules",
        "DPDP Rules 2025, Third Schedule",
        "CLAUDE.md §6: the roman-numeral schedule label must normalize too",
    ),
    (
        "the Schedule to the DPDP Act",
        "DPDP Act 2023, Schedule",
        "the Act's schedule field is 'The Schedule' — index/query handles must agree",
    ),
    (
        "What does Part B of the First Schedule require?",
        "DPDP Rules 2025, First Schedule, Part B",
        "the Part handle must discriminate Part B from Part A and from other Schedules",
    ),
    # A Schedule is a bare TABLE: its subject is written down only in its parent rule. The
    # Third Schedule IS the retention table and contains "retain"/"retention"/"erase"/"erasure"
    # ZERO times — so it went missing from every retention query until index_text started
    # prepending the parent provision's opening words. Found by a Certinal marketer question
    # ("how long must we retain signed contracts"), which got an honest "the sources do not
    # include the Third Schedule" — a correct answer built on the wrong evidence.
    (
        "How long must a Data Fiduciary keep personal data before erasing it?",
        "DPDP Rules 2025, Third Schedule",
        "the retention-period table; retrievable ONLY via its parent rule's context (r.8)",
    ),
    (
        "What is the data retention period for an e-commerce company?",
        "DPDP Rules 2025, Third Schedule",
        "the Third Schedule names the classes and their three-year period",
    ),
]

# A BARE citation is unambiguous — the reader named the provision, so it must LEAD, not merely
# appear. Prose questions that happen to mention a provision are deliberately NOT in here: see
# the ceiling note on test_an_exact_citation_query_ranks_its_provision_first.
TOP_RANK_CASES = [
    ("Section 8(7)", "DPDP Act 2023, s.8"),
    ("Rule 7", "DPDP Rules 2025, r.7"),
    ("First Schedule Part B", "DPDP Rules 2025, First Schedule, Part B"),
    ("Fourth Schedule Part A", "DPDP Rules 2025, Fourth Schedule, Part A"),
    ("Schedule III", "DPDP Rules 2025, Third Schedule"),
    # The four a marketer's content brief broke (dual-persona test): bare citations where
    # dense noise + rank-based RRF beat a decisive sparse win, and sub-split ambiguity.
    ("r.22", "DPDP Rules 2025, r.22"),
    ("Section 33", "DPDP Act 2023, s.33"),
    ("s.44(2)", "DPDP Act 2023, s.44(2)"),
    ("rule 8(1)", "DPDP Rules 2025, r.8"),
    ("s.6(9)", "DPDP Act 2023, s.6(9)"),
    ("Section 6(3)", "DPDP Act 2023, s.6(1-8)"),  # a sub inside a RANGE chunk must find it
]

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else ': ' + detail}")
    if not ok:
        FAILURES.append(name)


# (query, handles that MUST be minted, handles that must NOT be) — each line is a measured bug.
MINT_CASES = [
    ("sub-section 7 of section 8", {"section8"}, {"section7", "s7"}),
    ("subsection 7 of section 8", {"section8"}, {"section7", "s7"}),
    # The Rules say "sub-rule" as often as the Act says "sub-section", but the guard was
    # only ever added to the sections branch: this minted rule3 and pinned r.3 (Notice)
    # level with the rule actually asked about. Both branches must reject a sub- prefix.
    ("sub-rule 3 of rule 6", {"rule6"}, {"rule3", "r3"}),
    ("sub rule 3 of rule 6", {"rule6"}, {"rule3", "r3"}),
    ("DPDP Rules 2025 notice requirements", set(), {"rule2025", "r2025"}),
    ("What does Part B of the First Schedule require?", {"firstschedule", "partb"}, {"parta"}),
    ("Schedule III of the DPDP Rules", {"thirdschedule"}, set()),
    ("the Schedule to the DPDP Act", {"theschedule"}, set()),
    ("Section 8(7)", {"section8", "s8"}, set()),
    ("Rule 7", {"rule7", "r7"}, set()),
    ("What are the rights of a Data Principal?", set(), {"section1", "rule1"}),
    # A possessive before a number is not a citation. This minted section44 and pinned
    # s.44 (TRAI/IT-Act amendments) to ranks 1-3 for a question about the Act's structure.
    ("the DPDP Act's 44 sections", set(), {"section44", "s44"}),
    ("the DPDP Act’s 44 sections", set(), {"section44", "s44"}),  # Word curls apostrophes
    ("s.44(2)", {"section44", "s44", "s44sub2"}, set()),
    ("rule 8(1)", {"rule8", "r8", "r8sub1"}, set()),
]


def test_a_query_expansion_mints_no_junk_handles() -> None:
    """A FALSE handle is worse than none: it is high-IDF, so it drags an unrelated provision
    into the top-k. Every case below was observed mis-ranking a real query."""
    for query, must, must_not in MINT_CASES:
        minted = set(expand_query(query).split()) - set(query.split())
        # `must <= minted` is VACUOUS when must is empty — the empty set is a subset of
        # everything, so the four "mints nothing" cases printed PASS no matter what was
        # minted. A regression that minted section15 for "rights of a Data Principal" (a
        # false high-IDF handle, which is exactly what pins the wrong provision to rank 1)
        # would have sailed through the test written to catch it. Empty must => mint NOTHING.
        ok = (must <= minted) if must else not minted
        check(f"mints {sorted(must) or 'nothing'}: {query[:44]!r}", ok, f"got {minted}")
        check(f"mints no {sorted(must_not)}: {query[:44]!r}", not (must_not & minted), f"got {minted}")


def test_a_mint_parity_offline() -> None:
    """For EVERY chunk: a natural citation query must share >=1 synthetic handle with what
    the index minted for that chunk. This is the invariant the citation-handle design rests
    on, and it runs offline — it caught the Act Schedule minting 'scheduleschedule' while
    the query side minted 'theschedule' (they never matched)."""
    bad = 0
    for c in load_chunks():
        n = (c.get("number") or "").split("(")[0].strip()
        if n:
            query = f"{'Section' if c['doc'].startswith('DPDP Act') else 'Rule'} {n}"
        else:
            sched = c["schedule"]  # "The Schedule" already contains the word; ordinals don't
            query = sched if sched.lower().endswith("schedule") else f"{sched} Schedule"
        indexed = set(provision_terms(c).split())
        minted = set(expand_query(query).split()) - set(query.split())
        if not indexed & minted:
            bad += 1
            check(
                f"mint parity: {c['citation']}",
                False,
                f"query {query!r} mints {minted or '{}'} vs indexed {indexed}",
            )
    check("mint parity holds for every chunk", bad == 0)


def test_collection_is_complete() -> None:
    """Every chunk in the JSONL is in Qdrant. A silently missing section is uncitable."""
    expected = len(load_chunks())
    actual = qdrant().count(COLLECTION, exact=True).count
    check("all chunks indexed", actual == expected, f"{actual} points, expected {expected}")


def test_retrieval_finds_the_right_provision() -> None:
    for query, must_cite, why in CASES:
        hits = search(query)
        cites = [h.citation for h in hits]
        hit = must_cite in cites
        rank = cites.index(must_cite) + 1 if hit else 0
        check(
            f"{query[:52]!r:56s} -> {must_cite}",
            hit,
            f"not in top-{TOP_K} ({why}). Got: {cites}",
        )
        if hit and rank > 3:
            print(f"      note: found at rank {rank}/{TOP_K} — weak, watch this one")


def test_an_exact_citation_query_ranks_its_provision_first() -> None:
    """A bare citation is unambiguous — the reader named the provision. If it is not rank 1,
    generation gets chunks of noise ahead of the one the reader asked for.

    Known ceiling (measured, accepted): a PROSE question mentioning a part — "What does Part B
    of the First Schedule require?" — returns Part B at rank 2, behind Part A. BM25 length-
    normalises, and Part A is 421 tokens to Part B's 1402, so Part A's shared terms outscore
    Part B's two unique handles; RRF then splits them by 0.00002. Accepted because both Parts
    land in the top-k, each carrying its own citation, so nothing is mis-cited — only one of six
    slots is spent. Do NOT "fix" this by weighting fusion toward sparse: the semantic queries in
    CASES depend on the dense side, and this is a coin-flip tie, not a retrieval failure.
    """
    for query, must_cite in TOP_RANK_CASES:
        hits = search(query)
        top = hits[0].citation if hits else "(nothing)"
        check(f"rank 1 for {query[:44]!r}", top == must_cite, f"rank 1 was {top}, wanted {must_cite}")


def test_off_topic_questions_are_not_grounded() -> None:
    """The golden rule ("nothing relevant -> 'no grounded source', never generate anyway") was
    UNENFORCEABLE until Hit.relevance existed: RRF scores are computed from ranks, so "how do I
    fix my car engine" scored 0.70 — the same as the best real query. Every question looked
    equally well-grounded."""
    for q in UNGROUNDED:
        hits = search(q)
        best = max((h.relevance for h in hits), default=0.0)
        check(f"NOT grounded: {q[:40]!r}", not is_grounded(hits), f"best relevance {best:.3f}")

    for q in LAY_GROUNDED:
        hits = search(q)
        best = max((h.relevance for h in hits), default=0.0)
        check(f"grounded: {q[:40]!r}", is_grounded(hits), f"best relevance {best:.3f} < {MIN_RELEVANCE}")


def test_the_relevance_threshold_keeps_its_margin() -> None:
    """A threshold with no daylight around it is a coin flip. Keep a real gap on both sides, or
    a corpus/model change will silently turn junk into 'grounded'."""
    worst_real = min(max(h.relevance for h in search(q)) for q in LAY_GROUNDED)
    best_junk = max(max(h.relevance for h in search(q)) for q in UNGROUNDED)
    check(f"real questions clear the bar (worst {worst_real:.3f})", worst_real >= MIN_RELEVANCE * 1.2)
    check(f"junk stays under it (best {best_junk:.3f})", best_junk <= MIN_RELEVANCE * 0.8)


def test_every_hit_carries_its_authority_status() -> None:
    """CLAUDE.md §3: generation may never imply an obligation is live before its date.
    It can only do that if retrieval hands it the status."""
    hits: list[Hit] = search("obligations of a Data Fiduciary")
    check("retrieval returns hits", bool(hits), "empty — no grounded source")
    valid = {"in force", "effective 2026-11-13", "effective 2027-05-13"}
    for h in hits:
        check(
            f"authority_status on {h.citation}",
            h.authority_status in valid,
            f"got {h.authority_status!r}",
        )
        check(f"page on {h.citation}", isinstance(h.page, int) and h.page > 0, f"page={h.page}")


def test_penalties_are_not_advertised_as_in_force() -> None:
    """The penalty Schedule is `effective 2027-05-13`. If retrieval ever labels it
    'in force', marketing copy will tell readers they can be fined today. They cannot."""
    hits = search("penalty for a data breach under the DPDP Act")
    sched = [h for h in hits if h.citation == "DPDP Act 2023, Schedule"]
    check("penalty Schedule retrieved", bool(sched), "not in top-k")
    if sched:
        check(
            "penalty Schedule is NOT 'in force'",
            sched[0].authority_status == "effective 2027-05-13",
            f"got {sched[0].authority_status!r} — this would date-lie in published copy",
        )


def test_no_hindi_bleed_through_in_indexed_text() -> None:
    """The Rules PDF is bilingual. Devanagari in a payload means a corrupt chunk shipped."""
    # limit must cover the WHOLE collection: a hard-coded 200 would silently check only the
    # first page once the corpus outgrew it, and still report PASS on the chunks it never saw.
    total = qdrant().count(COLLECTION, exact=True).count
    points = qdrant().scroll(COLLECTION, limit=total, with_payload=True)[0]
    check("scrolled every indexed chunk", len(points) == total, f"{len(points)} of {total}")
    bad = [
        p.payload["citation"]
        for p in points
        if any("ऀ" <= ch <= "ॿ" for ch in p.payload["text"])
    ]
    check("no Devanagari in any indexed chunk", not bad, f"Hindi found in: {bad}")


def test_merge_hits_dedups_by_citation_keeping_max_relevance() -> None:
    """Pure logic, no network. The decomposed-query merge must keep ONE entry per provision, at
    its best relevance, most-relevant first — else a sub-query's weak hit could bury a strong
    hit for the same section."""
    def h(cite: str, rel: float) -> Hit:
        return Hit(cite, "in force", "x.pdf", 1, "t", rel, rel)

    out = merge_hits([[h("DPDP Act 2023, s.8", 0.5), h("DPDP Rules 2025, r.7", 0.3)],
                      [h("DPDP Act 2023, s.8", 0.9)]])
    cites = [x.citation for x in out]
    check("merge dedups by citation, relevance-ordered",
          cites == ["DPDP Act 2023, s.8", "DPDP Rules 2025, r.7"], f"got {cites}")
    check("merge keeps the max relevance per citation", out[0].relevance == 0.9, f"got {out[0].relevance}")


def test_cross_refs_only_add_provisions_the_hits_reference() -> None:
    """expand_refs must be a SUPERSET of bare search (it never drops a hit), CAPPED, and every
    provision it adds must be one the base hits actually cross-reference in their text — never
    an invention. Anything added is a real chunk, so cite_check still governs it downstream."""
    q = "obligations of a Data Fiduciary"
    base = search(q)
    expanded = search(q, expand_refs=True)
    base_cites = {h.citation for h in base}
    exp_cites = [h.citation for h in expanded]

    check("expand_refs keeps every base hit", base_cites <= set(exp_cites))
    check("expand_refs adds no duplicate citation", len(exp_cites) == len(set(exp_cites)),
          f"dupes in {exp_cites}")
    added = [c for c in exp_cites if c not in base_cites]
    check("cross-refs are capped at 6", len(added) <= 6, f"added {len(added)}: {added}")
    check("a grounded query stays grounded after expansion", is_grounded(expanded))

    by_cite, _ = _catalog()
    referenced = set().union(*(_referenced_handles(h.text) for h in base)) if base else set()
    for c in added:
        owned = set(by_cite[c][0])
        check(f"added {c} is genuinely referenced by a base hit", bool(owned & referenced),
              f"{c} owns {owned} — none appear as a cross-reference in the base hits")


# pytest bridge. check() COLLECTS failures instead of asserting, so under pytest every test
# in this file returns None and reports PASS no matter what failed — a broken retriever or a
# fabricated citation would come back green in CI. This is the one assert that makes the file
# honest to a runner other than the __main__ block below. Must sort LAST (pytest runs in
# definition order), hence the zz.
def test_zz_all_checks_passed() -> None:
    assert not FAILURES, f"{len(FAILURES)} check(s) failed: {FAILURES}"


if __name__ == "__main__":
    # skip the pytest bridge: FAILURES is already reported below, and re-raising it here
    # would replace the summary with a traceback.
    for t in [v for k, v in sorted(globals().items())
              if k.startswith("test_") and k != "test_zz_all_checks_passed"]:
        print(f"\n--- {t.__name__}")
        t()
    print(f"\n{'ALL PASS' if not FAILURES else str(len(FAILURES)) + ' FAILED: ' + str(FAILURES)}")
    sys.exit(1 if FAILURES else 0)
