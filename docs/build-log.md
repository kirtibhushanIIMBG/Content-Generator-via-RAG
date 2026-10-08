# Build Log — DPDP RAG Content Farm

Everything that has happened on this project, why it happened, and what is still open.
Written 2026-07-14, covering Phases 1–4 (commits `bbf28fc` … `907c860`); extended 2026-07-15
with §7 (Phase 5, LangGraph + `cite_check`) and §8 (Phase 6, the human review console).

[docs/system-design.md](system-design.md) is the architecture. [CLAUDE.md](../CLAUDE.md) is the
standing instruction set. **This file is the history**: the decisions, the things that broke,
and how each was caught. It exists because most of what this project knows was learned by
finding a bug, not by planning — and a plan that omits the bugs teaches the next person nothing.

---

## 1. What the system is

A citation-grounded RAG system that drafts marketing content about India's **DPDP Act 2023**
and **DPDP Rules 2025** for Certinal. Every factual claim must trace to a specific Section,
Rule, or Schedule of the official texts.

One property is binding and everything else is subordinate to it:

> **The system must never claim what it cannot prove from the official texts.**

Concretely that means: retrieval that fails is *told*, not papered over; a topic the statutes
do not answer returns `no grounded source` rather than a plausible paragraph; and a provision
that is not yet in force is never presented as a duty today.

**Architecture** (cloud-only at runtime — no local file, model, or index is on the serving path):

```
topic ─► hybrid retrieval (Qdrant Cloud: dense OpenAI 3072 + sparse BM25, RRF fusion)
       ─► is_grounded() relevance gate ──(fails)──► "no grounded source", no LLM call
       ─► strict prompt (numbered sources + citations + authority status)
       ─► claude-sonnet-5 ──(429/5xx/network)──► gpt-4o-mini failover, provider tagged
       ─► disclaimer appended in CODE
       ─► Draft.fabricated() detector ─► Streamlit UI (draft + the 6 sources it stands on)
```

The source PDFs are **build-time inputs only**. After ingestion the deployed app depends on
nothing but Qdrant Cloud + the hosted APIs.

---

## 2. Phase-by-phase history

### Phase 1 — Scaffold (`bbf28fc`, `c681b8f`, `4b4f65a`) · 2026-07-13

Project structure, dependency split, and verification harness. Two decisions made here paid off
repeatedly:

- **Runtime deps and build deps are separate files.** `requirements.txt` is what Streamlit Cloud
  installs (~2.7 GB RAM ceiling); `requirements-build.txt` holds the ingestion-only libraries.
  `unstructured` was dropped entirely — never imported, and it drags in spacy/nltk/numba/llvmlite.
- **Source verification before any parsing.** [docs/source-verification.md](source-verification.md)
  records the evidence that the PDFs are the *final* texts (Gazette G.S.R. 846(E), 13 Nov 2025)
  and not the superseded January 2025 draft. Citing the draft is a golden-rule violation, so
  this gate came before a line of chunker code.

### Phase 2 — Legal chunking (`146de3d`, `070d849`, `9ae3e25`, `e9ff11d`) · 2026-07-13

The slowest, most important phase — everything downstream inherits its errors. Output: **81
chunks** (49 Act + 32 Rules) in `data/processed/*.jsonl`, each carrying full metadata
(citation, authority_status, source_ref, page).

**Why the chunker uses two PDF libraries** (this is deliberate; do not consolidate it):

| Library | Used for | The silent corruption it prevents |
|---|---|---|
| **pdfminer.six** | body text | The Act is a two-column Gazette whose section titles sit in an 8pt **margin column**. Flat extraction interleaves those words into the middle of legal sentences (`"...only in accordance PROCESSING with the provisions..."`). pdfminer exposes per-line `(x0, size)`, so the margin is removed *geometrically*. |
| **pypdf** (`extraction_mode="layout"`) | Schedules | Every Schedule is a **table**. pypdf's default mode emits the penalty table in *column* order — all 7 breaches, then all 7 penalties — which cheerfully welds "250 crore" onto the wrong breach. It reads plausibly, which is what makes it dangerous. Layout mode preserves row alignment. |

**Authority status is derived from the gazette, not from memory.** The Act fixes no commencement
date in its own text (s.1(2): *"such date as the Central Government may appoint"*), so the dates
come from **G.S.R. 843(E)** (MeitY, 13 Nov 2025) — a third PDF used as a build-time *metadata*
source and never chunked. `commencement_evidence()` asserts the notification's operative clauses
are literally present in that PDF and **refuses to build** otherwise. If the wrong PDF is dropped
in, the build stops rather than quietly re-dating the law.

The resulting three-bucket scheme, which all published content must respect:

| Status | What is in it |
|---|---|
| `in force` | Definitions, the Data Protection Board (ss.18–26), and misc. sections |
| `effective 2026-11-13` | s.6(9) and Rule 4 — the Consent Manager route |
| `effective 2027-05-13` | **The entire substantive compliance regime** — notice, consent, security, children, SDF, and *all penalties* |

> Most of the Act is **not yet in force**. Content that says "you can be fined ₹250 crore today"
> is false. This is why `authority_status` rides on every chunk and into every prompt.

### Phase 3a — Qdrant index + hybrid retrieval (`1d1ca1e` + five hardening commits) · 2026-07-13

Collection `dpdp` in Qdrant Cloud: 81 points, named vectors `dense` (OpenAI
text-embedding-3-large, 3072, cosine) + `sparse` (FastEmbed BM25, `modifier=IDF`), fused
**server-side with RRF**. Pure dense misses literal section numbers; pure sparse misses
paraphrase. Legal queries are both.

