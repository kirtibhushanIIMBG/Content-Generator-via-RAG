"""Phase 5 verification — cite_check must catch what generate() could only warn about, and
the graph must DISCARD a bad draft, redraft it against the specific failure, and refuse to
auto-pass one that never gets clean.

    python tests/test_cite_check.py            # offline (free) + one live graph run
    python tests/test_cite_check.py --offline  # no API calls, no cost

The retry loop is tested with a FAKE drafter (a scripted sequence of drafts), because the
thing under test is the graph's behaviour on failure — not the model's mood. The live run at
the end proves the real wiring holds.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import src.graph.pipeline as pipe  # noqa: E402
from src.generation.generate import DISCLAIMER, NO_SOURCE, Draft  # noqa: E402
from src.graph.cite_check import Report, check, is_claim, sentences  # noqa: E402
from src.retrieval.hybrid import Hit  # noqa: E402

FAILURES: list[str] = []


def check_(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else ': ' + detail}")
    if not ok:
        FAILURES.append(name)


def _hit(citation: str, status: str = "in force") -> Hit:
    return Hit(citation=citation, authority_status=status, source_ref="DPDP_Act_2023.pdf",
               page=7, text="Fake statutory text.", score=0.5, relevance=0.5)


HITS = [_hit("DPDP Act 2023, s.33"), _hit("DPDP Rules 2025, r.7", "effective 2027-05-13")]


def _draft(body: str, hits=HITS) -> Draft:
    return Draft(f"{body}\n\n{DISCLAIMER}", "anthropic", True, hits)


def test_a_sentence_split_survives_citations() -> None:
    """Citations are full of dots ("[DPDP Act 2023, s.8]") and would shred a naive splitter,
    which would then hand cite_check half-sentences to score."""
    s = sentences(_draft(
        "# Heading\n"
        "A Data Fiduciary must notify the Board [DPDP Rules 2025, r.7]. This matters.\n"
        "- Penalties reach Rs. 250 crore [DPDP Act 2023, s.33]."
    ).text)
    check_("heading is not a sentence", not any(x.startswith("#") for x in s), f"{s}")
    check_("split on terminators, not on citation dots", len(s) == 3, f"{len(s)}: {s}")
    check_("citation stays attached to its claim",
           any("r.7]" in x and "must notify" in x for x in s), f"{s}")
    check_("disclaimer is excluded", not any("legal advice" in x for x in s), f"{s}")


def test_a2_structure_is_not_an_uncited_claim() -> None:
    """The measured false positives — both of which no redraft could ever fix, so they would
    escalate a good draft to a human forever (live run 2026-07-14: 3 attempts, 73%, zero
    fabrications, every flagged item structural)."""
    d = _draft(
        "## How the penalty is determined\n"
        "**Penalty for failing to notify**\n"
        "The Board must consider the following factors [DPDP Act 2023, s.33]:\n"
        "- Whether the person took timely action to mitigate the breach's effects;\n"
        "- The nature of the personal data affected.\n"
    )
    r = check(d)
    flagged = " | ".join(r.unsupported)
    check_("a markdown heading is not a claim", "How the penalty" not in flagged, flagged)
    check_("a bold heading is not a claim", "Penalty for failing" not in flagged, flagged)
    check_("a bullet inherits its stem's citation", "timely action" not in flagged, flagged)
    check_("structure-only draft passes", r.ok, f"{r.traceability_score:.2f} {r.unsupported}")

    # ...but an uncited bullet under an UNCITED stem is still an uncited claim.
    r = check(_draft("The Rules require the following:\n- The Board must be notified.\n"))
    check_("a bullet under an uncited stem is still flagged", not r.ok, f"{r.unsupported}")

    # A bolded CLAIM is not a heading. If it were dropped as one, a draft could hide an
    # uncited claim from the checker simply by bolding it.
    r = check(_draft("**A Data Fiduciary must intimate the Board of every breach.**"))
    check_("a bolded claim sentence is still scored",
           any("intimate the Board" in s for s in r.unsupported), f"{r.unsupported}")


def test_a3_body_ignores_the_disclaimer_not_the_draft() -> None:
    """Draft.body() splits on the WHOLE disclaimer. Splitting on its '---' first line would
    drop every section after the model's first horizontal rule — silently, from the scoring."""
    d = _draft("First [DPDP Act 2023, s.33].\n\n---\n\nThe Board may impose a penalty.")
    check_("a '---' rule in the body does not truncate scoring",
           any("Board may impose" in s for s in sentences(d.text)), f"{sentences(d.text)}")
    check_("the disclaimer itself is still excluded",
           not any("legal advice" in s for s in sentences(d.text)))


