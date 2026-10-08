# HANDOFF — DPDP RAG session, 2026-07-21

Context dump for the next session. Read `CLAUDE.md` first (it is binding); this file is what
happened on top of it. Everything below was **verified in-session** unless marked *(assumed)*.

---

## 0. TL;DR — where things stand

- The **`s.6(1-8)` citation fix is LIVE** on Render (commit `33c41a9a`, deployed 08:19Z).
- The **rich LinkedIn style presets + the n8n dropdown split are built**; n8n side is **live**,
  but the matching `generate.py` is **NOT yet uploaded**.
- A **guideline-sync system** (docs = source of truth → `generate.py`) + **CI drift guard** is built.
- **`upload_2026-07-21_final.zip` (11 files) is ready to upload and has not been uploaded yet.**
- Full eval: **ALL GATES PASS**. LangSmith tracing: **active** (local + prod).

---

## 1. Architecture — three surfaces, one core

All three share `src/generation/generate.py`, `src/graph/pipeline.py`, `src/graph/cite_check.py`,
`src/retrieval/hybrid.py`.

| Surface | How it runs | Style support | Updated by |
|---|---|---|---|
| **Render API** `dpdp-rag-api` | FastAPI `/generate` → `run_headless()` | **yes** (`style` param) | GitHub push → auto-deploy |
| **Streamlit** `app.py` | imports the pipeline **in-process**; `run()` + `resume()` (interactive human review) | **no** — `run()` takes no `style`, always default prose | GitHub push → auto-deploy |
| **n8n** "DPDP Content W" | calls the Render API over HTTP | **yes** | **edited directly** (MCP/UI), *never* from GitHub |

**Critical:** GitHub upload updates Render **and** Streamlit. It does **not** touch n8n. n8n is a
separate cloud system edited directly.

### n8n "DPDP Content W" flow (id `zmenPhZYryCSz5N7`, active, certinal.app.n8n.cloud)
```
Form → Normalize Input → route(News | Reference-link | Direct)
  ├─ "Generate Ideas (News/Link)"  ← in-n8n Anthropic LLM, IDEATION ONLY (cites nothing)
  → Select Idea → Build Generate Payload
  → "Call DPDP RAG API"  POST https://dpdp-rag-api.onrender.com/generate  {topic, reference_link, word_count, style}
  → Build Doc Text (REVIEW BANNER + superscript cites + REFERENCES list)
  → Google Doc.  NO auto-publish.
```
**cite_check IS in the loop** (server-side, inside `run_headless`). The in-n8n LLM nodes only
brainstorm titles/angles — they never produce grounded legal claims.

### The style mechanism (the most-misunderstood part)
n8n sends only a **style KEY** (`blog` | `linkedin_article` | `linkedin_article_short` | `newsletter` | `""`).
The actual guideline **text** lives in the `STYLES` dict in `generate.py`, served by Render.
> **Update 2026-07-23:** `short_post` was **removed**; `LinkedIn Article Short` now maps to the new
> compressed-article preset `linkedin_article_short` (sourced from `LinkedIn_Article_Short_Instructions.md`).
> The narrative below predates this and still names `short_post` — treat it as history.
Editing `docs/style-linkedin-*.md` prose alone changes **nothing at runtime** — see §5.

---

## 2. What changed this session

### 2.1 Style-guide docs + samples (`docs/`)
Audited and fixed 10 defects. The two that mattered:
- **Penalty slab was wrong.** Verified from the `DPDP Act 2023, Schedule` chunk: **₹250 crore is
  ONLY the s.8(5) security-safeguards slab.** Breach-notification s.8(6)=₹200cr, children s.9=₹200cr,
  SDF s.10=₹150cr, s.15 duties=₹10,000, **everything else = residuary, up to ₹50 crore.** A
  consent-withdrawal failure is residuary → **₹50 crore**, not ₹250cr. Both guides now warn about this.
- **Citation format.** `cite_check` parses **bracketed** citations via `CITE =
  re.compile(r"\[\s*\*{0,2}\s*(DPDP[^\[\]]*?)\s*\*{0,2}\s*\]")` — it must be in `[...]` **and start
  with "DPDP"**. A bare `[s.6(4)]` or prose "under s.8(5)" is invisible → scored uncited.