Then real-world query batteries (a marketer, a layperson, messy input) found **five classes of
bug that a fully-green test suite had missed.** These are the most valuable lessons on the
project:

1. **Provisions do not state their own subject.** The Act's section titles ("Notice.",
   "Exemptions.") are *margin side-notes* — which the chunker correctly strips, because read
   inline they corrupt legal sentences. But that left every Act section with no statement of
   its own topic: the Act's body says the word "Notice" **zero** times. So the Act lost topical
   queries to the Rules, which carry their headings inline. Fixed by feeding the side-note title
   to the **embedding only** (`index_text`), never the payload (`4564000`).
2. **Schedules state their subject nowhere at all.** The Third Schedule *is* the data-retention
   table, yet it contains "retain", "retention", "erase" and "erasure" **zero** times — it says
   only "Time period" and "Three years from...". Both retrieval sides went blind, and a marketer
   asking "how long must we retain data" was never shown the table that answers them. Fixed by
   prepending the **parent rule's** opening words to the embedded text, read from the Schedule's
   own `[See rule 8(1)]` line (so it follows the statute, not a hand-assignment).
3. **BM25 cannot do citation lookup.** "Section 8(7)" tokenises to `section` / `8` / `7` — all
   low-IDF, since every chunk is full of cross-references. Fixed by minting **synthetic handles**
   (`section8`, `rule7`, `firstschedulepartb`) that occur in exactly one chunk. The index side
   and query side must mint *identically*, which is why both live in `hybrid.py`.
4. **The RRF score is not a relevance signal.** Fusion scores are computed from *ranks*, so
   "how do I fix my car engine" came back scoring **0.70 — identical to the best real query**.
   Every question looked equally well-grounded. The golden rule "if retrieval returns nothing
   relevant, refuse" was *unenforceable* until `is_grounded()` existed, which measures true
   cosine relevance (real questions 0.37–0.67; off-topic 0.08–0.16; threshold 0.25).
5. **Two Schedule tables shipped corrupt.** The Fourth Schedule's Parts A and B carry a
   full-width *caption* above the table; the parser grew the table from line 0, no prefix ever
   parsed as a table, and the whole Schedule silently fell back to raw layout text — which
   welds each row's cells together. Fixed by finding where the table *starts* (the header row
   is the one whose row-number column is filled), not just where it ends.

### Phase 3b — Cited generation + failover (`5215123`, `43c57c1`) · 2026-07-14

`generate()`: retrieve → `is_grounded()` gate → strict prompt → `claude-sonnet-5` → gpt-4o-mini
failover on 429/5xx/network, with the provider tagged for LangSmith.

Two properties are enforced **in code**, not left to the model:
- An ungrounded topic **never reaches an LLM** — the refusal happens before any generation call.
- The disclaimer is appended deterministically, so it survives regardless of how well the model
  followed instructions.

**Model decision (human, 2026-07-14):** `claude-sonnet-5`. It **rejects the temperature
parameter outright** (API 400), so factual determinism is enforced by the strict prompt contract
instead of sampling params. Its adaptive thinking counts toward `max_tokens`, hence the 8192
headroom. *This has a consequence that surfaced later — see §4.*

### Eval harness (`f3ce093`) · 2026-07-14 — built early, on request

`eval/run_eval.py` + an 18-case golden set (plus 2 `must_refuse` and 3 `must_not_assert`).

**Not RAGAS.** `ragas` 0.4.x hard-imports `langchain_community.chat_models.vertexai`, removed in
langchain-community 0.4.x, so `import ragas` dies against this LangChain 1.x stack. Pinning
LangChain back is not an option — LangGraph 1.x's `interrupt()` is what Phase 5's human review
is built on. So the same four judge dimensions are computed **directly** (judge: gpt-4o-mini).
RAGAS proper remains **Phase 7**, as a build/CI dependency only.

### Phase 4 — Deploy + keep-alives (`b69a4bd`) · 2026-07-14

- [app.py](../app.py) — the deployed surface. Topic in, draft out, plus the six sources it
  stands on (citation, page, authority status, relevance) so any claim is verifiable in seconds.
  Thin by design: no golden rule is re-implemented here, so the UI cannot weaken one.
- [.github/workflows/keepalive.yml](../.github/workflows/keepalive.yml) — GitHub Actions cron,
  twice daily. Qdrant's free tier suspends after ~1 week idle (taking the index with it) and
  Streamlit sleeps after ~12h. GitHub Actions rather than the n8n the design doc names: zero new
  infrastructure, and n8n does not exist until Phase 8.
- [tests/test_app.py](../tests/test_app.py) — drives the real app through Streamlit's own
  `AppTest`: a grounded topic must render a cited draft with the disclaimer and all six sources;
  an ungrounded one must render the refusal and offer nothing to download.

### Full-code audit (`907c860`) · 2026-07-14

A line-by-line read of every file. **Eight real defects** — see §4.

---

## 3. Current state

| | |
|---|---|
| **Corpus** | 81 chunks (49 Act + 32 Rules), zero missing sections/rules, no Hindi bleed-through, tables intact |
| **Index** | Qdrant Cloud `dpdp`, 81 points, hybrid dense+sparse, server-side RRF |
| **Generation** | claude-sonnet-5 → gpt-4o-mini failover, grounding gate + disclaimer enforced in code |
| **App** | Written and tested; **not deployed** — needs a push + your Streamlit Cloud click-through |
| **Keep-alives** | Written and verified against live Qdrant (`"status":"green"`); **not running** — needs the push + GitHub secrets |

