# Writing Style Profile — Sujeet Katiyar (DPDP / Healthcare)

**v3 — 120 articles, recency-weighted.** Supersedes v2 (72 articles) and v1 (24).
Corpus: 472 titles + 120 full articles, May 2014 – Jul 2026.
Fetched via WebFetch from LinkedIn Pulse. Jina was unusable throughout (401 on every endpoint).

**Read §2 first.** It explains *why* the citation layer is empty, and that explanation determines
how much of this profile you can safely reuse.

---

## 1. WEIGHTING & PROVENANCE

Index in the source JSON maps reliably to date (newest first). Anchors confirmed by fetch:

| Index | Date | Weight |
|---|---|---|
| 1–120 | Mar–Jul 2026 | **×4** |
| 120–200 | Dec 2025 – Feb 2026 | ×3 |
| 200–255 | Nov–Dec 2025 (post-notification) | ×2 |
| 255–400 | Jan–Oct 2025 (draft-Rules era) | ×1 |
| 400–450 | 2024 | ×0.5 |
| 450–472 | 2014–2023 | ×0.25 |

Roughly **40% of his output is 2026**. Every rule below is stated for the 2026 corpus unless
marked LEGACY.

**Reliability.** Heading lists, dates, and citation presence/absence are high confidence.
Word counts, sentence tallies and contraction detection are extraction estimates — directional only.

**Comment contamination is real and was caught five times.** LinkedIn renders comment threads into
page text. Confirmed instances where a naive scrape would misattribute to the author: a `Rule 8(3)`
citation, GDPR + HIPAA references, PDPL (Saudi/UAE) and JCI/CBAHI, a commenter handle containing
"GDPR360.eu", and the sharpest line on one page. **Always separate body from comments before
treating anything as his.**

---

## 2. THE CENTRAL FINDING — why the citations are missing

This corpus is a **modular content system**, not a series of essays. A fixed skeleton, a fixed
micro-style, and a swappable topic slot. Re-angling a piece means changing the vertical noun in
the title, replacing the examples, and re-cutting the stakeholder section. The argument underneath
does not change.

**The uncited-paraphrase register is not an oversight. It is the load-bearing adaptation that
makes the modularity possible.**

> `"Under the DPDP framework, X must Y"` survives any topic swap.
> `"s.8(2) requires a valid contract"` does not.

This predicts everything else, and it predicts correctly: the two most citation-demanding topics
in the whole corpus — **contracts** and **retention** — are exactly where the omission is most
conspicuous, because those are the topics where the skeleton has least to say and the statute has
most.

**Measured consequence.** Across ~10,500 words on eight DPDP topics in one batch: zero section
numbers, zero rule numbers, zero schedule references, zero penalty figures. A 1,500-word article
on mandatory Fiduciary–Processor contract clauses **quotes the statutory phrase "reasonable
security safeguards" in quotation marks and withholds the section.** Its safeguards list
substantially reproduces R6 — the Rule that already answers the question it poses.

**For your pipeline:** the structure is reusable, the argumentation is often genuinely good, and
the citation layer supplies nothing. It must be built entirely from your chunk metadata.

---

## 3. VOICE VERSUS SUBJECT

Tested against eight non-DPDP articles (quantum computing, agentic AI, medical negligence, LLMs,
MeitY, SAHI, BODH, a Microsoft report).

**Genuinely his — survives every subject:**
1. **Third-person institutional prescription.** *"Hospitals must," "Developers cannot."*
2. **International precedent in the penultimate slot**, 7/8.
3. **India-positioning as the argumentative payoff.**
4. **Contrast-pair reasoning**, 8/8.
5. **Bullet-and-subhead architecture, zero tables.**
6. **Statutes cited precisely, evidence cited vaguely** — he names a report and its page count
   without quoting one figure from it. *For a grounded system this is the most dangerous habit
   to absorb.*

