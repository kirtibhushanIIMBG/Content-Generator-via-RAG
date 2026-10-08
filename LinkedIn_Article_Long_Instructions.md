# How to Write a LinkedIn Article — LONG form

**Use this when the form option `LinkedIn Article — Long` is selected.**
Reference for generating a long-form LinkedIn article on India's DPDP Act 2023 / DPDP Rules 2025 for
Certinal. Follow it top to bottom. It is the working distillation of
[LinkedIn_Article_Playbook_Certinal.md](LinkedIn_Article_Playbook_Certinal.md) (the evidence) and it
inherits the legal gates in [Blog_Content_Generation_Instructions.md](Blog_Content_Generation_Instructions.md) §8.

| Setting | Value |
|---|---|
| Target length | **1,200–2,200 words** |
| Deployed `style` | `linkedin_article` |
| `mode` | `dpdp` (grounded + cite_check + human review) — never `general` for anything that touches the law |
| Output is | a **draft for verification**, never final copy — it goes through cite_check and a human reviewer before any publish step |

> **The one rule above all others:** never write a legal claim you cannot support from a retrieved
> source. Omit rather than invent. Every rule below is subordinate to §7.

---

## 1. Before you write — pick the lane

Long-form has three registers. Choose one by **who the reader is**; do not mix them inside one piece.

| Lane | Reader | Engine | Default? |
|---|---|---|---|
| **A. Practitioner** | DPO, compliance lead, IT security owner | Unknown exposure — "your own systems are doing this and you can't see it" | **Yes — default** |
| **B. Executive** | CISO, GC, CIO, board | Say-do gap — "you know you must comply; few know how" | Board/strategy pieces only |
| **C. Explainer** | Solution-aware / technical evaluator | Hidden complexity — "this looks simple; here's what it actually takes" | "How the rule works" pieces |

If unsure, write **Lane A**. It is the shipped voice.

---

## 2. The structure (10 slots — the LinkedIn long-article template)

Fill each slot. Adapt the *depth* to the target length; at the shorter end (~1,200 words) keep every
move but compress it. **Headings are claims, not labels** — a reader skimming only the headings must
receive the whole argument. Write *"One Mistake Can Cost ₹250 Crore,"* never *"Penalties."*

| # | Slot | What it does | Note |
|---|---|---|---|
| 1 | **Executive headline** | 6–13 words, sentence case, attacks a *practice* — never asserts a legal position | §3 |
| 2 | **Executive summary / "At a Glance"** | 3 bullets, each a claim + consequence, a hard number in the first (Lane B especially) | scannable before prose |
| 3 | **Hook — cold-open scene** | A named role doing one mundane action that has quietly changed their legal position | no throat-clearing |
| 4 | **The framing turn** | "[Practice] has arrived. Governance has not." — name the gap | one-sentence paragraph |
| 5 | **The specific risky practices** | A short numbered list of the gaps | one level deep |
| 6 | **A labelled hypothetical** | "A Very Real Scenario (Hypothetical) in an Indian [setting]" | **must** say hypothetical |
| 7 | **International precedent** | A foreign regulator's posture — jurisdiction + year — as **context only** | never a claim about India |
| 8 | **What the DPDP obligation requires** | The provision, quoted in a blockquote, **pin-cited and date-labelled** | the spine — §7 |
| 9 | **The consequence** | The cost of the gap — the correct penalty slab, or omit | §7.4 |
| 10 | **Phased mitigation + close** | First 30 days / Next 90 days / Ongoing → then a question to a named leader or a "not just X, it is Y" line → two-beat CTA → disclaimer | end on a **short** sentence |

**Executive lane (B) swap:** replace slots 3–7 with the five-beat arc — *signal → say-do gap → why
the old playbook fails → a named, numbered framework (count stated up front, each move a bold
imperative) → each move anchored to a concrete practice*. Close on an *"Illuminating questions the
CISO should ask the board"* list.

**Explainer lane (C) swap:** open on one concrete case that makes the problem felt, coin a
plain-language handle for the hard concept and reuse it, run *problem → why the obvious fix fails →
the real mechanism*, then a **Rule → obligation → who it binds → effective date** table.

---

## 3. Craft rules (measured — apply to every slot)

**Headline**
- 6–13 words, sentence case. Patterns that work: the two-part *"situation. imperative."* (a period
  as the pivot), the contrarian reversal (*"[belief] is over — [replacement]"*), the "how it works"
  explainer, or the question title.