**Gates (all green):** chunks 27/27 · retrieval ALL PASS · generation ALL PASS · app ALL PASS ·
scaffold 6/6.

**Eval (18 golden + 5 negative cases):**

| Metric | Score | Target | |
|---|---|---|---|
| recall@6 | 100.0% | 80 | PASS |
| MRR | 79.2% | 70 | PASS |
| NDCG@6 | 82.1% | 75 | PASS |
| faithfulness | 98.3 | 85 | PASS |
| relevance | 100.0 | 85 | PASS |
| coherence | 91.1 | 80 | PASS |
| conciseness | 84.4 | 75 | PASS |
| answered | 100.0% | 100 | PASS |
| **citation_validity** | **94.4%** | **100** | **FAIL — see §4** |
| date_honesty | 100.0% | 100 | PASS |
| gate_refusal | 100.0% | 100 | PASS |
| no_false_assertion | 100.0% | 100 | PASS |

*R-Precision (55.6%) is reported but deliberately **not gated**: it scores ordering inside the
top-6, and all 6 chunks reach the prompt regardless, so it cannot change the output. Do not
"fix" it.*

**Latency (measured in the app path):** retrieval ~1.6–2.6s (the Qdrant Cloud hop dominates),
generation ~19s, end-to-end ~19s. Streaming was not built — it would fork a second code path
through `call_llm`, where failover, the disclaimer, and the refusal check all live.

---

## 4. The open failure: the model cites what it was never shown

Asked *"What is the penalty for not reporting a data breach?"*, the model produced a draft citing
**`[DPDP Act 2023, s.8]` — a section that was not among its six retrieved sources.** Retrieval for
that query is deterministic (verified across repeated runs); s.8 never appears. The model reached
for it **from its own memory of the Act**, because it "knows" breach duties live near s.8.

This is the precise failure the system exists to prevent, and it was **silent**. It is also
intermittent: Sonnet 5 accepts no temperature parameter, so earlier eval runs scored
citation_validity 100% by luck. **A prompt rule is not a control here. Only a check is.**

What exists now is a **detector, not a fix**:
- `Draft.fabricated()` returns any citation naming a provision absent from `Draft.hits`.
- `generate()` logs it loudly.
- `app.py` renders a **"Fabricated citation — do not publish"** banner above the draft.

**The eval's `citation_validity` gate therefore reads RED (94.4%), and that is the gate telling
the truth.** Do not make it green by weakening it. It goes green when Phase 5's `cite_check`
lands: parse every citation, validate it against chunk metadata, feed the specific failure back
to the model, retry (max 2), and escalate to a human rather than auto-passing.

> **RESOLVED in Phase 5 (§7).** `cite_check` shipped exactly as described above, and
> `citation_validity` now reads **100%** across all 18 golden cases — green because the failure
> is *caught and repaired*, not because the gate was loosened. The gate itself is unchanged.
> The detector (`Draft.fabricated()`) is still there and still load-bearing; what changed is
> that something now *acts* on it.

---

## 5. Defects found by the full-code audit (`907c860`)

Recorded because each one is a lesson about a *class* of mistake, not a one-off.

**Would have broken production:**

1. **`app.py` crashed on a fresh clone.** `st.secrets` **raises** `StreamlitSecretNotFoundError`
   when no `secrets.toml` exists — it does not return empty. That file is gitignored, so a clean
   checkout running from `.env` (the documented local setup) died on startup. The Phase 4 test
   could not see it: it runs from the repo root, where a blank placeholder happens to exist.
2. **A blank secret shadowed a real key.** Streamlit exports `secrets.toml` into `os.environ` as
   it parses it — *blanks included* — and `load_dotenv()` never overrides an already-set var. So
   the empty placeholder produced `OPENAI_API_KEY=""` and the app died "not set" with a perfectly
   good `.env` beside it. `app.py` now evicts blank env vars at startup.
3. **A spurious citation handle promoted the wrong provision.** `"sub-rule 3 of rule 6"` minted
   `rule3`, pinning **r.3 (Notice)** level with the rule actually asked about. The `(?<!sub)`
   guard existed on the *sections* branch and was never mirrored to *rules* — even though the
   Rules say "sub-rule" as often as the Act says "sub-section". These handles feed the rank-1
   pin, so a false one does not merely add noise: it **promotes the wrong law**. Golden-set MRR
   went 79.2 → 84.7 once fixed.

**Four ways a broken system reported green:**

4. **A refusal scored as a pass.** Nothing checked `d.grounded` for golden cases, so a system
   that refused all 18 questions scored **100% on citation_validity and date_honesty** — an empty
   draft cites nothing, so it fabricates nothing and mis-dates nothing. Three of the four
   non-negotiable gates were passable **by answering nothing at all**. New `answered` gate.
5. **An uncited draft scored 100% citation validity.** `cited - retrieved` is empty both when
   every citation checks out *and* when there are none at all.
6. **`must_not_assert` was a substring blocklist.** A near-miss fabrication — *"GDPR treats
   consent as one of six lawful bases"* — matched none of the forbidden strings and scored clean,
   while asserting law that is not in the corpus at all. Now backed by the faithfulness judge,
   which by construction cannot support a claim absent from the context.
7. **Three test files passed unconditionally under pytest.** They collect failures into a list
   that only the `__main__` block inspects, so under the planned Phase 7 CI runner a completely
   broken retriever would come back **green**. A bridge assertion was added to each.

**Weak assertions that could not catch what they were written to catch:**

