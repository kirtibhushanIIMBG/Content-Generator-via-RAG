# DPDP Content Farm — Complete Workflow Documentation

**Audience:** Anyone. This document assumes **no prior technical knowledge**. It explains, end to end, how the system takes a question about India's data-protection law and turns it into trustworthy, citation-backed marketing content — and exactly how a person operates it.

**What the system is, in one sentence:** an assistant that writes marketing content about India's **DPDP Act 2023** and **DPDP Rules 2025**, where **every legal statement it makes is quoted from the official law and labelled with the exact section it came from** — and if it can't find support in the law, it refuses to write rather than guess.

**The one rule that governs everything:** *It must never claim what it cannot prove from the official texts.* Every part of the workflow below exists to enforce that rule.

---

## 1. The complete workflow at a glance

Here is the whole journey, from a person typing a topic to a finished, approved document. The rest of this guide walks through each numbered stage.

```mermaid
flowchart TD
    A["👤 Operator types a topic<br/>e.g. 'What must a company do<br/>after a data breach?'"] --> B{"① RETRIEVE<br/>Search the law for<br/>relevant provisions"}
    B --> C{"② GROUNDING GATE<br/>Did we find anything<br/>actually relevant?"}
    C -- "No relevant law" --> C1["🛑 'No grounded source'<br/>Nothing is written.<br/>The AI is never even called."]
    C -- "Yes, relevant law found" --> D["③ DRAFT<br/>AI writes the content,<br/>citing each provision"]
    D --> E{"④ CITE-CHECK<br/>Machine verifies every<br/>citation & claim"}
    E -- "Fails" --> F["⑤ REDRAFT<br/>Send the specific errors back,<br/>ask the AI to fix them<br/>(up to 2 times)"]
    F --> E
    E -- "Passes" --> G["✅ Machine-verified"]
    E -- "Still failing after 2 retries" --> H["⚠️ Needs human<br/>(flagged, never hidden)"]
    G --> I["⑥ HUMAN REVIEW<br/>A person checks claims<br/>against the PDFs"]
    H --> I
    I -- "Approve" --> J["⑦ Downloadable / publishable<br/>with the AI-assisted disclaimer"]
    I -- "Edit & re-check" --> E
    I -- "Reject" --> K["🗑️ Not published,<br/>cannot be downloaded"]
```

**The key idea:** content can only leave the system through the far-right box, and the only way to reach it is by passing a **machine check** *and* a **human approval**. There is no shortcut around either.

---

## 2. Before anything runs: how the law gets into the system (one-time setup)

Before a single piece of content can be written, the official law must be loaded into the system. This is done **once**, by a technical person, at "build time." As an operator you never do this, but understanding it explains where the citations come from.

```mermaid
flowchart LR
    P1["📄 DPDP_Act_2023.pdf<br/>(official text)"] --> CH["✂️ Chunker<br/>splits the law into<br/>one piece per section/rule"]
    P2["📄 DPDP_Rules_2025.pdf<br/>(G.S.R. 846(E))"] --> CH
    CH --> M["🏷️ Each piece is tagged:<br/>which section, which page,<br/>whether it's in force yet"]
    M --> EMB["🔢 Each piece is turned into<br/>numbers a computer can<br/>search by meaning<br/>(OpenAI embeddings)"]
    EMB --> Q[("☁️ Qdrant Cloud<br/>Searchable library of<br/>81 pieces of law<br/>49 Act + 32 Rules")]
```

**In plain terms:** the two official PDFs are cut into **81 small, labelled pieces** — one per section of the Act or rule of the Rules. Each piece carries a label saying exactly what it is (e.g. *"DPDP Act 2023, s.8, page 7, in force"*). These pieces live in a cloud search engine called **Qdrant**. From now on, the system only ever quotes from these 81 pieces — never from the AI's general memory.

> **Why this matters:** because the AI can only draw from these 81 verified pieces, it physically cannot cite a law that wasn't loaded. This is the foundation of the "never claim what it can't prove" rule.

