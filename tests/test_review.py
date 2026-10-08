"""Phase 6 gate: nothing reaches a human's clipboard that a human did not approve.

The whole point of the review node is that it is UNSKIPPABLE, so these tests attack the ways
it could be skipped: by the graph running past it, by a bad resume value being read as
consent, by a rejection quietly finalizing anyway, by an edit smuggling in an uncited claim
or dropping the disclaimer, or by a lost checkpoint swallowing the verdict and reporting
success.

Free and deterministic: `retrieve_hits` and `draft_from` are patched on the pipeline module, so not
one API call is made and every verdict below is a property of the graph, not of the weather at
Anthropic. The live end-to-end path is covered by tests/test_app.py.

Run: venv/Scripts/python.exe -m tests.test_review     (~1s, no LLM/Qdrant call)

LangSmith still traces the graph, so on the Zscaler build machine pass REQUESTS_CA_BUNDLE too
(docs/system-design.md §5.4) or tolerate its retry noise on stderr — no check here depends on it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.graph.pipeline as pipe  # noqa: E402
from src.generation.generate import DISCLAIMER, Draft  # noqa: E402
from src.retrieval.hybrid import Hit  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  — ' + detail if detail and not ok else ''}")
    if not ok:
        FAILURES.append(name)


# Two real provisions, one of them not yet in force — so the authority-status flag and the
# date-honesty rule are both live in these fixtures rather than theoretical.
HITS = [
    Hit(citation="DPDP Act 2023, s.33", authority_status="in force",
        source_ref="DPDP_Act_2023.pdf", page=21, text="Penalties.", score=0.9, relevance=0.9),
    Hit(citation="DPDP Rules 2025, r.7", authority_status="effective 2027-05-13",
        source_ref="DPDP_Rules_2025.pdf", page=3, text="Breach intimation.",
        score=0.8, relevance=0.8),
]
CLEAN = f"The Board may impose a penalty [DPDP Act 2023, s.33].\n\n{DISCLAIMER}"

CALLS = {"draft_from": 0}


def _install(body: str = CLEAN):
    """Patch the pipeline's retrieval and drafting. Returns the real pair for restoration."""
    real = (pipe.retrieve_hits, pipe.draft_from)

    def fake_draft_from(topic, hits, feedback="", previous="", word_count=None, style=""):
        CALLS["draft_from"] += 1
        return Draft(body, "anthropic", True, list(hits))

    pipe.retrieve_hits = lambda q, k=6: list(HITS)
    pipe.draft_from = fake_draft_from
    return real


def _paused(s: dict) -> bool:
    """Is the graph stopped at human_review, waiting on a person?"""
    return bool(s.get("__interrupt__"))


def test_the_graph_stops_at_the_human_and_does_not_run_past_it() -> None:
    """A machine-PASSED draft is still not a published draft. The run must halt."""
    real = _install()
    try:
        s = pipe.run("penalties for a breach")
    finally:
        pipe.retrieve_hits, pipe.draft_from = real

    check("machine verdict is 'passed'", s["review_status"] == "passed", s["review_status"])
    check("graph PAUSED at human_review", _paused(s))
    check("no human decision yet", not s.get("decision"), repr(s.get("decision")))
    check("a thread handle came back to resume with", bool(s.get("thread_id")))

    packet = s["__interrupt__"][0].value
    check("reviewer is handed the draft", "[DPDP Act 2023, s.33]" in packet["draft"])
    check("reviewer is handed the machine verdict", packet["review_status"] == "passed")
    # Without source_ref and page, "verify it against the PDF" is an instruction with no way
    # to follow it — this is the field that makes review a 30-second job (CLAUDE.md §7).
    check("every source carries source_ref + page",
          all(src["source_ref"] and src["page"] for src in packet["sources"]),
          str(packet["sources"]))
    check("the not-yet-in-force provision is flagged to the reviewer",
          any(src["authority_status"] == "effective 2027-05-13" for src in packet["sources"]))