Also: date attribution corrected, `- a.` double-bullets fixed, redundant hashtag dropped, draft
gazette `G.S.R. 02(E)` warning added, out-of-band-facts clarifier added to the authority blocks.
Samples re-rendered with **superscript citations + a numbered References list** (matching what the
n8n Build Doc Text node actually publishes).

### 2.2 The `s.6(1-8)` fix — the significant technical find
`cite_supported()` requires the **retrieved chunk's citation to be a PREFIX of the draft's**. s.6 is
chunked as the **range** `"DPDP Act 2023, s.6(1-8)"`, so `s.6(4)` was flagged **FABRICATED** even
though (4) is inside that slice. (s.8 is chunked clean as `"s.8"`, so `s.8(5)` always worked.)

**Fix:** added `_within_range_chunk()` in `src/generation/generate.py` — a draft citing a *single
numeric* sub-section validates against a numeric-range chunk when `lo <= N <= hi` **and**
`_own_marker()` confirms `(N)` is genuinely in that chunk's text. Deliberately narrow:
- `s.6(9)` (outside the span) → rejected · nested `s.6(4)(a)` → rejected · `s.6(4)` vs the `s.6(9)`
  slice → rejected · `s.8` / `s.8(7)` truth tables **byte-for-byte unchanged**.

**Chosen over re-chunking + re-index** (same outcome, far lower blast radius — no destructive Qdrant
recreate, no chunk diff, no MIN_RELEVANCE re-measure). Gated by
`tests/test_cite_check.py::test_a4c`. **Deployed and live.**

> Optional future work: re-chunk s.6 to a clean `"s.6"` parent so cites read `s.6(4)` natively.
> That IS a re-index → requires sign-off (CLAUDE.md §10). Not done.

### 2.3 n8n changes (APPLIED, LIVE)
- **Build Doc Text** — added an `inRange` helper so `s.6(4)`-style cites keep their
  `[status] — file, p.N` metadata in the REFERENCES list (the JS mirror of the Python fix; the old
  `bySrc` used `startsWith` and dropped it). Verified 10/10 against a Node truth table.
- **Form dropdown split** → `LinkedIn Article Long (~1500 words)` + `LinkedIn Article Short (~800
  words)` (both route to `linkedin_article`, differing only in `word_count`), and `Short post` →
  renamed **`LinkedIn post (~120 words)`** (→ `short_post`). `Normalize Input` FORMATS map +
  `ALL_LABELS`/`ALL_SET` updated; **legacy labels kept** so open browser tabs don't break.
- Workflow validates: **0 errors** (2 pre-existing warnings on "Failed Ending" and "Find Folder" —
  unrelated, ignore).

### 2.4 STYLES presets rewritten (NOT yet deployed)
`linkedin_article` (3069 chars) and `short_post` (1632 chars, **with hashtags**) now carry the
condensed Katiyar voice — cold open, "practice has arrived / governance has not", labelled
hypothetical, phased mitigation, headings-as-claims, negation cascades, sustained second person.

**Smoke-tested live (3 generations):** voice faithful, `fabricated=[]`, dates honest, `s.6(1-8)` fix
validating throughout. **But all styled drafts escalate to `needs_human`** (traceability 54–77%)
because the voice's rhetorical framing sentences ("The danger is not X. It is Y.") read as uncited
claims to `cite_check`. **This is by design and safe** — marketing pieces go through human review
anyway. Do NOT "fix" it by loosening the gate.

### 2.5 Guideline-sync system (NOT yet deployed)
Solves: docs and runtime silently drifting.
- Each style doc got a **`<!-- PRESET:key --> … <!-- /PRESET -->` block = SINGLE SOURCE OF TRUTH.**
- `generate.py` holds a generated `_SYNCED_PRESETS` dict between
  `# >>> SYNCED-PRESETS-START <<<` / `# >>> SYNCED-PRESETS-END <<<`; `STYLES` references it.