8. The schedule page probe was `"PART A"` — printed on **p.9 (First Schedule) *and* p.13
   (Fourth)** — so a cross-schedule page swap passed. Each Part is now bounded to its own
   schedule's page span (mutation-tested: the old probe passes the buggy page; the new one
   catches it). Also fixed: vacuous "mints nothing" assertions (`set() <= anything` is always
   true), a `scroll(limit=200)` that would silently skip chunks, and a build-deps leak check that
   goes vacuous the moment `requirements.txt` is pinned — which its own header instructs you to do.

**Known and deliberately left:** `parse_rules` stores one page per rule rather than per line, so
if a Rule ever exceeded 1200 tokens its split chunks would report the wrong page. No rule does
today (0 of 32 chunks are split), so it is latent.

---

## 6. The lessons, distilled

- **Green tests are not proof.** Every deep audit on this project found a real bug that a fully
  passing suite had missed. Diff output against the source; do not re-run tests and report green.
- **A provision does not state its own subject.** Hit three separate times (Act titles, Schedules,
  citation handles). The fix always belongs in the **embedding** (`index_text`), never the payload
  — generation must only ever see pristine legal text.
- **Assert invariants, not examples.** Where two functions exist only to agree (the index-side and
  query-side handle minters), loop the whole domain and assert the agreement. Example cases only
  test the cases you thought of.
- **The dangerous failure reads plausibly.** A column-interleaved penalty table, a citation
  fabricated from memory, a draft that is faithful to the *wrong* provision — none of them look
  wrong. Only a mechanical check catches them.
- **Fail loudly.** No bare `except`, no silent fallback. If Anthropic fails and OpenAI serves, it
  is logged and tagged. If a citation is fabricated, it is shown to the human in red.

---

## 8. What happens next

**Blocked on the human** (nothing Claude can do):
1. **Push** — the commits are still local; nothing has left this machine.
2. **Deploy** — Streamlit Cloud → this repo → `app.py` → Python 3.12, then paste the 7 secrets.
3. **Turn the keep-alives on** — GitHub Actions *secrets* `QDRANT_URL`/`QDRANT_API_KEY`, and the
   *variable* `STREAMLIT_APP_URL`. The runbook is in [README.md](../README.md) → "Deploying".

**~~4. Citation spot-check~~ — DONE 2026-07-14. Definition of Done #3 is CLOSED.** Two fresh
drafts through the Phase 5 graph (both `passed`, 100% traceability, zero fabrications); five
citations traced to the printed statute and confirmed by the human against the PDFs:

| Draft claim | Citation | Page | Statute |
|---|---|---|---|
| Safeguards failure → ₹250 crore; notice failure → ₹200 crore | `Act, Schedule` | Act p.21 | Schedule rows 1–2, both amounts exact |
| Must protect data by reasonable security safeguards | `Act, s.8` | Act p.7 | s.8(5) |
| Must intimate BOTH the Board and each affected Data Principal | `Act, s.8` | Act p.7 | s.8(6) |
| Applies irrespective of contrary agreement / the Principal's own duties | `Act, s.8` | Act p.7 | s.8(1) |
| 72-hour Board follow-up; intimation via her user account | `Rules, r.7` | Rules p.3 | r.7(1)–(2) |

Every future-dated provision was correctly stated as taking effect 13 May 2027.

*Method note, recorded because the failure mode is instructive:* the first probe flagged r.7 and
the Schedule as page mismatches. **Both were artifacts of the probe, not defects** — the chunker
reads with **pdfminer** while the probe used **pypdf**, and the two differ on dash/space encoding;
the Schedule is additionally stored as a reformatted markdown table, which raw-text matching can
never match. Confirmed independently that r.7 is on Rules p.3 and THE SCHEDULE on Act p.21. A
verification tool that disagrees with the artefact is not automatically right — see
[[dpdp-chunker-two-pdf-libraries]].

**Next build phase — Phase 6:** human review console. See §7 for what Phase 5 landed, and §8
for what Phase 6 did.

Then: Phase 7 LangSmith + RAGAS CI gate · Phase 8 n8n publishing.

---

## 7. Phase 5 — LangGraph + `cite_check`: the answer to §4

§4 ended with *"a prompt rule is not a control here. Only a check is."* This is the check.

`src/graph/pipeline.py` is a LangGraph `StateGraph`:

    retrieve ──(ungrounded)───────────────────────────────> END   no_grounded_source
       │ grounded
       v
    draft <──────────(failed, attempts < 3, + feedback)───┐
       │                                                  │
       v                                                  │
    cite_check ──┬── ok ───────────────────────────────> END   passed
                 ├── failed, retries left ───────────────┘
                 └── failed, out of retries ──────────> END   needs_human

