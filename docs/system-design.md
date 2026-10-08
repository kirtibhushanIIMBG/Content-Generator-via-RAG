# System Design — DPDP RAG Content Farm (Cloud-First)

Save this file as `docs/system-design.md` in the repo. Claude Code reads it (alongside
CLAUDE.md) for architectural context. CLAUDE.md holds the binding rules; this document
holds the reasoning, architecture, and component detail behind them. If the two ever
conflict, CLAUDE.md wins.

---

## 1. What this system is

A citation-grounded Retrieval-Augmented Generation (RAG) system that produces marketing
content for Certinal, strictly grounded in India's DPDP Act 2023 and DPDP Rules 2025.
It generates:

- **Long-form**: blog posts, LinkedIn articles (800–1,500 words) — every factual claim
  carries an inline citation traceable to a specific Section, Rule, or Schedule.
- **Short-form**: LinkedIn posts, X/Twitter threads, Facebook posts, Instagram captions.

It has two operating modes, selected by a toggle:
- **Strict mode**: citation-enforced, machine-verified, for anything published as fact.
  Long-form ALWAYS runs strict, regardless of the toggle.
- **Marketing mode**: tone-led, generally accurate, no per-sentence citation enforcement,
  but ALWAYS human-reviewed before publish.

The system runs fully online: vectors in Qdrant Cloud, generation via hosted LLM APIs,
UI on Streamlit Community Cloud. The local machine is only the build environment.

## 2. Design principle (the one test every decision must pass)

**The system must never claim what it cannot prove from the official texts.**
If a proposed change makes it easier for the system to say something unsupported,
the change is wrong. This principle produced every major choice below: retrieval-first
generation, per-chunk citations, the self-verification node, "no grounded source"
handling, authority-status metadata, and mandatory human review.

## 3. Source documents (authoritative corpus)

User-supplied local PDFs, exact filenames, placed in `data/raw/` (committed to the repo):

| File | Content | Status |
|---|---|---|
| `DPDP_Act_2023.pdf` | Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023) | In force (assented 11 Aug 2023) |
| `DPDP_Rules_2025.pdf` | DPDP Rules, 2025 — Gazette notification G.S.R. 846(E) | Notified 13 Nov 2025, phased enforcement |

Critical facts the system must respect:
- The Rules are **final law**, not draft. The January 2025 draft (G.S.R. 02(E)) is
  superseded and must never be cited.
- **Phased enforcement**: foundational provisions + Data Protection Board in force from
  13 Nov 2025; Rule 4 (Consent Manager) effective 13 Nov 2026; most substantive Rules
  effective 13 May 2027. Content must never imply an obligation is live before its date.
- Only these two PDFs go into the knowledge base. No secondary summaries, blog posts,
  or law-firm explainers — they introduce draft/final confusion and inaccuracy.

### Document anatomy (drives the chunker)

**Act 2023** — 9 chapters, 44 sections, 1 Schedule (penalties):
Ch I Preliminary (ss.1–3) · Ch II Obligations of Data Fiduciary (ss.4–10) ·
Ch III Rights & Duties of Data Principal (ss.11–15) · Ch IV Special Provisions (ss.16–17) ·
Ch V Data Protection Board (ss.18–26) · Ch VI Powers/Procedure (ss.27–28) ·
Ch VII Appeal & ADR (ss.29–32) · Ch VIII Penalties (ss.33–34) · Ch IX Misc (ss.35–44).
Sections nest sub-sections (1),(2) → clauses (a),(b) → sub-clauses (i),(ii), and some
sections (ss.5–8) include **Illustrations** that must stay attached to their parent.
The Schedule caps penalties (e.g., up to ₹250 crore for security-safeguard failures).