def test_a4_subsection_citations_are_validated() -> None:
    """The drafter cites s.8(5) off a retrieved s.8 chunk — a MORE precise citation, not a
    fabrication, because it was shown the whole section. cite_supported accepts it when the
    sub-marker is genuinely in the chunk text, and still rejects an invented sub-section or a
    section that was never shown. This is the golden-rule gate, so assert the whole truth table,
    not one happy case."""
    from src.generation.generate import cite_supported
    s8 = Hit(citation="DPDP Act 2023, s.8", authority_status="in force",
             source_ref="DPDP_Act_2023.pdf", page=7, score=0.5, relevance=0.5,
             text="(1) A Data Fiduciary is responsible ... (5) shall protect personal data by "
                  "taking reasonable security safeguards ... (11) the last sub-section.")
    hits = [s8]
    for cite, want in [
        ("DPDP Act 2023, s.8", True),          # exact section match
        ("DPDP Act 2023, s.8(5)", True),       # real sub-section in the shown chunk
        ("DPDP Act 2023, s.8(1-5)", True),     # single-paren range: both endpoints present
        ("DPDP Act 2023, s.8(1)-(5)", True),   # TWO-paren range: both endpoints validated
        ("DPDP Act 2023, s.8(1)–(5)", True),   # en-dash range: normalized, both validated
        ("DPDP Act 2023, s.8(5)(b)", True),    # nested clause rests on a real top-level sub
        ("DPDP Act 2023, s.8(15)", False),     # INVENTED sub-section — no (15) in the text
        ("DPDP Act 2023, s.8(1-15)", False),   # single-paren range, invented endpoint
        ("DPDP Act 2023, s.8(1)-(15)", False), # two-paren range, invented endpoint (15)
        ("DPDP Act 2023, s.8(1)–(15)", False), # EN-DASH range, invented endpoint — audit hole:
                                               # dodged ASCII-only range detection, validated (1) alone
        ("DPDP Act 2023, s.8(1); DPDP Rules 2025, r.10(2)", False),  # MERGED bracket — audit
                                               # hole: first group validated, the rest rode through
        ("DPDP Act 2023, s.8(-)", False),      # vacuous range — audit hole: empty markers -> all([])
        ("DPDP Act 2023, s.8()-()", False),    # vacuous two-paren range
        ("DPDP Act 2023, s.27", False),        # section never retrieved
        ("DPDP Act 2023, s.27(1)", False),     # sub-section of an unshown section
    ]:
        check_(f"cite_supported({cite!r}) is {want}", cite_supported(cite, hits) is want)

    # CROSS-REFERENCE guard (audit-measured on the real corpus): s.2 has NO numbered
    # sub-sections; its only "(2)" lives inside "clause (a) of sub-section (2) of section 10".
    # A substring test validated the nonexistent s.2(2); _own_marker must not.
    s2 = Hit(citation="DPDP Act 2023, s.2", authority_status="in force",
             source_ref="DPDP_Act_2023.pdf", page=2, score=0.5, relevance=0.5,
             text='In this Act, "consent manager" means a person referred to in clause (a) '
                  "of sub-section (2) of section 10, and clauses (a) and (b) of section 5.")
    check_("cross-referenced marker does not validate a nonexistent sub-section",
           cite_supported("DPDP Act 2023, s.2(2)", [s2]) is False)
    check_("cross-referenced clause letters do not validate either",
           cite_supported("DPDP Act 2023, s.2(b)", [s2]) is False)

    # Sub-split chunk base: a chunk whose OWN citation carries the sub-ref accepts a deeper
    # clause when that clause marker is really in its text (was: unconditional false-reject).
    s87 = Hit(citation="DPDP Act 2023, s.8(7)", authority_status="in force",
              source_ref="DPDP_Act_2023.pdf", page=8, score=0.5, relevance=0.5,
              text="(7) A Data Fiduciary shall, by (a) erasing it, and (b) causing erasure.")
    check_("clause off a sub-split chunk validates against its text",
           cite_supported("DPDP Act 2023, s.8(7)(a)", [s87]) is True)
    check_("invented clause off a sub-split chunk still fails",
           cite_supported("DPDP Act 2023, s.8(7)(z)", [s87]) is False)

    # And the whole checker must agree: a draft citing a valid sub-section is NOT fabricated and
    # traces clean.
    d = Draft("A Data Fiduciary shall take reasonable security safeguards "
              "[DPDP Act 2023, s.8(5)].\n\n" + DISCLAIMER, "openai", True, hits)
    r = check(d)
    check_("valid sub-section draft is not fabricated", not r.fabricated, f"{r.fabricated}")
    check_("valid sub-section draft traces 100%", r.traceability_score == 1.0,
           f"{r.traceability_score}")