---

## 3. The workflow, stage by stage

### Stage ① — Retrieve: find the relevant law

**What happens:** the operator's topic (e.g. *"data breach notification"*) is compared against all 81 pieces of law, and the **6 most relevant** are pulled out.

**How it finds them (two methods at once):**

```mermaid
flowchart TD
    T["Topic: 'data breach notification'"] --> D1["🧠 Meaning search<br/>finds law that's<br/>ABOUT the same idea"]
    T --> D2["🔤 Exact-term search<br/>finds law that mentions<br/>'Section 8', 'Rule 7', etc."]
    D1 --> R["⚖️ Combine & rank<br/>(Reciprocal Rank Fusion)"]
    D2 --> R
    R --> TOP["Top 6 provisions<br/>handed to the next stage"]
```

- **Meaning search** understands that "data breach" relates to "security safeguards" even if the exact words differ.
- **Exact-term search** makes sure that if you ask about "Section 8(7)", the system actually finds Section 8 — not just something that *sounds* similar.
- The two are combined so the best answers rise to the top.

**Plain takeaway:** this stage gathers the 6 most likely-relevant pieces of law. It does **not** write anything yet.

---

### Stage ② — The grounding gate: is there actually anything relevant?

This is the system's first and most important safety valve.

**What happens:** each of the 6 retrieved pieces gets a **relevance score**. If the best score is too low — meaning nothing in the law really bears on the topic — the system **stops here**. It writes *"no grounded source"* and **never calls the AI at all.**

```mermaid
flowchart TD
    H["6 retrieved provisions,<br/>each with a relevance score"] --> Q{"Is the best score<br/>high enough?"}
    Q -- "No — nothing relevant" --> STOP["🛑 'No grounded source'<br/>The AI is NEVER called.<br/>Zero risk of making something up."]
    Q -- "Yes" --> GO["✅ Proceed to drafting"]
```

**Why this exists:** if you ask *"best biryani in Hyderabad,"* the law has nothing to say. A lesser system would let the AI improvise an answer anyway. This system refuses — it would rather say *"the DPDP texts are silent on this"* than invent a legal-sounding sentence.

**What the operator sees:** a clear message explaining either (a) nothing relevant was found, or (b) the provisions found were close but don't truly answer the question. Nothing is drafted in either case.

---

### Stage ③ — Draft: the AI writes the content

Only now, with 6 genuinely relevant pieces of law in hand, does the AI write.

**What happens:** the 6 provisions are handed to the AI along with strict instructions:
- Every legal claim **must** be cited to one of the 6 provisions, in square brackets, e.g. `[DPDP Act 2023, s.8]`.
- **Never** state anything the 6 provisions don't support.
- If a provision isn't in force yet, **say so and give the date**.
- The provided law is **information to quote**, never instructions to obey (a safety measure against hidden text in documents).

**Which AI writes it:**

```mermaid
flowchart LR
    P["Draft request"] --> O["✍️ OpenAI GPT-5 mini<br/>(primary writer)"]
    O -- "If OpenAI is<br/>overloaded/down" --> C["✍️ Claude Sonnet 5<br/>(automatic backup)"]
    O --> DR["Draft with citations"]
    C --> DR
```

- **Primary writer:** OpenAI's **GPT-5 mini**.
- **Automatic backup:** if OpenAI is unavailable, the system instantly retries with **Claude Sonnet 5** using the identical instructions. The operator never notices — the document just gets written. The system records which one wrote it.

**Plain takeaway:** the AI produces a first draft where every legal sentence has a citation attached. But a first draft is **not trusted yet** — that's what the next stage is for.

---

### Stage ④ — Cite-check: the machine verifies itself

This is the system's self-verification. It is a **plain, rule-based checker** (not another AI), so it cannot itself hallucinate. It asks three questions about the draft:

```mermaid
flowchart TD
    DR["The AI's draft"] --> Q1{"1. FABRICATION<br/>Does every citation point to<br/>one of the 6 provisions<br/>it was actually shown?"}
    Q1 -- "Cites something<br/>it was never shown" --> FAIL["❌ FAIL"]
    Q1 -- "OK" --> Q2{"2. DATE HONESTY<br/>If it cites a not-yet-in-force<br/>law, does it say so and<br/>give the date?"}
    Q2 -- "Implies a future law<br/>is active today" --> FAIL
    Q2 -- "OK" --> Q3{"3. TRACEABILITY<br/>Do at least 90% of the<br/>legal claims carry a<br/>valid citation?"}
    Q3 -- "Below 90%" --> FAIL
    Q3 -- "OK" --> PASS["✅ PASS"]
```

1. **Fabrication check** — every citation must point to one of the 6 provisions the AI was actually given. If it cites something from memory that wasn't retrieved, that's caught.
   - *Precision note:* the AI is allowed to cite a **specific sub-section** like `[DPDP Act 2023, s.8(5)]` even though the retrieved piece is the whole of Section 8 — **as long as sub-section (5) genuinely exists in that text.** This makes citations more precise (pointing you to the exact line) while still blocking anything invented (e.g. a made-up `s.8(15)` is rejected).
2. **Date-honesty check** — most of the DPDP law is **not in force until 2027** (see §7). If the draft cites such a provision, it must clearly say it isn't active yet and give the date. A draft that implies a future obligation applies *today* fails.
3. **Traceability check** — at least **90%** of the sentences that state a legal requirement must carry a valid citation. A confident, uncited legal claim is exactly the danger this system exists to prevent.

---

### Stage ⑤ — Redraft: fix the specific errors (the retry loop)

If cite-check fails, the system doesn't give up and it doesn't lower its standards. It sends the **exact problems** back to the AI and asks for a surgical fix.

```mermaid
flowchart TD
    F["Cite-check FAILED"] --> FB["Send back the SPECIFIC errors:<br/>'These sentences have no citation…'<br/>'You cited s.X which wasn't provided…'"]
    FB --> RD["AI revises ONLY the flagged parts<br/>(keeps everything already correct)"]
    RD --> CC{"Cite-check again"}
    CC -- "Pass" --> OK["✅ Verified"]
    CC -- "Fail, and under 2 retries" --> FB
    CC -- "Fail after 2 retries" --> ESC["⚠️ Escalate to a human<br/>— flagged loudly, never auto-passed"]
```

- The AI is told to **revise only the flagged sentences** and leave the correct ones untouched (blindly rewriting from scratch tends to introduce *new* errors).
- This repeats up to **2 times**.
- If it *still* fails, the system does **not** quietly pass it. It marks the draft **"needs human"** and shows exactly why — because a draft that fails verification but reads like a polished article is the most dangerous possible output.

---

### Stage ⑥ — Human review: a person is the final authority

The machine can prove a citation *points to a real provision*. It **cannot** prove the citation is attached to the *right* claim — only a human can. So every draft stops here for a person to check.

```mermaid
flowchart TD
    D["Draft + its 6 sources<br/>+ the machine's verdict"] --> REV["👤 Reviewer opens the PDFs<br/>at the listed pages and<br/>checks at least 3 claims"]
    REV --> DEC{"Reviewer decides"}
    DEC -- "Approve" --> AP["✅ Cleared to publish"]
    DEC -- "Edit & re-check" --> ED["Reviewer fixes wording →<br/>goes back through cite-check<br/>(no new AI call)"]
    DEC -- "Reject" --> RJ["🗑️ Will not publish"]
    ED --> D
```

**What the reviewer sees on screen:**
- A **banner** stating the machine's verdict: *"Machine-verified"* (green) or *"Failed verification — do not publish"* (red, with the reasons).
- The **draft** itself.
- An expandable **"Sources retrieved"** panel listing all 6 provisions — each with its citation, **the exact PDF page number**, whether it's in force, and its relevance score — so the reviewer can open the official PDF and confirm any claim in seconds.
- If any provision is **not yet in force**, a reminder that the draft must not present it as a current obligation.

