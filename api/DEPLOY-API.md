# Deploying the RAG API (Phase 8B)

The API wraps the grounded pipeline so n8n can call it over HTTPS. It depends only on hosted
services (Qdrant Cloud + OpenAI + Anthropic) — no local files, no PDFs. Verified to boot with
`uvicorn api.main:app` and serve `/health` + `/generate`.

## Recommended: Render (pulls from GitHub — no local git push)

Render clones the GitHub repo itself, so the Zscaler push block that affects your machine does
not apply here (same reason Streamlit Cloud works).

1. Push the repo state to GitHub as usual (the `render.yaml` at the repo root must be up there).
2. **render.com → New → Blueprint →** pick the `DPDP-Content-RAG` repo. Render reads `render.yaml`
   and proposes the `dpdp-rag-api` Docker service.
3. **Set the secrets** it asks for (they are `sync:false`, so Render never sees them until you type
   them): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, and `API_KEY`
   (invent a long random string — n8n sends it as `X-API-Key`). These are the SAME values as the
   Streamlit app, plus the new `API_KEY`.
4. Deploy. Render builds `api/Dockerfile` and gives you `https://dpdp-rag-api.onrender.com`.
5. **Smoke test:**
   ```
   curl https://dpdp-rag-api.onrender.com/health
   # {"status":"ok"}
   curl -X POST https://dpdp-rag-api.onrender.com/generate \
     -H "Content-Type: application/json" -H "X-API-Key: <your API_KEY>" \
     -d '{"topic":"What must a Data Fiduciary do after a personal data breach?","word_count":400}'
   ```
   Expect JSON with `review_status`, `content`, `sources`, etc.

**RAM caveat (the one risk):** Render free is 512 MB. The API loads `fastembed` for sparse
vectors; the `Qdrant/bm25` model is light, but if the service OOMs on boot (Render shows the
container being killed), switch to the fallback below — it has 16 GB.

**Cold start:** Render free spins down after 15 min idle; the first call after that takes ~30–60s
while it wakes. Add it to the keepalive (below).

## Fallback: Hugging Face Spaces (16 GB RAM, free)

Use this if Render OOMs. HF Spaces has plenty of RAM but you upload files via its web UI (its git
remote has the same push issue as GitHub).

1. **huggingface.co → New Space → Docker (blank).** It creates a Space repo.
2. Upload, at the Space root: `api/Dockerfile` renamed to `Dockerfile` (or add a one-line root
   Dockerfile: `FROM ...` — easiest is to copy `api/Dockerfile` to the root and change the two
   `COPY` paths since the Space root will hold `src/`, `api/`, `requirements.txt`). Also upload
   `src/`, `api/`, and `requirements.txt`.
3. **Settings → Variables and secrets:** add the same five secrets as above.
4. The Space builds and serves at `https://<user>-dpdp-rag-api.hf.space`. Smoke test as above.
   (HF Docker Spaces route to port 7860, which the Dockerfile already binds.)

## Keepalive

Add the API to the existing `.github/workflows/keepalive.yml` (or a new one): a twice-daily
`curl <api-url>/health` keeps Render/HF from sleeping, just like the Qdrant + Streamlit pings.

## Once it's live

Note the base URL and the `API_KEY` — Phase 8C (the n8n workflow) needs both: n8n's HTTP Request
node POSTs to `<api-url>/generate` with the `X-API-Key` header.