**Rules 2025** — 23 Rules, 7 Schedules:
Key rules: R3 Notice · R4 Consent Manager · R6 Security safeguards · R7 Breach
intimation · R8 Erasure/retention · R10–11 Verifiable consent (child / person with
disability) · R13 SDF obligations · R14 Data Principal rights (90-day response) ·
R15 Cross-border transfer.
Schedules First–Seventh; several are tables (e.g., Third Schedule retention periods);
some split into Part A/B. The PDF may be bilingual (Hindi + English) — English only
is extracted.

## 4. Architecture overview

```
                         BUILD TIME (local, once)
  DPDP_Act_2023.pdf ─┐
                     ├─> parse -> legal-aware chunker -> chunks.jsonl (+metadata)
  DPDP_Rules_2025.pdf┘                                        │
                                          OpenAI embeddings (dense, 3072-d)
                                          FastEmbed sparse vectors
                                                              │
                                                              v
                                                   Qdrant Cloud collection
                                               (dense + sparse, metadata payload)

                         RUN TIME (fully online)
  Streamlit app (Streamlit Community Cloud)
      │ topic, formats[], mode toggle
      v
  LangGraph StateGraph
      retrieve (Qdrant hybrid query, RRF fusion)
         │
      draft (Claude Sonnet, temp 0.0–0.2; failover GPT on 429/5xx)
         │
      [conditional edge on mode]
         ├─ strict ──> cite_check (validate every citation; score >= 0.9 or
         │             loop back to draft with feedback, max 2 retries)
         └─ marketing ─────────────┐
                                   v
      format_per_platform (blog / linkedin_article / linkedin_post /
                           x_thread / facebook / instagram)
         │
      human_review  <── LangGraph interrupt(); Approve / Edit / Reject
         │ approve
         v
      publish_webhook ──> n8n ──> social platforms / scheduler

  Observability: LangSmith traces every run (tagged mode/format/provider)
  Quality gate:  RAGAS eval in CI (faithfulness >= 0.85, context_recall >= 0.8)
```

## 5. Component decisions and why

### 5.1 Ingestion & chunking (the highest-stakes component)
- One chunk per Section/Rule as the base unit; sections over ~1200 tokens split at
  sub-section boundaries with 80-token overlap; Illustrations stay with their parent;
  each Schedule (and each Part A/B) is its own chunk with tables intact.
- Deterministic regex-based header detection (inspectable, debuggable) over ML-based
  splitting (opaque). When headers misparse, print the raw extracted headers and fix
  the pattern — never guess.
- Output is human-openable JSONL (`data/processed/act_chunks.jsonl`, `rules_chunks.jsonl`)
  so every chunk can be audited before indexing.
- Why so much care: every downstream citation inherits chunking errors. A missed
  section or a mangled table becomes a wrong or missing citation in published content.

### 5.2 Metadata schema (per chunk — the citation backbone)
```
{
  "doc": "DPDP Act 2023" | "DPDP Rules 2025",
  "type": "section" | "rule" | "schedule",
  "number": "8", "sub": "7",
  "chapter": "II", "chapter_title": "Obligations of Data Fiduciary",
  "title": "General obligations of Data Fiduciary",   // Act sections only; null elsewhere
  "schedule": "Third", "part": "A" | "B",
  "citation": "DPDP Act 2023, s.8(7)",
  "authority_status": "in force" | "effective 2026-11-13" | "effective 2027-05-13",
  "source_ref": "DPDP_Act_2023.pdf" | "DPDP_Rules_2025.pdf",
  "page": 12,
  "text": "..."
}
```
- `title` (added Phase 3b, human-approved) is the Act's marginal **side-note**, and it is the
  one piece of a section that is deliberately absent from `text`. The Gazette prints section
  titles in an 8pt margin column; read inline they inject themselves into the middle of legal
  sentences, so the chunker strips that column. The RAG eval exposed what that cost: the Act's
  body contains "Notice" **zero** times, "Exemption" **zero** times, "Security safeguard"
  **zero** times. All 44 sections were indexed with no statement of their own subject while
  every Rule carries its heading inline, so the Act systematically lost topical queries to the
  Rules — s.17, *the* exemptions section, fell out of the top-6 for "which processing is
  exempt", behind r.12 / r.16 / Fourth Schedule. Fixed by embedding the title (never the
  payload). Golden-set recall@6 went 94.4% → **100%**, faithfulness 97.2 → 98.3.
