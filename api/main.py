"""RAG API — the HTTP surface n8n calls (Phase 8, the n8n->Docs flow).

RUNTIME service (CLAUDE.md §3): hosted APIs only. One endpoint does the whole grounded pipeline
so the correctness guarantees live in ONE place, not spread across n8n nodes:

    POST /generate  {topic, reference_link?, word_count?, style?, mode?}
        -> distil the reference link to a topic/angle hint  (untrusted; never a source of claims)
        -> retrieve DPDP chunks -> draft -> cite_check retry loop  (run_headless; no pause)
        -> {content, citations, sources, review_status, ...}

    POST /relevance {topic}   -> {grounded, top_relevance, top_citation}
        The same gate /generate applies, asked in advance and without drafting, so n8n can offer
        an off-topic submission a choice instead of writing it a Doc saying "no grounded source".

    mode="general" on /generate is the OTHER half of that choice (2026-07-21): an article with no
    sources, no citations and no legal claims, for a topic outside the corpus. It is a scoped
    exception to CLAUDE.md §3 and is never inferred — see UNGROUNDED_SYSTEM in
    src/generation/generate.py for the rules that make it safe, and _generate_ungrounded below.

The response carries the MACHINE verdict (review_status). It is NOT permission to publish: the
Google Doc n8n writes is the review surface, and a `needs_human` / `no_grounded_source` result
must reach the reviewer as such (that banner is built in n8n from these fields). This service
never publishes anything itself.

Env: the usual RAG keys (ANTHROPIC/OPENAI/QDRANT/...). Optional API_KEY — if set, callers must
send it as `X-API-Key`, so a public endpoint cannot be run up as a free LLM by anyone who finds
the URL.
"""

from __future__ import annotations

import logging
import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from api.reference import combined_topic  # noqa: E402  (after load_dotenv, like app.py)
from src.generation.generate import (  # noqa: E402
    DISCLAIMER,
    NEEDS_GROUNDING,
    STYLES,
    cite_supported,
    draft_ungrounded,
    retrieve_hits,
)
from src.graph.pipeline import run_headless  # noqa: E402
from src.retrieval.hybrid import is_grounded  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("dpdp.api")

WORD_MIN, WORD_MAX = 100, 2000  # a request outside this is a mistake; MAX keeps within MAX_TOKENS

# FAIL CLOSED. This used to be `if expected and not compare_digest(...)`, so an UNSET API_KEY
# silently disabled auth altogether — audit-proven 2026-07-16: with API_KEY popped from the env,
# POST /generate with no header returned 200 on an internet-facing, billable LLM endpoint, with
# no warning anywhere. render.yaml declares API_KEY with `sync: false`, which means a human must
# paste it into the Render dashboard by hand; `sync: false` does NOT guarantee it is set, so one
# forgotten paste was all it took. The test suite never caught it because tests/test_api.py sets
# API_KEY before import, exercising only the configured path.
#
# Refusing to boot is the correct trade: a service that is DOWN gets noticed in minutes; a
# service that is OPEN gets noticed on the invoice, or never.
API_KEY = os.getenv("API_KEY") or ""
if not API_KEY:
    raise RuntimeError(
        "API_KEY is not set — refusing to start. An unset key previously meant 'no auth', which "
        "silently exposed /generate to the internet. Set API_KEY in the Render dashboard "
        "(render.yaml declares it sync:false), or export API_KEY=dev for a local run."
    )

app = FastAPI(title="DPDP RAG API", version="1.0")


class GenerateIn(BaseModel):
    # max_length: audit-measured, an unbounded topic reaches embeddings/LLM/logs whole — one
    # probe request put 978 KB into the log. 500 chars is beyond any real topic.
    topic: str = Field(..., min_length=3, max_length=500,
                       description="What to write about, in DPDP terms")
    reference_link: str = Field("", max_length=2048, description="Optional URL — steers topic/angle only")
    word_count: int | None = Field(None, description="Soft length target; cite_check still governs")
    style: str = Field("", max_length=40,
                       description="Format preset (blog | linkedin_article | linkedin_article_short | newsletter); "
                                   "'' = default prose. Structure/tone only — grounding and cite_check "
                                   "apply unchanged.")
    # Defaults to "dpdp", so every caller written before 2026-07-21 — n8n's payload included —
    # keeps its exact behaviour. "general" is never inferred: n8n only sends it after the user
    # has been shown the off-topic form page and has declined to join the topic with DPDP.
    mode: str = Field("dpdp", max_length=16,
                      description="dpdp = grounded RAG, cite_check enforced (default) | "
                                  "general = UNGROUNDED: no sources, no citations, no legal "
                                  "claims, cite_check does not run. Only for topics outside the "
                                  "DPDP corpus.")


