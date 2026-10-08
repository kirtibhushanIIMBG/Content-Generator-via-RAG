# RAG API container — for Hugging Face Spaces (Docker SDK), free CPU tier.
# Build context is the REPO ROOT (the image needs both api/ and src/), so build with:
#   docker build -f api/Dockerfile -t dpdp-api .
# HF Spaces does this for you when api/Dockerfile is the Space's Dockerfile and the repo root is
# the Space root.
FROM python:3.12-slim

# Runtime only. The source PDFs are NOT copied — after ingestion the service depends solely on
# Qdrant Cloud + the hosted APIs (CLAUDE.md §3), so the image stays small and holds no statute.
WORKDIR /app

# Deps first, for layer caching. api/requirements.txt pulls in ../requirements.txt, so both must
# be present before the install.
COPY requirements.txt ./requirements.txt
COPY api/requirements.txt ./api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Then the code the service actually imports.
COPY src ./src
COPY api ./api

# HF Spaces routes to $PORT (default 7860). Bind there; fall back to 7860 locally.
ENV PORT=7860
EXPOSE 7860
# Single worker: the free tier has ~2 vCPU and fastembed/onnxruntime hold state per process;
# one worker keeps the memory footprint predictable. Scale with a bigger tier, not more workers.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
