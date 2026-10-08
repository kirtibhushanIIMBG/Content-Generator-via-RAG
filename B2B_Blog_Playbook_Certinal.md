# Certinal B2B Blog Playbook

**Built from:** live analysis of 7 blogs — Ahrefs, HubSpot, Search Engine Journal, Intercom,
Zapier, Semrush, Kinsta — scraped 2026-07-22 via the Jina Reader API. Every rule below is backed
by a verbatim example from a real published post, not by opinion.

> ## Benchmark set: four models, three demoted
>
> After measuring all seven, **the models Certinal writes like are: Intercom, Kinsta, Semrush,
> Ahrefs** — all B2B SaaS, all selling to a buying committee.
>
> **Demoted to reference data only — do not copy their architecture, register, or business model:**
>
> - **Search Engine Journal** — an ad-funded media publisher, not a SaaS company. News-velocity
>   architecture, sponsored posts inline with editorial, advertiser-collateral "case studies", and
>   a flagship report that discloses **no methodology**.
> - **Zapier** — SMB/prosumer audience, consumer app roundups, jokey register. The premise for
>   including it ("best short paragraphs") was **false**: it has the longest paragraphs measured.
> - **HubSpot** — needs a lead-magnet machine at a scale we don't have, and its signature move
>   (7 gated offers / 46 link instances in one post) is actively wrong on content interpreting law.
>
> Their measurements remain in the comparison tables — the numbers are still true and useful as a
> spread. A handful of their specific mechanics were salvaged and are credited inline. Full
> reasoning and the salvage list: §0 of
> [B2B_Blog_Feature_Playbook_Certinal.md](B2B_Blog_Feature_Playbook_Certinal.md).

**How to use this:** Sections 1–8 are the craft rules, each with the evidence that produced it.
Section 9 is the Certinal overlay — the constraints that apply because we publish about law.
Section 10 has four ready-to-fill post skeletons. Section 11 is the pre-publish checklist.

> **Certinal's hard constraint, before anything else:** we write about the DPDP Act 2023 and
> DPDP Rules 2025, and about signature law. **Never write a legal claim that isn't supported by
> the source text.** Omit rather than invent. Everything in this playbook is subordinate to that.
> See §9.

---

## 1. Headlines

### What the benchmarks do

| Blog | Casing | Signature move |
|---|---|---|
| SEJ | Aggressive Title Case | Declares a practice dead |
| Ahrefs | Title Case | Puts the receipt in brackets |
| Zapier | Strict sentence case | Number + category + year |
| Semrush | Sentence case (new) | States the sample size |
| Kinsta | Sentence case | Names a false belief, then corrects it |
| Intercom | Sentence case | Bare declarative belief, zero keywords |
| HubSpot | Mixed → sentence case | Bracketed lead magnet |

### The seven formulas that actually recur

**1. The reversal / obituary** — declare the reader's current practice obsolete.
> "Evergreen Content Is Over – The Individual Is The Only Strategy Left" *(SEJ)*
> "The Content Framework That Worked In 2019 Is Now Working Against You" *(SEJ)*
> "Why scaling infrastructure doesn't fix bot traffic problems" *(Kinsta)*

**2. The named false belief in quotes** — put the wrong idea in the headline and mark it wrong.
> "Performance consistency: Why 'fast on average' hosting fails real users" *(Kinsta)*

**3. Stat-first** — the number *is* the headline.
> "96.55% of Content Gets No Traffic From Google. Here's How to Be in the Other 3.45%" *(Ahrefs)*
> "84% of companies have AI pilots that never reach deployment. Here's what's keeping them locked in limbo." *(Zapier)*

**4. Bracketed credibility tag** — prove the work in the title.
> "Anchor Text: A Data-Driven Guide (384,614 Web Pages Studied)" *(Ahrefs)*
> "AI visibility is a topic-level game: A study of 50,000 brands in ChatGPT [Study]" *(Semrush)*

**5. Keyword colon payoff** — exact-match keyword left of the colon, hook right of it.
> "Image SEO: 12 Actionable Tips (for More Organic Traffic)" *(Ahrefs)*
> "Link building for SEO: What works in 2026" *(Semrush)*