**The three actions:**
- **Approve** — the draft is cleared. If the reviewer approves a draft that *failed* the machine check, they are **required to write a note** explaining what they checked (an override is allowed — the human is the higher authority — but it is recorded as an override, never as a clean pass).
- **Save edit & re-check** — the reviewer corrects the wording; the edited version goes **back through cite-check** (no new AI call, no cost) so any citation the reviewer typed gets the same scrutiny.
- **Reject** — the draft is discarded and cannot be downloaded.

---

### Stage ⑦ — Publish: the only exit

```mermaid
flowchart LR
    AP["Human-approved draft"] --> DL["⬇️ Download as .md file"]
    DL --> DISC["📎 Always carries the disclaimer:<br/>'AI-assisted, general information only,<br/>not legal advice.'"]
    DISC --> CMS["Paste into a CMS,<br/>Google Doc, etc."]
```

- **Only an approved draft can be downloaded.** A machine-passed-but-not-yet-approved draft is *readable* but not *exportable*. A rejected one cannot leave at all.
- The downloaded file **always** carries the disclaimer — it's added automatically by the system, not left to the AI.
- The file is saved in a format that displays correctly on Windows (handling the em-dashes common in legal text).

---

## 4. The two ways to operate the system

There are two front doors. Most people use the first.

### Way A — The web app (for people)

**Where:** **https://dpdprag.streamlit.app**

```mermaid
flowchart TD
    U["👤 Open the web app"] --> T["Type a topic → click 'Draft'"]
    T --> W["Wait ~30-70 seconds<br/>('Retrieving, drafting, verifying…')"]
    W --> RES["Read the verdict banner + draft"]
    RES --> SRC["Open 'Sources retrieved' → verify citations against the PDFs"]
    SRC --> ACT["Approve / Edit / Reject in the review console"]
    ACT --> DL["Download the approved .md"]
```

**Step by step:**
1. Open the link. You'll see a title and a single **Topic** box.
2. Type your topic in plain English and click **Draft**.
3. Wait while it retrieves, drafts, and verifies (a spinner shows this; typically ~30–70 seconds).
4. Read the **banner** (machine verdict) and the **draft**.
5. Expand **"Sources retrieved"** and spot-check at least three claims against the PDF pages listed.
6. In **Human review**, click **Approve**, **Save edit & re-check**, or **Reject**.
7. If approved, click **Download draft (.md)**.

### Way B — The API (for automation)

**Where:** **https://dpdp-rag-api.onrender.com**

This is the same engine behind the app, exposed so other software (like an automation tool) can request content without a person clicking buttons. It's how the upcoming automated flow (§6) works.

```mermaid
flowchart LR
    CALLER["Automation tool"] -->|"POST /generate<br/>{topic, optional reference link,<br/>optional length}<br/>+ secret key"| API["🔌 RAG API"]
    API --> PIPE["Same retrieve → draft → cite-check<br/>engine as the app"]
    PIPE -->|"Returns: the content, its citations,<br/>the machine verdict, the sources<br/>with page numbers"| CALLER
```

- You send it a **topic** (and optionally a reference link for tone, and a target word count).
- You must include a **secret key** (so not just anyone can use it).
- It returns the drafted content, its citations, the machine's verdict, and the list of sources.
- **It never marks anything as safe to publish without review** — the review still has to happen (in the automated flow, the human reviews the resulting Google Doc).
- `GET /health` is a simple "are you awake?" check used by the keep-alive (§5).

---

## 5. Keeping the system alive & healthy (background workflows)

The system runs entirely on free cloud tiers, which "go to sleep" when idle. Two automated background workflows keep it healthy. As an operator you don't run these — they run themselves — but here's what they do.

### Keep-alive (runs twice a day, automatically)