class Source(BaseModel):
    citation: str
    source_ref: str
    page: int
    authority_status: str


class GenerateOut(BaseModel):
    # passed | needs_human | no_grounded_source  (grounded, mode="dpdp")
    # ungrounded | needs_grounding              (mode="general" — see UNGROUNDED_SYSTEM)
    review_status: str
    publishable_without_review: bool   # ALWAYS False — the Doc is the review surface (never auto-ok)
    content: str                       # full draft incl. disclaimer, or the refusal text
    body: str                          # content without the trailing disclaimer
    disclaimer: str
    citations: list[str]
    sources: list[Source]
    traceability: float | None
    fabricated: list[str]
    unsupported: list[str]             # legal-claim sentences with no valid citation — with the
    # hybrid retry policy (2026-07-20) a coverage-only miss ships as needs_human at attempt 1,
    # so the reviewer needs the exact sentences to cite-or-delete, not just the score
    not_in_force: list[str]            # cited provisions not yet effective — the reviewer must flag
    provider: str
    attempts: int
    reference_hint: str                # what the link distilled to (audit trail; "" if none/failed)
    word_count: int | None
    style: str                         # the format preset that shaped the draft ("" = default)


def _require_key(x_api_key: str | None) -> None:
    # compare_digest: constant-time, closing the (theoretical) timing channel on a public URL.
    # No `if expected` guard — API_KEY is proven non-empty at import (see above), so there is no
    # code path here that skips the check.
    if not secrets.compare_digest(x_api_key or "", API_KEY):
        raise HTTPException(status_code=401, detail="missing or wrong X-API-Key")


class RelevanceIn(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500,
                       description="The user's raw topic, before any DPDP framing")


class RelevanceOut(BaseModel):
    grounded: bool          # would /generate be able to draft this, or would it refuse?
    top_relevance: float    # the best chunk's relevance — log it: near-misses are the ones to watch
    top_citation: str       # what it matched, for the audit trail; "" if nothing came back


@app.get("/health")
def health() -> dict:
    """Liveness for keepalive + n8n. Cheap: no LLM, no Qdrant call."""
    return {"status": "ok"}


@app.post("/relevance", response_model=RelevanceOut)
def relevance(body: RelevanceIn, x_api_key: str | None = Header(default=None)) -> RelevanceOut:
    """Is this topic in the DPDP corpus? Asked BEFORE generating, so an off-topic submission gets
    a form page offering a choice instead of a Google Doc containing "no grounded source".

    THE SAME GATE /generate USES, not a second opinion. It calls `retrieve_hits` — the function
    the pipeline's retrieve() node calls (src/graph/pipeline.py) — and not bare `search()`.
    That distinction is the whole correctness of this endpoint: retrieve_hits decomposes the
    topic and, on a compound one, expands cross-references, so a multi-part question can ground
    here when a single bare search would not. Answering from `search()` would make this endpoint
    disagree with the pipeline on exactly the queries the pipeline handles best, and the popup
    would fire on topics /generate drafts perfectly well. One gate, one verdict — the same rule
    eval/run_eval.py follows for date_honest.

    Cost: one short decompose() call (best-effort, falls back to the bare topic, so it cannot
    fail this request) plus 1-4 Qdrant searches. No draft, so a fraction of a generation.
    """
    _require_key(x_api_key)
    topic = body.topic.strip()
    if len(topic) < 3:  # min_length counts PRE-strip, same as /generate
        raise HTTPException(422, "topic must be at least 3 non-whitespace characters")

    hits = retrieve_hits(topic)
    ok = is_grounded(hits)
    best = max((h.relevance for h in hits), default=0.0)
    # Logged on every call, not just refusals: the worst REAL question measured 0.319 against a
    # 0.25 floor (2026-07-17), so the interesting number is how often a genuine topic lands near
    # the margin. Without this line a creeping false-refusal rate is invisible.
    log.info("relevance: topic=%r grounded=%s best=%.3f", topic[:200], ok, best)
    return RelevanceOut(grounded=ok, top_relevance=best,
                        top_citation=hits[0].citation if hits else "")