**6. Question that mirrors the query verbatim.**
> "What is competitive analysis? How to do one (+ template)" *(Semrush)*
> "What is a customer journey map? The complete overview [examples + templates]" *(HubSpot)*

**7. Second-person accusation** — the headline points at the reader.
> "Google Data Shows AI Search Users Moved Past Keywords, Your Content Hasn't" *(SEJ)*

### Rules for Certinal

- **Sentence case.** Matches Kinsta, Zapier, Semrush, Intercom — the modern convention. Title
  Case reads dated outside news publishing.
- **45–75 characters.** Data-study headlines may run to ~105.
- **Never title a post with an unqualified legal assertion.** "DPDP fines can reach ₹250 crore"
  is a headline that misstates the law (that slab is specific to one breach type). Use the
  *misconception* formula instead: *Why "we'll get consent later" doesn't survive the DPDP Rules*.
- Reserve stat-first headlines for numbers **we can cite** — a section number, a notified date,
  a figure from our own customer data. Never a borrowed statistic without its source in the body.
- Year-stamping ("in 2026") works for compliance-deadline content, where recency *is* the value.

**Certinal-shaped examples:**
- *Why "we'll get consent later" breaks under the DPDP Rules*
- *Consent Manager registration: what Rule 4 actually requires, and when*
- *Most DPDP readiness checklists skip the erasure clock. Here's the one that matters.*
- *Wet signature vs. eSignature under Indian law: what changes, what doesn't*

---

## 2. Paragraphs

### Measured, not guessed

Sentences per paragraph, counted across the first 15–20 paragraphs of one real post per blog:

| Blog | Sequence | Avg | Max | Single-sentence |
|---|---|---|---|---|
| Semrush | 4,2,1,1,1,1,1,1,1,1,3,1,1,2,3 | **1.6** | 4 | 67% |
| SEJ | 2,1,2,3,1,2,2,2,1,2,1,2,2,1,1 | **1.67** | 3 | 40% |
| HubSpot | 3,3,1,2,2,2,3,2,1,2,2,1,3,2,1 | **2.0** | 3 | 20% |
| Ahrefs | 7,2,3,1,3,4,2,1,1,2,4,1,3,4,2 | **2.67** | 7 | 27% |
| Intercom | 4,4,4,3,1,5,1,1,3,4,2,2,3,2,2 | **2.73** | 5 | 20% |
| Zapier | 4,4,3,3,2,2,4,4,5,3,3,3,4,6,2… | **3.3** | 6 | 0% |
| Kinsta | *(not directly counted — reported ~2.5–3.2)* | ~3 | 6 | — |

**The whole industry sits between 1.6 and 3.3 sentences per paragraph. Nobody exceeds 7.**
Corroborated independently by The Blogsmith's editorial standard: *"Try to limit paragraphs to
three sentences."*

### Rules for Certinal

- **Target average 2–3 sentences. Hard ceiling 5.** Legal writing drifts long; this is the single
  highest-leverage readability fix available to us.
- **Use one-sentence paragraphs for load-bearing claims**, not for transitions. Intercom's method:
  > "One principle shapes all of this: **not every P1 is an incident, but every incident should be a team's P1.**"
- **A statutory quotation is not a paragraph.** Quote the provision as a blockquote, then explain
  it in a 2-sentence paragraph underneath. Never inline a 60-word sub-section into running prose.
- Break every ~3 paragraphs with a heading, list, table, or callout. Zapier achieves zero
  single-sentence paragraphs and still reads light purely through this rhythm.

---

## 3. Subheadings

### What H2s are *for* — four distinct models observed

**Argument stages** *(Intercom, Kinsta)* — principle → anatomy → institutionalisation.
> "The discipline of helping" → "The anatomy of an incident" → "Making the right response repeatable"

**Findings as full-sentence claims** *(Semrush)* — the heading *is* the conclusion; the body proves it.
> "2. SEO metrics don't always predict who wins a topic in ChatGPT"
> "3. Once you own a topic in ChatGPT, you tend to hold it. But only if your lead is wide."

**Search-intent slots** *(Zapier, HubSpot)* — each H2 is a query someone actually types.
> "Best free photo editing app for Android" · "What is a sales plan?" · "Which Android or iPhone photo editing app should I use?"