- **`tools/sync_presets.py`** — `python tools/sync_presets.py` regenerates; `--check` exits 1 on drift.
  Pure stdlib, reads `generate.py` as **text** (does not import it) → no deps, no secrets.
- **`tests/test_presets_synced.py`** — drift guard in the test suite.
- **`.github/workflows/presets.yml`** — CI check (~10s, no pip install, no secrets). Its own workflow
  because `eval.yml`'s push trigger does **not** watch `docs/**`.

**Workflow for a guideline change:** edit the doc's PRESET block → `python tools/sync_presets.py` →
commit both → upload → Render + Streamlit redeploy.

---

## 3. Measurements (this session)

**Eval — ALL GATES PASS**
- Retrieval: recall@k **100%**, MRR 88.0%, nDCG@k 88.3%, HitRate 100%, R-precision 66.7% (ungated)
- Generation: faithfulness **98.9**, correctness 100, relevance 100, coherence 90.6, conciseness 84.2
- Golden-rule gates: citation_validity **100**, date_honesty **100**, no_contradiction 100,
  gate_refusal 100, no_false_assertion 100, answered 100
- `verified` **38.9%** (ungated by design) · traceability mean **76.4%** (11/18 below 90% → escalate)
- Latency: eval retrieval P50 3.3s, generation P50 16.7s / P95 23.1s

**LangSmith (30d, project `default`)**
- 1,031 root runs (1,007 local · 24 prod) · error rate **1.6%**, all on 07-15/16 (OpenAI-key
  incident), **zero since 07-17** · prod latency P50 **21.2s** / P95 57.5s
