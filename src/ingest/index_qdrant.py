"""Embed data/processed/*_chunks.jsonl and upsert into Qdrant Cloud.

Build-time only. Idempotent: point ids are a uuid5 of (source_ref, citation, sub), so
re-running overwrites in place — it never duplicates and never drops the collection.

    python -m src.ingest.index_qdrant           # create if absent, embed, upsert, verify count
    python -m src.ingest.index_qdrant --dry-run # validate chunks + count, contact nothing

Dropping/recreating the collection is destructive (CLAUDE.md §10) — do it by hand, after
asking. This script deliberately has no --recreate flag.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from qdrant_client import models

from src.retrieval.hybrid import (
    COLLECTION,
    CONTEXT_CHARS,
    DENSE_SIZE,
    embed_dense,
    embed_sparse,
    index_text,
    parent_ref,
    qdrant,
)

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / "data" / "processed"
BATCH = 64

# CLAUDE.md §7: a chunk without these must never be indexed.
# `number` is NOT here: schedule chunks have none — they are identified by `schedule` (+ `part`).
REQUIRED = ("doc", "type", "citation", "authority_status", "source_ref", "page", "text")
VALID_STATUS = {"in force", "effective 2026-11-13", "effective 2027-05-13"}
NAMESPACE = uuid.UUID("6d1f0a4e-8b3a-4a1e-9c2f-b1c200000000")  # fixed: ids must be stable


def load_chunks() -> list[dict]:
    """Load every chunk and refuse the whole batch if any one is unciteable."""
    chunks: list[dict] = []
    for path in sorted(CHUNKS.glob("*_chunks.jsonl")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            c = json.loads(line)
            where = f"{path.name}:{lineno}"
            for field in REQUIRED:
                if c.get(field) in (None, ""):
                    raise ValueError(f"{where}: chunk missing '{field}' — refusing to index")
            # page must be a real 1-based page NUMBER, not merely present: a 0 or a string "7"
            # would index fine and only fail later, in a human reviewer's hands.
            if not isinstance(c.get("page"), int) or c["page"] < 1:
                raise ValueError(f"{where}: page must be an int >= 1, got {c.get('page')!r}")
            if c["authority_status"] not in VALID_STATUS:
                raise ValueError(f"{where}: bad authority_status {c['authority_status']!r}")
            if not (c.get("number") or c.get("schedule")):
                raise ValueError(f"{where}: chunk has neither 'number' nor 'schedule'")
            c["_id"] = str(
                uuid.uuid5(NAMESPACE, f"{c['source_ref']}|{c['citation']}|{c.get('sub')}")
            )
            chunks.append(c)

    ids = [c["_id"] for c in chunks]
    if len(set(ids)) != len(ids):
        dupes = {c["citation"] for c in chunks if ids.count(c["_id"]) > 1}
        raise ValueError(f"duplicate chunk identity (citation+sub) — would overwrite: {dupes}")
    if not chunks:
        raise ValueError(f"no chunks in {CHUNKS} — run `python -m src.ingest.chunk` first")
    return chunks


def schedule_contexts(chunks: list[dict]) -> dict[str, str]:
    """citation -> parent provision's opening words, for every Schedule chunk.

    A Schedule states its subject nowhere in itself (see hybrid.index_text). Its parent is
    named in its own '[See rule 8(1)]' line, so the topic is READ from the statute rather
    than hand-assigned — if the chunker or the law changes, this follows automatically.
    """
    heads: dict[tuple[str, str], str] = {}
    for c in chunks:
        if c["type"] in ("rule", "section") and c.get("number"):
            # first chunk of a split provision opens with the heading — setdefault keeps it
            heads.setdefault((c["doc"], c["number"]), c["text"][:CONTEXT_CHARS])

    out: dict[str, str] = {}
    for c in chunks:
        n = parent_ref(c)
        if not n:
            continue
        head = heads.get((c["doc"], n))
        if not head:
            raise ValueError(
                f"{c['citation']}: parent provision {n} of {c['doc']} not found — "
                "a Schedule with no locatable parent is untopiced and will not retrieve"
            )
        out[c["citation"]] = head

    scheds = [c["citation"] for c in chunks if c["type"] == "schedule"]
    missing = [s for s in scheds if s not in out]
    if missing:
        raise ValueError(f"schedules with no '[See rule/section N]' parent line: {missing}")
    return out


def ensure_collection() -> None:
    if qdrant().collection_exists(COLLECTION):
        # Validate what already exists instead of trusting it: a collection created by hand
        # without modifier=IDF degrades BM25 to raw term frequency SILENTLY — the upsert
        # succeeds, the counts match, and only retrieval quality drops (audit finding).
        info = qdrant().get_collection(COLLECTION)
        sparse = (info.config.params.sparse_vectors or {}).get("sparse")
        if sparse is None or sparse.modifier != models.Modifier.IDF:
            raise ValueError(
                f"collection {COLLECTION!r} exists WITHOUT the IDF modifier on its sparse "
                "vector — BM25 would silently degrade to term frequency. Recreate it "
                "(CLAUDE.md §10: ask the human first)."
            )
        return
    print(f"creating collection {COLLECTION!r}")
    qdrant().create_collection(
        collection_name=COLLECTION,
        vectors_config={
            "dense": models.VectorParams(size=DENSE_SIZE, distance=models.Distance.COSINE)
        },
        # IDF is what makes BM25 BM25 — without it the sparse side is raw term frequency.
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="validate only; no network calls")
    args = ap.parse_args()

    chunks = load_chunks()
    print(f"{len(chunks)} chunks validated (citation + authority_status + source_ref + page)")
    contexts = schedule_contexts(chunks)
    print(f"{len(contexts)} schedules topiced from their parent provision")
    if args.dry_run:
        print("--dry-run: nothing embedded, nothing indexed.")
        return 0

    ensure_collection()

    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        # Embed citation + handles + parent topic (schedules) + text; the payload keeps the
        # pristine `text` (see hybrid.py).
        texts = [index_text(c, contexts.get(c["citation"], "")) for c in batch]
        dense, sparse = embed_dense(texts), embed_sparse(texts)
        qdrant().upsert(
            collection_name=COLLECTION,
            points=[
                models.PointStruct(
                    id=c["_id"],
                    vector={"dense": d, "sparse": s},
                    payload={k: v for k, v in c.items() if k != "_id"},
                )
                for c, d, s in zip(batch, dense, sparse)
            ],
            wait=True,
        )
        print(f"upserted {min(i + BATCH, len(chunks))}/{len(chunks)}")

    indexed = qdrant().count(COLLECTION, exact=True).count
    print(f"\ncollection {COLLECTION!r}: {indexed} points")
    if indexed != len(chunks):
        print(f"MISMATCH: expected {len(chunks)} — stale points from an earlier run?")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
