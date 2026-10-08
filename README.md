# DPDP RAG Content Farm

Citation-grounded RAG that generates marketing content for Certinal, strictly grounded in
India's **DPDP Act 2023** and **DPDP Rules 2025**. Every factual claim traces to a specific
Section, Rule, or Schedule in the official texts.

The binding rule: **the system must never claim what it cannot prove from the official texts.**
See [CLAUDE.md](CLAUDE.md) for the standing instruction set and
[docs/system-design.md](docs/system-design.md) for the architecture, and
[docs/build-log.md](docs/build-log.md) for the full history — what was built, what broke, what
each bug taught, and what is still open.

> All generated content is AI-assisted, general information only, and **not legal advice**.

## Status

Phase 6 — every draft is machine-verified, and **nothing leaves the building that a human did
not approve.** Chunking (81 chunks), hybrid retrieval, cited generation with failover, the eval
harness, and the Streamlit app are all in. Phase 5 added `cite_check`: a draft that cites a
provision it was never shown is caught, fed its own failure back, and redrafted (max 2 retries)
rather than auto-passed — `citation_validity` went 94.4% → 100%. Phase 6 added the review
console: `human_review` is an `interrupt()` node **inside the graph**, so the draft stops there
and the download (and, at Phase 8, publication) hangs off the *human's* verdict, not the
machine's. A reviewer may approve, edit (re-checked, no LLM call), or reject; approving a draft
the machine failed is allowed but requires a written reason, and the page says it was an
override. See [docs/build-log.md](docs/build-log.md) §8.

Still open: the strict/marketing toggle and multi-format fan-out (both blocked on
`format_per_platform`), the RAGAS CI gate (Phase 7), and n8n publishing (Phase 8).

Run it: `streamlit run app.py`  ·  Gate it: `python -m tests.test_app` ·
Review gate (free, no API calls): `python -m tests.test_review`

## Setup

Requires **Python 3.12**. (3.14 is not usable: `scikit-network`, a `ragas` dependency, has no
3.14 wheel and won't build from source.)

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then verify the scaffold:

```powershell
python tests\test_scaffold.py
```

This checks the folder layout, that both source PDFs are present, and that `.env`,
`.streamlit/secrets.toml`, and `.gitignore` are correct. It reads config **key names only** —
never secret values.

## Configuration

Seven variables, in `.env` locally and in the Streamlit Cloud dashboard when deployed
(CLAUDE.md §5):

| Variable | Used for |
|---|---|
| `ANTHROPIC_API_KEY` | Claude Sonnet — generation failover |
| `OPENAI_API_KEY` | Embeddings (`text-embedding-3-large`) + gpt-5.6-terra primary generation |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant Cloud vector store |
| `LANGSMITH_API_KEY` / `LANGSMITH_TRACING` | Tracing |
| `N8N_WEBHOOK_URL` | Publishing |

`.streamlit/secrets.toml.example` is a committed template mirroring these names (no values).
Copy it to `.streamlit/secrets.toml` — which is **gitignored** — and fill it in locally. For
deployment, paste the same keys into Streamlit Cloud → App → Settings → Secrets.

```powershell
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

## Layout

```
data/raw/          Source PDFs (gitignored, build-time only, never pushed)
data/processed/    Chunked JSONL output — human-openable, audit before indexing
src/ingest/        PDF parsing + legal-aware chunking
src/retrieval/     Qdrant hybrid search (dense + sparse, RRF fusion)
src/generation/    Cited generation, OpenAI primary / Claude failover
src/graph/         LangGraph StateGraph workflow
tests/             Verification scripts
.streamlit/        Streamlit config + secrets template
```

## Architecture in one line

Build time (local, once): PDFs → legal-aware chunker → `chunks.jsonl` → OpenAI embeddings +
FastEmbed sparse → Qdrant Cloud.
Run time (fully online): Streamlit → LangGraph (`retrieve → draft → cite_check → human_review →
publish`) → n8n.

Nothing at runtime depends on the local machine. The PDFs are build-time inputs only.

## Build order (binding — see docs/system-design.md §7)

1. ~~Scaffold~~
2. ~~Legal chunking~~ (slowest, most important — everything downstream inherits its errors)
3. ~~Qdrant index + cited generation + failover~~
4. ~~Deploy thin app online + keep-alives~~
5. ~~LangGraph + cite_check~~ (the toggle and multi-format are still open — see the build log)
6. ~~Human review console~~ ← you are here
7. LangSmith + RAGAS CI gate
8. n8n publishing

Chunking → retrieval → evidence-bounded generation → self-verification → human review → only
then formats and polish. A polished UI on top of wrong citations is a liability, not a product.

## Deployment notes

- **Build-time deps are already split out** (done at Phase 2, was flagged for Phase 4).
  `requirements.txt` is what Streamlit Cloud installs — runtime only. Ingestion libraries live in
  `requirements-build.txt`; for a local build: `pip install -r requirements-build.txt`.
  `unstructured` was **dropped entirely** — it was never imported (the chunker uses pdfminer.six +
  pypdf directly) and it drags in spacy, nltk, numba and llvmlite, which would have blown the
  ~2.7 GB free-tier RAM budget. `test_build_deps_never_leak_into_the_runtime_requirements` guards
  the split. Note `fastembed`/`onnxruntime` *are* runtime deps — sparse query vectors need them.
- **Pin before deploying.** `requirements.txt` is unpinned. After the last build phase, run
  `pip freeze > requirements.lock.txt` and deploy from the lock file.
- **Set the Python version to 3.12** in Streamlit Cloud → Advanced settings. Confirm 3.12 is
  offered before relying on it.
- **Keep-alives** (Phase 4): Qdrant free tier suspends after 1 week idle and is deleted after 4;
  Streamlit sleeps after ~12h. [`.github/workflows/keepalive.yml`](.github/workflows/keepalive.yml)
  pings both twice daily — GitHub Actions rather than n8n, because the repo is already here and
  n8n doesn't exist until Phase 8.

## Deploying (Phase 4)

1. **Streamlit Community Cloud** → New app → this repo, branch `master`, main file `app.py`,
   Python **3.12** (Advanced settings).
2. **App → Settings → Secrets**: paste the seven variables from `.streamlit/secrets.toml.example`
   with real values (the same ones in your local `.env`). The app copies them into the
   environment itself, so every module keeps reading `os.getenv` as it does in CI.
3. **Turn the keep-alives on** in the GitHub repo:
   - Settings → Secrets and variables → Actions → **Secrets**: `QDRANT_URL`, `QDRANT_API_KEY`.
   - Same page → **Variables**: `STREAMLIT_APP_URL` = the app's public URL (the Streamlit ping
     is skipped until this exists, so the workflow is safe to merge before you have a URL).
   - Actions tab → `keepalive` → Run workflow, to confirm both pings pass before trusting the cron.

The deployed app depends only on hosted services (Qdrant Cloud, OpenAI, Anthropic). The source
PDFs are build-time inputs and are never needed at runtime.
