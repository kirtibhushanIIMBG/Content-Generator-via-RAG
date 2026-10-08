# How to Write a NEWSLETTER item

**Use this when the form option `Newsletter section` is selected.**
Reference for generating one **email-newsletter item** on India's DPDP Act 2023 / DPDP Rules 2025
(and, where retrieval supports it, eSignature validity) for Certinal. Follow it top to bottom. It is
the working distillation of [Newsletter_AI_Training_Corpus_Certinal.md](Newsletter_AI_Training_Corpus_Certinal.md)
(the evidence — 10 gold-standard B2B/executive/compliance sources scraped 2026-07-23) and it inherits
the legal gates in §7.

| Setting | Value |
|---|---|
| Target length | **350–600 words** (subject line + preview text + body; the form's `word_count` governs, soft aim) |
| Deployed `style` | `newsletter` |
| `mode` | `dpdp` (grounded + cite_check + human review) — never `general` for anything that touches the law |
| Output is | a **draft for verification**, never a sent email — it goes through cite_check and a human reviewer, who owns the actual send |

> **The one rule above all others:** never write a legal claim you cannot support from a retrieved
> source. Omit rather than invent. Every rule below is subordinate to §7.

> **What this is — and is NOT.** This is ONE self-contained newsletter item — a compact digest unit
> that lands in a busy inbox and competes with twenty other emails. It carries its own subject line
> and preview text (the email wrapper supplies masthead, other sections, unsubscribe). It is NOT a
> blog post, NOT a LinkedIn article, and NOT a full multi-section email. **One clear message**, then
> out. The reader is a DPO, general counsel, compliance lead, or IT/security owner scanning on a
> phone between meetings.

---

## 1. Before you write — pick the register

Newsletter items have two registers. Choose one by **what the item is doing**; do not mix them.

| Register | When | Engine | Default? |
|---|---|---|---|
| **A. Digest brief** | "Here is what changed and what to do" — a rule, a date, an obligation | Time pressure — a deadline is closer than the reader thinks | **Yes — default** |
| **B. Executive insight** | "Here is what this shift means for you" — a strategic read | Say-do gap — you know the rule is coming; few know how to prepare | Board/strategy issues |

If unsure, write **Register A**. It is the shipped voice: brisk, factual, useful — a good internal
briefing, not marketing.

---

## 2. The structure (7 slots — the newsletter template)

Fill each slot in order. Keep the whole thing scannable on a phone: short blocks, generous white
space, the load-bearing few words in **bold**.

| # | Slot | What it does | Note |
|---|---|---|---|
| 1 | **Subject line** | 4–9 words. Earns the open. Attacks a *practice* or names a *change* — never asserts a legal position (a subject line can carry no citation) | §3 |
| 2 | **Preview text** | 40–90 characters. The *second* hook — complements the subject, never repeats it; adds the stakes or the deadline | shows in the inbox beside the subject |
| 3 | **Hook** | 1–2 sentences already inside the problem — a behavioural mirror or a dated fact. Zero throat-clearing | no "In today's…" |
| 4 | **Main insight** | ONE message: the single most important point, stated plainly, in one bolded lead line | the "one clear message" rule |
| 5 | **Supporting evidence** | The provision, **pin-cited and date-labelled**; the correct penalty slab where relevant; 2–4 short lines or a tight bullet list | the spine — §7 |
| 6 | **Actionable takeaway** | A line beginning **"What this means for you:"** — one concrete step the reader can take, no purchase | always present |
| 7 | **CTA** | ONE soft, on-topic line — a question, a "reply and tell us", or one conditional Certinal line. Never a hard sell | end short |

---

## 3. Craft rules (measured from the corpus — apply to every slot)

**Subject line** (the single highest-leverage element — Best: HubSpot, Intercom, Ahrefs; compliance: CMS, Becker's)
- 4–9 words. Sentence case. Patterns that work, verbatim shapes observed in the corpus:
  - **Number-led:** *"5 things the DPDP Rules change for consent"* (Becker's *"5 things to know"*, Ahrefs *"6 Ways to…"*)
  - **Colon + payoff:** *"Consent Manager registration: what Rule 4 requires, and when"* (Ahrefs *"RAG Explained: How AI Decides…"*)
  - **Actor + action + purpose:** *"MeitY notified the Rules — here is your clock"* (CMS *"CMS Modernizes … Designed to …"*)
  - **Contrarian / tension:** *"Your consent form works — until someone withdraws"* (Ahrefs *"Works—Until It Backfires"*)
  - **Question:** *"Can you prove consent today?"* (McKinsey *"Will brands evolve with them?"*)
- **Never assert a legal position in the subject line** — it can carry no citation. Attack a practice
  or name a change, never *"You must do X by law."*
- No clickbait, no "Ultimate", no ALL-CAPS, no emoji, at most one number, never a naked date alone.

**Preview text**
- 40–90 characters. It is the second line the inbox shows. **Complement**, never echo, the subject:
  if the subject names the change, the preview names the stakes or the deadline. No "View in browser".

**Hook**
- Zero throat-clearing. Banned openers: "In today's…", "In the ever-evolving…", "As we all know…".
- First sentence is already inside the problem: a behavioural mirror (the reader's own shortcut, then
  its cost) or a dated fact ("The Rules were notified on 13 November 2025.").
- Do not open with a statistic unless it is a pin-cited provision.

**Sentences & readability** (Best: Zapier, Kinsta — this is a phone-first format)
- Sentences average **10–16 words**. One idea per sentence. Prefer full stops to commas.
- Paragraphs are **1–2 sentences**. Generous white space — a line break between most sentences.
- Bold the **load-bearing few words** in a block (the deadline, the threshold, the obligation
  trigger), never a whole sentence. At most one short bullet list (3–5 items).
- One clear message. If you are explaining a second obligation, it is a second newsletter item.

**Tone**
- Brisk, factual, useful — the register of a good internal briefing, not marketing. Second person for
  what the reader must do. Contractions fine.
- Serious — no humour, no emoji, no exclamation marks. Say **"must"** for obligations, never "should".
- Hedge Certinal's *interpretation* ("in our view"), never the statutory text — quote the provision flat.
- **Banned words:** revolutionary, game-changing, seamless, cutting-edge, robust, leverage, unlock,
  supercharge, effortless, best-in-class. No academic connectives (moreover, thus, heretofore).

**CTA**
- Exactly one, soft, on-topic. A question to the reader, a "reply and tell us how you're preparing",
  or **one** conditional Certinal line — *"If you already use Certinal, the audit-trail export covers
  the evidentiary side"* — never *"Certinal makes you compliant."* No comment/share/subscribe stuffing.

---

## 4. Citations — the exact format (inherited, non-negotiable)

Cite every DPDP claim **in square brackets, beginning with "DPDP"**, verbatim from the retrieved
`# Source:` header:

- `[DPDP Act 2023, s.8(5)]` · `[DPDP Rules 2025, r.7]` · `[DPDP Act 2023, Schedule]`
- A bare `[s.8(5)]`, an un-bracketed *"under s.8(5)"*, or a gazette number as a cite is **invisible to
  cite_check** and scores as uncited.
- Prefer the **precise sub-section** the retrieved chunk supports; never cite a sub-section the chunk
  lacks. Off a range slice, do not nest deeper than one level.
- Every sentence stating a legal requirement carries a citation — including in the evidence bullets.
  A bulleted list may cite on its stem. The subject line and preview text carry NO citation, which is
  exactly why neither may assert a legal position.

---

## 5. The Certinal legal facts (for status-dating — never a substitute for retrieval)

Every date, provision, and penalty you **print** must still trace to a retrieved chunk. These are for
accuracy-checking only:

- **Cite the final notified Rules** — Gazette **G.S.R. 846(E), 13 Nov 2025**. **Never** the January
  2025 draft (G.S.R. 02(E)).
- **Effective dates** — state authority status plainly; present tense only for what is live:
  - Foundational provisions + Data Protection Board of India — **in force (13 Nov 2025)**
  - Rule 4, Consent Manager registration/obligations — **effective 13 Nov 2026** → "will apply from"
  - Most substantive Rules (security, breach, retention, rights) — **effective 13 May 2027** → "will apply from"
- **Never imply a future obligation binds today.** State it is not yet in force, then give the date.
- **Penalties are breach-specific.** ₹250 crore is **only** the s.8(5) security-safeguards slab;
  breach-notification ₹200 crore; child-data ₹200 crore; SDF duties ₹150 crore; every other breach is
  the residuary head, up to ₹50 crore. Cite the matching slab from `[DPDP Act 2023, Schedule]`.
- Never present a foreign figure (e.g. GDPR's 72-hour clock) as an Indian requirement.

---

## 6. Fill-in skeleton

```
SUBJECT:  [4–9 words — attack a practice or name a change; no legal position]
PREVIEW:  [40–90 chars — the stakes or the deadline; complements the subject]

[HOOK — 1–2 sentences already inside the problem. A behavioural mirror or a dated fact.]

**[Main insight — the single most important point, one bolded lead line.]**

What the source says:
- [Provision, plain-English, pin-cited]   [DPDP Rules 2025, r.N]
- [Effective date in its own line, if future-dated]
- [The correct penalty slab, cited — or omit the number]   [DPDP Act 2023, Schedule]

**What this means for you:** [one concrete step, no purchase].

[CTA — one soft line: a question, a "reply and tell us", or one conditional Certinal line.]

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
7. Disclaimer present (service-appended). Human review before any send. No exceptions.
8. If retrieval returns no grounded source, output `no grounded source` — do not write around it.

---

## 8. Pre-send checklist

**Structure & voice**
- [ ] One register chosen; one clear message only
- [ ] Subject line 4–9 words, asserts **no** legal position; preview text complements, doesn't repeat
- [ ] Hook is inside the problem; no banned opener
- [ ] Main insight is a single bolded lead line
- [ ] Sentences avg 10–16 words; paragraphs 1–2 sentences; load-bearing words bolded; ≤1 short list
- [ ] "What this means for you:" line present; exactly one soft CTA; no hype register
- [ ] Ends short

**Legal — blocking**
- [ ] Every legal claim in a `[DPDP …]` bracket, verbatim from the source header
- [ ] Rules cites are G.S.R. 846(E), never the January 2025 draft
- [ ] Every obligation date-labelled; no future obligation in present tense
- [ ] Penalty figures matched to the correct slab; ₹250 crore only for s.8(5)
- [ ] Disclaimer present; citations spot-verified by a human; human review complete

---

## 9. Runtime preset (auto-synced into generate.py — THIS is what actually runs)

The condensed, machine-facing distillation of the guide above. `tools/sync_presets.py` copies the
text between the markers verbatim into `generate.py` `STYLES["newsletter"]`, which Render and
Streamlit deploy. After you edit the guide, mirror the change here and run
`python tools/sync_presets.py` (CI runs `--check`, which fails on drift). Edit only BETWEEN the
markers; whitespace/line-wrapping is normalised to single spaces on sync (the preset is one flowing
instruction to the model). The preset changes STRUCTURE AND TONE ONLY — it is followed by
`_STYLE_RULES_REMINDER`, so it can never loosen a hard rule or a legal gate; the §7 gates are enforced
there and in `STRICT_SYSTEM`, not here. It encodes **Register A (the digest brief)** — the shipped
default (§1).

<!-- PRESET:newsletter -->
Format this piece as ONE SELF-CONTAINED EMAIL-NEWSLETTER ITEM — a compact digest unit that lands in a
busy inbox and competes with twenty other emails, NOT a blog post, NOT a LinkedIn article, and NOT a
full multi-section email. The reader is a privacy or compliance professional (a DPO, general counsel,
compliance lead, or IT/security owner) scanning on a phone between meetings. ONE clear message only —
carry a single change, obligation or deadline from start to finish; if a second obligation needs
saying, that is a second item, not this one. Register is the DIGEST BRIEF: brisk, factual, useful —
the voice of a good internal briefing, never marketing. Serious throughout — no humour, no emojis, no
exclamation marks, and none of the hype register (revolutionary, game-changing, seamless,
cutting-edge, robust, leverage, unlock, supercharge, effortless, best-in-class). Second person for
what the reader must do; say 'must' for obligations, never 'should'. Produce seven slots in order and
label the first two plainly: (1) SUBJECT: a 4-9 word subject line in sentence case that attacks a
practice or names a change and NEVER asserts a legal position, because a subject line can carry no
citation — use one of these shapes: number-led ('5 things the new Rules change for consent'), colon
plus payoff ('Consent Manager registration: what Rule 4 requires, and when'), actor plus action ('The
DPDP Rules were notified — here is your clock'), a tension line ('Your consent form works, until
someone withdraws'), or a question ('Can you prove consent today?'); no clickbait, no 'Ultimate', no
ALL CAPS, at most one number; (2) PREVIEW: a 40-90 character preview line that COMPLEMENTS the subject
rather than repeating it, adding the stakes or the deadline; (3) a HOOK of one or two sentences that
is already inside the problem — a behavioural mirror (the reader's own shortcut, then its cost) or a
dated fact — with zero throat-clearing, never 'In today's...', and no opening statistic unless it is a
cited provision; (4) a MAIN INSIGHT stated as a single bolded lead line that gives the one most
important point so a reader who reads only it has the gist; (5) SUPPORTING EVIDENCE as two to four
short lines or a tight three-to-five item bullet list, each legal point stated plainly with its
citation inline and its effective date on its own line when the provision is future-dated, and the
correct penalty slab named to its Schedule or the number omitted; (6) an ACTIONABLE TAKEAWAY line that
begins exactly with 'What this means for you:' and gives one concrete step the reader can take with no
purchase; (7) a single soft CTA — a question to the reader, a 'reply and tell us how you are
preparing', or exactly one on-topic Certinal line in conditional voice ('If you already use Certinal,
the audit-trail export covers the evidentiary side'), never a bare product claim and never a
comment/share/subscribe prompt. Keep it phone-first and scannable: sentences average 10-16 words, one
idea each; paragraphs are one to two sentences with a line break between most of them; bold only the
load-bearing few words in a block (the deadline, the threshold, the obligation trigger) and never a
whole sentence; use at most one short bullet list; no tables unless the content is a genuine date or
mapping. No salutations and no sign-offs — the newsletter wrapper adds those. Gloss any term of art in
parentheses the first time, then prefer plain references ('the organisation', 'the individual'). End
short. Do NOT append a personal bio, a masthead, an unsubscribe line, or 'View in browser'.
<!-- /PRESET -->