def test_approve_finalizes_and_reject_never_does() -> None:
    real = _install()
    try:
        a = pipe.run("penalties")
        a = pipe.resume(a["thread_id"], "approved", note="checked s.33 on p.21")
        r = pipe.run("penalties")
        r = pipe.resume(r["thread_id"], "rejected", note="tone is wrong")
    finally:
        pipe.retrieve_hits, pipe.draft_from = real

    check("approved: decision recorded", a.get("decision") == "approved", repr(a.get("decision")))
    check("approved: graph finished", not _paused(a))
    check("approved: the note survives as the audit trail", "p.21" in a.get("note", ""))

    check("rejected: decision recorded", r.get("decision") == "rejected", repr(r.get("decision")))
    check("rejected: graph finished", not _paused(r))
    # The one that matters: a rejection must not leave anything that a publish path could read
    # as consent. decision is that gate — review_status stays "passed" because the MACHINE did
    # pass it, and laundering the human's no into the machine's field would lose both facts.
    check("rejected content NEVER finalizes as approved", r.get("decision") != "approved")


def test_a_bad_resume_value_is_never_read_as_consent() -> None:
    """The resume value comes from outside the graph. A typo, a stale payload, a client that
    resumes with None — none of them may fall through to publication. The edge validates."""
    real = _install()
    try:
        s = pipe.run("penalties")
        tid = s["thread_id"]
        for bad in ("maybe", "", "APPROVED", "approve", None, "publish"):
            out = pipe.resume(tid, bad)  # type: ignore[arg-type]
            check(f"invalid input {bad!r} -> re-asks the human, does not proceed",
                  _paused(out) and out.get("decision") != "approved",
                  f"paused={_paused(out)} decision={out.get('decision')!r}")
        # ...and the thread is still live afterwards: a fat-fingered click must not destroy
        # the review, it must just ask again.
        out = pipe.resume(tid, "approved", note="ok")
        check("still approvable after the bad inputs", out.get("decision") == "approved")
    finally:
        pipe.retrieve_hits, pipe.draft_from = real


