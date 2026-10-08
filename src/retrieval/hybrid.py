"""Hybrid retrieval over the DPDP corpus in Qdrant Cloud.

RUNTIME module (CLAUDE.md §3): depends only on hosted APIs — Qdrant Cloud + OpenAI
embeddings. No PDF, no JSONL, no local index. The indexer (src/ingest/index_qdrant.py)
imports from here so index-time and query-time use the same embedders.

Two named vectors per point:
  dense  — OpenAI text-embedding-3-large (3072, cosine). Semantic: "what must a notice say".
  sparse — FastEmbed BM25 (IDF modifier, server-side). Exact terms: "Section 8(7)", "Rule 7".
Fused server-side with RRF. Pure dense misses literal section numbers; pure sparse misses
paraphrase. Legal queries are both.
"""

from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from openai import OpenAI
from qdrant_client import QdrantClient, models
import openai
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()
log = logging.getLogger(__name__)

COLLECTION = "dpdp"
DENSE_MODEL = "text-embedding-3-large"  # human's decision 2026-07-17; -small before that
DENSE_SIZE = 3072
SPARSE_MODEL = "Qdrant/bm25"
TOP_K = 6  # docs/system-design.md §5.4
# Ceiling on the merged source list a DECOMPOSED query feeds to generation. decompose() caps
# at 4 sub-queries, each contributing ~6 primary hits + up to 6 cross-refs, so a pathological
# fan-out could pile up ~40 provisions and bloat the prompt. 20 keeps every realistic answer
# (the measured worst case is ~16) while bounding the tail, and merge_hits LOGS anything it
# drops — a silent cap would read as "covered everything" when it hadn't.
# ponytail: flat top-N by relevance. If a low-cosine but on-topic provision (e.g. the penalty
# Schedule) is ever trimmed, tier the cap to keep primary hits over cross-refs (score==0.0).
MERGE_CAP = 20
# Below this cosine, nothing retrieved bears on the question -> "no grounded source".
# Measured, not guessed: real DPDP questions 0.37-0.67, off-topic questions 0.08-0.16.
MIN_RELEVANCE = 0.25


@lru_cache(maxsize=1)
def qdrant() -> QdrantClient:
    url, key = os.getenv("QDRANT_URL"), os.getenv("QDRANT_API_KEY")
    if not url or not key:
        raise RuntimeError("QDRANT_URL / QDRANT_API_KEY not set (.env or Streamlit secrets)")
    return QdrantClient(url=url, api_key=key, timeout=30)


@lru_cache(maxsize=1)
def _openai() -> OpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set — embeddings are OpenAI-only (no Anthropic API)")
    return OpenAI()


@lru_cache(maxsize=1)
def _bm25() -> SparseTextEmbedding:
    return SparseTextEmbedding(model_name=SPARSE_MODEL)


# Retry ONLY what a retry can fix (429/5xx/network). A 400 (empty input) or 401 (bad key) is
# OUR bug and can never succeed — retrying it burned 4 calls and ~7s of backoff before
# surfacing the real error (audit-measured on search("")).
@retry(retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError,
                                      openai.InternalServerError)),
       stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=20), reraise=True)