- LLM calls 785 — OpenAI 454 / Anthropic 331 (**42% Anthropic** — likely failover during that
  incident + the retrieval workflow's Claude calls; worth confirming recent failover is low)
- Tracing **active** in `.env` (`LANGSMITH_TRACING=true`) **and** Render prod (Linux/AWS traces prove it)

`DPDP_RAG_KPI_Report_2026-07-21.pdf` was generated at the project root — **build artifact, do not commit.**

---

## 4. Deploy state — what is live vs pending

| Item | State |
|---|---|
| `s.6(1-8)` cite fix | ✅ **LIVE** on Render (commit `33c41a9a`) |
| n8n Build Doc Text `inRange` | ✅ **LIVE** (applied via MCP) |
| n8n dropdown split + routing | ✅ **LIVE** (applied via MCP) |
| Rich STYLES presets | ⏳ in `generate.py`, **NOT uploaded** → dropdown works but uses the OLD thin preset until uploaded |
| Sync tooling + CI workflow | ⏳ built, **NOT uploaded** |
| **`upload_2026-07-21_final.zip` (11 files)** | ⏳ **ready, NOT uploaded** |

**The zip contains:** `src/generation/generate.py`, `tests/test_cite_check.py`,
`tests/test_presets_synced.py`, `tools/sync_presets.py`, `tools/__init__.py`,
`.github/workflows/presets.yml`, `docs/katiyar-style-profile.md`, `docs/style-linkedin-article.md`,
`docs/style-linkedin-post.md`, `docs/samples/*.md` (2).

⚠️ **Separate pending batch (NOT mine, not in the zip):** `eval/run_eval.py` and
`src/graph/cite_check.py` are modified in the working tree from the **07-20** batch and appear never
to have been uploaded. Confirm with the user before bundling them.

---

## 5. Non-obvious gotchas (these cost time to rediscover)

- **Docs ≠ runtime.** Editing `docs/style-linkedin-*.md` prose changes nothing live. Only the
  `<!-- PRESET -->` block + `tools/sync_presets.py` + a `generate.py` deploy does.
- **Zscaler TLS on the build machine.** Any outbound HTTPS needs `SSL_CERT_FILE` **and**
  `REQUESTS_CA_BUNDLE` (LangSmith uses `requests`, which ignores `SSL_CERT_FILE`). Canonical bundle:
  `~/.certs/ca-bundle.pem`. (I rebuilt one from the Windows cert store — 293 certs incl. the Zscaler
  root — when the env vars weren't set in the tool shell.) Never fix this in code.
- **`eval/run_eval.py` does NOT call `load_dotenv()`** — load `.env` into the environment first, or it
  fails on missing keys.
- **LangSmith `list_runs(limit=…)` caps at 100** — paginate (iterate the generator, break at a cap).
- **PowerShell zips:** `Compress-Archive` **flattens folder paths**. Use .NET `ZipFile` +
  `CreateEntryFromFile` with explicit entry names, and load **both** `System.IO.Compression.FileSystem`
  *and* `System.IO.Compression` (the `ZipArchiveMode` enum lives in the latter).
- **Scripts in scratchpad need `PYTHONPATH=<project root>`** to `import src…`.
- **Local git is ~46 commits "ahead" of `origin/main`** — an artifact of uploading files via the
  GitHub **web UI** ("Add files via upload" commits). Histories diverged; file content is synced
  manually. Each uploaded file **overwrites** GitHub's copy, so there's no partial-diff risk.
- **Render service** `srv-d9bimsbtqb8s73cnd770` — autoDeploy on commit to `main`, Docker,
  **`no-cache`** build (so no stale layers), health check `/health`.
- **Distinguish prod vs local traces** in LangSmith via `extra.runtime.platform`: Linux = Render,
  Windows = local.

---

## 6. User preferences / working style

- **Runs nothing locally.** Claude runs all verification and pastes the output. Never hand over a
  local command as the deliverable.
- **LangSmith must stay ON** — never pass `LANGSMITH_TRACING=false` / `LANGCHAIN_TRACING_V2=false`,
  even in throwaway test runs. (Stated explicitly this session.)
- Deploys by **uploading a zip's contents via the GitHub web UI**, then Render/Streamlit auto-deploy.
- Terse and action-oriented ("Do this", "Yes do it", "Do 1"). Wants the work done, then the summary.
- Live n8n edits and writes to external MCP destinations are **permission-gated** — expect the
  classifier to block them until the user explicitly approves that specific change.

---

## 7. Open threads / suggested next steps

1. **Upload `upload_2026-07-21_final.zip`** → makes the rich presets + sync tooling + CI live.
2. **Decide on the 07-20 batch** (`eval/run_eval.py`, `src/graph/cite_check.py`) — still unuploaded.
3. **"Is there a harsher evaluation method?"** — the user asked this and interrupted before an
   answer. **Never answered.** Options to cover: adversarial/ensemble judging, stricter grounding
   (claim-level entailment), lowering `MIN_TRACEABILITY`'s tolerance, negative/adversarial goldens.
4. **Judge model:** user asked about switching judge `gpt-4o-mini` → `gpt-5.6-terra`. **Recommended
   against** — terra is the *drafter*, so it would grade its own output (self-preference bias), plus
   cost, terra's ~14% spurious 401s, and threshold recalibration. If a stronger judge is wanted, use
   a **different-provider** model (Claude Sonnet 5) and re-calibrate the gates.
5. **Optional:** add styled formats to Streamlit (needs `run()` to accept `style` like
   `run_headless` does).
6. **Optional:** confirm recent Anthropic failover rate is low (the 42%/30d is likely the old incident).
7. **Optional:** LangSmith runs land in the `default` project; a named project would organise better.

---

## 8. Quick reference

| Thing | Value |
|---|---|
| n8n workflow | "DPDP Content W" · `zmenPhZYryCSz5N7` · certinal.app.n8n.cloud |
| Render service | `dpdp-rag-api` · `srv-d9bimsbtqb8s73cnd770` · https://dpdp-rag-api.onrender.com |
| GitHub repo | `kirtibhushannonhare-certinal/dpdp-content-rag` (branch `main`) |
| Last deploy | commit `33c41a9a`, live 2026-07-21 08:19:35Z |
| Sync check | `python tools/sync_presets.py --check` |
| Style keys | `blog` · `linkedin_article` · `linkedin_article_short` · `newsletter` · `""` (default prose) |
| Preset markers | docs: `<!-- PRESET:key -->` · generate.py: `# >>> SYNCED-PRESETS-START/END <<<` |

Durable facts are also in the project memory files under
`.claude/projects/<project>/memory/` (see `MEMORY.md` index) — that is the authoritative long-term
store; this file is the session narrative.