def test_an_edit_is_re_checked_not_re_drafted() -> None:
    real = _install()
    CALLS["draft_from"] = 0
    try:
        s = pipe.run("penalties")
        after_draft = CALLS["draft_from"]

        # The reviewer pastes in a citation for a provision that was NEVER retrieved — the
        # exact failure cite_check exists to catch, now arriving from a human's keyboard
        # instead of the model's. It must be caught all the same.
        s = pipe.resume(s["thread_id"], "edited",
                        text="Consent is required [DPDP Act 2023, s.6]. Fines apply.")
        check("edit cost ZERO LLM calls", CALLS["draft_from"] == after_draft,
              f"{CALLS['draft_from']} vs {after_draft}")
        check("edit does not spend the model's retry budget", s["attempts"] == 1, str(s["attempts"]))
        check("a human-pasted fabricated citation is caught",
              s["report"].fabricated == ["DPDP Act 2023, s.6"], str(s["report"].fabricated))
        check("machine verdict flips to needs_human on a bad edit",
              s["review_status"] == "needs_human", s["review_status"])
        check("still paused — the reviewer sees their own edit's verdict", _paused(s))
        check("the disclaimer the human deleted is put back", DISCLAIMER in s["draft"].text)

        # Now they fix it. The same deterministic check must clear it.
        s = pipe.resume(s["thread_id"], "edited",
                        text=f"The Board may impose a penalty [DPDP Act 2023, s.33].\n\n{DISCLAIMER}")
        check("a corrected edit turns the verdict green again", s["review_status"] == "passed",
              s["review_status"])
        check("no duplicate disclaimer when the human kept it",
              s["draft"].text.count("not legal advice") == 1)

        # THE property, and the one an over-clever fix broke: an edit is never silently
        # truncated. A reviewer may write BELOW the disclaimer (it sits mid-textarea if they
        # were handed the whole draft) or merely mention its opening words. Cutting the text at
        # that phrase deleted their correction and cite_check then graded a draft that was not
        # what the human wrote — silent data loss on the one path CLAUDE.md calls mandatory.
        # Only an exact TRAILING copy — the one the code itself appended — may be removed.
        s = pipe.resume(s["thread_id"], "edited", text=(
            f"The Board may impose a penalty [DPDP Act 2023, s.33].\n\n{DISCLAIMER}\n\n"
            "Addendum: erasure is also required [DPDP Act 2023, s.33]."))
        check("an edit written BELOW the disclaimer is not silently dropped",
              "Addendum" in s["draft"].text, repr(s["draft"].text[-200:]))
        check("the disclaimer still ends the draft", s["draft"].text.endswith(DISCLAIMER))
        # The text now carries the disclaimer twice — deliberately. The stray copy is mid-body,
        # and guessing where it ends is what deleted the addendum above. So it stays, and it is
        # LOUD: cite_check scores it as an uncited claim and the draft escalates to a human,
        # rather than quietly publishing a doubled disclaimer.
        check("a stray mid-body disclaimer escalates instead of publishing quietly",
              s["review_status"] == "needs_human", s["review_status"])

        # The ordinary case: a reviewer returns the draft with the disclaimer untouched at the
        # end (or app.py hands back body() alone). Exactly one, appended by the code.
        s = pipe.resume(s["thread_id"], "edited", text=(
            f"The Board may impose a penalty [DPDP Act 2023, s.33].\n\n{DISCLAIMER}"))
        check("a verbatim TRAILING disclaimer is not duplicated",
              s["draft"].text.count("This content was AI-assisted") == 1,
              f"{s['draft'].text.count('This content was AI-assisted')} copies")
        check("...and that draft is clean again", s["review_status"] == "passed",
              f"{s['review_status']} — {s['report'].unsupported}")

        s = pipe.resume(s["thread_id"], "edited", text=(
            "This content was AI-assisted, so check it. "
            "The Board may impose a penalty [DPDP Act 2023, s.33]."))
        check("a body that merely MENTIONS the disclaimer phrase is not truncated",
              "The Board may impose a penalty" in s["draft"].text, repr(s["draft"].text[:80]))

        s = pipe.resume(s["thread_id"], "approved")
        check("the human's words are what got approved",
              "[DPDP Act 2023, s.33]" in s["draft"].text and s["decision"] == "approved")
    finally:
        pipe.retrieve_hits, pipe.draft_from = real


def test_a_lost_review_thread_fails_loudly_instead_of_approving_nothing() -> None:
    """Measured on langgraph 1.2.9: resuming a thread whose checkpoint is gone does NOT raise
    — it re-runs the graph from START and DISCARDS the resume value. On Streamlit Cloud (which
    sleeps after ~12h and restarts empty) that is a reviewer clicking Approve, being told it
    worked, and having approved nothing at all. resume() must refuse."""
    real = _install()
    CALLS["draft_from"] = 0
    try:
        try:
            pipe.resume("a-thread-that-never-existed", "approved")
            check("dead thread raises instead of silently re-running", False, "no exception")
        except LookupError as e:
            check("dead thread raises instead of silently re-running", True)
            check("the error tells the human nothing was approved",
                  "approved" in str(e).lower() and "re-run" in str(e).lower(), str(e))
        check("and it did NOT secretly start a fresh draft", CALLS["draft_from"] == 0,
              f"{CALLS['draft_from']} draft calls")
    finally:
        pipe.retrieve_hits, pipe.draft_from = real


