"""Citation spot-check — the artefact a human signs off (CLAUDE.md §9, Definition of Done #3).

    SSL_CERT_FILE=... REQUESTS_CA_BUNDLE=... PYTHONIOENCODING=utf-8 python -m eval.spot_check
    python -m eval.spot_check "How long can a company retain my personal data?"

Runs real topics through the Phase 5 graph and prints, per citation:
  * every claim in the draft that rests on it,
  * the provision as the model saw it (the chunk payload),
  * the SAME page re-extracted from the source PDF, independently of the chunker.

Definition of Done #3 asks a HUMAN to verify citations against the PDFs. This does the legwork
— find the pages, pull the statutory words, flag anything that does not line up — so that job
is minutes, not an afternoon. It does NOT replace the human: nothing here can tell whether a
real citation actually SUPPORTS the sentence it is attached to. That judgement is the point.

Why the PDF is re-read here at all: the chunk payload could be corrupt and the draft would
still look perfectly cited. This is the one check that goes back to the paper.

NOTE — the chunker reads body text with pdfminer and Schedules with pypdf (both deliberately;
see src/ingest/chunk.py). They disagree about SPACES, so every comparison below goes through
chunk.nospace(). Do not re-roll that normalisation: a collapse-based copy of it reported a
false page mismatch on r.7 during the first spot-check, and a checker that cries wolf teaches
its reader to ignore real flags.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypdf import PdfReader  # noqa: E402

from src.generation.generate import CITE  # noqa: E402
from src.graph.cite_check import claim_units  # noqa: E402
from src.graph.pipeline import run  # noqa: E402
from src.ingest.chunk import nospace  # noqa: E402  — the SHARED comparison key

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

DEFAULT_TOPICS = [
    "What must a Data Fiduciary do when a personal data breach occurs?",
    "How long can a company retain my personal data?",
]


def page_text(source_ref: str, page: int) -> str:
    return PdfReader(str(RAW / source_ref)).pages[page - 1].extract_text() or ""


def on_page(chunk_text: str, is_schedule: bool, page: str) -> bool:
    """Is this chunk really printed on that page? Schedules are re-wrapped into markdown
    TABLES by the chunker, so their prose never matches the PDF verbatim — probe the heading
    line instead, exactly as tests/test_chunks.py does."""
    probe = chunk_text.splitlines()[0] if is_schedule else chunk_text[:60]
    return nospace(probe) in nospace(page)


def main() -> int:
    topics = sys.argv[1:] or DEFAULT_TOPICS
    suspect = 0

    for topic in topics:
        s = run(topic)
        d, rep = s["draft"], s.get("report")
        print("\n" + "=" * 100)
        print(f"TOPIC: {topic}")
        if rep:
            print(f"review_status={s['review_status']}  attempts={s['attempts']}  "
                  f"traceability={rep.traceability_score:.0%}  fabricated={rep.fabricated}")
        else:
            print(f"review_status={s['review_status']} — nothing drafted, nothing to check")
            continue
        print("=" * 100)

        # Seed with EVERY citation in the draft, then fill in the claims that rest on each.
        #
        # Seeding matters: claim_units() deliberately DROPS headings (a "## Penalties" line is
        # not a claim, and scoring it would drive redrafts that cannot succeed — cite_check.py).
        # So a citation that appears ONLY in a heading never entered by_cite, was never compared
        # against d.hits, and never incremented `suspect`. Measured: a draft whose report reads
        # fabricated=['DPDP Act 2023, s.99'] — the citation sitting in a `## Penalties under
        # [s.99]` heading — made this tool print "Every citation is a retrieved provision" and
        # exit 0. This is the artefact a human signs the Definition of Done against; it must
        # never be the thing that lies. Every citation is now checked, wherever it appears.
        by_cite: dict[str, list[str]] = {c: [] for c in dict.fromkeys(d.citations())}
        for sent, scope in claim_units(d.text):
            for c in dict.fromkeys(CITE.findall(scope)):  # the SAME regex the checker uses
                if sent not in by_cite.setdefault(c, []):
                    by_cite[c].append(sent)

        hits = {h.citation: h for h in d.hits}
        for c, sents in by_cite.items():
            print(f"\n\n### CITATION: [{c}]")
            h = hits.get(c)
            if not h:
                suspect += 1
                print("    *** FABRICATED — this provision was never retrieved. DO NOT PUBLISH. ***")
                continue

            print(f"    source: {h.source_ref}  page {h.page}   authority: {h.authority_status}")
            page = page_text(h.source_ref, h.page)
            ok = on_page(h.text, h.citation.count("Schedule") > 0, page)
            if not ok:
                suspect += 1
            print(f"    chunk really printed on {h.source_ref} p.{h.page}? "
                  f"{'YES' if ok else 'NO  <-- INVESTIGATE'}")

            print(f"\n    CLAIMS IN THE DRAFT THAT REST ON IT ({len(sents)}) — does the "
                  "provision below actually support each one?")
            for x in sents:
                print(f"      - {x}")

            print("\n    THE PROVISION AS THE MODEL SAW IT (chunk payload):")
            for line in h.text.strip().splitlines()[:16]:
                print(f"      | {line}")
            print(f"\n    THE SAME PAGE, RE-EXTRACTED FROM {h.source_ref} p.{h.page}:")
            for line in [ln for ln in page.splitlines() if ln.strip()][:16]:
                print(f"      > {line}")

    print("\n" + "=" * 100)
    if suspect:
        print(f"{suspect} citation(s) need investigation — see the INVESTIGATE/FABRICATED lines above.")
    else:
        print("Every citation is a retrieved provision, printed on the page it claims.")
    print("A HUMAN still has to read the claims against the provisions: this tool cannot tell")
    print("whether a real citation actually supports the sentence it is attached to.")
    return 1 if suspect else 0


if __name__ == "__main__":
    sys.exit(main())