```mermaid
flowchart LR
    CRON["⏰ Twice daily<br/>(GitHub Actions)"] --> P1["Ping Qdrant<br/>(law library — sleeps after 1 week idle)"]
    CRON --> P2["Ping the web app<br/>(sleeps after ~12h idle)"]
    CRON --> P3["Ping the API's /health<br/>(wakes it up)"]
```

- Keeps the **law library** and the **web app** from lapsing.
- Wakes the **API** — though note the API still cold-starts (~30–50 seconds) if it's been idle more than ~15 minutes; the twice-daily ping proves it's alive, it doesn't keep it permanently warm.

### Quality gate (Continuous Integration / "CI")

Every time the system's code is updated, an automated quality check runs:

```mermaid
flowchart TD
    UP["Code updated on GitHub"] --> RET["Retrieval gate (free, every update)<br/>Does search still find the right law?"]
    SCHED["Weekly, or on-demand"] --> FULL["Full gate<br/>Runs 23 test questions through the<br/>whole pipeline and scores the answers"]
    RET -- "Pass" --> GREEN1["✅"]
    FULL --> SCORE{"Are all quality<br/>thresholds met?"}
    SCORE -- "Yes" --> GREEN2["✅ Safe"]
    SCORE -- "No" --> RED["❌ Blocks — a quality<br/>regression was introduced"]
```