def embed_dense(texts: list[str]) -> list[list[float]]:
    resp = _openai().embeddings.create(model=DENSE_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def embed_sparse(texts: list[str]) -> list[models.SparseVector]:
    """Document-side BM25 (term frequencies). IDF is applied server-side by Qdrant."""
    return [
        models.SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
        for e in _bm25().embed(texts)
    ]


def embed_sparse_query(text: str) -> models.SparseVector:
    """Query-side BM25 — NOT the same as embed_sparse: no term-frequency weighting."""
    e = next(iter(_bm25().query_embed(text)))
    return models.SparseVector(indices=e.indices.tolist(), values=e.values.tolist())


# --- citation handles -------------------------------------------------------------
# Raw BM25 cannot do citation lookup, and that is the one job the sparse side exists for.
# "Section 8(7)" tokenises to section / 8 / 7 — all three are low-IDF (every chunk is full
# of cross-references), so the top hits came back as noise. Fix: mint ONE synthetic token
# per provision ("section8", "rule7"). Punctuation-free, so BM25 never splits it, and it
# occurs in exactly one chunk — maximal IDF, guaranteed rank-1. Index side and query side
# MUST mint identical tokens, which is why both live here.

_ORDINALS = "first|second|third|fourth|fifth|sixth|seventh"
# "the" is NOT in the ordinal list, and cannot be: it is an ordinary English word, and
# "schedule" is ordinary marketing vocabulary. Matched case-insensitively alongside the real
# ordinals, it minted `theschedule` — the maximal-IDF handle for the Act's PENALTY table — out
# of "What is the schedule for DPDP compliance?", "How long is the schedule for consent
# managers?", "Publish the schedule of deliverables." A minted handle is not mere noise: it is
# PINNED to rank 1 by search(), so the penalties table displaced a real source out of the top-6
# on any query that used the word in its everyday sense.
#
# The Act's own field is "The Schedule", and a genuine reference to it capitalises SCHEDULE, as
# the statute prints it ("the Schedule to the DPDP Act", "The Schedule"). The capital S is the
# whole discriminator — it is what separates the citation from the calendar — so only that
# letter is matched case-sensitively; the article may be either case. A lowercase
# "the schedule for compliance" now mints nothing and falls back to dense retrieval: losing a
# handle is cheap, pinning the penalties table to rank 1 of an unrelated query is not.
_THE_SCHEDULE = re.compile(r"\b[Tt]he\s+Schedule\b")
# How a genuine schedule CITATION continues after the ordinal/digit: end-of-query, punctuation,
# or a citation-shaped function/verb word. Calendar-speak ("schedule 3 LinkedIn posts",
# "first schedule a demo") continues into an object noun instead, and mints nothing. A
# whitelist, deliberately: the failure mode of missing a continuation word is a LOST handle
# (dense retrieval still serves the query); the failure mode of a loose guard is the wrong
# table pinned to rank 1.
_SCHED_CONT = re.compile(
    r"\s*(?:$|[,.;:!?)\]—–-]|(?:of|to|under|in|on|for|and|or|parts?|says?|said|states?|"
    r"requires?|provides?|lists?|sets?|covers?|specif\w*|prescribes?|is|are|was|were|"
    r"table|entry|item|read)\b)",
    re.I,
)
# CLAUDE.md §6: normalize BOTH "First–Seventh Schedule" and "Schedule I–VII" (or 1–7).
_SCHED_NUMERAL = {
    "i": "first", "1": "first", "ii": "second", "2": "second", "iii": "third", "3": "third",
    "iv": "fourth", "4": "fourth", "v": "fifth", "5": "fifth", "vi": "sixth", "6": "sixth",
    "vii": "seventh", "7": "seventh",
}


def _subs(sub: str) -> list[str]:
    """The sub-section numbers a chunk covers: '2' -> ['2'], '1-8' -> ['1'..'8']."""
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", sub)
    if m:
        return [str(i) for i in range(int(m.group(1)), int(m.group(2)) + 1)]
    return [sub] if sub.isdigit() else []


def provision_terms(c: dict) -> str:
    """Index side: the handles for one chunk. Works on chunk dicts AND Qdrant payloads
    (same fields) — search() re-mints these to pin explicitly-named provisions."""
    terms, n = [], (c.get("number") or "").split("(")[0].strip()
    if n and c["doc"].startswith("DPDP Act"):
        terms += [f"section{n}", f"s{n}"]
        # Sub-split chunks (s.44(1)/(2)/(3), s.6(1-8)/(9)/(10)) share number=44 and so mint
        # IDENTICAL handles — BM25 scored them 14.4/14.4/14.3 for "s.44(2)". The sub handle
        # is what lets a sub-precise citation find the right split.
        terms += [f"s{n}sub{x}" for x in _subs(str(c.get("sub") or ""))]
    elif n:
        terms += [f"rule{n}", f"r{n}"]
        terms += [f"r{n}sub{x}" for x in _subs(str(c.get("sub") or ""))]
    if sched := c.get("schedule"):
        # First word, not last: the Act's field is "The Schedule" -> "theschedule",
        # matching what expand_query mints from "the Schedule". Rules: "First" -> "firstschedule".
        handle = f"{sched.split()[0].lower()}schedule"
        terms += [handle, "schedule"]
        if part := c.get("part"):
            # A bare "partb" handle does NOT rank Part B over Part A: BM25 length-normalises,
            # and Part A is a third the length, so the shared "firstschedule" term outweighs the
            # single part token. The COMPOUND occurs in exactly one chunk -> IDF decides, not length.
            terms += [f"part{part.lower()}", f"{handle}part{part.lower()}"]
    return " ".join(terms)


def expand_query(q: str) -> str:
    """Query side: the same handles, mined out of however the user wrote the citation
    ("Section 8(7)", "s.8", "sec 8", "Rule 7", "r.7", "Third Schedule", "Schedule III").

    Four things here are load-bearing and each fixes a measured mis-ranking:
    * (?<!sub...) — "sub-section 7 of section 8" was minting section7, dragging the unrelated
      s.7 into the results. Legal prose says "sub-section" constantly.
    * (?<!')(?<!’) — a possessive before a number is not a citation: "the Act's 44 sections"
      minted section44 and pinned s.44 (TRAI/IT-Act amendments) to ranks 1-3 for a question
      about the Act's structure. Both apostrophe forms, since Word/Outlook curl them.
    * \\d{1,2} — the corpus is ss.1-44 / rr.1-23, so a citation number is never >2 digits.
      Without the bound, the DOCUMENT'S OWN NAME ("DPDP Rules 2025") minted `rule2025`.
    * part[ab] — the index mints `parta`/`partb`, so the query side must too, or "Part B of
      the First Schedule" cannot outrank First Schedule Part A. It could not.
    """
    sub_ref = r"(?:\s*\(\s*(\d{1,2})\s*\))?"  # the "(2)" of "s.44(2)" — optional
    terms = []
    for n, sub in re.findall(
        r"(?<!sub)(?<!sub-)(?<!sub )(?<!')(?<!’)\b(?:sections?|secs?|ss?)\.?\s*(\d{1,2})\b" + sub_ref,
        q,
        re.I,
    ):
        terms += [f"section{n}", f"s{n}"] + ([f"s{n}sub{sub}"] if sub else [])
    # Same (?<!sub) guard as the sections branch above, for the same measured reason: the
    # Rules say "sub-rule" as constantly as the Act says "sub-section", and "sub-rule 3 of
    # rule 6" was minting rule3 — pinning r.3 (Notice) level with the rule actually asked
    # about. Any handle minted here goes straight into search()'s pin, so a spurious one
    # does not merely add noise: it promotes the wrong provision to rank 1.
    for n, sub in re.findall(
        r"(?<!sub)(?<!sub-)(?<!sub )\b(?:rules?|r)\.?\s*(\d{1,2})\b" + sub_ref, q, re.I
    ):
        terms += [f"rule{n}", f"r{n}"] + ([f"r{n}sub{sub}"] if sub else [])

    # The ordinal and DIGIT schedule forms are ordinary marketing vocabulary — "schedule 3
    # LinkedIn posts", "we should schedule 1 review call", "first schedule a demo" all minted
    # a maximal-IDF Schedule handle and PINNED the wrong statutory table to rank 1 (audit-
    # measured; same failure class as `theschedule` above, and the same trade-off applies:
    # losing a handle is cheap, pinning the penalties table is not). Discriminator: a genuine
    # citation CONTINUES like one — "Schedule 3 of the Rules", "the Third Schedule says",
    # "First Schedule Part B", or simply ends — while calendar-speak continues into an object
    # noun ("3 LinkedIn posts", "a demo"). Roman numerals (Schedule III) are exempt: "iii" has
    # no everyday reading, so it stays unguarded either case.
    def _cites_on(end: int) -> bool:
        return bool(_SCHED_CONT.match(q, end))

    scheds = [m.group(1).lower() for m in re.finditer(rf"\b({_ORDINALS})\s+schedules?\b", q, re.I)
              if _cites_on(m.end())]
    # "Schedule-I" / "Schedule–III" as well as "Schedule I": users hyphenate routinely, and the
    # separator was \s+ only, so a hyphenated form minted nothing at all.
    for m in re.finditer(r"\bschedules?[\s\-–—]+(vii|vi|v|iv|iii|ii|i|[1-7])\b", q, re.I):
        tok = m.group(1).lower()
        if tok.isdigit() and not _cites_on(m.end()):
            continue
        scheds.append(_SCHED_NUMERAL[tok])
    scheds += ["the"] * len(_THE_SCHEDULE.findall(q))  # case-sensitive; see _THE_SCHEDULE
    # A Part exists ONLY inside a Schedule, so a part handle is minted only when the query names
    # one. Unguarded, `\bpart\s*[ab]\b` fired on ordinary prose — "This is in part a consequence
    # of...", "We built part b of the platform" — and pinned all four Schedule-Part chunks to the
    # front of the results. Same class of failure as `theschedule` above.
    parts = ([p.lower() for p in re.findall(r"\bpart\s*[-–]?\s*([ab])\b", q, re.I)]
             if scheds else [])
    terms += [f"{s}schedule" for s in scheds]
    terms += [f"part{p}" for p in parts]
    # Same compound the index mints — the only handle that survives BM25 length normalisation.
    terms += [f"{s}schedulepart{p}" for s in scheds for p in parts]

    # ponytail: enumerated citations ("ss. 4 and 5") only mint a handle for the FIRST number;
    # the rest fall back to dense retrieval. Widen to a number list if that shows up in real use.
    return f"{q} {' '.join(terms)}" if terms else q


# --- schedule context ------------------------------------------------------------
# A Schedule is a bare TABLE. Its subject is never stated in itself — it lives in the rule
# that made it. The Third Schedule IS the data-retention table, yet it contains the words
# "retain", "retention", "erase" and "erasure" exactly zero times: it says only "Time period"
# and "Three years from the date the Data Principal last approached...". So BOTH retrieval
# sides went blind on it — dense saw a table of e-commerce/gaming/social-media classes, and
# BM25 had no term to match — and it never once surfaced for a retention question. Generation
# then honestly reported "the sources do not include the Third Schedule", which is a correct
# answer to the wrong evidence: the marketer asking "how long must we retain data" was never
# shown the table that answers them.
#
# Fix: prepend the PARENT provision's opening words to the embedded text. r.8 opens "...shall
# erase such personal data, unless its retention is necessary...", which is exactly the
# vocabulary the table lacks. Same principle as the citation handles above — scaffolding goes
# into the vector, never into the payload. The parent is taken from the Schedule's own
# "[See rule 8(1)]" line, so it is read from the statute, not hand-assigned.
SEE_PARENT = re.compile(r"\[See (?:rules?|sections?)\s+(\d{1,2})")
# 300 is measured, not guessed. Third Schedule hit-rate over 6 retention queries, sweeping
# this value and re-indexing each time (control set: 7 queries incl. all 5 bare-citation
# rank-1 cases — NONE regressed at any setting):
#     0 (no context) -> 2/6      300 -> 4/6      600 -> 4/6      900 -> 4/6      1200 -> 4/6
# The whole gain arrives at 300 and nothing is bought after it, so take the smallest. 300
# spans r.8's heading plus its operative clause ("...shall erase such personal data, unless
# its retention is necessary..."), which is the vocabulary the table itself lacks.
#
# ponytail: 2 of the 6 still miss ("...retain signed CONTRACTS", "when must a company DELETE
# my data") — the Schedule's own rows name only e-commerce / online-gaming / social-media
# classes, so it is arguably not the answer to the contract one. Both queries still retrieve
# r.8, which explains the Schedule's mechanism. Revisit only if a real query needs the table
# itself and does not get it.
CONTEXT_CHARS = 300


def parent_ref(c: dict) -> str | None:
    """The provision number a Schedule hangs off, per its own '[See rule 8(1)]' line."""
    if c.get("type") != "schedule":
        return None
    m = SEE_PARENT.search(c.get("text") or "")
    return m.group(1) if m else None


def index_text(c: dict, context: str = "") -> str:
    """What gets EMBEDDED — the chunk's own citation and handles are prepended so a
    citation-shaped query can match at all, plus (for Schedules) the parent provision's
    opening words, which are the only place a Schedule's SUBJECT is written down.
    The PAYLOAD keeps the pristine legal text; generation must never see this scaffolding."""
    parts = [
        c["citation"],
        provision_terms(c),
        c.get("chapter_title") or "",
        c.get("title") or "",  # the Act's side-note heading — absent from `text` entirely
        context,
        c["text"],
    ]
    return "\n".join(p for p in parts if p)


@dataclass
class Hit:
    citation: str
    authority_status: str
    source_ref: str
    page: int
    text: str
    score: float  # RRF fusion score — RANK-based. Says nothing about relevance. Use `relevance`.
    relevance: float  # cosine(query, chunk) in [0, 1] — the only honest "is this on-topic" signal

    def as_source_header(self) -> str:
        """The line the generation prompt puts above each chunk (CLAUDE.md §8)."""
        return f"# Source: {self.citation} ({self.source_ref}, p.{self.page}) [{self.authority_status}]"


def _to_hit(payload: dict, score: float, relevance: float) -> Hit:
    """One place that turns a Qdrant payload into a Hit — search() and cross_refs() both use
    it, so the two can never drift on which payload fields a Hit carries."""
    return Hit(
        citation=payload["citation"],
        authority_status=payload["authority_status"],
        source_ref=payload["source_ref"],
        page=payload["page"],
        text=payload["text"],
        score=score,
        relevance=relevance,
    )


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def is_grounded(hits: list[Hit]) -> bool:
    """Does ANY retrieved chunk actually bear on the question?

    CLAUDE.md §3: "If retrieval returns nothing relevant, output 'no grounded source' —
    never generate anyway." That rule was unenforceable before this function existed. The
    RRF score cannot enforce it: fusion scores are computed from RANKS, so the 6 chunks for
    "how do I fix my car engine" came back scoring 0.70 — identical to the best real query.
    Every question looked equally well-grounded, including the ones the DPDP texts say
    nothing about (a common person asking "can I get compensation?" — the Act grants no
    such right).

    Measured over the live index: real DPDP questions score 0.37–0.67; off-topic questions
    score 0.08–0.16. MIN_RELEVANCE sits in that gap with ~1.5x margin either side. Re-measure
    with tests/test_retrieval.py if the corpus or the embedding model changes.
    """
    return any(h.relevance >= MIN_RELEVANCE for h in hits)


# --- cross-reference expansion --------------------------------------------------
# A retrieved provision constantly points at others it does NOT contain: s.8 says "in
# accordance with the provisions of section 8", the penalty Schedule hangs off "[See section
# 33]", r.8 leans on the Third Schedule for the actual time periods. Generation grounded only
# on the chunks the query matched misses that connected material. So after retrieval, read the
# references OUT of each hit's own text and pull the ones that weren't retrieved.
#
# The references are mined with expand_query — the SAME handle-miner the sparse side already
# uses — so this needs no cross_references field and no re-index (human's decision 2026-07-16).
# One hop only, capped, and ordered by cosine to the query so only on-topic references come in.
# Everything added is a real retrieved chunk, so cite_check validates it like any other.


def _scroll_all() -> list:
    """Every point in the collection, with dense vectors. 81 chunks — one cheap scroll."""
    out, offset = [], None
    while True:
        batch, offset = qdrant().scroll(
            collection_name=COLLECTION, limit=256,
            with_payload=True, with_vectors=["dense"], offset=offset,
        )
        out.extend(batch)
        if offset is None:
            return out


@lru_cache(maxsize=1)
def _catalog() -> tuple[dict, dict]:
    """Two lookups over the whole corpus, built once: citation -> (owned handles, payload,
    dense vector), and handle -> [citations that own it]. The index is static between deploys,
    so this is cached for the process like the embedders are."""
    by_cite: dict[str, tuple[frozenset, dict, list]] = {}
    owner: dict[str, list[str]] = {}
    for p in _scroll_all():
        owned = frozenset(provision_terms(p.payload).split())
        by_cite[p.payload["citation"]] = (owned, p.payload, p.vector["dense"])
        for h in owned:
            owner.setdefault(h, []).append(p.payload["citation"])
    return by_cite, owner


def _referenced_handles(text: str) -> set[str]:
    """The provision handles a chunk's own text points at — its cross-references. Mints exactly
    what expand_query mints (section8, rule7, theschedule, firstschedulepartb, …)."""
    return set(expand_query(text).split()) - set(text.split())


def cross_refs(hits: list[Hit], query_vec: list[float], cap: int = 6) -> list[Hit]:
    """Provisions the retrieved chunks reference but that weren't themselves retrieved.

    One hop, capped at `cap`, ordered by relevance to the ORIGINAL query so only references
    that bear on the question are added — a definitions chunk points at dozens of provisions,
    and pulling them all would drown the real answer. Handles already covered by a retrieved
    chunk are skipped, so a chunk never pulls in its own siblings.
    """
    by_cite, owner = _catalog()
    have = {h.citation for h in hits}
    covered = set().union(*(by_cite[c][0] for c in have if c in by_cite)) if have else set()
    wanted = set().union(*(_referenced_handles(h.text) for h in hits)) if hits else set()

    seen, extras = set(have), []
    for handle in wanted - covered:
        for cite in owner.get(handle, []):
            if cite in seen:
                continue
            seen.add(cite)
            _, payload, vec = by_cite[cite]
            extras.append(_to_hit(payload, 0.0, _cosine(query_vec, vec)))
    extras.sort(key=lambda h: -h.relevance)
    return extras[:cap]


def merge_hits(groups: list[list[Hit]], cap: int = MERGE_CAP) -> list[Hit]:
    """Union hits from several sub-query searches; dedup by citation, keep the max relevance.
    Ordered most-relevant first so is_grounded() and the prompt see the strongest evidence on
    top. Used to fold the results of a decomposed query back into one source list.

    Trimmed to `cap` provisions (MERGE_CAP) to bound prompt cost on a wide fan-out. A trim is
    LOGGED with the dropped citations — never silent (CLAUDE.md §1)."""
    best: dict[str, Hit] = {}
    for hits in groups:
        for h in hits:
            cur = best.get(h.citation)
            if cur is None or h.relevance > cur.relevance:
                best[h.citation] = h
    ordered = sorted(best.values(), key=lambda h: -h.relevance)
    if cap and len(ordered) > cap:
        log.info("merge_hits: %d provisions -> capping to %d (dropped %s)",
                 len(ordered), cap, [h.citation for h in ordered[cap:]])
        ordered = ordered[:cap]
    return ordered


def search(query: str, k: int = TOP_K, expand_refs: bool = False) -> list[Hit]:
    """Server-side hybrid query with RRF fusion.

    Returns hits regardless of relevance — ALWAYS gate the result with is_grounded() before
    generating from it. Retrieval on a 81-chunk corpus always returns k chunks; whether any of
    them answers the question is a separate question, and only `Hit.relevance` answers it.

    expand_refs=True appends the provisions the top-k explicitly cross-reference (see
    cross_refs). OFF by default so eval and the retrieval tests measure raw hybrid recall; the
    generation path (generate.retrieve_hits) turns it on.
    """
    qv = embed_dense([query])[0]
    res = qdrant().query_points(
        collection_name=COLLECTION,
        prefetch=[
            models.Prefetch(query=qv, using="dense", limit=k * 4),
            models.Prefetch(query=embed_sparse_query(expand_query(query)), using="sparse", limit=k * 4),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=k,
        with_payload=True,
        with_vectors=["dense"],  # so relevance can be measured; RRF's own score cannot
    )

    # Pin explicitly-named provisions to the front. For a bare citation the dense side is
    # noise, and RRF — being rank-based — lets chunks that are mediocre in BOTH lists beat
    # the one that is decisively #1 in sparse: "r.22" fused to [r.2, r.16, r.22, ...] while
    # sparse had r.22 first at 16.0 vs 6.2. If the reader NAMED a provision and it was
    # retrieved, it leads. Most handle matches first (so "s.44(2)" beats its s.44 siblings),
    # original fused order otherwise — deterministic and inspectable.
    minted = set(expand_query(query).split()) - set(query.split())
    points = sorted(
        enumerate(res.points),
        key=lambda ip: (-len(minted & set(provision_terms(ip[1].payload).split())), ip[0]),
    ) if minted else list(enumerate(res.points))

    hits = [_to_hit(p.payload, p.score, _cosine(qv, p.vector["dense"])) for _, p in points]
    if expand_refs:
        hits += cross_refs(hits, qv)
    return hits


if __name__ == "__main__":  # quick manual probe: python -m src.retrieval.hybrid "notice"
    import sys

    q = " ".join(sys.argv[1:]) or "What must a notice to the Data Principal contain?"
    hits = search(q)
    if not is_grounded(hits):
        print(f"no grounded source (best relevance {max(h.relevance for h in hits):.3f} "
              f"< {MIN_RELEVANCE}) — the DPDP texts do not answer this")
    for h in hits:
        print(f"rel={h.relevance:.3f}  {h.as_source_header()}")
