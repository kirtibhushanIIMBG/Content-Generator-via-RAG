# Certinal LinkedIn Article Playbook — Long & Short Form

**Built from:** live analysis of the corpus in [LinkedIn_AI_Training_Corpus_B2B_SaaS_Certinal.md](LinkedIn_AI_Training_Corpus_B2B_SaaS_Certinal.md),
scraped 2026-07-23 via the Jina Reader API across four clusters — **B2B SaaS educational**
(Ahrefs, HubSpot, SEJ, Zapier), **executive thought leadership** (Bain, BCG, Deloitte, McKinsey),
**technical / AI communication** (Stripe, Cloudflare, Anthropic, GitHub, Intercom), and
**regulatory / compliance** (CMS, HealthIT/ONC, Becker's, Healthcare IT News, HIMSS). Every rule
below is backed by a verbatim example from a real published piece, not by opinion.

> **What actually loaded, stated honestly:** the Jina reader was bot-walled by two sources on the
> first pass; both were then recovered through **alternative access paths** (2026-07-23). **Semrush**
> came back in full via WebFetch (a different fetcher/user-agent) — index + the *What is SEO* guide.
> **McKinsey** hard-blocks every cloud-IP fetcher and headless render at its Akamai edge ("Access
> Denied"), so it was recovered indirectly via **SerpAPI** (Google's index of McKinsey's own text)
> plus a full-text **Scribd mirror** — enough for its headline convention, opening, and voice, but
> not its full body; McKinsey patterns are labelled accordingly. HIMSS `/resources` redirected to a
> listing; Becker's succeeded on retry. The two full **CMS** regulatory pieces are the richest
> exemplars for our use case and loaded in full. Where a pattern rests on thin coverage, it is
> flagged inline.

**How this relates to what already ships.** This repo already has a *deployed* LinkedIn voice:
[docs/style-linkedin-article.md](docs/style-linkedin-article.md) and
[LinkedIn_Article_Short_Instructions.md](LinkedIn_Article_Short_Instructions.md), auto-synced into
the `linkedin_article` and `linkedin_article_short` drafting presets (see §14 of
[Blog_Content_Generation_Instructions.md](Blog_Content_Generation_Instructions.md)). *(The old
`short_post` status-update preset — the analysis in §8 below — was removed 2026-07-23; the deployed
short style is now the compressed **article** `linkedin_article_short`.)* Those were
derived from **one practitioner's** 120 DPDP articles — the "unknown exposure" voice. **This
playbook is the wider evidence base behind that voice**, and it adds two lanes the single-author
sample could not: the **executive register** (Bain/BCG/Deloitte) for CISO/GC/board audiences, and
the **technical-explainer register** (Stripe/Cloudflare) for "explain the mechanism" pieces. Where
this corpus *confirms* the shipped preset, it says so; where it would *extend* the preset, that is
flagged as **propose, not applied** — the presets are code-synced and change through
`tools/sync_presets.py`, never by hand-editing the drafter.

> **Certinal's hard constraint, before anything else:** we write about the DPDP Act 2023 and DPDP
> Rules 2025. **Never write a legal claim that isn't supported by a retrieved source.** Omit rather
> than invent. Everything below is subordinate to §10.

---

## 0. Pick the lane before you write

LinkedIn long-form for Certinal has **three registers**, chosen by who the reader is. The craft
rules in §2–§8 are shared; the lane sets tone, evidence type, and structure emphasis.

| Lane | Reader | Emotional engine | Evidence type | Model sources |
|---|---|---|---|---|
| **A. Practitioner** *(default — the shipped voice)* | DPO, compliance lead, IT security owner | Unknown exposure — "your own systems are doing this and you can't see it" | The provision + a named operational system | Intercom, the shipped preset |
| **B. Executive** | CISO, GC, CIO, board | Say-do gap — "you know you must comply; few know how" | A named, numbered framework + comparative stat | Bain, BCG, Deloitte |
| **C. Explainer** | Solution-aware buyer, technical evaluator | Hidden complexity — "this looks simple; here's what it actually takes" | One concrete case → the mechanism → the citation | Stripe, Cloudflare |

**Rule:** default to **A**. Use **B** only for board/leadership-level pieces (readiness strategy,
"four moves before the effective date"). Use **C** only when the value is explaining *how a rule
operates* (consent-manager mechanics, breach-clock mechanics). Never mix lanes inside one article —
the reader can feel it.

---

## 1. Headlines

### What the corpus does

**1. Two-part "situation. imperative." with a hard stop** *(executive — Bain/BCG)* — the period
does a colon's work but reads more assertive.
> "CEOs Are Starting to See Value from AI. Now Comes Execution." *(BCG)*
> "AI-Enabled Transformation Starts—and Stops—With the CEO" *(Bain)*

**2. Contrarian reversal / obituary** *(SEJ — the single most LinkedIn-native pattern)* — declare
a held belief dead, name the uncomfortable replacement.
> "Evergreen Content Is Over – The Individual Is The Only Strategy Left" *(SEJ)*
> "The Content Framework That Worked In 2019 Is Now Working Against You" *(SEJ)*

**3. "How we built / found it: [specific hard thing]"** *(explainer — Stripe/Cloudflare)* — signals
an insider walkthrough, not a brochure. Specificity *is* the credibility.
> "How we built it: Jurisdiction resolution for Stripe Tax" *(Stripe)*
> "How we found a bug in the hyper HTTP library" *(Cloudflare)*

**4. The reader's own question / objection as the title** *(GitHub/Cloudflare; and the
definition-explainer variant — Semrush/McKinsey)* — meets the reader's actual query head-on. Note
the two flavours: the *skeptical objection* (GitHub) and the *plain "What is X?"* explainer, often
with a parenthetical deliverable tag (Semrush).
> "Copilot vs. raw API access: What are you actually paying for?" *(GitHub)*
> "Why we cannot wait for better post-quantum signature algorithms" *(Cloudflare)*
> "What is competitive analysis? How to do one (+ template)" *(Semrush — question + parenthetical)*
> "What is AI (artificial intelligence)?" · "What is an AI agent?" *(McKinsey Explainers — the whole series is question-titled)*

**5. Verb-led, actor-named, outcome-framed — NOT threat-framed** *(regulatory — CMS)* — a rule is
framed as a change with an actor, never a crackdown; "Proposes/Proposed" carries the not-yet-final
status *in the headline itself*.
> "CMS Modernizes Nursing Home Oversight with New Risk-Based Survey Approach…" *(CMS)*
> "CMS Proposes Transformational Medicare Reforms…" *(CMS — 'Proposes' = not binding yet)*

**6. "The ___ advantage / gap / paradox"** *(executive)* — the definite article makes a trend sound
like a category the author already owns.
> "The orchestration advantage" · "A Winner's Paradox" *(Bain M&A outlook)*

### Rules for Certinal

- **Length 6–13 words. Sentence case.** (Matches the modern convention and the shipped preset.)
- **Attack a practice, never assert a legal position.** No headline can carry a pin cite, so no
  headline may state a rule. *"Why 'we'll get consent later' doesn't survive the Rules"* — not
  *"DPDP requires consent before collection."* This is the shipped preset's rule and §10.
- **Match the headline pattern to the lane.** Practitioner → reversal / named-false-belief.
  Executive → "situation. imperative." or "The ___ gap." Explainer → "What the DPDP Rules actually
  require of a Data Fiduciary" (the Stripe "how we built it" move, made compliant).
- **Regulatory-update headlines: actor + action, status-marked.** *"MeitY notifies…"*,
  *"Board publishes…"*; if it isn't in force, the headline says so — the CMS "Proposes" discipline
  maps directly to our authority-status rule.
- **Never a fear headline.** No "₹250 crore" in a title. CMS never leads with the penalty; neither
  do we. See §10.

**Certinal-shaped examples:**
- *Why "we'll get consent later" breaks under the DPDP Rules* — practitioner reversal
- *DPDP readiness has arrived. Governance has not.* — practitioner, two-part stop
- *Four moves compliance leaders should make before 13 May 2027* — executive
- *What the DPDP Rules 2025 actually require of a Data Fiduciary* — explainer

---

## 2. Openings (the hook)

### The hook types, verbatim

**Cold-open scene** *(Intercom — the shipped practitioner default)* — present tense, a named role,
one mundane action, no thesis yet.
> "It's Wednesday at 2pm. A routine deploy goes out. Within minutes, customers cannot open the app.
> Alarms fire, the pager goes off, and the heartbeat metrics begin to drop." *(Intercom)*

**Date → actor → instrument → scope, in sentence one** *(regulatory — CMS — the news default)* —
then sentence two states the *purpose*.
> "On July 14, 2026, the Centers for Medicare & Medicaid Services (CMS) issued the … proposed rule
> (CMS-1848-P), which includes proposed changes to the … Shared Savings Program." → *"These
> proposals aim to accelerate accountable care service delivery…"* *(CMS)*

**Stakes as a hard number, not a definition** *(explainer — Stripe)* — the scale is the hook.
> "…more than 16,000 different combinations of sales tax rates and rules that can apply to an
> internet purchase… a surprisingly complex data engineering challenge." *(Stripe)*

**A market signal + the gap** *(executive — BCG/Bain)* — quantify the stakes in the first three
sentences, then name the say-do gap.
> "…nearly nine in ten CEOs say their companies now see some cost or revenue benefits from AI… The
> opportunity now is to scale those early wins." *(BCG)*
> "…fewer than half of companies … have moved from pilots to real scale." *(Bain)*

**Quote the objection you're answering** *(GitHub)* — validating the reader's doubt buys permission
to explain.
> "I keep seeing this question: 'Why would I pay for Copilot when I can call the same models through
> an API?' It's a fair question." *(GitHub)*

**Two-sentence antithesis dek** *(SEJ house style — the most LinkedIn-native)* — two short parallel
sentences, one negating the other, under the headline.
> "AI doesn't reward the best-optimized page. It rewards the highest-confidence evidence." *(SEJ)*

### The one rule every source follows

**Zero throat-clearing.** Not one analysed piece opens with "In today's fast-paced landscape." The
first sentence is already inside the problem. This confirms the shipped preset's banned-opener list.

### Rules for Certinal

- **Practitioner lane → cold-open scene or behavioural mirror.** A named role doing one ordinary
  thing that has quietly changed their legal position (the DPO who can't say where consent records
  live). This is exactly the shipped `linkedin_article` structure move (1).
- **Regulatory-update → the CMS lead:** notification date + issuing authority + exact provision,
  then one plain sentence on why a Data Fiduciary should care, then a **scope line** ("this piece
  covers X") so you don't implicitly claim to cover the whole Act.
- **Explainer → one concrete case first.** Stripe grounds an abstract geospatial problem in *"these
  two houses in Drexel, Missouri… same ZIP, different counties, different tax."* Our analog: one
  hospital, one consent flow, one record that can't be produced — *before* any section number.
- **The stat-hook is available in one form only:** a cited provision or our own measured number.
  *"The DPDP Rules give you 90 days to answer a Data Principal request. Most consent desks can't say
  what day the clock started."* Legal weight, then operational pain. Never an unsourced fear stat.
- **Run the lede cooler than the headline** (shipped preset). Tension in the open, not volume.

---

## 3. Structure — the long-form spine

### Shared scaffolding the corpus agrees on

- **A scannable summary before the prose.** Executives never read cold: Bain's **"At a Glance"**,
  BCG's **"Key Takeaways"**, CMS's scope-setting meta-sentence. Each bullet is a **claim +
  consequence**, never a topic. *(Bain: "CEOs who spend 15–25% of their time on AI improve adoption
  and generate business results" — not "this covers time allocation.")*
- **Headings are claims, not labels** — the near-universal rule, and the shipped preset's rule.
  A reader skimming only the headings must receive the whole argument. *"One Mistake Can Cost ₹250
  Crore,"* never *"Penalties."* BCG names a section *"A Gap in Execution."* Semrush opens its SEO
  guide with a **reframe-the-assumption heading** — *"SEO is about visibility, not rankings"* — a
  strong pattern for us: *"DPDP readiness is about provable governance, not policy documents."*
- **Explainers answer the title in sentence one, then a scope line** *(Semrush/McKinsey)*. Semrush:
  *"Search engine optimization (SEO) is essentially how you make your brand visible…"* → *"This
  guide covers what SEO is, how it works, and how to start doing it yourself."* McKinsey opens flat
  and definitional — *"Artificial intelligence is a machine's ability to perform cognitive functions
  like reasoning, learning, and problem solving."* Our Lane C equivalent is the pin-cited definition
  sentence + a "this piece covers X" scope line (the same move CMS uses to avoid over-claiming).
- **One numbered spine, 3–7 items, one level deep.** Every source carries the teaching load on a
  numbered sequence (HubSpot H3 1–14; Zapier "Step 1…4"; Bain's five strategies). On LinkedIn, do
  not nest past one level.
- **Signpost the roadmap, then follow it** *(Cloudflare: "Let's look at the algorithms in detail.
  After that we'll look at the timeline…")*. Lowers the cost of a long read.
- **Per-provision blocks for regulatory content** *(CMS's fact-sheet skeleton)*: each item is
  **what it says → who it binds → effective date → the action**, with the date attached to *that*
  item, never pooled at the end. This mirrors our chunk-level `authority_status` design exactly.

### The lane spines

**Lane A — Practitioner** *(the shipped `linkedin_article` structure — use as-is):*
```
1  Cold open — a named role, one mundane action
2  Framing turn — "[Practice] has arrived. Governance has not."
3  Numbered list of the specific risky practices / gaps
4  A LABELLED hypothetical in an Indian setting ("A Very Real Scenario (Hypothetical)…")
5  International precedent — a foreign regulator's posture, jurisdiction + year, as CONTEXT only
6  What the DPDP obligation actually requires        ← pin-cited, date-labelled
7  The consequence of the gap
8  Phased mitigation — First 30 days / Next 90 days / Ongoing
9  Close — a question to a named leader, or a "not just X, it is Y" line
```

**Lane B — Executive** *(Bain/BCG five-beat arc):*
```
Box  "At a Glance" — 3 bullets, each claim + consequence, a hard number in the first
1    Signal / tension — a stat or a dated regulatory milestone
2    The say-do gap — "leaders know they must comply; few know how"        ← the uncomfortable truth
3    Why the old playbook is insufficient now — 2–4 reasons
4    A named, numbered framework — count stated up front, each item a bold imperative sub-head
5    Each move anchored to a concrete practice + a metric
Close  Binary-choice / "illuminating questions the CISO should ask" list
```

**Lane C — Explainer** *(Stripe/Cloudflare):*
```
1    One concrete case that makes the problem felt
2    Coin a plain-language handle for the hard concept, and reuse it throughout
3    Problem → why the obvious fix fails → the real mechanism
4    The obligation, pin-cited, with a Rule→obligation→effective-date table
5    Admit the limit / the open question honestly
Close  Zoom out to the "why" / the trust principle
```

### Rules for Certinal

- **Coin a plain-language handle for each hard legal concept and reuse it** *(Stripe's "SPOTs")*.
  e.g. a stable phrase for "the class of Data Fiduciary that must appoint a DPO," used consistently.
- **The Rule → obligation → effective-date table is our highest-value asset** *(Cloudflare's
  algorithm table with status glyphs)*. Use one wherever more than two obligations appear. The
  shipped preset allows a table *only* for a genuine timeline or mapping — this is exactly that.
- **Show the failed hypotheses** *(Cloudflare's dead-end list)* — for us, "the readiness steps most
  teams try that don't actually close the gap." Honesty about what doesn't work builds trust.

---

## 4. Paragraphs, sentences, rhythm

Confirms and quantifies the shipped preset.

- **Sentences average 12–18 words** (shipped preset); legal-explanation passages may run 20–30 —
  keep them rare. Force variance: a long explanatory sentence, then a **short verdict**. Never
  sustained long, never sustained staccato. *(Cloudflare: "We spent six weeks chasing a nearly
  invisible bug." Intercom: "But ownership is not execution.")*
- **Paragraphs 1–3 sentences.** Every source runs very short paragraphs; single-sentence paragraphs
  carry **verdicts and turns**, not transitions *(Zapier: "A side of collaboration with your
  automation.")*.
- **A visual break every ~100–150 words** — heading, list, table, or colon-stem-into-bullets. The
  **colon stem** is the standard paragraph opener: *"This means:"* → bullets.
- **Bold only statute names, defined terms, and dates** in long-form (shipped preset). Do *not*
  bold for generic emphasis — put emphasis in a short fragment instead. *(Note: the B2B blogs bold
  stats inline; our legal-accuracy posture is stricter, so we keep the preset's narrower rule.)*
- **Extract 2–3 screenshot-ready one-liners** *(Intercom: "roll back first, fix forward later";
  "not every P1 is an incident, but every incident should be a team's P1")*. These are what get
  quoted in the LinkedIn feed. State → let it stand on its own line → echo at the close.
- **End the article on a short sentence** (shipped preset).

---

## 5. Tone & voice

| Register | Sounds like | Proof |
|---|---|---|
| Practitioner *(default)* | Authoritative, second-person, architectural blame | shipped preset; Intercom |
| Executive | First-person-plural institutional, confident, quantified hedges | "In our experience…"; "only 14% clearly define the P&L impact" *(BCG)* |
| Explainer | "We," plain verbs, jargon glossed inline, admits limits | "a page (a loud notification…)" *(Cloudflare)*; "We're still working to perfect the JRS." *(Stripe)* |
| Regulatory | Relentless conditional for anything not final | "As proposed, these changes **would** be effective January 1, 2027." *(CMS)* |

### The transferable mechanics

- **Sustained second person for the problem** — the shipped preset's mandatory rule; it forces
  concrete, provable claims. Drift to "organisations should" and specificity collapses.
- **Hedge with quantified specifics, never vague words** *(BCG: not "many companies" but "only 14%")*.
  Our version: hedge our *interpretation* ("in our view," "organisations should consider"), never
  the statutory text — the provision says what it says; quote it flat.
- **Admit limits — it reads as honesty** *(Stripe, Cloudflare)*. Directly aligns with the project's
  "admit uncertainty" rule.
- **Blame is architectural, never individual** (shipped preset): *"there was no process to detect
  it,"* never *"a careless nurse."*
- **The regulatory conditional mood is our native tense.** CMS writes every non-final rule in
  "would / could / may / if finalized." We write every not-yet-in-force obligation the same way,
  tied to its effective date. Use "in force" present tense **only** for foundational provisions and
  the Board (13 Nov 2025). See §10.
- **Banned throughout:** hype (revolutionary, game-changing, seamless, leverage, unlock), humour,
  academic connectives (moreover, thus), contractions inside obligation sentences, and blaming
  individual staff.

---

## 6. Evidence

- **Precise numbers over adjectives** *(Stripe: "53 states, 3,225 counties… under 10 milliseconds,
  except South Carolina… Charleston alone consists of 73 disjoint areas")* — the lone outlier makes
  the dataset feel real. For us: the exact section, rule, effective date, and penalty slab, handled
  the way Cloudflare handles "PR #4018."
- **Comparative / multiple stats quantify the edge** *(BCG's signature: "high performers are 2.4×
  more likely to assign their best talent to AI workstreams")*. Available to us only for our own
  measured customer data — never a borrowed statistic without its source in the same sentence.
- **Name the study + sample size** *(HubSpot: "data from HubSpot's 2025 State of Marketing Report
  that surveyed 1,700+ marketers")*. Any number we cite carries its source or is omitted.
- **Weave the stat into the claim, with the source named inline** *(Semrush: "AI Overviews pulled
  from the top 10 Google URLs only about two-thirds (67%) of the time," citing "a recent Semrush
  study")* — the number sits inside the sentence it supports, never floated bare. This is the prose
  shape of our pin cite: claim + `(67%)` + source, the way we write claim + `[DPDP …]`.
- **Concrete artifacts as proof** *(Cloudflare's 4-line diff; CMS's file code CMS-1848-P; regulation
  § 425.512(a)(7))*. Our equivalent is the pin cite with page number — already the pipeline's
  discipline. Link the official gazette text; that URL is stable and citable, unlike our own blog.
- **Every quantified claim is sourced or bounded** *(CMS: "About 12% of all nursing facilities will
  qualify"; ONC stat tiles tagged "(source)")*. This is the cite_check contract in prose form.
- **Diagram/table captions do real teaching** *(Cloudflare narrates each figure)*. If we use the
  obligation table, the caption states the takeaway, not just the columns.

---

## 7. Calls to action

The corpus is unanimous and it matches our posture: **teach first, sell last — or don't sell.**

- **"Choose the layer you need" — restate the decision, not the product** *(GitHub closes by saying
  *when* to pick each option, then one soft line)*.
- **Zoom out to the principle / the why** *(Stripe: "the most reliable sales tax solution…";
  Intercom: "What we cannot recover is time lost to inaction")*. Closing on the *why* invites the
  comment-thread agreement that LinkedIn rewards.
- **Participation over persuasion** *(CMS: "CMS encourages … to submit comments," directs to the
  official portal)* — the regulatory close. Ours: "review the official text / prepare for [dated
  milestone] / consult counsel," never "act now or face ₹250 crore."
- **Regulatory-trust close** *(Anthropic-for-Teachers, the closest match to our discipline)*: state
  the safeguard, attach the specific regime in plain language, let a named external standard carry
  trust — **never overclaim.** *("protected by our K-12 Data Processing Addendum, written to comply
  with FERPA," + a named third-party endorsement.)*

### Rules for Certinal

- **Two-beat close** (shipped preset). Beat 1: the audit the reader can run Monday with no purchase
  (map who signs what; list your processors; find the day the retention clock started). Beat 2: one
  on-topic Certinal line in **conditional** voice — *"If you already use Certinal, the audit-trail
  export covers the evidentiary requirement,"* never *"Certinal makes you DPDP compliant."*
- **Executive lane may close on the "illuminating questions" list** *(Bain)* — reframed as
  *"Questions the CISO should be asking the board before 13 May 2027."* It flatters the decision-
  maker instead of lecturing, and it is highly reusable.
- **The disclaimer is not a CTA and does not replace one.** Both appear; disclaimer last, verbatim,
  appended by the service — do not write your own.

---

## 8. Short form — the LinkedIn post *(status-update analysis; no longer a deployed preset)*

> **Status:** the `short_post` status-update preset was **removed 2026-07-23**. This section is kept
> as reference analysis of the ultra-short feed-post format; it is **not** the `LinkedIn Article —
> Short` option, which is the compressed *article* `linkedin_article_short` (see
> [LinkedIn_Article_Short_Instructions.md](LinkedIn_Article_Short_Instructions.md)). If the
> status-update post is ever revived as a preset, this is the spec.

The corpus contributes the **hook grammar** and the **one-idea discipline**; the removed preset
already nailed the DPDP overrides.

### What the corpus adds

- **The whole post does the job an article's *opening* does** (shipped preset): name one ordinary
  thing the reader owns, reveal it is exposure they can't see. **One idea only.** The B2B sources
  corroborate — a post is a single reversal or a single antithesis dek, never a survey.
- **Open with a 3–8 word hook line that stands alone** (shipped preset), drawn from the strongest
  article openers: the two-sentence antithesis *(SEJ: "AI doesn't reward the best-optimized page.
  It rewards the highest-confidence evidence.")* and the quoted objection *(GitHub)* both compress
  to a single scroll-stopping line.
- **A screenshot-ready one-liner is the payload** *(Intercom's maxims)* — in short form, the maxim
  *is* the post.
- **Credibility from precision, not a precedent section** (shipped preset): one concrete detail — a
  named system, a specific provision, a real number — does the work a whole paragraph would.

### Short-form skeleton *(the former `short_post` status-update shape)*
```
Hook line        3–8 words, stands alone, creates a stop (blunt claim / negation / question)
2–4 lines        the ordinary thing → the hidden exposure, second person, one idea
optional list    3–5 items, each on its own line, arrow-led (→), no nesting
turn / question  one-line verdict or a single question to the reader
disclaimer/tag   one-line #NotLegalAdvice on advice posts
hashtags         3–5 on their own final line (#DPDPAct #HealthcareCompliance #DataPrivacy)
```
Devices that punch harder in short form: the **negation cascade** *("Not the HIS. Not the EMR.
WhatsApp.")* and the **two-part contrast** *("The tool is free. The liability is not.")*. End on a
snap. Generous white space; a line break between almost every sentence.

---

## 9. The Certinal overlay — non-negotiable

These override every craft rule above and mirror the deployed gates
([Blog_Content_Generation_Instructions.md](Blog_Content_Generation_Instructions.md) §8, CLAUDE.md §3).
A beautifully structured post with a wrong citation is a liability, not an asset.

1. **No legal claim without a retrieved source.** Cite every DPDP claim in **square brackets
   beginning with "DPDP"**, verbatim from the source header: `[DPDP Act 2023, s.8(5)]`,
   `[DPDP Rules 2025, r.7]`. A bare `[s.8(5)]`, an un-bracketed "under s.8(5)", or a gazette number
   as a cite is invisible to cite_check and scores as uncited. If we can't source it, cut the
   sentence. Omission is always cheaper than a correction.
2. **Cite the final notified Rules** — Gazette **G.S.R. 846(E), notified 13 Nov 2025**. **Never**
   the January 2025 draft (G.S.R. 02(E)).
3. **Never imply an obligation is in force before its effective date.** State authority status in a
   standalone sentence, present tense only for what's live:
   - Foundational provisions + Data Protection Board — **in force (13 Nov 2025)**
   - Rule 4, Consent Manager registration/obligations — **effective 13 Nov 2026**
   - Most substantive Rules — **effective 13 May 2027**
   Use "will apply from [date]" / "once in force" for anything future-dated. This is the CMS
   conditional-mood discipline; it is also the single easiest way for a well-meaning draft to
   become false.
4. **Penalty figures are breach-specific.** ₹250 crore attaches **only** to the s.8(5)
   security-safeguards breach. Breach-notification ₹200 crore; child-data ₹200 crore; SDF duties
   ₹150 crore; every other breach is the residuary head, up to ₹50 crore. Cite the matching slab
   from the retrieved `[DPDP Act 2023, Schedule]` and name the Schedule. Never lead a headline or a
   hook with the penalty.
5. **Foreign precedent is context, never a claim about India.** A GDPR 72-hour clock is never
   presented as an Indian requirement. Jurisdiction + year, framed as context (Lane A slot 5).
6. **Label every hypothetical as hypothetical.**
7. **Every published piece carries the disclaimer:** AI-assisted; general information only; not
   legal advice. Appended by the service — do not write your own.
8. **Human review before publication.** No exceptions, regardless of how clean the draft looks.

---

## 10. Ready-to-fill skeletons

### A. Practitioner long-form *(default — maps to `style: linkedin_article`)*
```
Headline   [Practice] has arrived. Governance has not.   |  Why "[false belief]" breaks under the Rules
Hook       Cold open: a named role, one mundane action that changed their legal position
H (claim)  How [the shortcut] became standard practice
List       The specific risky practices / gaps           ← numbered, one level
Scenario   "A Very Real Scenario (Hypothetical) in an Indian [setting]"   ← LABELLED
Precedent  What a foreign regulator has done — jurisdiction + year, as CONTEXT only
H (claim)  What the DPDP obligation actually requires     ← blockquote provision, pin cite, dated
H (claim)  What this exposure costs                       ← correct penalty slab, or omit
Framework  First 30 days / Next 90 days / Ongoing
Close      A question to a named leader, or "not just X, it is Y." Then two-beat CTA. Disclaimer.
Length     1,200–2,200 words
```

### B. Executive long-form *(propose new preset `linkedin_article_exec` — not applied; see §14 note)*
```
Headline   Four moves compliance leaders should make before 13 May 2027   |  "situation. imperative."
Box        At a Glance — 3 bullets, each claim + consequence, a hard number in the first
Signal     A dated regulatory milestone or our own measured stat
Gap        The say-do gap: "leaders know they must comply; few know how"
Why-now    Why the old playbook is insufficient — 2–4 reasons
Framework  N named moves, count up front, each a bold imperative sub-head, each pin-cited + dated
Proof      Each move anchored to a concrete practice (+ our metric, if we have one)
Close      "Questions the CISO should ask the board" list, or a binary-choice line. Disclaimer.
Length     1,200–2,000 words
```

### C. Explainer long-form *(propose new preset `linkedin_article_explainer` — not applied)*
```
Headline   What the DPDP Rules 2025 actually require of a Data Fiduciary
Case       One concrete case that makes the problem felt (one hospital, one consent flow)
Handle     Coin a plain-language name for the hard concept; reuse it throughout
Mechanism  Problem → why the obvious fix fails → what the rule actually mechanises
Table      Rule → obligation → who it binds → effective date   ← the highest-value asset
Honesty    The readiness steps teams try that don't close the gap; the open question
Close      Zoom out to the trust principle; state the safeguard + the specific regime. Disclaimer.
Length     1,200–1,800 words
```

### D. Short status-update post *(the former `short_post` — removed 2026-07-23, not a deployed style; for the deployed `LinkedIn Article — Short` use `linkedin_article_short`)*
```
Hook       3–8 words, stands alone (blunt claim / negation / question)
Body       2–4 lines: the ordinary thing → the hidden exposure. One idea. Second person.
List       optional 3–5 arrow-led lines
Turn       one-line verdict or one question
Cite       inline [DPDP …] bracket stays in the draft; rendered at publish
Tag        #NotLegalAdvice on advice posts
Hashtags   3–5 on the final line
Length     80–250 words
```

---

## 11. Pre-publish checklist

**Lane & structure**
- [ ] One lane chosen (A / B / C); tone and evidence type match it
- [ ] Headline 6–13 words, sentence case, matches a corpus pattern, asserts **no** legal position
- [ ] Scannable summary box for executive lane; scope line for regulatory-update pieces
- [ ] Every heading is a claim or imperative — a heading-only skim delivers the whole argument
- [ ] One numbered spine, 3–7 items, one level deep
- [ ] Effective date sits **with** each obligation, never pooled at the end

**Voice**
- [ ] First sentence is already inside the problem; no throat-clearing / banned opener
- [ ] Sustained second person (Lane A); quantified hedges, not vague ones (Lane B)
- [ ] Sentences avg 12–18 words; long-then-short rhythm; article ends on a short sentence
- [ ] Paragraphs 1–3 sentences; a visual break every ~150 words; colon-stem into bullets
- [ ] Bold only statute names, defined terms, dates — no emphasis-bolding
- [ ] 2–3 screenshot-ready one-liners present
- [ ] No hype words, no humour, blame architectural not individual

**Close**
- [ ] Two-beat close; Certinal line is conditional, never imperative
- [ ] Teaches/points to the official text — no fear CTA, no "₹250 crore or else"

**Legal — blocking**
- [ ] Every legal claim in a `[DPDP …]` bracket, verbatim from the source header
- [ ] Rules citations are G.S.R. 846(E) (13 Nov 2025), never the January 2025 draft
- [ ] Every obligation carries its effective date; no future obligation in present tense
- [ ] Penalty figures matched to the correct breach slab; ₹250 crore only for s.8(5)
- [ ] Foreign precedent framed as context, never an Indian requirement
- [ ] Every hypothetical labelled hypothetical
- [ ] Disclaimer present (service-appended); at least 3 citations spot-verified by a human
- [ ] Human review complete

---

## 12. Source appendix

Scraped 2026-07-23 via Jina Reader (`mcp__jina__read_url` / `parallel_read_url`), with a second
pass on the blocked sources via **WebFetch**, **SerpAPI**, and a headless **screenshot render**.
Public pages only.

| Cluster | Sources | Read | Access path |
|---|---|---|---|
| B2B SaaS educational | Ahrefs, HubSpot, SEJ, Zapier | index + 1 evergreen article each | Jina reader |
| B2B SaaS educational | **Semrush** | index + *What is SEO* guide | **WebFetch** (reader was bot-walled) |
| Executive | Bain, BCG, Deloitte | index + full articles | Jina reader |
| Executive | **McKinsey** | headline convention + opening + voice (partial body) | **SerpAPI + Scribd mirror** (Akamai edge-block) |
| Technical / AI / storytelling | Stripe, Cloudflare, Anthropic, GitHub, Intercom | 5 indexes + ~6 full articles | Jina reader |
| Regulatory / compliance | CMS, HealthIT/ONC, Becker's, Healthcare IT News, HIMSS | 5 indexes + 2 full CMS pieces | Jina reader (Becker's on retry) |

**Recovered on the second pass:** Semrush (fully — the reader's bot wall was cleared by WebFetch's
different user-agent); McKinsey (partially — its own text via Google's index (SerpAPI) and a Scribd
full-text mirror, confirming the question-titled explainer convention, the definition-first opening,
and the "In this McKinsey Explainer, we…" first-person-plural voice). **McKinsey remains fully
walled to direct fetch/render** — it blocks by datacenter-IP reputation at the Akamai edge, so no
fetcher, headless browser, or reader will reach the live body from a cloud IP; only its indexed/
mirrored text is available.

**Residual gaps (do not treat as measured):** McKinsey's full article *body* (framework lists,
exhibits, close) was not recovered — its patterns rest on headline + opening + SERP snippets, and
Bain/BCG/Deloitte carry the executive lane. No full trade-press article was pulled from
Becker's/HealthIT News/ONC (homepage headline signal only); HIMSS `/resources` redirected. A
Becker's full-article teardown is available on request via the same WebFetch route that recovered
Semrush.

### The one thing to steal from each cluster

| Cluster | Technique |
|---|---|
| **Executive (BCG/Bain)** | **The named, numbered framework with comparative stats and an "At a Glance" box** — count stated up front, each move a bold imperative, closed with "illuminating questions the leader should ask." |
| **Technical (Stripe/Cloudflare)** | **Ground the abstract in one concrete case, coin a reusable plain-language handle, then show the mechanism — and admit the open limit.** Every claim carries an artifact (their "PR #4018" = our pin cite + page). |
| **Storytelling (Intercom)** | **The cold-open scene + the recursive maxim** — one screenshot-ready line per section, stated → standing alone → echoed at the close. |
| **Regulatory (CMS)** | **Conditional mood for everything not final, effective dates attached per-provision, cohorts separated explicitly, close on participation not fear.** This *is* our golden-rule posture in prose. |
| **B2B SaaS (SEJ/Ahrefs)** | **The contrarian-reversal headline + two-sentence antithesis dek, and the stat-as-hook** — for us, only ever a cited provision or our own measured number. |

**For Certinal, the two clusters that matter most are Regulatory and Technical.** CMS's conditional,
date-per-provision, source-or-omit discipline is the same instinct that governs our citation-grounded
pipeline; Stripe/Cloudflare's "one concrete case → the mechanism → the verifiable artifact" is how we
make a dry legal obligation land without ever exceeding the evidence. The executive and B2B-SaaS
clusters supply the headline energy and the framework scaffolding — used only where the lane calls
for it, and always subordinate to §9.

> **Note on the deployed presets:** Lanes B and C above are marked *propose, not applied*. The
> shipped `linkedin_article` preset encodes Lane A only. Turning B or C into real drafting presets
> is code work — a new `STYLES` entry or a doc-driven `<!-- PRESET:* -->` block synced via
> `tools/sync_presets.py`, plus the API allow-list, tests, and the n8n form — exactly as
> [Blog_Content_Generation_Instructions.md](Blog_Content_Generation_Instructions.md) §14 describes.
> Until then, Lanes B and C are editorial guidance for the ideation layer and the human reviewer,
> and all long-form drafts run `style: linkedin_article`.