`src/graph/cite_check.py` is deterministic and offline — no API call, so it cannot itself
hallucinate, and its whole test suite is free. It answers three questions, in the order they
can hurt you: does the draft **cite what it was never shown** (§4's failure); does it cite a
**not-yet-in-force** provision without saying when it starts; and what fraction of its legal
claims **carry a valid citation** (`traceability_score`, gate 0.9 per design §5.7).

`review_status` is the only thing a caller may trust. `app.py` now refuses to render a
`needs_human` draft as if it were sound, and the eval gates on it (`verified`, target 100).

### What the measurements forced, that the design did not predict

**1. Blind regeneration does not converge.** The first build discarded a failed draft and
redrew it from scratch. Measured on one topic across three attempts, each pass fixed the
flagged sentences and introduced *fresh* uncited ones elsewhere: traceability went
60% → 61% → 73% and escalated to a human. The retry now hands the model **its own draft back**
and asks for a surgical revision, keeping verified sentences verbatim. Same topic: passes.

**2. Structure is not decoration — it decides what counts as cited.** The first checker flagged
markdown headings (`## How the penalty is determined`) and every bullet in a list whose citation
sat on the stem sentence above it (`The Board must consider [DPDP Act 2023, s.33]:`). Those are
false positives *no redraft can fix* — the model rewrites the body, keeps the heading, fails
again. And a false alarm is not harmless: it trains the reader to ignore the banner, which is
worse than not having one. `claim_units()` now drops headings and lets a bullet inherit its
stem's citation. A **bolded** line is a heading only if it has no sentence terminator — else a
draft could hide an uncited claim from the checker by bolding it.

**3. The drafter has to know the rule it is graded against.** Even after (1) and (2), *no*
topic passed on the first attempt: the model writes restatement sentences ("This means…",
"In other words…", "Note that these provisions take effect on…") uncited, and those *are*
legal claims. Rule 3 of `STRICT_SYSTEM` now states the machine's rule — restatements re-cite;
a list may carry its citation on the stem; sentences asserting no legal requirement need none.
Aligning the drafter with the checker is honest: **that rule is the contract.**

### Measured (full eval, 18 golden + 6 negative cases, final code)

| Gate | Phase 3b | Phase 5 |
|---|---|---|
| `citation_validity` (no fabricated citation) | **94.4% RED** | **100% PASS** |
| `verified` (cite_check's own verdict on the shipped draft) | — (did not exist) | **100% PASS** |
| `date_honesty` · `no_contradiction` · `gate_refusal` · `no_false_assertion` · `answered` | 100% | 100% |
| faithfulness / correctness | 96.7 / 98.3 | **98.3 / 99.4** |

**Zero escalations to a human across 18 cases, and zero fabricated citations.** The retry loop
is doing real work, not decorating: **14 of 18 cases needed a redraft** (12 recovered on
attempt 2, 2 on attempt 3) — i.e. in 14 cases the first draft would have shipped with an
uncited legal claim or a fabricated citation, and now does not.

**The price is latency, and it is not small:** generation P50 went **19s → 39.6s** (P95 67s),
because most drafts are written twice. That is the cost of the check, paid per draft, and it
is worth it — but do not "optimise" it away by raising the traceability gate or cutting the
retries. Get the *first* draft to pass instead (see 3 above; that is what took it from 0/18
first-attempt passes to 4/18).

### Known ceilings (do not mistake these for solved)

- `CLAIM_CUE` is a **cue-word list**. It under-detects a claim phrased without one, which
  *inflates* traceability, and it over-fires on business advice ("Organisations should use the
  runway to prepare"), which costs a redraft. It is a floor, not a proof.
- A citation can be **real but not actually support the claim it is attached to**. Nothing here
  detects that. Human review (Phase 6) is the backstop — this is why review is mandatory.
- Verification costs **1–3 Claude calls per draft** — only 4 of 18 golden cases pass on the
  first attempt, so most drafts are written twice. Latency doubled (§ Measured).

### Deliberately NOT built in Phase 5

- **The strict/marketing toggle.** It routes to `format_per_platform`, which does not exist.
  A marketing branch today would route *around* `cite_check` to nothing at all.
- **Multi-format fan-out.** Blocked on the same missing node; formats are style, and style on
  top of unverified citations is the liability §4 warned about.
- **`interrupt()` / checkpointer.** Phase 6. `review_status` is the field it will hang off.

**Still unanswered by the human:** the Act's long title / enacting formula is deliberately
unchunked (it is front matter, with no `type` for it in the metadata schema), so it is
**uncitable**. Marketing may want to quote it. Adding it is a schema change, so it needs a
decision first.

---

## 8. Phase 6 — the human review console: the backstop §7 said was mandatory

§7 ended on a ceiling it could not raise: **a citation can be real and still not support the
claim it is attached to.** `cite_check` cannot see that. Nothing mechanical here can. The whole
design has said since day one that human review is the answer, and until now the "review" was a
banner and the honour system — the app happily handed you a `.md` file the moment the *machine*
was satisfied.

`human_review` is now a node **inside the graph**, and it is where the graph stops:

    cite_check ──┬── failed, retries left ──> draft
                 ├── no_grounded_source ────> END          (nothing was drafted to review)
                 └── passed | needs_human ──> human_review
                                                  │  interrupt() — the run STOPS here
    human_review ──┬── approved ────────────> END          decision="approved"
       ^           ├── rejected ────────────> END          decision="rejected"
       │           ├── edited ──> apply_edit ─┘            (re-checked, no LLM)
       └───────────┴── anything else ─────────┘            invalid input: re-ask

**Why in the graph and not as a button in `app.py`.** Phase 8's `publish_webhook` attaches to
the `approved` edge. That makes publication *unreachable* except through a human verdict — a
property of the state machine, not of the UI. A button can be got wrong by the next person who
edits the page; an edge that does not exist cannot be clicked around. This is the same reason
the eval grades `run()` and not `generate()`.

### Two verdicts, two fields — deliberately not merged

| field | authority | values |
|---|---|---|
| `review_status` | the **machine** | `passed` · `needs_human` · `no_grounded_source` |
| `decision` | the **human** | `approved` · `rejected` · *(empty: still awaiting one)* |

Overloading one field would have been shorter and would have destroyed the only case that
matters. A reviewer **may** approve a `needs_human` draft — they are the higher authority, and
a real-citation-on-the-wrong-claim is exactly the failure only they can catch. But then both
facts must survive: the machine said no, the human said yes, and *the note says why*. The
console **refuses an override with no note** (an override with no stated reason is
indistinguishable from a mis-click), and the page renders it as *"Approved by a human,
overriding a FAILED machine check"* — never the same green banner as a clean pass. Laundering
an override into a pass is how an audit trail dies at the UI.

The download button — the one affordance that lets a draft leave the building — now hangs off
`decision == "approved"`, not off the machine's verdict. Phase 5 had it hanging off `passed`.

### An edit is RE-CHECKED, not re-drafted

`apply_edit` costs **zero LLM calls** and does not touch `attempts` (the retry budget belongs to
the model's failures, not the human's edits). But it is not trusted either: a reviewer fixing a
flagged sentence types citations *by hand*, and a hand-typed citation can name a provision that
was never retrieved exactly as the model's could. It faces the same deterministic `check()`, and
the machine verdict is recomputed — an edit that fixes a `needs_human` draft turns it green, one
that breaks a passing draft turns it red, and the reviewer sees their own edit's verdict before
approving. The disclaimer is re-appended even if they delete it (golden rule: every piece carries
it).

### What the measurements forced, that the design did not predict

**1. A lost review thread SILENTLY approves nothing.** Measured on langgraph 1.2.9: resuming a
thread whose checkpoint is gone does **not** raise. It re-runs the graph *from START* with an
empty input and **discards the resume value**. Streamlit Community Cloud sleeps after ~12h and
restarts empty, so the production path is: reviewer returns to an open tab, clicks **Approve**,
the UI says it worked — and nothing was approved, while a fresh retrieve+draft quietly burns API
calls. `resume()` now checks `get_state()` first and raises `LookupError` on a dead thread, and
the app says so and drops the stale draft. A second, contradictory click on an *already finalized*
thread is ignored rather than flipping the verdict (a stale tab must not turn an approval into a
rejection).

**2. `st.secrets` overwrites a real env var with a blank, and only import order was saving us.**
Reading `st.secrets` exports the whole file into `os.environ` at parse time — blanks included —
and the local `.streamlit/secrets.toml` is an all-empty placeholder (the real local keys are in
`.env`). `app.py` has evicted those blanks since Phase 4, but it was then relying on the
module-level `load_dotenv()` *inside* `src/` to put the real keys back — which only runs if
`app.py` is the first thing to import `src`. The new Phase 6 test imports `src` first, and
`OPENAI_API_KEY` was gone for the whole process. It was never a Streamlit bug; it was a hidden
ordering dependency in our own startup. `app.py` now calls `load_dotenv()` itself, right after
the eviction, and owns its environment instead of inheriting it by luck. (Cloud is unaffected —
no `.env` there, and the secrets are real — but a future multipage entrypoint would have hit it.)

**3. The checkpointer would have broken in production, on someone else's release.** langgraph
warns that it deserializes unregistered types (our `Hit`, `Draft`, `Report`) from a checkpoint
today but **will block it in a future version**. `requirements.txt` is unpinned and the app is
already live, so that flip arrives on Streamlit Cloud as an upgrade we did not make, and takes
`resume()` — the review console — with it. The three types are now on an explicit
`allowed_msgpack_modules` allowlist, which is also the safer posture (an allowlist, not
"deserialize anything"). Verified by running the whole suite under `LANGGRAPH_STRICT_MSGPACK=true`,
i.e. against the future default.

### Verified

`tests/test_review.py` — **32 checks, all green, ~1s, zero API calls** (retrieval and drafting
are patched, so every verdict is a property of the graph rather than of the weather at
Anthropic). It attacks the ways the gate could be skipped: the graph running past it; a bad
resume value (`"maybe"`, `""`, `"APPROVED"`, `None`, `"publish"`) being read as consent — each
one re-asks the human instead, and the thread stays approvable afterwards; a rejection
finalizing anyway; an edit smuggling in a fabricated citation or dropping the disclaimer; a lost
thread swallowing a verdict; a refusal being parked in front of a human with nothing to approve.

`tests/test_app.py` — the live end-to-end path through a real interrupt and a real `resume()`:
a grounded topic drafts, is **not** downloadable, gets approved, and *then* downloads. Plus the
override case rendered from a canned state. All green, and the Phase 5 gate
(`tests/test_cite_check.py`) still passes unchanged.

### Known ceilings (do not mistake these for solved)

- **A paused review dies with the process.** `InMemorySaver` — a Streamlit Cloud restart drops
  every in-flight review. Survivable, because a lost review loses no *published* work (only an
  unfinished draft) and `resume()` refuses a dead thread loudly. The upgrade path is a
  Postgres/SQLite checkpointer, and it becomes necessary the day reviews must outlive a restart
  — i.e. the moment there is a review *queue* rather than one reviewer in one session.
- **One session, one reviewer.** There is no queue, no assignment, no second pair of eyes. The
  design's second human gate lives in n8n (§5.10), not here.
- **The console cannot make a bad reviewer good.** It puts the citation, the `source_ref` and
  the **page number** in front of them and asks for three checks. It cannot verify they looked.

### Deliberately NOT built in Phase 6

- **The strict/marketing toggle and multi-format fan-out.** Still blocked on
  `format_per_platform`, for the reasons in §7. Unchanged.
- **`publish_webhook`.** Phase 8. The `approved` edge is the socket it plugs into; until it
  exists, an approved draft's exit is the download button.

---

## 9. The audit — eight real bugs a fully-green suite was hiding

Every suite passed. Every one of these was live anyway. (See [[green-tests-are-not-proof-reconcile]]:
this is the fourth deep audit on this project, and the fourth to find a real bug behind a green
suite. Re-running the tests is not auditing.)

**Two were shipping wrong content, today.**

*The Rules gazette's signature block was inside a legal table cell.* The Rules PDF signs off with
`[F. No. AA-11038/1/2025-CLandES]` / `AJIT KUMAR, Jt. Secy.` — two lines that sit, on the last
page, **inside the horizontal span of the Seventh Schedule's third column**. So `looks_tabular`
held, `table_span` ran the table over them, and `build_rows` folded them into row 3 as
continuation text. The shipped chunk named a civil servant as the **"Authorised person"** for
assessing a Significant Data Fiduciary. A model could quote it as statute and cite it as
`DPDP Rules 2025, Seventh Schedule` — and **`cite_check` would pass it**, because the citation is
real; only the cell contents are not. `NOISE` had only ever carried the *Act's* colophon. This is
the same failure as [[dpdp-schedule-tables-caption-trap]], at the tail instead of the head.

*"the schedule" minted a citation handle.* `the` sat in the ordinal list, matched
case-insensitively, so `"What is the schedule for DPDP compliance?"` minted `theschedule` — the
maximal-IDF handle for the Act's **penalty table** — which `search()` then **pins to rank 1**,
displacing a real source out of the top-6. "Schedule" is everyday vocabulary for a *marketing*
content system. A minted handle is never merely noise; it is a promotion. Same class:
`"part b of the platform"` pinned all four Schedule-Part chunks. Fixes: only a capitalised
"the Schedule" (the statute's own proper noun) mints the Act's handle, and a Part handle now
requires a Schedule in the query.

**Two were mine, hours old, in the Phase 6 code above.**

`with_disclaimer()` cut the text at the **first** occurrence of the disclaimer's opening words.
A reviewer appending a correction *below* the disclaimer had it **silently deleted**, and
`cite_check` then graded a draft that was not what the human wrote. A body that merely *mentioned*
the phrase was truncated to the disclaimer alone. Silent data loss on the one path CLAUDE.md calls
mandatory — strictly worse than the duplicated disclaimer it was written to prevent. It now
removes only an exact **trailing** copy and never deletes anything else; a mangled copy is left in
place, logged, and flagged. The real defence is upstream: `app.py` hands the reviewer
`draft.body()`, so the disclaimer is never in the edit box to be mangled.

And the test written for *that* found worse: `Draft.body()` and `claim_units()` split on the
**first** disclaimer, so every sentence after a stray one was **invisible to cite_check while
still shipping in the draft**. Measured: an uncited *"Fines reach 250 crore."* placed after a
stray disclaimer scored **100% traceability and passed**. Both now cut at the **last** one.

**Three were the gates themselves lying.**

- `eval/spot_check.py` printed *"Every citation is a retrieved provision"* and **exited 0** on a
  draft whose own report read `fabricated=['DPDP Act 2023, s.99']`. `claim_units` drops headings
  (correctly — a heading is not a claim), so a citation hiding in `## Penalties under [s.99]` was
  never compared against the hits. **This is the artefact a human signs the Definition of Done
  against.** It now seeds from every citation in the draft, wherever it appears.
- `no_contradiction` was the **one** judge field that defaulted to the *passing* value. Every
  other defaults to `0`, which fails its gate. A judge returning valid JSON without the key — all
  `response_format=json_object` actually guarantees — scored a clean 100% on a draft asserting a
  wrong deadline. Now fails closed. (`bool("false")` is `True`, so the coercion was wrong in the
  other direction too.)
- The `must_not_assert` loop still carried the `cited - retrieved` asymmetry the golden loop had
  already fixed: empty **both** when every citation checks out and when the draft cited nothing.

**One was three regexes that existed only to agree.** `Draft.citations()`, `cite_check._CITE` and
`cite_check.check` each spelled the citation pattern out, and none tolerated `[ DPDP...]` or
`[**DPDP...**]`. A **fabricated** citation written in bold was therefore invisible to
`fabricated()` — and if its sentence carried a second, valid citation, the draft shipped as
`passed`. One shared `CITE` now, swept over all 81 citations × 5 bracket forms.
([[assert-invariants-not-examples]]: functions that exist only to agree must be swept, not sampled.)

**One was latent, and that is the worst kind.** `parse_rules` gave every split chunk the page where
the *rule* began; `parse_act` has used `locate_page` for exactly this since Phase 2. No rule reaches
`MAX_TOKENS` today, so the chunk diff is empty — an amended Rules PDF would simply have started
pointing reviewers at the wrong page, with nothing failing.

**Verified:** all 7 suites green; the 81-chunk diff read field-by-field (one chunk, 55 characters);
index/query mint parity swept over every provision; the live Qdrant payload confirmed clean after
re-indexing.

**Open — needs a human decision, not a guess.** The Fourth Schedule's trailing `Note:` block
*defines* "clinical establishment", "educational institution" and "allied healthcare professional"
— the very terms **Part A's rows are built from** — but the Parts are cut at the `PART A`/`PART B`
markers, so the Note lands wholly in **Part B**. Part A names those classes and defines none of
them. Moving or duplicating it changes a legal chunk boundary (CLAUDE.md §10).

## 10. The embedding swap — `-small` → `-large` · 2026-07-17

It began as an audit request — *"check if there are errors in the code"* — and the code was clean.
The errors were two layers out, in the environment, and the first one hid the second.

**The fault chain.** 14 of 85 tests failed, none of them on code. The outer layer was this
machine's Zscaler TLS interception ([[dpdp-build-machine-zscaler-tls]]): every SDK call died on
`CERTIFICATE_VERIFY_FAILED` until `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` were set. With that out of
the way the real fault surfaced — the OpenAI project **403'd on `text-embedding-3-small`**, while
`models.list()` cheerfully listed that very model among the four the project was allowed. Chat
models answered fine; only the embeddings *endpoint* was denied, which points at a restricted
key's scope rather than the model allowlist. Every retrieval path starts at `embed_dense()`, so
**100% of the system's retrieval was dead — and 71 offline tests stayed green throughout.**
([[green-tests-are-not-proof-reconcile]], again.) The keep-alive would not have caught it either:
it pings `/health`, which by design touches neither OpenAI nor Qdrant, so production can rot
silently. A new key cleared the 403, and the human took the opening to move the model up.

**The swap itself is two lines.** `DENSE_MODEL`/`DENSE_SIZE` are one definition in `hybrid.py`,
imported by the indexer, so index and query sides cannot drift. Everything around it is the work:
the collection dropped and recreated (1536 cannot hold 3072), all 81 chunks re-embedded and
re-indexed (~$0.01, no PDFs needed — `data/processed/` is enough), and every
`text-embedding-3-small` mention corrected across CLAUDE.md, the README, `eval.yml` and these docs.

### What the measurement forced, that the plan did not predict

`MIN_RELEVANCE` is not a constant — it is a **calibration**. 0.25 was measured against `-small`'s
cosine distribution (real questions 0.37–0.67, junk 0.08–0.16). `-large` scores real questions
**lower**: the worst real question in the suite now sits at **0.319** against the margin test's
floor of 0.30 — **0.019 of daylight**, where `-small` had room to spare. Junk was unchanged at
0.108. The threshold held, so nothing was adjusted. But a swap done without re-measuring could
have silently turned junk into "grounded" — the grounding golden rule failing quietly, which is
the only way it ever fails. `tests/test_retrieval.py` is the gate; CLAUDE.md §5 now says so out
loud, because the next person to swap a model will not derive this from the diff.

### Measured (full eval, 18 golden + 5 negative cases, CI run `29531758199`, sha `0d63042`)

| Gate | Phase 5 (`-small`) | 2026-07-17 (`-large`) |
|---|---|---|
| faithfulness / correctness | 98.3 / 99.4 | **99.4 / 100.0** |
| relevance · coherence · conciseness | not recorded | **100.0 · 90.6 · 85.0** |
| recall@6 · MRR · NDCG@6 | not recorded | **100% · 90.7% · 90.4%** |
| `verified` (cite_check's own verdict) | 100% | **100%** — zero escalations |
| `citation_validity` · `date_honesty` · `gate_refusal` · `no_false_assertion` · `answered` · `no_contradiction` | 100% | **100%** |
| first drafts needing a redraft | 14 of 18 | **12 of 18** |
| generation P50 | 39.6s | **18.8s** |

**Do not read that table as "`-large` improved the system."** The generator changed twice between
those two columns (Sonnet 5 → gpt-5-mini → gpt-5.6-terra), and cross-reference expansion plus
query decomposition landed in between. The honest claim is the one the evidence supports:
**nothing regressed, and every figure is at its best recorded value.** Crediting the embeddings
would be precisely the plausible-sounding, unearned conclusion this project exists to refuse.

(Retrieval P50 was **321ms in CI** against ~2.9s on the build machine. That 9× is the Zscaler
MITM, not the system. Do not go optimising local latency.)

### The first full-gate run died on a 401 that was not real

Terra 401s **spuriously** — documented since 2026-07-16 at ~10%, re-measured off the failing run
at **7 of ~50 calls (14%)**. `_invoke_gpt` already retried it, because a 401 must never fail over
to Claude (a genuinely broken OpenAI config would then be masked forever by a working failover) —
but only 3 attempts at 0.5s/1s. One draft call drew three in a row, so the loop read OpenAI's
flakiness as a real auth fault and propagated it: **the run died at case 16 of 18, throwing away
15 cases of paid drafts and judge calls, with no report written at all.** At 14%, three-in-a-row
is ~0.3% per call but **~13% per 50-call run** — a coin-flip every few evals.

Now 5 attempts backing off 1s/2s/4s/8s (~0.3% per run). The spacing matters as much as the count:
0.5s lands inside whatever propagation window causes this, which is why the old backoff lost
*twice* in the same run. A real fault still fails every attempt and still propagates, 15s later.

**The passing run does not prove that fix.** The re-run drew **zero** 401s — odds of ~0.06% across
50 calls at a 14% rate, so terra simply went quiet. What proves the retry is
`tests/test_generation.py::test_b2`, which drives both paths offline: a transient 401 is survived,
and a persistent one reaches the caller without ever touching Claude. A green run is not evidence
for a fix the run never exercised.

The code had called its own shot, and that is the lesson worth keeping: the `ponytail:` note on
`AUTH_RETRIES` read *"Revisit if the rate climbs above ~10%."* It had climbed. Nobody re-read it
until it bit. **A comment that names its own trigger condition is worth exactly as much as the
next person's attention.**

### Known ceilings (do not mistake these for solved)

- **The relevance margin is thin.** 0.019 above the floor. The next corpus or model change is
  likelier to break the margin test than anything else here — re-measure, do not re-tune the gate.
- **One flaky call can still nuke a whole eval run.** The retry makes it ~0.3% instead of ~13%,
  but any unhandled error mid-loop still discards every case before it and writes no report.
  Left alone deliberately: per-case `try/except` is how a real failure gets masked.
- **The old key's 403 was never explained**, only routed around. `models.list()` and the
  inference endpoint disagreed; a restricted key's scope is the theory, not a finding.