- The **retrieval gate** runs on every code change (it's quick and cheap) and confirms search still finds the right provisions.
- The **full gate** runs weekly (or on demand) and puts 23 test questions through the entire pipeline, scoring things like: *are the answers faithful to the law? are they correct? does every citation check out? is the not-yet-in-force dating honest?* If any threshold is missed, it flags a regression.
- Current measured scores: **faithfulness, correctness, and citation validity all 100%.**

---

## 6. The upcoming automated flow (Phase 8C — planned)

The next addition connects everything into a hands-off pipeline for content requests:

```mermaid
flowchart LR
    FORM["📝 Someone fills a form<br/>(topic + optional reference link)"] --> N8N["🔗 Automation (n8n)"]
    N8N -->|"POST /generate"| API["🔌 RAG API"]
    API -->|"content + citations + verdict"| N8N
    N8N --> DOC["📄 Creates a Google Doc DRAFT<br/>with a review banner, the sources<br/>with page numbers, and the content"]
    DOC --> HUMAN["👤 A person reviews the<br/>Google Doc before it's used"]
```

**In plain terms:** someone fills in a simple form, the system drafts the content, and a **Google Doc draft** appears automatically — complete with the machine's verdict and the list of sources — ready for a person to review. The human check never disappears; it just moves to the Google Doc.

---

## 7. Understanding the law's timeline (critical for reading any output)

Most of the DPDP law is **not in force yet.** The system knows this and dates its claims accordingly — and so must anyone reading its output.

| Part of the law | Status | What it means |
|---|---|---|
| Data Protection Board + foundational definitions | **In force** (13 Nov 2025) | Active now |
| Consent Manager registration (Rule 4) | **Effective 13 Nov 2026** | Not active until then |
| Most substantive obligations & penalties | **Effective 13 May 2027** | Not active until then |

> **When you read a draft:** if it discusses penalties, breach notification, or most day-to-day obligations, it should say those take effect **13 May 2027** — they are not enforceable today. The system is built to state this; your review confirms it.

---

## 8. How to read a citation

Citations look like `[DPDP Act 2023, s.8(5)]` or `[DPDP Rules 2025, r.7]`. Here's how to decode one:

| Part | Meaning |
|---|---|
| `DPDP Act 2023` or `DPDP Rules 2025` | Which document |
| `s.8` | **Section 8** of the Act (rules use `r.7` = **Rule 7**) |
| `(5)` | **Sub-section 5** — the specific paragraph within the section |
| `Schedule` / `Third Schedule` | A table or list attached to the law |

To verify one: open the **"Sources retrieved"** panel, find that citation, note its **PDF page number**, open the official PDF to that page, and confirm the draft's sentence matches what the law actually says.

---

## 9. Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| **"No grounded source"** (best relevance too low) | The law genuinely has nothing on this topic | Rephrase using the statute's own terms, or accept the DPDP texts are silent on it |
| **"No grounded source"** (provisions found but don't answer) | Close but not a real answer | Narrow or rephrase the topic |
| **"Failed verification — do not publish"** (red banner) | The AI's draft couldn't be fully verified even after 2 retries | Check every claim against the PDFs yourself; if sound, approve **with a note**; otherwise reject and re-run |
| The app is slow to load the first time | It was asleep (free tier) | Wait ~10–20 seconds; it wakes up |
| The API request hangs ~30–50s then responds | The API cold-started after being idle | Normal; it stays warm with use |
| A citation looks wrong | The machine can't catch a *misattached* citation — only a human can | This is exactly why review exists — verify against the PDF and reject/edit if wrong |

---

## 10. Glossary

| Term | Plain meaning |
|---|---|
| **DPDP Act 2023 / Rules 2025** | India's data-protection law and its detailed rules — the *only* things this system quotes from |
| **Chunk / provision** | One labelled piece of the law (a section or rule); there are 81 |
| **Retrieval** | Searching those 81 pieces for the ones relevant to your topic |
| **Grounding gate** | The safety check that refuses to write when nothing relevant is found |
| **Citation** | The bracketed label showing exactly which provision a claim comes from |
| **Cite-check** | The automatic, rule-based verifier of every citation and claim |
| **Traceability** | The % of legal claims that carry a valid citation (must be ≥ 90%) |
| **Fabrication** | Citing a provision the AI was never actually shown — automatically blocked |
| **In force / effective date** | Whether a part of the law is active now, or only from a future date |
| **Human review** | The mandatory step where a person approves, edits, or rejects |
| **Disclaimer** | The "AI-assisted, not legal advice" note automatically added to every output |
| **Qdrant** | The cloud search engine holding the 81 pieces of law |
| **Streamlit** | The web app the operator uses |
| **RAG API** | The automation entry point (same engine, no buttons) |
| **Keep-alive / CI** | Background workflows that keep the system awake and quality-checked |
| **GPT-5 mini / Claude Sonnet 5** | The primary AI writer and its automatic backup |

---

## 11. The whole system, in one map

```mermaid
flowchart TB
    subgraph People
        OP["👤 Operator<br/>(web app)"]
        REV["👤 Reviewer"]
    end
    subgraph Apps["What people touch"]
        APP["🌐 Web app<br/>dpdprag.streamlit.app"]
        API["🔌 RAG API<br/>dpdp-rag-api.onrender.com"]
    end
    subgraph Engine["The engine (same for both)"]
        RETR["① Retrieve"]
        GATE["② Grounding gate"]
        DRAFT["③ Draft (AI)"]
        CHECK["④ Cite-check + ⑤ retry"]
        REVIEW["⑥ Human review"]
    end
    subgraph Cloud["Cloud services"]
        Q[("☁️ Qdrant<br/>81 pieces of law")]
        OAI["OpenAI<br/>writing + search"]
        ANT["Anthropic<br/>backup writer"]
        LS["LangSmith<br/>activity tracing"]
    end
    OP --> APP --> RETR
    API --> RETR
    RETR --> GATE --> DRAFT --> CHECK --> REVIEW
    REV --> REVIEW
    RETR -.-> Q
    DRAFT -.-> OAI
    DRAFT -.-> ANT
    Engine -.-> LS
    REVIEW --> OUT["⬇️ Approved, disclaimed<br/>content"]
```

---

*This document describes the workflow only. Every safety property it describes — the grounding gate, the citation checks, the mandatory human review, the disclaimer — is enforced in the system's code, not left to chance or to the AI's goodwill. If a draft ever states something the law doesn't support, the system is designed to catch it before it reaches you — and the human review is the final backstop if it doesn't.*