def _generate_ungrounded(topic: str, word_count: int | None, style: str,
                         reference_link: str) -> GenerateOut:
    """The mode="general" response: no sources, no citations, no legal claims, no cite_check.

    A separate function rather than a branch inside generate()'s body, so the grounded path is
    left byte-for-byte as it was and every field here is set EXPLICITLY. A shared assembly that
    both paths fell through would be one careless edit away from leaking a grounded default
    (sources, traceability, a citation list) into a response that has no grounding behind it.
    """
    if reference_link:
        # Deliberately not distilled: combined_topic() exists to steer a RETRIEVAL query, and
        # there is no retrieval on this path. Ignoring it silently is the surprise, so log it.
        log.info("ungrounded: ignoring reference_link %r — nothing to steer", reference_link[:200])
    log.info("generate: UNGROUNDED topic=%r words=%s style=%r", topic[:200], word_count, style)

    d = draft_ungrounded(topic, word_count=word_count, style=style)
    refused = d.text.strip() == NEEDS_GROUNDING
    if refused:
        log.info("ungrounded: REFUSED %r — routing the user back to the grounded pipeline", topic[:200])

    return GenerateOut(
        review_status="needs_grounding" if refused else "ungrounded",
        publishable_without_review=False,   # unchanged: nothing here publishes unreviewed either
        content=d.text,
        # d.body() strips the appended disclaimer; the refusal has none to strip.
        body=d.text if refused else d.body(),
        disclaimer=DISCLAIMER,
        # UNGROUNDED_SYSTEM rule 2 says write no citations. If the model wrote some anyway they
        # are reported in BOTH fields — present in the draft, and unsupported by construction
        # (no hits, so cite_supported rejects every one). n8n renders `fabricated` in the review
        # banner, so a stray bracket reaches the reviewer flagged instead of looking sound.
        citations=d.citations(),
        fabricated=d.fabricated(),
        sources=[],
        # None, never 0.0: 0.0 reads as "cite_check ran and everything failed". cite_check did
        # not run at all, because there is nothing to check a sourceless draft against.
        traceability=None,
        unsupported=[],
        not_in_force=[],
        provider=d.provider,
        attempts=1,
        reference_hint="",
        word_count=word_count,
        style=style,
    )


@app.post("/generate", response_model=GenerateOut)
def generate(body: GenerateIn, x_api_key: str | None = Header(default=None)) -> GenerateOut:
    _require_key(x_api_key)

    wc = body.word_count
    if wc is not None and not (WORD_MIN <= wc <= WORD_MAX):
        raise HTTPException(422, f"word_count must be {WORD_MIN}-{WORD_MAX} (got {wc})")

    # min_length counts PRE-strip: "   " (3 spaces) passed validation and reached the pipeline
    # as "". Enforce the bound on what the pipeline actually receives.
    topic_in = body.topic.strip()
    if len(topic_in) < 3:
        raise HTTPException(422, "topic must be at least 3 non-whitespace characters")

    # Unknown style is a 422, never a silent fallback to default prose: the caller asked for a
    # format and would otherwise get a different one with no signal (CLAUDE.md §1, fail loudly).
    style = body.style.strip().lower()
    if style and style not in STYLES:
        raise HTTPException(422, f"unknown style {style!r} — allowed: {sorted(STYLES)} or ''")

    # Same rule as style: an unrecognised mode is a 422, never a silent fall back to "dpdp". A
    # typo'd mode must not quietly return grounded content to a caller that asked for ungrounded
    # (or, far worse, the reverse).
    mode = body.mode.strip().lower()
    if mode not in ("dpdp", "general"):
        raise HTTPException(422, f"unknown mode {mode!r} — allowed: 'dpdp' or 'general'")

    if mode == "general":
        return _generate_ungrounded(topic_in, wc, style, body.reference_link.strip())

    topic, hint = combined_topic(topic_in, body.reference_link.strip())
    log.info("generate: topic=%r hint=%r words=%s style=%r", topic_in[:200], hint, wc, style)

    s = run_headless(topic, word_count=wc, style=style)
    d, report = s["draft"], s.get("report")
    cited = set(d.citations())
    # cite_supported, not exact equality: the model cites refinements (r.7(1) of a retrieved
    # r.7), and an exact match let a cited future-dated provision vanish from the one field
    # the reviewer is told to flag (audit-measured). If any citation rests on the hit, the
    # hit's status travels with it.
    not_in_force = sorted({h.citation for h in d.hits
                           if h.authority_status != "in force"
                           and any(cite_supported(c, [h]) for c in cited)})

    return GenerateOut(
        review_status=s["review_status"],
        publishable_without_review=False,
        content=d.text,
        body=d.body() if d.grounded else d.text,
        disclaimer=DISCLAIMER,
        citations=d.citations(),
        sources=[Source(citation=h.citation, source_ref=h.source_ref, page=h.page,
                        authority_status=h.authority_status) for h in d.hits],
        traceability=report.traceability_score if report else None,
        fabricated=report.fabricated if report else [],
        unsupported=report.unsupported if report else [],
        not_in_force=not_in_force,
        provider=d.provider,
        attempts=s.get("attempts", 0),
        reference_hint=hint,
        word_count=wc,
        style=style,
    )
