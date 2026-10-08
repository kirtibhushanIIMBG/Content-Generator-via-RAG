"""The LangGraph pipeline (Phases 5–6) — retrieve -> draft -> cite_check -> human_review.

RUNTIME module (CLAUDE.md §3): hosted APIs only.

    retrieve ──(ungrounded)──────────────────────────────────> END   review="no_grounded_source"
       │ grounded
       v
    draft <──(fabrication/date-lie, one retry, with feedback)┐
       │                                                     │
       v                                                     │
    cite_check ──┬── golden-rule failure, retry left ────────┘
                 │   (a coverage-only miss skips the retry: needs_human at attempt 1)
                 ├── no_grounded_source (model refused) ───> END
                 └── passed | needs_human ─────────────> human_review
                                                              │  interrupt() — the graph STOPS
    human_review ──┬── approved ───────────────────────────> END   decision="approved"
       ^           ├── rejected ───────────────────────────> END   decision="rejected"
       │           ├── edited ────> apply_edit ─────────────┘      (re-check, no LLM)
       └───────────┴── anything else (invalid resume input) ─┘      re-ask

Phase 5 answered "does the draft cite what it was never shown": a failed draft is DISCARDED and
rewritten against its specific failure, and one that still fails after 2 retries is never
silently passed. But `cite_check` cannot see a citation that is REAL yet does not support the
claim it hangs off (docs/build-log.md §7, "known ceilings"). Nothing mechanical can. That is
why review is mandatory and why it lives HERE, inside the graph, rather than as a button in
app.py: Phase 8's publish_webhook attaches to the `approved` edge, so the only path from a
draft to the outside world runs through a human. A UI can be got wrong; an unreachable edge
cannot.

Two verdicts, two fields, deliberately not merged:
* `review_status` — the MACHINE's verdict (passed | needs_human | no_grounded_source).
* `decision`      — the HUMAN's verdict (approved | rejected). Publication gates on this one.
A human may approve a needs_human draft (they are the authority, and the ceiling above is
exactly the case only they can catch) — but then both fields record what happened, and the
override survives in the state instead of being laundered into a "passed".

Still not here, deliberately: the mode toggle (strict|marketing) and multi-format fan-out —
both route to format_per_platform, which does not exist. A marketing branch today would route
around cite_check to nothing at all.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from src.generation.generate import NO_SOURCE, Draft, draft_from, retrieve_hits, with_disclaimer
from src.graph.cite_check import Report, check
from src.retrieval.hybrid import TOP_K, Hit, is_grounded

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 2  # the first draft + 1 retry — and the retry is spent ONLY on a golden-rule
# failure (fabricated citation or date-lie); a coverage-only miss ships as needs_human at
# attempt 1 (human's speed/safety hybrid 2026-07-20, replacing the flat 2-retry loop of
# design §5.7). Detection is untouched: every draft is still checked, nothing auto-passes.

ReviewStatus = Literal["passed", "needs_human", "no_grounded_source"]
DECISIONS = ("approved", "rejected", "edited")  # everything else is invalid input


class State(TypedDict, total=False):
    topic: str
    k: int
    hits: list[Hit]
    draft: Draft
    report: Report
    feedback: str          # cite_check's verdict on the last attempt, fed to the redraft
    attempts: int
    review_status: ReviewStatus
    thread_id: str         # the paused review's handle — resume() needs it
    decision: str          # the HUMAN's verdict: approved | rejected | edited (in flight) | ""
    edit_text: str         # the reviewer's rewrite, awaiting apply_edit
    note: str              # why they decided that — the audit trail for an override
    word_count: int        # soft length target for draft() (None = STRICT_SYSTEM default)
    style: str             # STYLES preset for draft() ("" = STRICT_SYSTEM default prose)


def retrieve(s: State) -> State:
    hits = retrieve_hits(s["topic"], s.get("k") or TOP_K)
    if not is_grounded(hits):
        best = max((h.relevance for h in hits), default=0.0)
        log.info("ungrounded topic %r (best relevance %.3f) — refusing without an LLM call",
                 s["topic"], best)
        return {"hits": hits, "draft": Draft(NO_SOURCE, "none", False, hits),
                "review_status": "no_grounded_source"}
    return {"hits": hits}


def draft(s: State) -> State:
    n = s.get("attempts", 0) + 1
    fb = s.get("feedback") or ""
    prev = s["draft"].body() if fb and s.get("draft") else ""  # body(): the disclaimer is
    if fb:                                                     # re-appended by draft_from
        log.warning("redraft %d/%d — previous draft failed cite_check:\n%s", n, MAX_ATTEMPTS, fb)
    return {"draft": draft_from(s["topic"], s["hits"], fb, prev, s.get("word_count"),
                                s.get("style") or ""),
            "attempts": n}


def cite_check(s: State) -> State:
    """Verify, and decide the verdict HERE. A conditional edge cannot write state, so if the
    'out of retries' decision lived in the edge, the escalated run would end with no
    review_status at all — and a caller reading it would see None, not "needs_human"."""
    d: Draft = s["draft"]
    # The model can judge its own sources insufficient (STRICT_SYSTEM rule 5). That is a
    # refusal, not a bad draft: there is nothing to verify and nothing a redraft would fix.
    if not d.grounded:
        return {"review_status": "no_grounded_source"}

    r = check(d)
    log.info("cite_check: traceability=%.0f%% (%d claims) fabricated=%s date_ok=%s",
             r.traceability_score * 100, r.claims, r.fabricated, r.date_ok)
    if r.ok:
        return {"report": r, "review_status": "passed", "feedback": ""}
    # The single retry is spent ONLY on a golden-rule failure — a fabricated citation or a
    # date-lie — the failures a reviewer might not catch and that must never ship. A
    # coverage-only miss (claims under the 0.9 bar, nothing invented, dates honest) escalates
    # immediately with the uncited sentences in the report: the reviewer can cite-or-delete
    # those faster than a second LLM call can, and the redraft loop was the pipeline's main
    # latency (measured P50 19s -> 39.6s when every failure looped).
    serious = bool(r.fabricated) or not r.date_ok
    if serious and s["attempts"] < MAX_ATTEMPTS:
        log.warning("cite_check: golden-rule failure (fabricated=%s date_ok=%s) — spending "
                    "the single retry", r.fabricated, r.date_ok)
        return {"report": r, "feedback": r.feedback()}
    log.error(
        "cite_check FAILED (attempt %d, serious=%s) — escalating to a human, NOT auto-passing. "
        "traceability=%.0f%% fabricated=%s date_ok=%s",
        s["attempts"], serious, r.traceability_score * 100, r.fabricated, r.date_ok,
    )
    return {"report": r, "feedback": r.feedback(), "review_status": "needs_human"}


def human_review(s: State) -> State:
    """The mandatory gate (CLAUDE.md §3, design §5.9). interrupt() STOPS the graph here and
    hands the packet below to whatever is driving it; the run resumes only on a human verdict.

    Nothing is decided in this node. The verdict is validated in the EDGE (_after_review), per
    the pipeline contract — a while-loop in here would spin on bad input with the graph's own
    state machine looking on, and could not be tested without driving the loop."""
    d: Draft = s["draft"]
    r: Report | None = s.get("report")
    got = interrupt({
        "topic": s["topic"],
        "review_status": s["review_status"],          # what the machine thinks
        "draft": d.text,
        "traceability": r.traceability_score if r else None,
        "fabricated": r.fabricated if r else [],
        # The reviewer's job is to check claims against the PDFs, so hand them the page numbers.
        "sources": [{"citation": h.citation, "source_ref": h.source_ref, "page": h.page,
                     "authority_status": h.authority_status} for h in d.hits],
    })
    got = got if isinstance(got, dict) else {}
    return {"decision": str(got.get("decision") or ""),
            "edit_text": str(got.get("text") or ""),
            "note": str(got.get("note") or "")}


def apply_edit(s: State) -> State:
    """A human edit is RE-CHECKED, never re-drafted: no LLM call, and `attempts` is untouched
    (the retry budget belongs to the model's failures, not the human's edits).

    Re-checked, though — not trusted. A reviewer fixing a flagged sentence pastes citations by
    hand, and a hand-typed citation is exactly as capable of naming a provision that was never
    retrieved as the model's was. It faces the same deterministic check the draft faced, and
    the machine verdict is recomputed from the edited text: a human who fixes a needs_human
    draft turns it green, and one who breaks a passing draft turns it red."""
    # with_disclaimer(), not a split() on the exact text: a reviewer who RETYPES the disclaimer
    # rather than leaving it verbatim is invisible to an exact split, and their copy then lands
    # inside the body cite_check scores — where it is flagged as an uncited legal claim that no
    # edit can fix (measured; see generate.with_disclaimer).
    d = replace(s["draft"], text=with_disclaimer(s["edit_text"]))
    r = check(d)
    log.info("human edit re-checked: traceability=%.0f%% (%d claims) fabricated=%s",
             r.traceability_score * 100, r.claims, r.fabricated)
    return {"draft": d, "report": r, "decision": "",
            "review_status": "passed" if r.ok else "needs_human"}


def _after_retrieve(s: State) -> Literal["draft", "__end__"]:
    return END if s.get("review_status") else "draft"


def _after_cite_check(s: State) -> Literal["draft", "human_review", "__end__"]:
    # cite_check sets review_status on every terminal verdict. No verdict yet means retries
    # remain. A verdict of no_grounded_source is a refusal: there is no draft to review.
    status = s.get("review_status")
    if not status:
        return "draft"
    return END if status == "no_grounded_source" else "human_review"


def _after_review(s: State) -> Literal["apply_edit", "human_review", "__end__"]:
    """Validate the resume input HERE, in the edge (CLAUDE.md §8). Anything that is not a real
    verdict — a typo, a stale payload, a client that resumed with None — routes back to
    human_review, which interrupts again and asks. It is never read as consent."""
    d = s.get("decision")
    if d in ("approved", "rejected"):
        return END
    if d == "edited" and s.get("edit_text", "").strip():
        return "apply_edit"
    log.warning("invalid review input %r — re-asking the human, NOT proceeding", d)
    return "human_review"


# The checkpointed state carries our own dataclasses (Hit, Draft, Report), and langgraph today
# deserializes ANY type from a checkpoint with only a warning — a default it says it will BLOCK
# in a future version. requirements.txt is unpinned and the app is already live, so that flip
# would arrive on Streamlit Cloud as somebody else's release and break resume() — i.e. the
# review console — in production, not here. Naming the three types explicitly is both the
# forward-compatible posture and the safe one (an allowlist, not "deserialize anything").
# Verified by running the suite under LANGGRAPH_STRICT_MSGPACK=true.
SERDE = JsonPlusSerializer(allowed_msgpack_modules=[
    ("src.retrieval.hybrid", "Hit"),
    ("src.generation.generate", "Draft"),
    ("src.graph.cite_check", "Report"),
])


def _build():
    g = StateGraph(State)
    g.add_node("retrieve", retrieve)
    g.add_node("draft", draft)
    g.add_node("cite_check", cite_check)
    g.add_node("human_review", human_review)
    g.add_node("apply_edit", apply_edit)
    g.add_edge(START, "retrieve")
    g.add_conditional_edges("retrieve", _after_retrieve)
    g.add_edge("draft", "cite_check")
    g.add_conditional_edges("cite_check", _after_cite_check)
    g.add_conditional_edges("human_review", _after_review)
    g.add_edge("apply_edit", "human_review")  # an edit is reviewed again, by the same human
    # ponytail: InMemorySaver — a paused review dies with the process (Streamlit Cloud sleeps
    # after ~12h idle). That is survivable because a lost review loses no published work, only
    # an unfinished draft, and resume() REFUSES a dead thread rather than pretending. Swap for
    # a Postgres/SQLite saver the day reviews must outlive a restart (a review queue, Phase 8+).
    return g.compile(checkpointer=InMemorySaver(serde=SERDE))


GRAPH = _build()


def _after_cite_check_headless(s: State) -> Literal["draft", "__end__"]:
    # Same as _after_cite_check, but EVERY terminal verdict ends the graph — there is no
    # human_review node. No verdict yet means retries remain.
    return "draft" if not s.get("review_status") else END


def _build_headless():
    """retrieve -> draft -> cite_check -> END. The SAME nodes as the reviewed graph, so the
    grounding gate and the cite_check retry loop are byte-for-byte identical — it just stops at
    the machine verdict instead of pausing for a human.

    For the n8n/API flow (the Google Doc is the review surface, design decision 2026-07-15): the
    caller wants the draft plus its `review_status` in one synchronous call, and the human review
    happens later, in Docs. Reusing the reviewed graph and reading its pre-interrupt state would
    work, but every call would strand a paused thread in the checkpointer — a slow leak in a
    long-lived API. This graph has no checkpointer and no interrupt, so there is nothing to leak
    and nothing to resume."""
    g = StateGraph(State)
    g.add_node("retrieve", retrieve)
    g.add_node("draft", draft)
    g.add_node("cite_check", cite_check)
    g.add_edge(START, "retrieve")
    g.add_conditional_edges("retrieve", _after_retrieve)
    g.add_edge("draft", "cite_check")
    g.add_conditional_edges("cite_check", _after_cite_check_headless)
    return g.compile()


HEADLESS = _build_headless()


def run_headless(topic: str, k: int = TOP_K, word_count: int | None = None,
                 style: str = "") -> State:
    """Topic in, verified draft out — NO human-review pause. Returns the machine verdict for a
    caller that reviews downstream (the RAG API; the Google Doc is the review surface).

    Same trust contract as run(): `review_status` is 'passed' (machine-verified — still not
    human-approved), 'needs_human' (failed verification), or 'no_grounded_source'. The API must
    carry that status into the Doc so the reviewer sees it; a needs_human draft is NOT clean.

    `style` is a generate.STYLES preset ("" = default prose). It shapes the DRAFT prompt only —
    retrieval sees the bare topic, and cite_check applies unchanged."""
    return HEADLESS.invoke(
        {"topic": topic, "k": k, "attempts": 0, "word_count": word_count, "style": style},
        config={"tags": ["api", "strict", "headless"], "run_name": "dpdp_headless"},  # LangSmith
    )


def _cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id},
            "tags": ["phase6", "strict"], "run_name": "dpdp_strict"}  # LangSmith


def run(topic: str, k: int = TOP_K, thread_id: str = "") -> State:
    """Topic in, verified draft out — PAUSED at human_review, awaiting resume().

    `review_status` is the machine verdict a caller may trust: 'passed' (machine-verified),
    'needs_human' (failed verification), 'no_grounded_source' (nothing bears on it). It is NOT
    permission to publish — only `decision == "approved"`, set by resume(), is that.
    """
    thread_id = thread_id or uuid4().hex
    return GRAPH.invoke({"topic": topic, "k": k, "attempts": 0, "thread_id": thread_id},
                        config=_cfg(thread_id))


def resume(thread_id: str, decision: str, text: str = "", note: str = "") -> State:
    """Deliver the human's verdict to the paused graph.

    The guard is not ceremony. LangGraph does NOT raise when you resume a thread whose
    checkpoint is gone (measured on langgraph 1.2.9): it runs the graph from START with an
    empty input and DISCARDS the resume value. In this pipeline that means a reviewer's
    "Approve" click on a restarted app would silently kick off a fresh retrieve+draft and
    approve nothing, while the UI reported success. Fail loudly instead (CLAUDE.md §1).
    """
    snap = GRAPH.get_state(_cfg(thread_id))
    if not snap.values:
        raise LookupError(
            f"review thread {thread_id!r} is gone — the app restarted and the paused draft "
            "went with it. Nothing was approved or published. Re-run the topic."
        )
    if not snap.next:  # already finalized: a double-click, or a stale browser tab resubmitting
        log.warning("thread %s is already %r — ignoring a second %r",
                    thread_id, snap.values.get("decision"), decision)
        return {**snap.values, "thread_id": thread_id}

    log.info("human decision on %s: %s%s", thread_id, decision, f" — {note}" if note else "")
    return GRAPH.invoke(Command(resume={"decision": decision, "text": text, "note": note}),
                        config=_cfg(thread_id))


if __name__ == "__main__":  # python -m src.graph.pipeline "breach duties"
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    topic = " ".join(sys.argv[1:]) or "What is the penalty for not reporting a data breach?"
    s = run(topic)
    r: Report | None = s.get("report")
    print(f"\nreview_status={s['review_status']}  attempts={s['attempts']}  "
          f"provider={s['draft'].provider}"
          + (f"  traceability={r.traceability_score:.0%}  fabricated={r.fabricated}" if r else ""))
    print()
    print(s["draft"].text)
    if s.get("__interrupt__"):  # the graph is PAUSED at human_review; app.py drives resume()
        print(f"\n-- paused for human review (thread {s['thread_id']}) — nothing may publish "
              "until resume() carries an approval.")