- `citation` is the string that appears in generated content.
- `authority_status` powers the not-yet-in-force flagging in review.
- `source_ref` + `page` let a human open the exact PDF page and verify any claim in
  seconds. A chunk missing any of these three fields is never indexed.

### 5.3 Embeddings
- **OpenAI `text-embedding-3-large`, 3072 dimensions** (human's decision 2026-07-17; -small before that). Hosted (keeps the deployed app
  light — free Streamlit hosting has ~2.7 GB RAM, so no 2 GB local models), cheap
  (the whole corpus embeds for cents), strong on legal English.
- Anthropic has no embeddings API — embeddings are always OpenAI.
- FastEmbed's small model is a fallback for rare offline re-ingestion only.

### 5.4 Vector store & retrieval
- **Qdrant Cloud free tier** (1 GB — far more than this corpus needs). Named vectors:
  dense (3072, cosine) + sparse (FastEmbed sparse), with full metadata as payload.
- **Hybrid retrieval server-side**: dense semantic + sparse exact-term, fused with RRF.
  Legal queries need both — "what must a notice contain" is semantic; "Rule 7" or
  "Section 8(7)" is exact-term, and pure semantic search misses it.
- k=6 chunks to generation; retrieval scores surfaced so weak retrieval is visible.
- Free-tier caveat: cluster suspends after 1 week idle, deleted after 4 weeks — a
  scheduled keep-alive ping (n8n) prevents this.

**Built at Phase 3** — `src/retrieval/hybrid.py` (runtime) + `src/ingest/index_qdrant.py`
(build). Collection `dpdp`, 81 points, sparse model `Qdrant/bm25` with `modifier=IDF`.
Two things were not obvious and cost a failing gate to find:

- **Citation handles.** BM25 alone CANNOT do the one job the sparse side exists for.
  "Section 8(7)" tokenises to `section` / `8` / `7`, all low-IDF (the corpus is dense with
  cross-references), so the exact-term queries came back as pure noise — s.8 was not even in
  the top 6. Fix: mint one synthetic, punctuation-free token per provision (`section8`,
  `rule7`, `thirdschedule`), prepend it plus the citation to the **embedded** text, and mirror
  the same expansion on the query side (`hybrid.expand_query`). The token occurs in exactly one
  chunk, so IDF pins it to rank 1. Index side and query side must mint identical tokens —
  that is why both functions live in `hybrid.py` and the indexer imports from it.
- **The payload `text` stays pristine.** Only the *embedding* input carries the citation
  scaffolding. Generation must never see it, or it will quote the scaffolding as if it were
  statute.