def test_a4c_subsection_within_a_split_chunks_range_validates() -> None:
    """The chunker slices an over-long section and names the slice by its SPAN — "s.6(1-8)".
    A draft citing one sub-section of that slice ("s.6(4)") is a MORE precise citation, not a
    fabrication. It must validate IFF the sub-section is inside the range AND really in the text,
    and must never leak a nested clause or an out-of-range sub-section through the range label.
    Golden-rule gate — assert the whole truth table."""
    from src.generation.generate import cite_supported
    # markers (1)-(8) are the slice's own; "(9)" appears ONLY as a cross-reference (out of span).
    s6 = Hit(citation="DPDP Act 2023, s.6(1-8)", authority_status="effective 2027-05-13",
             source_ref="DPDP_Act_2023.pdf", page=5, score=0.5, relevance=0.5,
             text="(1) consent shall be free and specific. (4) the Data Principal has the right "
                  "to withdraw her consent. (6) the Data Fiduciary shall cease processing. (8) the "
                  "Consent Manager shall be accountable. The withdrawal in sub-section (9) is dealt "
                  "with in a separate provision.")
    hits = [s6]
    for cite, want in [
        ("DPDP Act 2023, s.6(1-8)", True),    # exact slice cite
        ("DPDP Act 2023, s.6(4)", True),      # THE goal: surgical sub-section inside the slice
        ("DPDP Act 2023, s.6(1)", True),      # low endpoint
        ("DPDP Act 2023, s.6(8)", True),      # high endpoint
        ("DPDP Act 2023, s.6(9)", False),     # out of span AND only a cross-ref in the text
        ("DPDP Act 2023, s.6(10)", False),    # out of span
        ("DPDP Act 2023, s.6(0)", False),     # below span
        ("DPDP Act 2023, s.6(4)(a)", False),  # nested clause must NOT ride the range label through
        ("DPDP Act 2023, s.6", False),        # bare section is not a sub-section refinement
        ("DPDP Act 2023, s.7(4)", False),     # a different section entirely
    ]:
        check_(f"cite_supported({cite!r}) is {want}", cite_supported(cite, hits) is want)

    # A sub-section only validates against the slice that CONTAINS it: s.6(4) must not ride the
    # s.6(9) chunk (audit-shape: the wrong split leaking a neighbour's sub-section).
    s69 = Hit(citation="DPDP Act 2023, s.6(9)", authority_status="effective 2026-11-13",
              source_ref="DPDP_Act_2023.pdf", page=6, score=0.5, relevance=0.5,
              text="(9) Every Consent Manager shall be registered with the Board.")
    check_("a sub-section does not validate against the wrong slice",
           cite_supported("DPDP Act 2023, s.6(4)", [s69]) is False)


