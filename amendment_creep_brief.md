# Agency 2026 – Challenge 4: Sole Source & Amendment Creep
## Strategic Brief — Regis Nde Tene

---

## The Problem Worth Solving

Every major procurement scandal in Canada shares the same architectural gap.

It is not that no one was watching. It is that the system had no mechanism to ask the right questions **before a commitment became irreversible** — and no mechanism to determine what findings were **strong enough to act on** after the fact.

ArriveCAN: $54.7M in costs that could not be attributed or verified. Not because the data did not exist. Because no governance architecture required the reasoning chain to be documented at commitment time.

PPE Medpro: A $32M contract awarded through a referral channel with compressed timelines. Not because auditors were incompetent. Because the amendment process had no gate asking whether the original competitive justification still held.

The 19,303 amendments that doubled original contract values in Nate's analysis: each one represents a commitment made without a structured question being asked about whether the original scope, the original competition, and the original value still justified the new total.

**Detection finds these patterns. That is the necessary first step.**

**But detection is not the same as a defensible finding.**

---

## The Gap That Makes Detection Insufficient Alone

When an analytics system surfaces a contract where an amendment doubled the original value, it has produced a signal. That signal is useful. It is not, by itself, an accountability outcome.

The institution receiving that signal faces a question no dashboard can answer:

> *What are we permitted to conclude from this pattern — and what specifically needs to happen next?*

Without a structured answer to that question, three failure modes follow.

**Failure Mode 1 — Overclaiming.** The finding gets translated into an allegation stronger than the evidence supports. A 200% amendment ratio becomes "fraud" in a briefing note. An institution acts on a claim it cannot defend when challenged.

**Failure Mode 2 — Underclaiming.** The finding gets buried because no one knows how to formally escalate it. The signal existed. Nothing happened. The audit three years later finds the signal was visible at the time.

**Failure Mode 3 — Reasoning chain erasure.** The finding is acted on, but the reasoning behind the action cannot be reconstructed. The Auditor General asks why the contract was flagged and escalated. No one can replay the answer. The institution is left defending a decision it cannot document.

All three failure modes share the same root cause: **the gap between pattern detection and institutionally defensible action was never governed.**

---

## What a Complete Accountability System Must Do

A detection tool surfaces Amendment Creep candidates. That is the signal layer.

A complete accountability system must also:

1. **Match claim strength to evidence strength.** A contract with a 300% amendment ratio is not the same as a contract with a 25% ratio. The finding must communicate the difference explicitly — and must not speak at a level of certainty the evidence cannot support.

2. **Apply structural screening before escalation.** Some amendments reflect legitimate scope expansion. Some reflect project complexity growth. Some reflect authorized pricing adjustments. A system that flags all amendments equally produces noise. A system that screens structural explanations before escalating produces signal.

3. **Document the reasoning chain at every step.** The finding that survives parliamentary scrutiny, ministerial briefing, and access-to-information requests is the one where every gate evaluation, every evidence source, every escalation decision is recorded and replayable. Not because policy requires it — because accountability requires it.

4. **Know what it is not allowed to say.** The most dangerous output a procurement analytics system can produce is a strong claim built on weak evidence. A system with explicit prohibited content — no fraud accusation without law enforcement determination, no named individual adverse association without corroborated record, no CRITICAL classification without external corroboration — is architecturally safer than a system that relies on analyst discretion to apply those limits.

---

## What the Demo Should Show

The strongest possible demonstration of this challenge is not a ranked list of suspicious contracts.

It is a ranked list of suspicious contracts **with a documented, replayable answer to the question: what is this finding permitted to claim, and why?**

Specifically:

- Three or four Amendment Creep candidates surfaced from the federal contracts data
- Each one evaluated against a structured set of questions in sequence — provenance, identity, claim strength, harm boundary, structural explanation, escalation authority
- Different candidates producing **different governed outcomes** from the same evaluation framework — because the evidence is different, not because the algorithm was tuned differently
- A reasoning chain that can be replayed for any finding — showing exactly which signals were considered, which structural explanations were ruled out, and what specific evidence requirement would allow the finding to escalate further

The demo line that wins the room: **"Detection found forty contracts with amendment ratios above 300%. Governance evaluated the top five and produced three different governed answers with documented reasoning. The system knows what it found, what it is permitted to say about it, and exactly what additional evidence each finding needs before it can escalate."**

---

## Why This Matters Beyond the Hackathon

Every provincial and federal department that receives a procurement analytics finding faces the same downstream problem: they do not know how strong the finding is, whether they are permitted to act on it, or how to document the reasoning if they do.

A system that solves that problem is not a dashboard. It is a governance layer for institutional accountability — applicable to any domain where AI surfaces patterns that humans must act on responsibly.

That is the higher-order problem this challenge is asking us to solve. Detection is the entry point. Governed accountability is the outcome.

---

## Bottom Line

Build the detection layer cleanly and fast. Ranked contracts, amendment ratios, threshold split detection, visual output. That is the foundation.

Then build the layer that answers the question every government official in that room is actually asking: **"Now that we know — what are we allowed to do about it, and how do we document why?"**

That answer is what separates a useful analytical tool from an accountable governance system. And it is the answer no other team in the room will have.
