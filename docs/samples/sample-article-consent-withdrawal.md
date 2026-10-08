> **STYLE DEMONSTRATION.** Written against style-linkedin-article.md, shown as the workflow PUBLISHES
> it: the generator emits inline [DPDP Act 2023, s.X] brackets (what cite_check validates), then Build
> Doc Text renders each as a superscript with the numbered References list below. Citations here are
> illustrative — live, every provision comes from a Qdrant-retrieved chunk and passes cite_check first.
> Abbreviated to ~800 words to show structure; the guide targets 1,200–2,200.

---

# You Got Consent at Admission. The Patient Withdrew It Last Week. Would Your Hospital Even Know?

A patient registered at your hospital fourteen months ago. At the desk, they signed your consent
form. Last Tuesday, they emailed your general enquiries inbox with one line: "Please stop using my
data for anything except my treatment."

That email changed your legal position. You may not have noticed.

## Withdrawal Is a Right, Not a Request

Under the DPDP Act 2023, a Data Principal may withdraw consent at any time, and the withdrawal must
be as easy to make as the consent was to give¹. From the moment that email arrived, every downstream
use of that patient's data outside their care became processing without a lawful basis.

Not next billing cycle. Not once someone opens the inbox. From the moment it was received.

This duty is not yet in force — it takes effect 13 May 2027¹. But the exposure is being built into
your systems today, and unwinding it later is far harder than designing for it now.

## Three Things Most Hospitals Have Never Built

Consider what answering that email actually requires. In most hospitals, none of it exists:

- A channel where a withdrawal is *received as a workflow event*, not lost in a shared inbox.
- A map of every downstream system the data reached — the HIS, the TPA, the analytics dashboard,
  the marketing CRM — so processing can actually stop everywhere.
- A record proving you stopped, and when.

Without the map, you cannot comply even if you want to. The data has already travelled somewhere no
one is watching, and you have no mechanism to call it back.

## A Very Real Scenario (Hypothetical) in an Indian Hospital

A cardiac patient withdraws consent for marketing use. The front desk notes it. But their contact
details were exported to a third-party campaign tool eight months earlier, and to the TPA for a
claim that is still open. The withdrawal reaches neither.

Six weeks later the patient receives a promotional message. They complain. Now the question is not
whether you honoured the withdrawal — it is whether you can *show* where their data went and prove
you controlled it. Most hospitals cannot.

## What Europe Has Already Dealt With

European regulators have enforced the right to withdraw consistently since GDPR took effect in 2018,
and the recurring finding is not malicious misuse — it is organisations that could not demonstrate
they had stopped. The penalty landed on the absence of a mechanism, not on bad intent.

India's Schedule sets penalties by the specific breach, not one headline number. Failing to honour a
withdrawal is not the ₹250 crore security-safeguards slab — it falls under the residuary head, up to
₹50 crore². This is the Indian figure; do not assume any foreign amount or timeline transfers.

## What You Must Build Before 13 May 2027

1. First 30 days — make withdrawal a logged event with an owner, not an inbox.
2. Next 90 days — map every downstream recipient of patient data; you cannot stop what you cannot see.
3. Ongoing — retain proof of cessation, and test it with a live drill.

## The Question Your Leadership Must Answer

If a patient withdrew consent today, could you show — right now, with evidence — every system that
stopped processing, and when?

If answering that requires an investigation, the gap is already your compliance gap.

## References

1. DPDP Act 2023, s.6(4) [effective 2027-05-13] — DPDP_Act_2023.pdf, p.5
2. DPDP Act 2023, Schedule [effective 2027-05-13] — DPDP_Act_2023.pdf, p.21

---

*AI-assisted, general information only, not legal advice.*