**Bare keyword entities for snippet capture** *(SEJ, Ahrefs)* — middle H2s are the term itself.
> "Customer Acquisition Cost" · "Return On Ad Spend" · "Lifetime Value"

### The near-universal rules

1. **The final heading is never "Conclusion."** Every single benchmark converts it into a claim
   or an imperative:
   - "The line between human and machine is gone" *(Kinsta)*
   - "Making the right response repeatable" *(Intercom)*
   - "Start Building Better Reports" *(SEJ)*
   - "How to start winning at the topic level" *(Semrush)*
   - "Final thoughts" *(Ahrefs — the one boring exception)*
2. **H3s enumerate what the H2 announces** — causes, steps, options, or objections.
3. **Objections make excellent H3s.** Kinsta puts the excuse in quotes and answers it:
   > "We'll manage access manually" · "Clients don't need that much access" · "This hasn't caused issues yet"
4. **TOC on anything over ~1,500 words.** Ahrefs uses a sticky rail; HubSpot a jump-link list;
   Semrush a sticky TOC plus a "Key takeaways" box above it.

### Rules for Certinal

- **Structure long-form as: what the law says → what it requires of you → when it bites → what to do now.**
- **Put the provision number in the H3, the plain-English meaning in the H2.** The H2 wins the
  topical query; the H3 wins the "section 8(5) DPDP" query. This mirrors Zapier's split
  (use-case in H2, product name in H3).
- Every obligation section must carry its **effective date in the heading or the first line**.
  See §9.

---

## 4. Hooks

### The six hook types, verbatim

**Cold-open scene** *(Intercom)* — present tense, no thesis yet.
> "It's Wednesday at 2pm. A routine deploy goes out. Within minutes, customers cannot open the app. Alarms fire, the pager goes off, and the heartbeat metrics begin to drop."

**Second-person humiliation scene** *(SEJ)* — the reader's own effort, dismissed by a quoted boss.
> "You're finalizing a monthly PPC report, excited to show improvements you've seen in the account… Yet when you present the report to leadership, you still get questions like, 'How are these actions helping us grow revenue?'"

**Behavioural mirror** *(Kinsta)* — describe the reader's shortcut without judgment, then charge interest.
> "You share Admin credentials because it's faster… The problem is that these shortcuts become part of the template for every project that follows."

**Counterintuitive claim + staccato proof** *(Ahrefs)*
> "Some of the highest-traffic pages on the internet aren't articles. They're tools. A grade calculator. A file converter."

**Reversal cold open** *(Semrush)* — and note they deliberately **withhold the statistic**.
> "Brand visibility in ChatGPT shifts prompt by prompt… Track only one, and you'd think you're winning. Look across the topic, and the picture changes."

**Concede the objection, then credential** *(HubSpot)*
> "User experience design gets a bad rap for being too abstract. And true, it's tough to quantify 'user-friendliness.' … As editor of HubSpot's Website blog, I come across and analyze dozens of websites every week."

### The rule every one of them follows

**Zero throat-clearing.** Not one of 21 analysed posts opens with "In today's fast-paced digital
landscape." The first sentence is already inside the problem. Semrush's discipline is worth
copying explicitly: **no post opens with a statistic** — the numbers are held for the Key
Takeaways box, so the opening earns attention with tension instead.

### Rules for Certinal

- **Default to the behavioural mirror or the cold-open scene.** Compliance readers respond to
  the specific operational moment: the DPO who cannot answer where consent records live, the
  procurement lead who discovers a vendor's signature audit trail doesn't survive a challenge.
- **The stat-hook is available to us in one form only:** a cited provision. *"The DPDP Rules give
  you 90 days to respond to a Data Principal request (Rule 14). Most consent desks cannot tell
  you what day the clock started."* — legal weight, then operational pain.
- **Never open with an unsourced fear statistic.** No "73% of Indian companies are unprepared"
  unless we can link the study in the same paragraph.

---

## 5. Tone

### What each blog sounds like, with evidence