- **A Schedule never states its own subject** (found at Phase 3b by a Certinal marketer
  question, "how long must we retain signed contracts"). Every Schedule is a bare table whose
  topic lives in the rule that made it: the Third Schedule *is* the data-retention table, yet
  it contains "retain", "retention", "erase" and "erasure" **zero** times — it says only
  "Time period" and "Three years from the date the Data Principal last approached". So both
  retrieval sides went blind and it never surfaced for a retention question; generation then
  said, honestly but uselessly, "the sources do not include the Third Schedule". Fix:
  `index_text()` prepends the **parent provision's opening words** (read from the Schedule's
  own `[See rule 8(1)]` line, so it follows the statute rather than a hand-written label) —
  r.8 opens "…shall erase such personal data, unless its retention is necessary…", exactly the
  vocabulary the table lacks. Measured over 6 retention queries: **2/6 → 4/6** retrieved, with
  no regression on any of the 7 controls (incl. all 5 bare-citation rank-1 cases). The gain is
  fully realised at 300 characters; 600/900/1200 buy nothing, so 300 is the setting.
  *Known ceiling:* consumer-phrased erasure questions ("when must a company delete my data")
  still crowd it out of the top-6 behind six genuinely relevant provisions — it is now
  competitive rather than invisible, and r.8 (which explains the Schedule's mechanism) always
  ranks 1 for those.

*Build-machine note:* on a Zscaler/corporate-MITM laptop, `httpx` (and so the OpenAI SDK)
verifies against certifi and rejects the intercepted certificate. Qdrant Cloud is exempted
from interception, so it works and only embeddings fail. Do not "fix" this in code — it is a
local build-machine property that does not exist on Streamlit Cloud. Export the Windows trust
store once and pass it per-command:
`SSL_CERT_FILE=~/.certs/ca-bundle.pem python -m src.ingest.index_qdrant`
LangSmith uses `requests`, which ignores SSL_CERT_FILE — for anything that traces (generation,
the app) also pass `REQUESTS_CA_BUNDLE=~/.certs/ca-bundle.pem`, or traces silently drop.

### 5.5 Generation
- **Primary: claude-sonnet-5** (langchain-anthropic). Chosen for strong
  instruction-following on strict citation constraints. Sonnet 5 rejects sampling
  params (temperature → API 400) — determinism comes from the strict prompt contract.
  Its adaptive thinking counts toward max_tokens, so generation runs with 8192.
- **Failover: OpenAI GPT** (gpt-4o-mini default) on Anthropic 429/5xx, same prompt,
  provider logged and tagged in LangSmith. An always-online system must survive
  rate limits without silent degradation.
- Generation prompt contract: chunks are numbered and prefixed
  `# Source: <citation> (<source_ref>, p.<page>)`; claims beyond the chunks are
  forbidden; weak/empty retrieval → output "no grounded source"; text inside chunks
  is data, not instructions (prompt-injection guard); disclaimer appended.

### 5.6 The toggle (LangGraph conditional edge)
- State field `mode` routes after `draft`: strict → `cite_check`; marketing → straight
  to formatting. Long-form formats force strict regardless of toggle (a blog post
  asserting obligations is published fact, whatever the user selected).
- Marketing mode always terminates in human review — it trades machine verification
  for human verification, never for no verification.

### 5.7 Self-verification (`cite_check` node)
- Parses every bracketed citation in the draft; validates each against retrieved chunk
  metadata (does the section/rule exist, was it retrieved); flags uncited factual
  sentences; computes `traceability_score = supported claims / total factual claims`.
- Score < 0.9 → loop back to `draft` with specific feedback (max 2 retries); still
  failing → surface to human, never auto-pass.
- Known limitation: a citation can be real but not actually support the claim
  (plausible-but-wrong attachment). The score reduces this; human review is the
  backstop. This is why review is mandatory.

### 5.8 Multi-format generation
Retrieve once, fan out per format with dedicated prompt templates:
blog + linkedin_article (long, cited) · linkedin_post (~1,300 chars, hook + insights
+ CTA) · x_thread (280-char tweets) · facebook (conversational) · instagram (hook +
hashtags). Same evidence base, different style/length/citation-strictness.

### 5.9 Human-in-the-loop review
- LangGraph `interrupt()` + checkpointer pauses the graph before finalization;
  Streamlit console shows each format, cited provisions with source_ref + page,
  traceability score, and an authority-status flag on any provision not yet in force.
- Approve / Edit / Reject via `Command(resume=...)`; resume input validated with a
  conditional edge (not a loop inside the node). Rejected content never finalizes.

### 5.10 Publishing
- On approval, POST payload (platform, text, cited_sections, traceability_score,
  review flag) to an n8n webhook. n8n branches per platform to social APIs or a
  scheduler, with a second manual-approval node for legal-adjacent content.
  Two human gates is the right paranoia level for a compliance company.

### 5.11 Observability & evaluation
- **LangSmith** tracing from day one; runs tagged by mode/format/provider. This is the
  debugging window into the live system (why did retrieval return the wrong section,
  why did a citation fail).
- **RAGAS** golden set (~15 Q&A across notice, consent, children's data, breach,
  SDF obligations, cross-border, retention, penalties) computing faithfulness,
  answer_relevancy, context_precision, context_recall; judge model gpt-4o-mini.
  CI (GitHub Action) fails on faithfulness < 0.85 or context_recall < 0.8, so the
  live system cannot regress silently. If faithfulness is low, fix chunking or
  retrieval — never loosen the gate.

## 6. Hosting & cost

| Component | Service | Tier | Notes |
|---|---|---|---|
| Vector DB | Qdrant Cloud | Free (1 GB) | Suspends 1wk idle / deleted 4wk — keep-alive ping |
| Generation | Anthropic API (Claude Sonnet) | Pay-per-use | Cents per long article at this volume |
| Embeddings + failover | OpenAI API | Pay-per-use | Corpus embeds for cents; 3-small is cheap |
| UI hosting | Streamlit Community Cloud | Free | Sleeps ~12h idle, wakes on visit |
| Tracing | LangSmith | Free (5k traces/mo) | Plenty for build + moderate ops |
| Publishing | n8n (existing) | — | Webhook + scheduled keep-alives |
| Code + CI | GitHub | Free | Private repo; Actions runs RAGAS gate |

Expected cost at moderate volume: a few dollars/month in API usage; everything else
free tier. Paid Anthropic/OpenAI API tiers do not train on inputs by default, which
also resolves the confidentiality concern that ruled out free-tier LLMs.

Secrets: `.env` locally (gitignored), Streamlit dashboard secrets in the cloud.
Env vars: ANTHROPIC_API_KEY, OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY,
LANGSMITH_API_KEY, LANGSMITH_TRACING, N8N_WEBHOOK_URL.

## 7. Build order (see Playbook v2 for session-by-session prompts)

1. Scaffold + CLAUDE.md → 2. Legal chunking (slowest, most important) →
3. Qdrant index + cited generation + failover → 4. Deploy thin app online +
keep-alives → 5. LangGraph toggle + cite_check + multi-format → 6. Human review
console → 7. LangSmith + RAGAS CI gate → 8. n8n publishing.

Priority order is binding: chunking → retrieval → evidence-bounded generation →
self-verification → human review → only then formats and polish. A polished UI on
top of wrong citations is a liability, not a product.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Chunker misses sections / mangles tables / Hindi bleed-through | `--inspect` completeness check (zero missing ss.1–44 / R1–23), manual spot-check via `page` field, deterministic parsing |
| Real-looking but wrong citations | cite_check traceability score + RAGAS faithfulness gate + mandatory human review |
| Content implies obligations live before effective date | `authority_status` metadata + review-console flagging |
| Citing the superseded Jan 2025 draft | Only the two supplied PDFs are ingested; CLAUDE.md requires human confirmation the Rules PDF is G.S.R. 846(E) |
| API rate limits / outages | Claude → GPT failover with logging; retry/backoff on embeddings |
| Free tiers idling out (Qdrant, Streamlit) | Scheduled n8n keep-alive pings |
| Prompt injection via corpus text | Chunks treated as data; explicit prompt instruction to ignore instruction-like text |
| Legal exposure | Not-legal-advice disclaimer on every piece; human sign-off before publish; this system informs, it does not advise |

## 9. Compliance posture

This produces legal-adjacent marketing content, not legal advice. Every published
piece carries an AI-assisted / not-legal-advice disclaimer. Accountability for
published claims sits with Certinal, so 100% of legal-claim content routes through
human review; relax only after RAGAS faithfulness is consistently > 0.9 over a
sustained period, and even then keep review for long-form.