def test_headless_reaches_a_verdict_and_never_pauses() -> None:
    """run_headless() is what the RAG API calls (the Google Doc is the review surface, not an
    interrupt). It must reach a machine verdict and NEVER pause — a paused API call would hang
    n8n waiting for a resume that never comes — and it must thread word_count to the drafter."""
    real = _install()
    seen = {}
    base = pipe.draft_from  # the fake from _install, wrapped to capture word_count

    def capture(topic, hits, feedback="", previous="", word_count=None, style=""):
        seen["word_count"] = word_count
        return base(topic, hits, feedback, previous)
    pipe.draft_from = capture
    try:
        s = pipe.run_headless("penalties", word_count=400)
    finally:
        pipe.retrieve_hits, pipe.draft_from = real

    check("headless reaches a verdict", s.get("review_status") == "passed", str(s.get("review_status")))
    check("headless NEVER pauses (no interrupt for n8n to hang on)", "__interrupt__" not in s)
    check("headless leaves no decision to make", not s.get("decision"))
    check("word_count is threaded to the drafter", seen.get("word_count") == 400,
          repr(seen.get("word_count")))


def test_headless_refusal_still_refuses_without_an_llm() -> None:
    real = (pipe.retrieve_hits, pipe.draft_from)
    pipe.retrieve_hits = lambda q, k=6: [
        Hit(citation="DPDP Act 2023, s.1", authority_status="in force",
            source_ref="DPDP_Act_2023.pdf", page=1, text="Short title.", score=0.1, relevance=0.05),
    ]
    pipe.draft_from = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not draft"))
    try:
        s = pipe.run_headless("best biryani in Hyderabad")
    finally:
        pipe.retrieve_hits, pipe.draft_from = real
    check("headless refuses an ungrounded topic", s["review_status"] == "no_grounded_source")
    check("headless refusal called no LLM", s["draft"].provider == "none")


def test_a_second_click_cannot_flip_a_finished_verdict() -> None:
    """A stale browser tab resubmitting, or a double-click, must not turn an approval into a
    rejection (or vice versa) after the fact."""
    real = _install()
    try:
        s = pipe.run("penalties")
        s = pipe.resume(s["thread_id"], "approved", note="first")
        again = pipe.resume(s["thread_id"], "rejected", note="stale tab")
    finally:
        pipe.retrieve_hits, pipe.draft_from = real

    check("a second, contradictory verdict is ignored", again.get("decision") == "approved",
          repr(again.get("decision")))
    check("the original note stands", again.get("note") == "first", repr(again.get("note")))


def test_a_refusal_is_not_sent_for_review() -> None:
    """no_grounded_source drafted nothing. There is nothing to approve, so the graph must END,
    not park an empty draft in front of a human and invite a click."""
    real = (pipe.retrieve_hits, pipe.draft_from)
    pipe.retrieve_hits = lambda q, k=6: [
        Hit(citation="DPDP Act 2023, s.1", authority_status="in force",
            source_ref="DPDP_Act_2023.pdf", page=1, text="Short title.",
            score=0.1, relevance=0.05),  # below MIN_RELEVANCE: the gate refuses
    ]
    try:
        s = pipe.run("best biryani in Hyderabad")
    finally:
        pipe.retrieve_hits, pipe.draft_from = real

    check("refusal recorded", s["review_status"] == "no_grounded_source", s["review_status"])
    check("graph ENDED — no review interrupt on a refusal", not _paused(s))
    check("no decision to make", not s.get("decision"))


def test_zz_all_checks_passed() -> None:
    assert not FAILURES, f"{len(FAILURES)} check(s) failed: {FAILURES}"


if __name__ == "__main__":
    for t in [v for k, v in sorted(globals().items())
              if k.startswith("test_") and k != "test_zz_all_checks_passed"]:
        print(f"\n--- {t.__name__}")
        t()
    print(f"\n{'ALL PASS' if not FAILURES else str(len(FAILURES)) + ' FAILED: ' + str(FAILURES)}")
    sys.exit(1 if FAILURES else 0)