| Blog | Register | Proof |
|---|---|---|
| Ahrefs | Blunt, numerate, self-implicating | "that deck calculator cost me $1.24 and about a minute" |
| Intercom | Aphoristic, permission-giving | "Asking for help is not a failure. Rolling back is not an admission of defeat." |
| SEJ | Declarative, attributed | "As Duane Forrester said, 'If your content can be fully replaced by a summary, it has no moat.'" |
| Zapier | Warm, anti-hype, funny | "There's no reason to use a bad app with good marketing." |
| HubSpot | Chatty, prescriptive | "for the love of saving time and frustration, please:" |
| Semrush | Epistemically careful | "Treat that as a hypothesis, not a finding." |
| Kinsta | Peer-to-peer, hedged | "may not," "can create" — never "revolutionary" |

### The transferable mechanics

- **Second person for the problem, first-person plural for the evidence.** "You share Admin
  credentials…" / "In our AI & Bot Traffic Report, we analyzed…"
- **Contractions everywhere.** All seven. No exceptions.
- **Jargon glossed inline in parentheses**, never in a glossary box: *"dodging and burning
  (selectively darkening or brightening areas of your image)"* *(Zapier)*.
- **Hedging is credibility, not weakness** — but it must be *specific*: "Why the switches happen
  isn't something this data can answer" *(Semrush)* beats a vague "may vary".
- **Conviction avoids arrogance by pairing every claim with a cost or counter-example** *(Intercom)*.

### Rules for Certinal

- **Professional peer-to-peer.** Our reader is a DPO, GC, compliance lead, or IT security owner.
  They are competent; write to them as such. No humour — a wrong compliance call is somebody's
  regulatory exposure.
- **Ban the hype register outright:** revolutionary, game-changing, seamless, cutting-edge,
  robust, leverage, unlock.
- **Hedge legal interpretation, never legal text.** The provision says what it says — quote it
  flatly. Our *reading* of it is where "in our view" and "organisations should consider" belong.
- **Never write "you must" for an obligation not yet in force.** See §9.

---

## 6. Calls to action

### Three distinct models

**Two-beat close** *(Kinsta, Intercom, Ahrefs, SEJ)* — free homework first, one soft product line second.
> *(Kinsta, para 1)* "The next step is to put the access policy in writing using the role mapping table above, and run a first quarterly review on your existing portfolio…"
> *(Kinsta, para 2)* "For agencies managing client sites at scale, Kinsta's Agency Partner Program gives you dedicated support…"

Intercom's ending contains **no CTA at all** — the post simply ends on the reader's next move:
> "They start with one workflow, measure the result, and use that proof to make the case for what comes next."

Ahrefs closes on a three-word imperative aimed at the reader's own site: **"Go build one."**

**Conditional product weave** *(Intercom, Zapier)* — the product appears mid-body as an if-clause.
> "If you're using Fin, the Recommendations dashboard surfaces these insights directly."

**Saturation model** *(HubSpot)* — and this is the outlier. One post carried **7 distinct gated
offers across 46 link instances**, with the first CTA firing *before paragraph two*. It works
only because **the article's outline is the outline of the lead magnet** — each of the eight
component H3s maps 1:1 to a field in the downloadable template, so the offer is never an
interruption. Do not copy the volume without copying that structural discipline.

### Rules for Certinal

- **Use the two-beat close.** Paragraph 1: the concrete step the reader can take Monday with no
  purchase — run the record-of-consent audit, map who signs what, list your processors.
  Paragraph 2: one on-topic Certinal line.
- **Match the CTA to the post's specific problem.** Never a generic "Book a demo" on a post about
  erasure timelines.
- **Product CTAs are conditional, never imperative**, in any post that interprets law. "If you
  already use Certinal, the audit trail export covers this" — not "Certinal solves DPDP."
- **The disclaimer is not a CTA and does not replace one.** Both appear; disclaimer last.
- **No comment/share prompts.** None of the seven B2B benchmarks use them.

---

## 7. SEO and keywords

### Observed conventions

**Slugs are short, keyword-only, and deliberately decoupled from the headline.** This is
near-universal and is the most under-used technique on the list:

| Headline | Slug |
|---|---|
| "Turn off your slop cannon" | `/blog/remove-ai-slop-from-writing/` *(Zapier)* |
| "6 Steps to Create an Outstanding Marketing Plan" | `/marketing/marketing-plan-template-generator` *(HubSpot)* |
| "The ultimate guide to knowledge management for your Service Agent" | `/guide-customer-service-knowledge-management-ai/` *(Intercom)* |

The headline is free to be creative or to be rewritten later for CTR; the URL keeps the keyword
and the link equity. SEJ freezes the slug and rewrites headlines post-publish.

**Keyword placement:** exact keyword in slug + H1 + first ~50 words + at least one H2. Then stop
forcing it — semantic coverage takes over.

**Snippet formatting that recurs everywhere:**
- A definition sentence directly under a question H2: *"A sales plan outlines a team's objectives, high-level tactics, target audience, and potential obstacles."* *(HubSpot)*
- Numbered step H3s
- Comparison tables (Ahrefs ran 14+ tables in a single post)
- A "Key takeaways" bullet box above the fold *(Semrush)*
- Three-bullet takeaway blocks on news posts *(SEJ)*

**Meta description formula** — mechanism + benefit, one sentence:
> "How retrieval augmented generation works—and how to optimize your content so AI search engines like ChatGPT actually retrieve and cite it." *(Ahrefs)*
> "Cron jobs, imports, and backups can slow WordPress without warning. Learn how background activity affects performance." *(Kinsta)*

**Word counts by type:** news ~600 · opinion 800–1,400 · how-to 1,200–2,900 · data study
1,400–2,000 · pillar guide 4,500–6,200.

**Freshness signals:** Kinsta and HubSpot show "Updated" dates prominently. Zapier discloses in
italics at the foot: *"This article was originally published in November 2023. The most recent
update was in July 2026."* Ahrefs shows live organic-traffic stats instead.

### Rules for Certinal

- **Target problem phrases, not head terms.** Kinsta doesn't fight for "wordpress hosting"; it
  takes "reduce bandwidth waste bot traffic". We should not fight for "eSignature" — we should
  own *"DPDP consent manager registration requirements"*, *"data principal request 90 day
  response"*, *"eSignature legal validity India"*, *"DPDP breach intimation timeline"*.
- **Slug = the compliance query. Headline = the hook.** Slug `dpdp-consent-manager-rule-4`,
  headline *Consent Manager registration: what Rule 4 actually requires, and when*.
- **Definition sentences are mandatory** — they win snippets *and* they're how a compliance reader
  scans. Format: *"A Consent Manager is [definition] (DPDP Rules 2025, r.4)."*
- **Show "Updated" dates on everything.** Compliance content that looks stale is worse than
  useless — a reader can't tell whether it predates the 13 Nov 2025 notification.
- **Build hub-and-spoke clusters.** Kinsta ran five bot-traffic posts into one gated report.
  Ours: one pillar per obligation cluster — Consent · Breach & security · Retention & erasure ·
  Data Principal rights · Cross-border — each with 4–6 spokes citing individual provisions.

---

## 8. Internal linking

### Observed

| Blog | In-body internal links per long post |
|---|---|
| Ahrefs (pillar) | ~30 |
| Kinsta | 25–30 |
| HubSpot | 18 siblings + 24 offer links |
| Semrush | 16–18 |
| Zapier | ~16 |
| SEJ | 9–13 |
| Intercom | 7–9 |

**Anchor text is always descriptive; "click here" appears zero times across all seven.**

Three anchor styles worth distinguishing:
- **Exact-match noun phrase** *(HubSpot, Semrush)* — "buyer persona", "Keyword Magic Tool"
- **The target's full headline** *(Zapier)* — "The best free photo editors"
- **A sentence fragment that states the finding** *(Ahrefs, Intercom)* — "We studied this 'phenomenon' back in the day", "how we prepare for our busiest days"

The third is the most sophisticated: the anchor is the grammatical object of its own clause, so
the link reads as prose rather than as an insert. Intercom links the same target twice under two
different phrasings and has **no "Related reading" list at all** — every link is load-bearing.

### Rules for Certinal

- **15–25 in-body internal links** in long-form. We are currently far below industry norm.
- **Every provision mentioned links to our own explainer for that provision.** This is the
  compliance-content equivalent of Ahrefs' glossary linking, and it compounds: the more
  provisions we cover, the denser the mesh.