def test_a4b_subsection_citation_inherits_the_hits_effective_date() -> None:
    """Audit CRITICAL: date_honest matched citations by EXACT equality, so a draft citing the
    refinement r.7(1) of a future-dated r.7 chunk validated for traceability but slipped the
    date gate entirely — Report.ok=True on a draft implying a 2027 obligation is live today.
    A citation that RESTS ON a hit must inherit that hit's effective date."""
    r7 = Hit(citation="DPDP Rules 2025, r.7", authority_status="effective 2027-05-13",
             source_ref="DPDP_Rules_2025.pdf", page=3, score=0.5, relevance=0.5,
             text="(1) A Data Fiduciary shall intimate the Board. (2) Details within 72 hours.")
    undated = Draft("A Data Fiduciary must intimate the Board of every breach "
                    "[DPDP Rules 2025, r.7(1)].\n\n" + DISCLAIMER, "openai", True, [r7])
    r = check(undated)
    check_("sub-ref citation of a future provision WITHOUT the year fails date_honest",
           not r.date_ok and not r.ok, f"date_ok={r.date_ok} ok={r.ok}")
    check_("the feedback names the parent provision", "r.7" in r.date_why, f"{r.date_why!r}")

    # The date sentence carries its own citation — the checker's rule 3 demands one on every
    # legal-claim sentence, date restatements included (my first version of this test forgot
    # that and the checker rightly failed it at 50% traceability).
    dated = Draft("A Data Fiduciary must intimate the Board [DPDP Rules 2025, r.7(1)]. "
                  "Rule 7 takes effect on 13 May 2027 [DPDP Rules 2025, r.7(1)].\n\n"
                  + DISCLAIMER, "openai", True, [r7])
    check_("the same citation WITH the year passes", check(dated).ok is True)


def test_a5_plaintext_headings_are_not_claims() -> None:
    """The drafter writes section labels as BARE lines ('Effective date', 'Core security
    obligations') instead of '## ...'. They assert nothing but carry claim cue-words, and cost
    an unfixable redraft — grievance-90-days escalated on 'Effective date' alone at 89%.
    cite_check now treats a short, unterminated, uncited bare line as a heading — while a real
    claim (ends in '.') is still scored, so a genuine uncited claim can't hide as a 'heading'."""
    hits = [_hit("DPDP Act 2023, s.8")]
    d = Draft(
        "Core security obligations\n"
        "A Data Fiduciary must take reasonable security safeguards [DPDP Act 2023, s.8].\n"
        "Effective date\n\n" + DISCLAIMER, "openai", True, hits)
    r = check(d)
    check_("bare labels are not scored as uncited claims", not r.unsupported, f"{r.unsupported}")
    check_("the real cited claim still traces 100%", r.traceability_score == 1.0,
           f"{r.traceability_score}")

    # A FULL uncited sentence (ends in '.') must NOT be mistaken for a heading — still flagged.
    d2 = Draft("A Data Fiduciary must give notice to the Data Principal before any processing.\n\n"
               + DISCLAIMER, "openai", True, hits)
    check_("a full uncited claim sentence is still caught", check(d2).traceability_score < 0.9,
           f"{check(d2).traceability_score}")

    # Audit holes: a COLON-ended stem is an uncited CLAIM introducing bullets, not a label —
    # dropping it exempted the claim and orphaned its bullets' citation scope. And a short
    # line carrying a DIGIT ("...: 72 hours") asserts a time limit — a claim in label's clothes.
    from src.graph.cite_check import _is_heading
    check_("a colon-ended stem is NOT a heading",
           not _is_heading("The Board must consider the following factors:"))
    check_("a digit-bearing label is NOT a heading",
           not _is_heading("Breach notification deadline: 72 hours"))
    d3 = Draft("A Data Fiduciary must protect data [DPDP Act 2023, s.8].\n"
               "The Board must consider the following factors:\n"
               "- the nature, gravity and duration of the breach;\n\n" + DISCLAIMER,
               "openai", True, hits)
    check_("an uncited colon stem is scored and flagged", check(d3).traceability_score < 0.9,
           f"{check(d3).traceability_score}")


def test_b_claim_detection() -> None:
    for t in ["A Data Fiduciary must give notice.", "The Board may impose a penalty.",
              "Erasure is required within 3 years.", "Rule 7 applies to breaches."]:
        check_(f"claim: {t!r}", is_claim(t))
    for t in ["This matters for compliance teams.", "Here is what changes for Indian business.",
              "Certinal builds compliance software."]:
        check_(f"not a claim: {t!r}", not is_claim(t))


