"""Streamlit entrypoint — the deployed surface of the DPDP RAG content farm (Phases 4 & 6).

Thin by design: topic in -> src.graph.pipeline.run() -> draft + the sources it stands on ->
the human review console. No logic lives here that isn't about display; the golden rules
(grounding gate, disclaimer, failover, and now the review gate) are enforced in src/, so this
file cannot weaken them by getting the UI wrong. The console below only DELIVERS a verdict to
the paused graph — it does not decide anything, and there is no path around it: publication
hangs off the graph's `approved` edge, not off a button here.

Secrets: on Streamlit Cloud they arrive in st.secrets, but every module downstream reads
os.getenv (they must also run in CI and on the build machine). Copying them across before
the first API call keeps one secret-reading path for all environments.
"""

from __future__ import annotations

import os
import time

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

st.set_page_config(page_title="DPDP Content Farm", page_icon="📑", layout="centered")

# st.secrets RAISES when no secrets.toml exists — it does not return empty. secrets.toml is
# gitignored, so a fresh clone has none: reading it unguarded crashes the app on startup for
# anyone running from a plain .env, which is the documented local setup (CLAUDE.md §5).
# On Streamlit Cloud the dashboard supplies the file, so this falls through to the real keys.
try:
    _secrets = list(st.secrets.items())
except StreamlitSecretNotFoundError:
    _secrets = []

for _k, _v in _secrets:
    if isinstance(_v, str) and _v:
        os.environ[_k] = _v

# Then evict every BLANK env var, or the app dies "OPENAI_API_KEY not set" with a perfectly
# good .env sitting next to it. Streamlit exports secrets.toml into os.environ as it parses
# the file — blanks included — and the local .streamlit/secrets.toml is an all-empty
# placeholder (real local keys live in .env). load_dotenv() never overrides an already-set
# var, so the blank stands and shadows the real key. An empty credential is indistinguishable
# from an absent one to every consumer here, so dropping it loses nothing. On Cloud the
# secrets are real, so this is a no-op there.
for _k in [k for k, v in os.environ.items() if v == ""]:
    os.environ.pop(_k)

# Then load .env HERE, rather than leaning on the module-level load_dotenv() inside src/. That
# only ever worked because app.py happened to be the first thing to import src: st.secrets
# OVERWRITES a real os.environ value with the blank placeholder when it parses (measured), the
# eviction above then drops it, and a src module already in sys.modules will not re-run its
# load_dotenv() to put it back. Anything that imports src before this file runs — a test, a
# future multipage entrypoint — silently strips the keys for the whole process. Owning the
# load removes the ordering dependency. On Streamlit Cloud there is no .env and the secrets
# are real, so this is a no-op there (and never a local RUNTIME dependency — CLAUDE.md §3).
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.generation.generate import NO_SOURCE  # noqa: E402  (must follow the env copy)
from src.graph.cite_check import MIN_TRACEABILITY  # noqa: E402
from src.graph.pipeline import MAX_ATTEMPTS, resume, run  # noqa: E402
from src.retrieval.hybrid import MIN_RELEVANCE  # noqa: E402


import logging  # noqa: E402

_log = logging.getLogger("dpdp.app")


def decide(decision: str, text: str = "", note: str = "") -> None:
    """Deliver the reviewer's verdict to the paused graph, then re-render.

    resume() RAISES if the paused draft is gone (the app slept and restarted, taking the
    in-memory checkpoint with it). Say so and drop the stale draft — the alternative is a
    reviewer clicking Approve on a draft that no longer exists anywhere and being told it
    worked. Any OTHER failure (Qdrant blip, provider outage) is logged in full server-side and
    shown SANITIZED: Streamlit's default error page renders the whole traceback to any viewer
    of the public app, and a connection error's message can carry QDRANT_URL."""
    try:
        st.session_state.state = resume(
            st.session_state.state.get("thread_id", ""), decision, text, note
        )
    except LookupError as e:
        st.session_state.pop("state", None)
        st.session_state.lost = str(e)
    except Exception:  # noqa: BLE001 — boundary: log loud, render sanitized
        _log.exception("resume(%s) failed", decision)
        st.session_state.lost = (
            "Delivering your decision failed on a backend error (it was logged). "
            "Your decision was NOT recorded — the draft is unchanged. Try again."
        )
    st.rerun()


st.title("📑 DPDP Content Farm")
st.caption(
    "Grounded in the DPDP Act 2023 and the DPDP Rules 2025 (G.S.R. 846(E)). "
    "Every claim is cited to a provision; unsupported topics are refused, not improvised."
)