- **Anchor on the provision's plain-language name, not its number** — "the 90-day response
  window", not "Rule 14" — so the anchor carries topical meaning.
- **Every spoke links up to its pillar; the pillar links down to every spoke.**
- Link outward to the official gazette texts. SEJ links CourtListener and Reuters Institute
  freely; authority linking builds trust and costs nothing.

---

## 9. The Certinal overlay — non-negotiable

These override every craft rule above. A beautifully structured post with a wrong citation is a
liability, not an asset.

1. **No legal claim without a source.** Every factual assertion about the DPDP Act or Rules must
   trace to the official text. If we can't source it, cut the sentence. Omission is always
   cheaper than a correction.
2. **Cite the final notified Rules** — Gazette G.S.R. 846(E), notified 13 Nov 2025. **Never** the
   January 2025 draft (G.S.R. 02(E)).
3. **Never imply an obligation is in force before its effective date.** Label every obligation:
   - Foundational provisions + Data Protection Board — **in force (13 Nov 2025)**
   - Rule 4, Consent Manager registration/obligations — **effective 13 Nov 2026**
   - Most substantive Rules — **effective 13 May 2027**
   Present tense for what's live; "will apply from [date]" for what isn't. This is the single
   easiest way for a well-meaning draft to become false.
4. **Penalty figures are breach-specific.** ₹250 crore attaches only to the security-safeguards
   breach; the residuary slab is ₹50 crore. Never attach the headline number to an unrelated
   obligation.
5. **Citation format in body copy:** plain-language claim, then the pin cite —
   *"…within ninety days (DPDP Rules 2025, r.14(2))."* Reviewers must be able to verify in seconds.
6. **Every published piece carries the disclaimer:** AI-assisted; general information only; not
   legal advice.
7. **Human review before publication.** No exceptions, regardless of how clean the draft looks.

---

## 10. Post skeletons

### A. The misconception post *(default format — Kinsta/SEJ hybrid)*
```
H1     Why "[the false belief]" [fails / doesn't survive the Rules]
Hook   Behavioural mirror — the reader's own shortcut, described without judgment
H2     How [the shortcut] became standard practice
H2     What the law actually requires        ← provision quoted, pin-cited, dated
  H3   "[Objection 1 in quotes]"
  H3   "[Objection 2 in quotes]"
  H3   "[Objection 3 in quotes]"
H2     What this looks like when it's done right
H2     [Thesis as a claim — never "Conclusion"]
Close  Beat 1: the audit they can run Monday. Beat 2: one Certinal line. Disclaimer.
Length 1,200–1,800 words · 15–20 internal links
```

### B. The provision explainer *(Semrush/Zapier hybrid — snippet-optimised)*
```
H1     [Provision plain name]: what [Rule N] actually requires, and when
Box    Key takeaways — 3–5 bullets, including the effective date
H2     What is [X]?                          ← definition sentence, immediately, pin-cited
H2     Who it applies to
H2     What you have to do
  H3   [Requirement 1] · [Requirement 2] · [Requirement 3]
H2     When it takes effect                  ← its own section, always
H2     Common ways teams get this wrong
H2     [Imperative next step]
Length 1,000–1,500 words · definition sentence under every question H2
```

### C. The original data post *(Semrush model — highest authority, hardest to fake)*
```
H1     [Finding stated as a claim]: [a study of N …]
Box    Key takeaways
H2     Methodology                           ← BEFORE any finding
  H3   Definitions                           ← operationalise every threshold used later
H2     1. [Finding as a full-sentence claim]
H2     2. [Finding as a full-sentence claim]
H2     3. [Finding as a full-sentence claim]
H2     How to act on this
Rules  Every chart caption states the conclusion, not the axes.
       Every finding ends with a bolded "The takeaway:" line.
       Sample size and timeframe stated as a bulleted "Scope of the data" block.
```

### D. The comparison post *(Kinsta model — bottom of funnel)*
```
H1     [A] vs. [B]: what's the difference, and which should you use?
Box    TL;DR                                 ← the verdict, up top
H2     [A] and [B] are not the same thing
H2     Understanding [A]
H2     Where [B] fits
H2     What [B] adds on top of [A]
  H3   [capability] × 4–6
H2     Which approach should you use?
  H3   Use [A] if…
  H3   Use [B] if…
  H3   Avoid using both unless…              ← the honest option; it builds trust
H2     [Category shift as a claim]
Note   This is the one format where a full product block at the end is appropriate.
```