- **Never assert a legal position in a headline** — no headline can carry a pin cite. Attack a
  practice: *"Why 'we'll get consent later' breaks under the DPDP Rules."*

**Hook**
- Zero throat-clearing. Banned openers: "In today's…", "In the ever-evolving…", "As we all know…".
- The first sentence is already inside the problem. Run the lede cooler than the headline.
- Do **not** open with a statistic unless it is a pin-cited provision or our own measured data.

**Sentences & paragraphs**
- Sentences average **12–18 words**; legal-explanation passages may run 20–30 — keep them rare.
- Rhythm = one long explanatory sentence, then a **short verdict**. Never sustained either way.
- Paragraphs **1–3 sentences**. Use one-sentence paragraphs for verdicts and turns, not transitions.
- A visual break every ~100–150 words: heading, list, table, or a **colon stem into bullets**
  (*"This means:"* → bullets). Never more than 3 consecutive prose paragraphs.
- Required devices, at least one each: a **negation cascade** (*"Not eventually. Not next quarter.
  Now."*) and a **short two-part contrast** (*"The technology changed. The duty did not."*).

**Headings**
- Every heading is a claim or an imperative. The final heading is **never** "Conclusion."
- Put the plain-English meaning in the heading; the provision number belongs in the body/pin cite.

**Tone**
- Authoritative practitioner writing to a competent peer. **Sustained second person** ("your
  hospital," "you cannot prove") — the moment you drift to "organisations should," specificity dies.
- Blame is **architectural**, never individual: *"there was no process to detect it,"* never *"a
  careless nurse."*
- Serious throughout — no humour, no emojis, no hashtags in long form.
- Say **"must"** for obligations, never "should." Hedge our *interpretation* ("in our view,"
  "organisations should consider"), never the statutory text — quote the provision flat.
- **Banned words:** revolutionary, game-changing, seamless, cutting-edge, robust, leverage, unlock,
  supercharge, effortless, best-in-class. No academic connectives (moreover, thus, heretofore).

**Bold**
- Bold **only** statute names, defined terms, and dates. Do not bold for generic emphasis — put
  emphasis in a short sentence fragment instead.

**Evidence**
- Precise numbers over adjectives; every quantified claim carries its source in the same sentence or
  is omitted. Extract 2–3 screenshot-ready one-liners — they are what get quoted in the feed.

**Close**
- **Two-beat close.** Beat 1: the audit the reader can run Monday with no purchase (map who signs
  what; list your processors; find the day the retention clock started). Beat 2: **one** on-topic
  Certinal line in **conditional** voice — *"If you already use Certinal, the audit-trail export
  covers the evidentiary requirement,"* never *"Certinal makes you DPDP compliant."*
- No comment/share prompts. Do not append a personal bio, a consulting pitch, or "Article N of a
  series." The disclaimer is not a CTA — both appear; disclaimer last.

---

## 4. Citations — the exact format

Cite every DPDP claim **in square brackets, beginning with "DPDP"**, verbatim from the retrieved
`# Source:` header:

- `[DPDP Act 2023, s.8(5)]` · `[DPDP Rules 2025, r.7]` · `[DPDP Act 2023, Schedule]`
- A bare `[s.8(5)]`, an un-bracketed *"under s.8(5)"*, or a gazette number as a cite is **invisible
  to cite_check** and scores as uncited.
- Prefer the **precise sub-section** the retrieved chunk supports (`s.8(5)` off an `s.8` header
  validates); never cite a sub-section the chunk lacks. Off a range slice, do not nest deeper than
  one level.
- Every sentence stating a legal requirement carries a citation — including restatements ("This
  means…", "Note that…"). A bulleted list may cite on its stem.

---

## 5. The Certinal legal facts (for status-dating — never a substitute for retrieval)

Every date, provision, and penalty you **print** must still trace to a retrieved chunk. These are
for accuracy-checking only:

- **Cite the final notified Rules** — Gazette **G.S.R. 846(E), 13 Nov 2025**. **Never** the January
  2025 draft (G.S.R. 02(E)).
- **Effective dates** — state authority status in a standalone sentence; present tense only for
  what's live:
  - Foundational provisions + Data Protection Board of India — **in force (13 Nov 2025)**
  - Rule 4, Consent Manager registration/obligations — **effective 13 Nov 2026** → "will apply from"
  - Most substantive Rules (security, breach, retention, rights) — **effective 13 May 2027** → "will apply from"
- **Never imply a future obligation binds today.** State it is not yet in force, then justify acting
  now on cost / forward-compatibility grounds.
- **Penalties are breach-specific.** ₹250 crore is **only** the s.8(5) security-safeguards slab;
  breach-notification ₹200 crore; child-data ₹200 crore; SDF duties ₹150 crore; every other breach
  is the residuary head, up to ₹50 crore. Cite the matching slab from the retrieved
  `[DPDP Act 2023, Schedule]` and name the Schedule.
- Never present a foreign figure (e.g. GDPR's 72-hour clock) as an Indian requirement.

---

## 6. Fill-in skeleton

```
HEADLINE   [Practice] has arrived. Governance has not.   |   Why "[false belief]" breaks under the Rules

[At a Glance — 3 bullets, each claim + consequence; a hard number in the first]   ← Lane B especially

HOOK       [A named role — the DPO, the ward clerk — doing one ordinary thing that just changed
            their legal position. Present tense. No thesis yet.]

## How [the shortcut] became standard practice
[Behavioural mirror — describe the reader's own shortcut without judgment, then the delayed cost.]

## The gaps you cannot currently see
1. [risky practice]   2. [risky practice]   3. [risky practice]

## A Very Real Scenario (Hypothetical) in an Indian [hospital / bank / insurer]
[The labelled hypothetical. Concrete, sector-specific, named systems (HIS, PACS, a TPA workflow).]

## What the DPDP obligation actually requires
> [Provision quoted]   [DPDP Rules 2025, r.N]
[Plain-English restatement — cited. State the effective date in its own sentence.]

## What this exposure costs
[The correct penalty slab, cited to the Schedule — or omit the number.]   [DPDP Act 2023, Schedule]

## [Thesis restated as a claim — never "Conclusion"]
This means:
- First 30 days: [action]
- Next 90 days: [action]
- Ongoing: [action]

[Close: a question to a named leader, or a "not just X, it is Y" line. End on a SHORT sentence.]
[Two-beat CTA: the Monday audit, then one conditional Certinal line.]
[Disclaimer — appended by the service; do not write your own.]
```

---

## 7. Non-negotiable gates (blocking — override everything above)

1. No legal claim without a retrieved source. If you can't cite it, cut the sentence.
2. Cite G.S.R. 846(E) (13 Nov 2025) — never the January 2025 draft.
3. Every obligation carries its effective date; no future obligation in the present tense.
4. Penalty figures matched to the correct breach slab; ₹250 crore only for s.8(5).
5. Foreign precedent is context, never an Indian requirement.
6. Every hypothetical is labelled hypothetical.
7. Disclaimer present (service-appended). Human review before any publish. No exceptions.
8. If retrieval returns no grounded source, output `no grounded source` — do not write around it.

---

## 8. Pre-send checklist

**Structure & voice**
- [ ] One lane chosen; tone and evidence match it
- [ ] Headline 6–13 words, sentence case, asserts **no** legal position
- [ ] First sentence is inside the problem; no banned opener
- [ ] Every heading is a claim/imperative; final heading is not "Conclusion"
- [ ] Sentences avg 12–18 words; long-then-short rhythm; article ends on a short sentence
- [ ] Paragraphs 1–3 sentences; a visual break every ~150 words; no run of 4+ prose paragraphs
- [ ] One negation cascade and one two-part contrast present
- [ ] Bold only on statute names, defined terms, dates
- [ ] Two-beat close; Certinal line conditional; no bio/hashtags/comment-prompt

**Legal — blocking**
- [ ] Every legal claim in a `[DPDP …]` bracket, verbatim from the source header
- [ ] Rules cites are G.S.R. 846(E), never the January 2025 draft
- [ ] Every obligation date-labelled; no future obligation in present tense
- [ ] Penalty figures matched to the correct slab; ₹250 crore only for s.8(5)
- [ ] Foreign precedent framed as context; every hypothetical labelled
- [ ] Disclaimer present; ≥3 citations spot-verified by a human; human review complete

---

## 9. Runtime preset (auto-synced into generate.py — THIS is what actually runs)

The condensed, machine-facing distillation of the guide above. `tools/sync_presets.py` copies the
text between the markers verbatim into `generate.py` `STYLES["linkedin_article"]`, which Render and
Streamlit deploy. After you edit the guide, mirror the change here and run
`python tools/sync_presets.py` (CI runs `--check`, which fails on drift). Edit only BETWEEN the
markers; whitespace/line-wrapping is normalised to single spaces on sync (the preset is one flowing
instruction to the model). The preset changes STRUCTURE AND TONE ONLY — it is followed by
`_STYLE_RULES_REMINDER`, so it can never loosen a hard rule or a legal gate; the §7 gates are
enforced there and in `STRICT_SYSTEM`, not here. It encodes **Lane A (the practitioner)** — the
shipped default (§1) — because the runtime has no lane selector; the Executive and Explainer lanes
are human-authored variants and are not part of the automated preset.

<!-- PRESET:linkedin_article -->
Format this piece as a LONG-FORM LINKEDIN ARTICLE of about 1,200-2,200 words, in the voice of a
senior compliance practitioner writing to a competent peer. Emotional engine: UNKNOWN EXPOSURE — the
reader is compliant on the surface but unaware of what their own systems are doing; reveal the gap
they cannot see, and remember the danger is never the dramatic external event they watch for, it is
the unexamined ordinary thing they already own. Serious throughout — no humour, no emojis, no
hashtags. Blame is always architectural (a missing process, no mechanism), never an individual —
write 'there was no process to detect it', never 'a careless nurse'. Write in SUSTAINED SECOND PERSON
('your hospital', 'you cannot prove'): mandatory, because it forces concrete provable claims, and the
moment you drift to 'organisations should' the specificity collapses. Fill ten slots, adapting DEPTH
to the target length and compressing every move at the shorter end rather than dropping it: (1) an
EXECUTIVE HEADLINE of 6-13 words, sentence case, that attacks a practice and never asserts a legal
position, since no headline can carry a citation; (2) an AT-A-GLANCE summary of three bullets, each a
claim plus its consequence, leading with a grounded number where the sources give one; (3) a HOOK
cold-open — a named role doing one mundane action that has quietly changed their legal position, in
the present tense, with zero throat-clearing, never 'In today's...' and no opening statistic unless
it is a cited provision; (4) a FRAMING TURN as a one-sentence paragraph — the practice has arrived,
the governance has not; (5) a short NUMBERED LIST of the specific risky practices or gaps, one level
deep; (6) a clearly LABELLED hypothetical in an Indian setting ('A Very Real Scenario (Hypothetical)
in an Indian hospital'), concrete and sector-specific, naming real systems (HIS, PACS, a TPA
workflow); (7) INTERNATIONAL PRECEDENT — a foreign regulator's posture with its jurisdiction and
year, kept brief and framed as context, NEVER as a claim about the Indian regime; (8) WHAT THE DPDP
OBLIGATION REQUIRES — the provision quoted in a blockquote, then restated in plain English with its
citation inline and its effective date in its own sentence when the provision is future-dated; (9)
THE CONSEQUENCE — the cost of the gap, with the correct penalty slab named to its Schedule, or the
number omitted; (10) a PHASED MITIGATION close — First 30 days / Next 90 days / Ongoing — then a
closing question to a named leader or a 'not just X, it is Y' line, then a TWO-BEAT close: first the
audit the reader can run on Monday with no purchase (map who signs what, list the processors, find
the day the retention clock started), then exactly one on-topic Certinal line in conditional voice
('If you already use Certinal, the audit-trail export covers the evidentiary requirement'), never a
bare product claim. HEADINGS ARE CLAIMS, not labels — 'One Mistake Can Cost the Business', never
'Penalties' — and the final heading is never 'Conclusion'; a reader skimming only the headings must
receive the whole argument. Sentences average 12-18 words, with legal-explanation passages allowed to
run 20-30 but kept rare; the rhythm is a long explanatory sentence then a short verdict, never
sustained either way; paragraphs are 1-3 sentences, one-sentence paragraphs carry verdicts and turns,
and no more than three prose paragraphs run without a visual break (a heading, a list, a table, or a
colon stem into bullets — 'This means:'). Use at least one negation cascade ('Not eventually. Not
next quarter. Now.') and one two-part contrast of short sentences ('The technology changed. The duty
did not.'), and END the article on a SHORT sentence. Do not bold for emphasis — bold only statute
names, defined terms and dates. Vocabulary leans on the language of missing control (uncontrolled,
undetected, ungoverned, no audit trail, cannot demonstrate, no one noticed); say 'must', never
'should'; and avoid the hype register entirely (revolutionary, game-changing, seamless, cutting-edge,
robust, leverage, unlock, supercharge, effortless, best-in-class). Do NOT append a personal bio, a
consulting pitch, or 'Article N of a series'.
<!-- /PRESET -->