if lost := st.session_state.pop("lost", None):
    st.error(lost)

topic = st.text_input(
    "Topic",
    placeholder="What must a Data Fiduciary do when a personal data breach occurs?",
)

if st.button("Draft", type="primary", disabled=not topic.strip()):
    t0 = time.perf_counter()
    with st.spinner("Retrieving, drafting, and verifying every citation…"):
        # Boundary for the same reason as decide(): an uncaught Qdrant/provider error would
        # render a full traceback (connection strings included) to any viewer of the public
        # app, and leave the PREVIOUS topic's draft on screen under the new topic's input.
        try:
            st.session_state.state = run(topic.strip())
            st.session_state.elapsed = time.perf_counter() - t0
        except Exception:  # noqa: BLE001 — boundary: log loud, render sanitized
            _log.exception("run(%r) failed", topic.strip()[:120])
            st.session_state.pop("state", None)  # never leave a stale draft under a new topic
            st.error(
                "Drafting failed on a backend error (it was logged). Nothing was drafted — "
                "the backing services may be waking up; try again in a few seconds."
            )

state = st.session_state.get("state")
if state:
    draft, report = state["draft"], state.get("report")
    decision = state.get("decision", "")  # the HUMAN's verdict; "" = still awaiting one

    if state["review_status"] == "no_grounded_source":
        # TWO different refusals wear this status, and they need different copy. The gate
        # refusal (provider "none" — no LLM was ever called) is a relevance failure. The model
        # refusal happened DESPITE relevant-looking retrieval, so quoting the relevance score
        # at the reader would contradict itself ("nothing bears on this: relevance 0.55").
        if draft.provider == "none":
            best = max((h.relevance for h in draft.hits), default=0.0)
            st.error(
                f"**{NO_SOURCE}** — nothing in the Act or Rules bears on this topic "
                f"(best relevance {best:.2f}, needs ≥ {MIN_RELEVANCE:.2f}). "
                "Nothing was drafted. Rephrase in the statute's own terms, or accept that the "
                "DPDP texts are silent on it."
            )
        else:
            st.error(
                f"**{NO_SOURCE}** — the provisions retrieved below came close enough to be "
                "worth reading, but they do not actually answer this. Nothing was drafted, "
                "rather than drafted around the gap. Try the statute's own terms."
            )
    else:
        # cite_check already redrafted this up to MAX_ATTEMPTS times. If it is STILL failing,
        # that is the one failure this system exists to prevent, and it reads exactly like a
        # sound draft. Say so ABOVE it, before anyone starts reading it as fact.
        if state["review_status"] == "needs_human":
            why = []
            if report.fabricated:
                why.append(
                    "it cites " + ", ".join(f"`{c}`" for c in report.fabricated)
                    + " — **not** among the sources retrieved below (the model reached for it "
                    "from memory)"
                )
            if not report.date_ok:
                why.append(f"it {report.date_why} — a provision not yet in force")
            if report.unsupported:
                why.append(
                    f"only {report.traceability_score:.0%} of its {report.claims} legal claims "
                    f"carry a valid citation (needs ≥ {MIN_TRACEABILITY:.0%})"
                )
            st.error(
                f"**Failed verification after {state['attempts']} attempts — do not publish.** "
                + "; ".join(why)
                + ".\n\nA human must check every claim against the PDFs below, or re-run the topic."
            )
            if report.unsupported:
                with st.expander(f"Uncited legal claims ({len(report.unsupported)})"):
                    for s in report.unsupported:
                        st.markdown(f"- {s}")
        else:
            st.success(
                f"**Machine-verified.** Every citation matches a retrieved provision, and "
                f"{report.traceability_score:.0%} of its {report.claims} legal claims are cited"
                + (f" (took {state['attempts']} attempts)." if state["attempts"] > 1 else ".")
                + " Machine-checked is not human-approved: it cannot tell whether a real"
                " citation is attached to the right claim. Review below."
            )

        # The machine's verdict and the human's are two different facts by two different
        # authorities (pipeline.py: review_status vs decision), so they get two banners. An
        # approval that OVERRODE a failed check must not read like a clean pass.
        note = f" _{state['note']}_" if state.get("note") else ""
        if decision == "approved":
            st.success(("**Approved by a human** — cleared to publish." if
                        state["review_status"] == "passed" else
                        "**Approved by a human, overriding a FAILED machine check.**") + note)
        elif decision == "rejected":
            st.warning("**Rejected.** This draft will not publish, and cannot be downloaded."
                       + note)

        st.markdown(draft.text)
        # The download is the publish-adjacent affordance — the file someone pastes into a
        # CMS. It is the one thing here that lets a draft leave the building, so it hangs off
        # the HUMAN's verdict, not the machine's (CLAUDE.md §3: human review before anything
        # publishes). A machine-passed draft nobody has approved yet is readable, not
        # exportable; so is a needs_human one, and so is a rejected one.
        if decision == "approved":
            # utf-8-sig, not utf-8: the statute is full of em-dashes, and a BOM-less file
            # opened on a Windows machine that guesses ANSI renders every one as "â"
            # mojibake (measured on the first real download, 2026-07-14). The BOM makes
            # Windows editors detect UTF-8; everything else ignores it.
            st.download_button("Download draft (.md)", draft.text.encode("utf-8-sig"),
                               "dpdp-draft.md", "text/markdown")

    attempts = f" · attempt {state['attempts']}/{MAX_ATTEMPTS}" if state["attempts"] else ""
    st.caption(
        f"provider: `{draft.provider}` · {len(draft.citations())} citations"
        f"{attempts} · {st.session_state.elapsed:.1f}s"
    )

    with st.expander(f"Sources retrieved ({len(draft.hits)}) — verify any citation against the PDF"):
        for h in draft.hits:
            st.markdown(
                f"**{h.citation}** · {h.source_ref} p.{h.page} · `{h.authority_status}` "
                f"· relevance {h.relevance:.2f}"
            )
            st.text(h.text)
            st.divider()

    # ── Human review console (Phase 6, design §5.9) ──────────────────────────────────────
    # Shown only while the graph is PAUSED at human_review, i.e. a draft exists and no verdict
    # has been delivered. A refusal (no_grounded_source) drafted nothing: there is nothing to
    # review, and offering an "Approve" button for it would be inviting a click on thin air.
    if state["review_status"] != "no_grounded_source" and not decision:
        st.divider()
        st.subheader("Human review")
        st.caption(
            "The machine proved every citation names a provision it was actually shown. It "
            "**cannot** prove that a real citation is attached to the *right* claim — no "
            "machine here can, and that is what you are for. Open the PDFs at the pages listed "
            "above and check at least three claims before approving."
        )
        if any(h.authority_status != "in force" for h in draft.hits):
            st.info(
                "Some retrieved provisions are **not yet in force**: "
                + " · ".join(sorted({f"{h.citation} — {h.authority_status}" for h in draft.hits
                                     if h.authority_status != "in force"}))
                + ". The draft must not state them as present obligations."
            )

        # draft.body(), NOT draft.text: the disclaimer is not the reviewer's to edit. Handing
        # them the full text put it in the middle of a textarea, where it invited being retyped,
        # reflowed, or written past — and a reviewer's disclaimer, unlike the canonical one, gets
        # scored by cite_check as an uncited legal claim. The code owns the disclaimer (golden
        # rule: every published piece carries it); apply_edit re-appends it verbatim.
        edited = st.text_area("Draft — edit it here to correct it", draft.body(), height=320)
        reviewer_note = st.text_input(
            "Note (recorded with the decision)",
            placeholder="Checked s.33 and the Schedule against the PDF, p.21.",
            key="note",
        )
        c1, c2, c3 = st.columns(3)

        if c1.button("Approve", type="primary", key="approve"):
            # Approving a draft the machine FAILED is legitimate — the reviewer is the higher
            # authority — but it is an override, and an override with no stated reason is
            # indistinguishable from a mis-click. Make them say it; it goes in the state.
            if state["review_status"] == "needs_human" and not reviewer_note.strip():
                st.error(
                    "This draft **failed** machine verification. Approving it overrides that "
                    "— write in the note what you checked and why it is safe, so the override "
                    "is on the record."
                )
            else:
                decide("approved", note=reviewer_note)

        if c2.button("Save edit & re-check", key="edit"):
            # An edit is re-checked by cite_check, not re-drafted: no LLM call, no cost, and
            # the reviewer's words survive verbatim. A citation THEY typed gets the same
            # scrutiny the model's did.
            if edited.strip():
                decide("edited", text=edited, note=reviewer_note)
            else:
                st.error("An empty draft is not an edit.")

        if c3.button("Reject", key="reject"):
            decide("rejected", note=reviewer_note)