---

## 11. Pre-publish checklist

**Structure**
- [ ] Headline in sentence case, 45–75 chars, matches one of the seven formulas
- [ ] Slug is the short keyword phrase, decoupled from the headline
- [ ] Average paragraph 2–3 sentences; nothing over 5
- [ ] A heading, list, table, or callout every ~3 paragraphs
- [ ] Final heading is a claim or imperative — not "Conclusion"
- [ ] TOC present if over 1,500 words

**Voice**
- [ ] First sentence is already inside the problem; no throat-clearing
- [ ] Second person for the problem, "we" for our own evidence
- [ ] Zero hype adjectives
- [ ] Jargon glossed inline on first use
- [ ] Two-beat close: reader's homework, then one on-topic CTA

**SEO**
- [ ] Keyword in slug, H1, first 50 words, ≥1 H2
- [ ] Definition sentence under each question H2
- [ ] Meta description = mechanism + benefit, one sentence
- [ ] 15–25 in-body internal links, all descriptive anchors
- [ ] Links up to its pillar and down to its spokes
- [ ] "Updated" date displayed

**Legal — blocking**
- [ ] Every legal claim traced to the official text
- [ ] Rules cited are G.S.R. 846(E) (13 Nov 2025), never the January 2025 draft
- [ ] Every obligation labelled with its effective date; no future obligation in present tense
- [ ] Penalty figures matched to the correct breach type
- [ ] At least 3 citations spot-verified against the source PDFs by a human
- [ ] Disclaimer present
- [ ] Human review complete

---

## 12. Source appendix

Scraped 2026-07-22 via Jina Reader (`mcp__jina__read_url`), public pages only; Kinsta's post-level
figures came from an earlier WebFetch pass.

| Blog | URL | Analysed |
|---|---|---|
| Ahrefs | https://ahrefs.com/blog/ | index + 3 posts |
| HubSpot | https://blog.hubspot.com/ | index + 3 posts |
| Search Engine Journal | https://www.searchenginejournal.com/ | index + 3 posts |
| Intercom | https://www.intercom.com/blog/ | index + 3 posts |
| Zapier | https://zapier.com/blog | index + 3 posts |
| Semrush | https://www.semrush.com/blog/ | index + 3 posts |
| Kinsta | https://kinsta.com/blog/ | index + 4 posts |

**Known gap:** Kinsta's paragraph-length figures are reported estimates, not counted sequences
like the other six. Recount before treating that row as measured.

### The one thing to steal from each

| Blog | Technique |
|---|---|
| **Ahrefs** | **Every claim is priced.** Not "tools are cheap to build" but "that deck calculator cost me $1.24 and about a minute" — a specific number, its provenance, and the reproducible input, in the same sentence as the claim. |
| **Semrush** | **Methodology before findings**, with a Definitions block that operationalises every threshold the headline depends on — so every later stat is auditable. |
| **Intercom** | **The recursive maxim.** Each section compresses into one portable, opinionated sentence, stated → pull-quoted → echoed at the close. Always *after* the scene that earned it. |
| **SEJ** | **Attribute-then-argue with named, linked, non-competing humans** — turning an unprovable opinion into a reported piece. |
| **Zapier** | **The methodology receipt published before the first pick**, including what was disqualified and why. Converts a listicle into a defensible verdict. |
| **HubSpot** | **Write the article's outline from the outline of the offer**, so the CTA is the next logical step rather than an interruption. |
| **Kinsta** | **Name the false belief in the headline, correct it over 2,000 vendor-neutral words, and let one CTA carry all the commercial weight.** |

**For Certinal, the two that matter most are Semrush's and Ahrefs':** methodology-before-findings
and price-every-claim are the same instinct that governs our citation-grounded pipeline — show the
evidence before the conclusion, and make every assertion auditable by a reader who doesn't trust us
yet. That instinct is already our constraint. This playbook just makes it read well.