def test_c_report_catches_the_three_failures() -> None:
    clean = _draft(
        "A Data Fiduciary must intimate the Board of a breach [DPDP Rules 2025, r.7]; this "
        "takes effect on 13 May 2027. Penalties may reach Rs. 250 crore "
        "[DPDP Act 2023, s.33]. This is why breach readiness matters."
    )
    r = check(clean)
    check_("clean draft passes", r.ok, f"{r}")
    check_("clean draft traces 100%", r.traceability_score == 1.0, f"{r.traceability_score}")

    fab = _draft("Breach duties sit in [DPDP Act 2023, s.8], effective 2027. "
                 "Penalties may reach Rs. 250 crore [DPDP Act 2023, s.33].")
    r = check(fab)
    check_("fabricated citation is caught", r.fabricated == ["DPDP Act 2023, s.8"], f"{r.fabricated}")
    check_("fabricated draft fails", not r.ok)
    check_("feedback names the fabricated citation", "[DPDP Act 2023, s.8]" in r.feedback())
    # A claim whose ONLY citation is fabricated is not a supported claim.
    check_("a claim cited only to a fabricated provision is unsupported",
           any("s.8" in s for s in r.unsupported), f"{r.unsupported}")

    lie = _draft("A Data Fiduciary must intimate the Board of a breach [DPDP Rules 2025, r.7].")
    r = check(lie)
    check_("date-lie is caught (cites r.7, never says 2027)", not r.date_ok, f"{r.date_why}")
    check_("date-lie fails the report", not r.ok)
    check_("feedback names the date failure", "2027" in r.feedback(), r.feedback())

    thin = _draft(
        "A Data Fiduciary must publish the contact of its Data Protection Officer. "
        "Consent must be free, specific and informed. "
        "Penalties may reach Rs. 250 crore [DPDP Act 2023, s.33]."
    )
    r = check(thin)
    check_("uncited claims drag traceability below the gate",
           r.traceability_score < 0.9 and not r.ok, f"{r.traceability_score:.2f}")
    check_("feedback quotes the uncited sentences", "Data Protection Officer" in r.feedback())

    # The one that read as a clean 100% on the eval's fabrication gate: cite nothing, and you
    # can fabricate nothing. 700 words of sourceless law must never pass.
    naked = _draft("A Data Fiduciary must give notice before processing personal data. "
                   "The Board may impose penalties.")
    r = check(naked)
    check_("a draft with NO citations scores 0, not 100", r.traceability_score == 0.0 and not r.ok,
           f"{r.traceability_score}")