**Imposed by the DPDP subject — does not survive:**
- Second person (see §8 — it's format-linked, and it predicts citation quality)
- The concealment lexicon
- The prohibition on definitional openings
- The terminal role-targeted question

**Threat framing scales with operational proximity to daily practice** — not regulatory proximity.
WhatsApp and pharmacy counters get fragments; AI governance gets paragraphs.

---

## 4. TWO PRODUCTION PIPELINES

Correlation is perfect across the sampled 2026 run — these are two assembly lines, not drift:

| | Pipeline A | Pipeline B |
|---|---|---|
| Heading case | Title Case | sentence case |
| Bio | short, solo | long, two-director |
| CTA | explicit ("can reach out") | **absent** |
| Closer | "Closing Thought" | "The road ahead" |
| Register | punchy, second-person capable | expository, third-person |

Bios are word-identical within each pipeline. Headings are reused verbatim across pipeline-B
pieces. **Pick one and stay in it** — mixing them is the fastest way to produce something that
reads as neither.

---

## 5. TONE & VOICE

Authoritative practitioner. The reader's institution is assumed non-compliant and unaware; the
emotional engine is **unknown exposure** — ignorance of one's own operations, not of the law.

Never witty, ironic or self-deprecating. No humour in 120 articles.

**The deep structure under nearly every piece:**
> The danger is not the dramatic external event you are watching for.
> It is the unexamined ordinary thing you own.

Vendor pieces locate it in the supply chain, breach pieces in daily operations, retention pieces
in the archive, metadata pieces in the audit log.

---

## 6. SENTENCE MECHANICS

Measured across the 2026 corpus:

- **Sub-8-word sentences: 18–65 per article.** The most staccato piece runs roughly **half** its
  sentences under 8 words.
- **Over-25-word sentences: 2–35.** Near zero in the punchiest pieces.
- **One-sentence paragraphs: 6–65.** These are structural, not occasional.
- Shortest observed sentences are one word.

**Density rule (reliable):** fragment density rises with accusation and falls with exposition.
**Prose density tracks legal density** — when he has real authorities to marshal he writes
paragraphs; when he has principles he writes lists. *Use this as a quality signal on your own
drafts: bullet-heavy output usually means you're running on assertion.*

**Signature devices:**
- **Negation cascade** — parallel negations, then a verdict. *Not eventually. Not at the next billing cycle.*
- **The 4+4 thesis pair** — two sub-5-word sentences in contrast carrying the whole argument.
  *The technology may change. / The responsibility does not.*
- **Concessive pair** — *X enables Y. But it also Z.*
- **The three-beat pivot** — long setup → staccato fragment pair → **"Yet."** / **"But."**
- **Anadiplosis close** — *control defines responsibility. And responsibility defines risk.*
- **Sorites chain** — *If contracts are weak, governance is weak. If governance is weak, exposure is inevitable.*

**Closing on a short sentence is current practice.** Legacy pieces close on their longest sentence.

---

## 7. FORMATTING

- **Headings are claims, not labels** (from Nov 2025). Transitional form is the question-heading.
- **Deck-as-heading**: a standfirst rendered as heading #2. Current-era only.
- **No tables. Confirmed across 120 articles** — including a RASCI matrix, an ISO-vs-DPDP
  comparison, and a 10-clause contract checklist. All rendered as bullets. Mapping content uses
  **paired headings** (`Where X Supports…` / `Where X Ends…`) or arrow/pipe contrast pairs.
- **Emoji — one invariant: never mid-sentence in body prose.** Everything else varies per article.
  Default off; absent from all current work.
- **Bold was abandoned** in the newest run. Emphasis migrated into sentence fragments.
- **Colon-stem into bullets** is the dominant paragraph opener. Bare colon transitions
  (*"But:" "Now:" "Which means:"*) peak at ~20 per article in the most fragmented pieces.
- Orthography is inconsistent — *organisation* beside *Organizations*, *non compliance* unhyphenated.

---

## 8. PERSPECTIVE — and the finding that predicts quality

**Default is third-person institutional.**

**But the single most reproducible correlation in the corpus:**

> When he writes in **sustained second person**, he cites precisely and dates correctly.
> When he hands off to third-person institutional, the citations and dates evaporate.

The proof is a Jul 2026 consent-withdrawal article — the only piece with sustained accusatory
second person throughout, and the only one carrying a sub-section citation (**Section 6(4)**,
verified as body text), a penalty figure, GDPR with a date, HIPAA by instrument name, **and a
correctly framed deadline**. Three person-patterns are in play:

1. **Sustained second person** → precise, dated. Rare. *This is the mode to emulate.*
2. **Second-person hook, then handoff** → citations evaporate within a paragraph.
3. **Pure third-person institutional** → no citations, no dates.

**Practical instruction: write in sustained second person, because it forces the specificity.**

Credibility is structural, never asserted — foreign rulings, operational detail, population-scale
diagnosis, terminal bio. He never claims authority from Indian enforcement, because there is none.

---

## 9. VOCABULARY

**Negation-of-control is the primary register** — 5–10× more frequent than concealment words:
> uncontrolled · undetected · unmanaged · ungoverned · outside the hospital's control ·
> absence of governance · no audit trail · no stop mechanism · cannot demonstrate · no one noticed

He prefers *"you cannot see it because you have no mechanism to see it"* over *"it is hidden."*
Architectural, not conspiratorial — which is why **failure is never blamed on individual staff.**

Three flavours worth distinguishing: **absence-shaped** (no policy, no audit trail),
**incident-shaped** (misconfigured, lost device), **textual** (if the contract is silent).

**Concealment words are headline furniture:** hidden · silent · invisible · shadow · blind spot.

**Threat nouns:** time bomb · nightmare · catastrophe · collapse · trap · sword · crisis · minefield.

**Operational nouns** carry the credibility: data fiduciary · data principal · purpose limitation ·
data minimisation · retention · erasure · DPIA · ROPA · consent manager · significant data
fiduciary · reasonable security safeguards · breach notification · sub-processor · flow-down
obligations · liability survival · defensibility.

**Acronyms, no glossary:** HIS · EMR · EHR · PACS · LIS · RIS · TPA · CRO · ABDM · NABH · SDF · DPO.

**Verbs:** must (never *should* for obligations) · establish · embed · govern · demonstrate · prove · map.

**Contractions:** register-dependent, not prohibited. Default to none.

---

## 10. HEADLINE FORMULAS

1. **`When [ordinary thing] Becomes [legal catastrophe]`** — ~45+ uses
2. **Staccato multi-beat** — setup, period, reversal
3. **`DPDP for [Segment]: [Antithesis]`** — and the **`Every X…`** construction
4. **`[Country]'s [amount] [Entity] Fine & Lessons for India`**
5. **Date-as-headline / countdown**
6. **`Why Most X Will Not Y`** · 7. **`X Is Not Y`** · 8. **`From X to Y`**
9. **`[External standard] and DPDP`** · 10. **Direct question**

**Re-angling technique:** de-personalise the subject, add a legal noun and a vertical noun, convert
the assertion into a question. That's how a general AI-agent argument becomes a DPDP-healthcare piece.

---

## 11. TEMPLATES — scoped, because the rules differ per format

| | Sub-section cites | Role-targeted Q | Intl precedent | Boilerplate |
|---|---|---|---|---|
| Rule explainer | Yes (subject rule) | Yes | GDPR Art + HIPAA | Medium |
| **Shadow-IT series** | **s.8(5)/(6)/(7), R6** | **Yes, 7/7** | Verbatim slot | 80% structural |
| GDPR case study | No | Yes | Core of piece | High |
| Countdown | No | Yes | GDPR-as-precedent | Medium |
| Segment explainer | **None** | **No — "Final Thoughts"** | Qualitative only | **75–80%** |
| Standards bridge | None | No — roadmap | 6/8 | Medium |
| FAQ | **None** | No | None | **Exactly 15 Qs** |
| AI think-piece (2026) | **None** | Yes | Framework names | Two-slot template |

**The invariant 2026 spine:**
scenario cold-open → *"X Has Arrived. Governance Has Not."* → numbered practices creating exposure
→ **A Very Real Scenario in an Indian [setting]** → **What the World Has Already Learned** →
violations → consequences → **Mitigation Framework** (30/90/ongoing) → **The Question Every
[role] Must Answer** → bio.

**Structural boilerplate runs 75–85%, but prose boilerplate only 20–25%** — precedents, fines and
scenarios are freshly sourced per topic. A template, not a mail-merge. Only the bio is copy-pasted.

**The four-beat vendor move:** name a comfortable self-classification → reveal a layer beneath it
→ show liability travelling *up* the chain → close on an aphorism of transitive risk.

**The three-move consent machine:** bisect the act into two legal objects → make purpose, not
signature, the operative test (*"Purpose defines legality"*) → name bundling as villain,
granularity as remedy. Consent becomes an **architecture**, not a document. Doctrinally sound.

**The three-tier role ladder:** statutory definition → assignment as foreclosure → **role by de
facto control**. Tier 3 is his most original move *and most legally exposed* — DPDP allocates the
role by determination of purpose, not by system capability. His **role migration** refinement is
the sharpest idea in the corpus: a vendor that independently trains on the data may become a
separate Data Fiduciary.

---

## 12. OPENINGS & CLOSINGS

**Openings** (never throat-clearing; definitions only for technical subjects):
imperative inspection · micro-scenario (named role, one mundane action, compressed present tense)
· negation hook · aphorism · date-and-fine · time arithmetic.

The pivot from scene to consequence lands by sentence 2–4. Fastest observed: word 30.

**Closings by pipeline:**
- Shadow-IT / rule explainer → **role-targeted question** as evidentiary demand
  (*"can you produce, right now…"*) with a conditional sting
- Segment explainer → **"Final Thoughts"** on a *"Because…"* trust antithesis
- Pipeline B → **bifurcated future** — *those who prepare / those who delay* (closes 6 of 8)
- FAQ → the penalties answer, then nothing

---

## 13. CITATION HANDLING — the depth ceiling

**He cites every instrument at the granularity a non-specialist executive can hold in memory, and
rarely below it.** Technical standards are cited as vaguely as Indian law — no ISO clause numbers,
no SOC 2 criteria codes, no NABH objective-element codes, NIST SP 800-207 not cited at all.

**Two things break the ceiling:**
1. **Foreign statute** — GDPR reliably gets Article numbers.
2. **Contrast** — he reaches for a DPDP section when a number is needed to hold two systems apart.

**Format overrides everything.** The shadow-IT series cites sub-sections throughout. Segment
explainers, FAQs, doctrinal pieces and the 2024–25 corpus cite **zero**.

**Never cited anywhere in 120 articles:** the Schedule of penalties. ₹250 crore appears as a bare
ceiling with no statutory hook.

⚠️ **Borrowed-number hazard.** In an article about Indian breach reporting, his only concrete
number is **72 hours — a GDPR figure, unlabelled**, while R7 governs intimation in India and is
never mentioned. Watch for foreign figures migrating into Indian-law claims.

⚠️ **Category conflation.** His "Non-Negotiable Clauses **Under the DPDP Act**" list includes
**indemnity**, which is not a DPDP requirement at all. Statutory duty and prudent practice are
merged with no boundary marked.

---

## 14. DATE HANDLING — the one sentence worth stealing

**Effective dates are absent from the overwhelming majority.** Obligations are present-tense;
enforcement is future-tense; the date that reconciles them is never supplied. A date-titled
article frames 13 May 2027 entirely as *"what will change"* — never as *"not yet in force."*
One retention piece urges building frameworks now against a regime with deferred commencement.
One consent-manager piece recommends adopting a **Rule 4 mechanism over a year before that regime
exists**, with no date at all.

**But he demonstrates the correct move twice.** Use these as the model:

> *"It does not regulate AI. It enables structured validation. That distinction matters."*
> *"The enforcement date of 13 May 2027 does not create the risk. It simply makes it visible."*

**Pattern: state the status in a standalone sentence, then build urgency from
forward-compatibility.** That satisfies your date-honesty rule while keeping the rhetorical force.

---

## 15. WHAT NOT TO INHERIT

1. **Cite every DPDP claim to `s.X` / `s.X(y)` / `r.N`.**
2. **Always state `authority_status`** using the §14 pattern.
3. **Label hypotheticals.** His "mirror risk" and "very real scenario" vignettes are invented and unmarked.
4. **Add the AI-assistance disclaimer.** He carries none, ever.
5. **Use tables.** Zero in 120 articles; his countdowns contain no phased roadmap anywhere.
6. **Cite evidence with figures**, not just named sources.
7. **Keep the objection-rebuttal layer.** His older long-form anticipated and dismantled
   counter-arguments; the compressed 2026 pieces assert and never rebut. That's a real quality loss.
8. **Mark the boundary** between what the Act requires and what is merely prudent.
9. **Don't copy his s.7 taxonomy** — his nine "legitimate uses" are his own numbering and several
   don't map cleanly.
10. **Drop the personal-brand furniture** — 27-year bio, firm CTA, series numbering. Note his firm
    attribution is itself inconsistent (KGS Consulting / Surisolis Ventures / Fourteenth Degree Azimuth).
11. **Never source Rules content from a pre-13-Nov-2025 article** — those necessarily describe the
    January draft G.S.R. 02(E).

**Worth adopting outright:** the closed-list vs open-framework distinction (DPDP s.7 admits no
balancing test; GDPR Art 6(1)(f) is built on one). The **liability split** for naming vendors —
flat unhedged assertions about *use*, strictly descriptive statements about *what the vendor does*,
fault landing on absent governance. And the **role migration** idea.

---

## 16. CORRECTIONS LOG

| Claim | v1 | v2 | **v3** |
|---|---|---|---|
| Second person is the default | ✓ | ✗ third-person | **Format-linked — and it predicts citation quality** |
| Terminal role-targeted question | universal | format-scoped | Confirmed format-scoped; absent from most 2026 |
| Cites precisely when provision is subject | ✓ | ✗ | **Cites when contrast demands a number** |
| Foreign precise / Indian vague | ✓ | depth ceiling | **Depth ceiling; modularity is the cause** |
| Concealment lexicon strongest tic | ✓ | demoted | **Headline furniture; negation-of-control is the voice** |
| Short sentence arrives Dec 2024 | ✓ | ✗ | **Nov 2025** |
| Newer = better cited | — | implied | **✗ — July 2026 citation quality declined** |
| No tables | ✓ | ✓ | **Confirmed, 120 articles** |
| No contractions | ✓ | ✗ | Register-dependent |

---

## 17. GENERATION CHECKLIST

- [ ] Pipeline chosen (A or B) and held consistently
- [ ] Format chosen from §11; its rules applied, not the house average
- [ ] **Sustained second person** where the format allows — it forces specificity
- [ ] Opening: scenario/inspection/negation; pivot by sentence 4
- [ ] Headings are claims that carry the argument when skimmed alone
- [ ] Negation-of-control vocabulary; failure never blamed on individuals
- [ ] One 4+4 thesis pair; one negation cascade; one concessive pair
- [ ] International precedent with jurisdiction, amount **and year**
- [ ] Every DPDP claim carries `s.X` / `r.N` **and** authority status
- [ ] Not-yet-in-force stated in a standalone sentence; urgency from forward-compatibility
- [ ] No foreign figure presented as an Indian requirement
- [ ] Statutory duty distinguished from prudent practice
- [ ] Hypotheticals labelled; evidence cited with figures
- [ ] At least one counter-argument anticipated and answered
- [ ] Table used where mapping or timeline content warrants it
- [ ] Disclaimer present; no Katiyar bio, firm CTA, or series numbering
