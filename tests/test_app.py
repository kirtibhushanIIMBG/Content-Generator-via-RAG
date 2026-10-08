"""Phase 4 gate: the deployed surface actually drives the pipeline, both ways.

Streamlit's own AppTest runs app.py in-process — real Qdrant, real LLM, real widgets. Two
cases, because the app has exactly two jobs and the dangerous one is the refusal: a UI that
rendered a draft for an ungrounded topic would silently break the golden rule the pipeline
enforces below it.

Run: venv/Scripts/python.exe -m tests.test_app     (~40s, hits the live APIs)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# AppTest runs app.py IN THIS PROCESS, so app.py's `from src...` imports resolve against OUR
# sys.path. Without the root on it, the app dies on import and the test sees an empty page —
# an IndexError on at.text_input[0], not a readable failure. Every other test file here does
# this; this one did not, so it only worked when launched with `-m` from the repo root.
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

# Absolute path, for the same reason: AppTest.from_file falls back to the CALLER's directory
# when the path does not resolve, so a bare "app.py" silently becomes tests/app.py.
APP = str(ROOT / "app.py")

GROUNDED = "What must a Data Fiduciary do when a personal data breach occurs?"
UNGROUNDED = "How do I fix my car engine?"

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  — ' + detail if detail and not ok else ''}")
    if not ok:
        FAILURES.append(name)


def _run(topic: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.text_input[0].set_value(topic)
    at.button[0].click().run()
    return at


def test_grounded_topic_renders_a_cited_draft_and_gates_it_on_a_human() -> None:
    """Phase 6 tightened this: a machine-PASSED draft is no longer downloadable on its own.
    The download is the only affordance that lets a draft leave the building, so it hangs off
    the human's approval, not the machine's (CLAUDE.md §3). This drives the real graph through
    a real interrupt and a real resume() — the one place that is checked against live APIs.

    It does NOT assume the machine passes the draft. Sonnet is nondeterministic and rejects
    sampling params, so cite_check genuinely escalates some runs (caught in the wild on
    2026-07-15: traceability 74% after 3 attempts). Asserting `passed` here would be asserting
    the model's mood. What must hold on EVERY run is the gate: not downloadable until a human
    approves — and if the machine escalated, not approvable without a written reason.
    """
    at = _run(GROUNDED)
    check("app raised no exception", not at.exception, str(at.exception))

    # Every markdown element, not just the first: on an escalated draft the "uncited claims"
    # expander renders before the body, so markdown[0] is not the draft.
    body = "\n".join(m.value for m in at.markdown)
    check("a grounded topic is not refused as ungrounded",
          not any("no grounded source" in e.value.lower() for e in at.error),
          str([e.value[:60] for e in at.error]))
    check("draft carries a bracketed citation", "[DPDP" in body)
    check("disclaimer rendered", "not legal advice" in body.lower())
    check("all 6 sources shown for verification",
          any(e.label.startswith("Sources retrieved (6)") for e in at.expander),
          str([e.label for e in at.expander]))

    check("review console shown, awaiting a human", bool(at.text_area))
    check("NOT downloadable before a human approves it", not at.download_button)

    escalated = any("do not publish" in e.value.lower() for e in at.error)
    if escalated:
        # The machine failed it, so approving is an override and the console demands a reason.
        # (That it REFUSES a note-less override is checked deterministically further down.)
        at.text_input(key="note").set_value("Spot-checked s.33 against DPDP_Act_2023.pdf p.21.")

    at.button(key="approve").click().run()  # the graph resumes and finalizes
    check("app raised no exception on approve", not at.exception, str(at.exception))
    check("approval is recorded on the page",
          any("Approved by a human" in m.value for m in at.success),
          str([m.value[:60] for m in at.success]))
    check("downloadable ONLY once approved", bool(at.download_button))
    # (That the console RETIRES after a verdict is checked deterministically below — a bare
    # at.run() here trips an AppTest widget-teardown bug, not an app bug.)
    print(f"\n      {len(body.split())} words rendered · machine verdict: "
          f"{'needs_human (approved as an override)' if escalated else 'passed'}")


def test_ungrounded_topic_refuses_and_drafts_nothing() -> None:
    at = _run(UNGROUNDED)
    check("app raised no exception", not at.exception, str(at.exception))
    check("refusal banner shown", bool(at.error))
    check("refusal says 'no grounded source'",
          bool(at.error) and "no grounded source" in at.error[0].value)
    check("nothing downloadable when refused", not at.download_button)
    # EVERY markdown element, not just the first: the sources expander renders markdown too
    # (it sits outside the grounded/ungrounded branch), so this passed only by the accident
    # that the draft happens to render before it. A draft leaking into any later element
    # would have gone unseen — which is the exact failure this check exists to catch.
    check("no draft body rendered anywhere",
          not any("[DPDP" in md.value for md in at.markdown),
          f"draft text leaked into {sum('[DPDP' in md.value for md in at.markdown)} element(s)")


def test_needs_human_draft_is_readable_but_not_downloadable() -> None:
    """The download button is the publish-adjacent affordance — the file someone pastes into
    a CMS. Offering it under a "do not publish" banner is the UI weakening the golden rule
    (human review before anything publishes), and that is exactly what the app did until the
    2026-07-14 audit. The reviewer still needs to READ the draft, so the body must render.

    Deterministic and free: pipeline.run is patched to return a canned needs_human state —
    AppTest executes app.py's imports at .run() time, so `from src.graph.pipeline import run`
    picks up the patch. Forcing a real needs_human out of the live model is not reliable."""
    import src.graph.pipeline as pipe
    from src.generation.generate import DISCLAIMER, Draft
    from src.graph.cite_check import Report
    from src.retrieval.hybrid import Hit

    hit = Hit(citation="DPDP Act 2023, s.33", authority_status="effective 2027-05-13",
              source_ref="DPDP_Act_2023.pdf", page=21,
              text="Fake statutory text.", score=0.5, relevance=0.5)
    fake_state = {
        "topic": "penalties", "k": 6, "hits": [hit], "attempts": 3,
        "draft": Draft(f"Penalties are severe [DPDP Act 2023, s.8].\n\n{DISCLAIMER}",
                       "anthropic", True, [hit]),
        "report": Report(traceability_score=0.5, fabricated=["DPDP Act 2023, s.8"],
                         unsupported=["Penalties are severe."], claims=2,
                         date_ok=True, date_why=""),
        "review_status": "needs_human",
    }

    real = pipe.run
    pipe.run = lambda topic, k=6: fake_state
    try:
        at = _run("penalties for breach")

        check("app raised no exception on needs_human", not at.exception, str(at.exception))
        check("do-not-publish banner shown",
              bool(at.error) and "do not publish" in at.error[0].value.lower(),
              at.error[0].value[:120] if at.error else "no error element")
        check("banner names the fabricated citation",
              bool(at.error) and "DPDP Act 2023, s.8" in at.error[0].value)
        check("draft still readable for the reviewer",
              any("[DPDP" in md.value for md in at.markdown))
        check("NOT downloadable under a do-not-publish banner", not at.download_button)

        # A human MAY override a failed check — they are the higher authority, and a real
        # citation hung on the wrong claim is exactly the failure only they can see. But an
        # override with no stated reason is indistinguishable from a mis-click, so the console
        # refuses it. (Phase 6.)
        check("a failed draft still gets a review console", bool(at.text_area))
        at.button(key="approve").click().run()
        check("approving a FAILED draft with no note is refused",
              any("override" in e.value.lower() for e in at.error),
              str([e.value[:70] for e in at.error]))
        check("and it stays undownloadable", not at.download_button)
    finally:
        pipe.run = real


def test_an_override_downloads_but_never_reads_like_a_clean_pass() -> None:
    """The nastiest combination, and the one the two-field design exists for: the MACHINE
    failed this draft and a HUMAN approved it anyway. Both facts must survive to the page.

    It downloads — the human is the higher authority, and a real citation hung on the wrong
    claim is precisely the failure only they can catch. But it must not wear the same green
    banner as a draft that passed cleanly, or the override is laundered into a pass and the
    audit trail dies at the UI."""
    import src.graph.pipeline as pipe
    from src.generation.generate import DISCLAIMER, Draft
    from src.graph.cite_check import Report
    from src.retrieval.hybrid import Hit

    hit = Hit(citation="DPDP Act 2023, s.33", authority_status="in force",
              source_ref="DPDP_Act_2023.pdf", page=21,
              text="Penalties.", score=0.9, relevance=0.9)
    approved_override = {
        "topic": "penalties", "k": 6, "hits": [hit], "attempts": 3, "thread_id": "t-override",
        "draft": Draft(f"Penalties are severe [DPDP Act 2023, s.8].\n\n{DISCLAIMER}",
                       "anthropic", True, [hit]),
        "report": Report(traceability_score=0.5, fabricated=["DPDP Act 2023, s.8"],
                         unsupported=["Penalties are severe."], claims=2,
                         date_ok=True, date_why=""),
        "review_status": "needs_human",      # the machine said no...
        "decision": "approved",              # ...the human said yes, on the record:
        "note": "Verified s.33 against DPDP_Act_2023.pdf p.21 myself.",
    }

    real = pipe.run
    pipe.run = lambda topic, k=6: approved_override
    try:
        at = _run("penalties for breach")
    finally:
        pipe.run = real

    check("app raised no exception on an override", not at.exception, str(at.exception))
    check("an approved draft IS downloadable, even over a failed check", bool(at.download_button))
    check("the banner says it OVERRODE a failed check",
          any("overriding a FAILED machine check" in m.value for m in at.success),
          str([m.value[:70] for m in at.success]))
    check("the reviewer's reason is on the page",
          any("p.21" in m.value for m in at.success))
    check("console retires once a verdict is in", not at.text_area)


def test_starts_with_no_secrets_file_at_all() -> None:
    """A fresh clone has NO .streamlit/secrets.toml — the file is gitignored. st.secrets does
    not return empty in that case, it RAISES StreamlitSecretNotFoundError, which crashed the
    app on startup before app.py guarded it. The other tests in this file cannot see that:
    they run from the repo root, where a (blank) placeholder happens to exist. Streamlit looks
    for secrets relative to the CWD, so chdir'ing away is what reproduces a clean checkout.
    """
    import os
    import tempfile

    cwd = os.getcwd()
    os.chdir(tempfile.mkdtemp())
    try:
        at = AppTest.from_file(APP, default_timeout=90).run()
        check("app starts with no secrets.toml present", not at.exception, str(at.exception))
        check("topic input still renders", bool(at.text_input))
    finally:
        os.chdir(cwd)


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