def test_d_graph_retries_then_escalates() -> None:
    """The behaviour generate() could not have: a failing draft is discarded and redrawn
    against its specific failure, and one that never gets clean is flagged, never passed."""
    bad = "Breach duties sit in [DPDP Act 2023, s.8], effective 2027."
    good = ("A Data Fiduciary must intimate the Board of a breach [DPDP Rules 2025, r.7]; "
            "this takes effect on 13 May 2027.")

    seen_feedback: list[str] = []
    seen_previous: list[str] = []

    def fake_drafts(*bodies):
        it = iter(bodies)

        def _draft_from(topic, hits, feedback="", previous="", word_count=None, style=""):
            seen_feedback.append(feedback)
            seen_previous.append(previous)
            return _draft(next(it), hits)
        return _draft_from

    real_retrieve, real_grounded, real_draft = pipe.retrieve_hits, pipe.is_grounded, pipe.draft_from
    pipe.retrieve_hits, pipe.is_grounded = lambda q, k=6: HITS, lambda h: True
    try:
        # Attempt 1 fabricates, attempt 2 is clean -> passes on the retry.
        seen_feedback.clear()
        pipe.draft_from = fake_drafts(bad, good)
        s = pipe.run("breach")
        check_("recovers on retry", s["review_status"] == "passed", f"{s['review_status']}")
        check_("took exactly 2 attempts", s["attempts"] == 2, f"{s['attempts']}")
        check_("first attempt got no feedback", seen_feedback[0] == "")
        check_("the retry was told WHAT was wrong",
               "DPDP Act 2023, s.8" in seen_feedback[1], seen_feedback[1][:120])
        # Blind regeneration does not converge (measured: 60% -> 61% -> 73%, never clean).
        # The retry must get its own draft back to revise, WITHOUT the appended disclaimer —
        # the model would echo it and generate() would append a second.
        check_("the retry revises the previous draft, not a blank page",
               bad in seen_previous[1], seen_previous[1][:80])
        check_("the previous draft is handed over without the disclaimer",
               "legal advice" not in seen_previous[1])

        # Never gets clean -> escalate. It must NOT auto-pass, and must not loop forever.
        seen_feedback.clear()
        pipe.draft_from = fake_drafts(bad, bad, bad)
        s = pipe.run("breach")
        check_("a never-clean draft escalates to a human",
               s["review_status"] == "needs_human", f"{s['review_status']}")
        check_("stops at MAX_ATTEMPTS (no infinite loop)",
               s["attempts"] == pipe.MAX_ATTEMPTS, f"{s['attempts']}")
        check_("the failing report is surfaced, not swallowed",
               s["report"].fabricated == ["DPDP Act 2023, s.8"])

        # Hybrid policy (2026-07-20): a coverage-only miss — nothing fabricated, dates honest,
        # just claims under the 0.9 bar — ships to the human IMMEDIATELY. The retry budget is
        # reserved for failures a reviewer might not catch; uncited sentences are ones they fix
        # faster than a second LLM call would.
        thin = ("A Data Fiduciary must publish the contact of its Data Protection Officer. "
                "Penalties may reach Rs. 250 crore [DPDP Act 2023, s.33].")
        pipe.draft_from = fake_drafts(thin, thin)  # second draft must never be requested
        s = pipe.run("dpo contact")
        check_("a coverage-only miss escalates WITHOUT a retry",
               s["review_status"] == "needs_human", f"{s['review_status']}")
        check_("coverage-only miss ships at attempt 1", s["attempts"] == 1, f"{s['attempts']}")
        check_("the uncited sentences are in the report for the reviewer",
               any("Data Protection Officer" in u for u in s["report"].unsupported),
               f"{s['report'].unsupported}")

        # ...but a DATE-LIE is a golden-rule failure and still gets the single repair attempt.
        lie = "A Data Fiduciary must intimate the Board of a breach [DPDP Rules 2025, r.7]."
        pipe.draft_from = fake_drafts(lie, good)
        s = pipe.run("breach duties")
        check_("a date-lie spends the retry and recovers",
               s["review_status"] == "passed", f"{s['review_status']}")
        check_("date-lie recovery took exactly 2 attempts", s["attempts"] == 2, f"{s['attempts']}")

        # Ungrounded: the gate must still kill it before any drafting.
        pipe.is_grounded = lambda h: False
        pipe.draft_from = fake_drafts(good)  # would raise StopIteration if ever called
        s = pipe.run("best biryani in Hyderabad")
        check_("ungrounded topic dies at the gate",
               s["review_status"] == "no_grounded_source", f"{s['review_status']}")
        check_("ungrounded: no draft was written", s["draft"].text == NO_SOURCE)
        check_("ungrounded: no LLM was called", s["attempts"] == 0 and s["draft"].provider == "none")
    finally:
        pipe.retrieve_hits, pipe.is_grounded, pipe.draft_from = real_retrieve, real_grounded, real_draft


def test_e_live_graph_end_to_end() -> None:
    """Real Qdrant + real Claude. Proves the wiring (state keys, edges, LangSmith tags) holds
    outside the fakes. Costs a few cents."""
    if "--offline" in sys.argv:
        print("SKIP  live graph run (--offline)")
        return
    s = pipe.run("What is the penalty for not reporting a personal data breach?")
    r: Report = s.get("report")
    check_("live run terminated with a verdict",
           s["review_status"] in ("passed", "needs_human", "no_grounded_source"),
           f"{s.get('review_status')}")
    check_("live run produced a report", r is not None or s["review_status"] == "no_grounded_source")
    if r:
        check_("a passed draft has zero fabricated citations",
               s["review_status"] != "passed" or not r.fabricated, f"{r.fabricated}")
        check_("a passed draft meets the traceability gate",
               s["review_status"] != "passed" or r.traceability_score >= 0.9,
               f"{r.traceability_score:.2f}")
        print(f"\n      review={s['review_status']} attempts={s['attempts']} "
              f"traceability={r.traceability_score:.0%} claims={r.claims} "
              f"fabricated={r.fabricated} provider={s['draft'].provider}")


def test_zz_all_checks_passed() -> None:
    assert not FAILURES, f"{len(FAILURES)} check(s) failed: {FAILURES}"


if __name__ == "__main__":
    for t in [v for k, v in sorted(globals().items())
              if k.startswith("test_") and k != "test_zz_all_checks_passed"]:
        print(f"\n--- {t.__name__}")
        t()
    print(f"\n{'ALL PASS' if not FAILURES else str(len(FAILURES)) + ' FAILED: ' + str(FAILURES)}")
    sys.exit(1 if FAILURES else 0)
