# Oil City Hackers — Agency 2026 Specification
# Challenge 4: Sole Source & Amendment Creep
# Code freeze: 2:00 PM EDT | Build window: ~4 hours remaining

---

## What We Are Building

A two-layer accountability system:

**Layer 1 — Detection:** Surface federal contracts where amendment 
value significantly exceeds original award value. Ranked dashboard 
with drill-down per contract.

**Layer 2 — Governance:** For the top findings, apply a structured 
gate sequence that determines what the finding is permitted to claim 
and documents the reasoning chain. Produces governed finding cards 
with explicit evidence requirements before escalation.

---

## Database Connection

PostgreSQL (read-only):
postgresql://database_database_w2a1_user:JvqVh0msmuBrwgING68S52H0sz3wEEXI@dpg-d7auudv5r7bs738iqh70-b.replica-cyan.oregon-postgres.render.com/database_database_w2a1

**CRITICAL — PC-12 Summation Discipline:**
Never use raw SUM of agreement_value from grants_contributions.
Always use fed.vw_agreement_current for federal data.
Raw SUM inflates total by $388B (73%). This is a known data issue.

---

## Core Query — Amendment Creep Detection

```sql
SELECT 
  reference_number,
  vendor_name,
  owner_org_title AS department,
  description_en AS description,
  contract_date,
  CAST(NULLIF(original_value,'') AS DECIMAL(15,2)) AS original_value,
  CAST(NULLIF(amendment_value,'') AS DECIMAL(15,2)) AS amendment_value,
  CAST(NULLIF(contract_value,'') AS DECIMAL(15,2)) AS current_value,
  ROUND(
    (CAST(NULLIF(amendment_value,'') AS DECIMAL(15,2)) 
     / NULLIF(CAST(NULLIF(original_value,'') AS DECIMAL(15,2)),0)
    )::numeric, 3
  ) AS amendment_ratio,
  solicitation_procedure
FROM public.contracts
WHERE original_value ~ '^[0-9]'
  AND amendment_value ~ '^[0-9]'
  AND CAST(NULLIF(original_value,'') AS DECIMAL(15,2)) > 10000
  AND CAST(NULLIF(amendment_value,'') AS DECIMAL(15,2)) 
      > CAST(NULLIF(original_value,'') AS DECIMAL(15,2))
ORDER BY amendment_ratio DESC NULLS LAST
LIMIT 50
```

## Secondary Query — Threshold Split Detection (stretch goal)

```sql
SELECT 
  vendor_name,
  owner_org_title AS department,
  COUNT(*) AS contract_count,
  SUM(CAST(NULLIF(contract_value,'') AS DECIMAL(15,2))) AS total_value,
  MAX(CAST(NULLIF(contract_value,'') AS DECIMAL(15,2))) AS max_single,
  MIN(CAST(NULLIF(contract_value,'') AS DECIMAL(15,2))) AS min_single
FROM public.contracts
WHERE contract_value ~ '^[0-9]'
  AND CAST(NULLIF(contract_value,'') AS DECIMAL(15,2)) 
      BETWEEN 20000 AND 25000
GROUP BY vendor_name, owner_org_title
HAVING COUNT(*) >= 3
ORDER BY contract_count DESC
LIMIT 20
```

---

## Application Structure

### Frontend (Streamlit or TypeScript — team choice)

**View 1 — Dashboard**
- Total contracts scanned
- Count with amendment ratio > 25%
- Count with amendment ratio > 100%
- Count with amendment ratio > 300%
- Top 10 departments by amendment activity

**View 2 — Ranked Contract List**
- Table: vendor, department, original value, 
  amendment value, ratio, solicitation procedure
- Sortable by ratio descending
- Click row → drill down

**View 3 — Contract Drill-Down**
- Full contract detail
- Amendment timeline if available
- Gate evaluation results (from governance layer)
- Governed finding card

**View 4 — Governance Finding Card**
- Gate verdicts AG-01 through AG-06
- Claim validity: FLAGGED / INVESTIGATED
- Evidence requirements for escalation
- PC rule labels
- Reasoning chain (replayable)

---

## Governance Layer — Gate Sequence

Apply these six gates to the top 5 amendment creep candidates.
Gates are sequential. Downstream gate cannot pass if upstream fails.

**AG-01 Evidence Provenance**
- Can we trace the source? Reference number, department, 
  vendor name, original and amendment values all present?
- PASS: all fields populated
- FAIL: missing reference number or original value

**AG-02 Identity Resolution**  
- Is the vendor identity confirmed?
- PASS: vendor name matches golden records OR BN available
- PARTIAL: name only, no BN
- FAIL: no vendor identifier

**AG-03 Claim Strength (PRIMARY)**
- What is the maximum defensible claim?
- Amendment ratio > 25%: FLAGGED (pattern detected)
- Amendment ratio > 100% AND sole-source: INVESTIGATED
- CRITICAL: prohibited at Tier 3 without external audit

**AG-04 Harm Boundary**
- Would this output cause harm if it entered a 
  consequential workflow right now?
- No government confirmation of wrongdoing → HOLD
- Prevents premature escalation

**AG-05 Temporal Window**
- Does the pattern persist across contract lifecycle 
  or is it a single-year artifact?
- Check contract_date range
- Single amendment: PROVISIONAL
- Pattern across multiple periods: CONFIRMED

**AG-06 Program/Policy Coherence**
- Is there a structural explanation?
- solicitation_procedure = 'Competitive' → 
  original competition existed, creep is anomalous
- solicitation_procedure = 'Non-competitive' → 
  already sole-source, amendment is compounding
- Legitimate scope expansion not ruled out → HOLD

---

## Claim Validity Classifications

- **FLAGGED:** Pattern detected. Structural explanation 
  not yet ruled out. No action warranted.
- **INVESTIGATED:** Two corroborated signals. 
  Specific evidence requirements documented. 
  Human review warranted.
- **CLEARED:** Structural explanation confirmed. 
  Legitimate scope expansion or authorized sole-source.
- **CRITICAL:** Prohibited at Tier 3. 
  Requires external audit confirmation.

---

## Prohibited Content Rules (PC Rules)

- **PC-01:** Pattern is not verdict. 
  High amendment ratio ≠ misconduct.
- **PC-03:** Claim strength must not exceed 
  evidence strength. 
- **PC-05:** Every threshold must be documented. 
  Amendment threshold: 25% anchored to 
  PSPC CPN 2022-1.
- **PC-10:** Never use the word "fraud." 
  Requires law enforcement determination.
- **PC-12:** Never use raw SUM of agreement_value. 
  Always use vw_agreement_current.

---

## Demo Flow (5 minutes if selected as finalist)

1. Open dashboard — show scale: 
   "X contracts scanned, Y flagged above 25% threshold"
2. Click top amendment creep contract — 
   show original vs final value
3. Run governance gate sequence live on that contract
4. Show governed finding card: 
   FLAGGED or INVESTIGATED with specific rationale
5. Show second contract with different outcome — 
   different governed answer from same pipeline
6. Close: "Detection found the patterns. 
   Governance determined what we are permitted 
   to say about them."

---

## Key Numbers to Reference

- $388B: amount raw SUM inflates federal grants (F-3)
- 19,303: amendments that doubled original values 
  (Nate Glubish's analysis)
- 25%: amendment threshold anchored to PSPC CPN 2022-1
- ArriveCAN: $54.7M unverifiable — 
  reasoning chain erasure is the failure mode

---

## Division of Labour

- **chuget:** Database queries, analytics layer, 
  contract data normalization
- **Yunus/Adnan:** Frontend dashboard and 
  contract drill-down view
- **method.1/Dave:** AWS infrastructure, 
  Kiro agent coordination
- **Kingtsugi/Regis:** Governance layer, 
  gate evaluation logic, finding cards, 
  specification and demo narrative
- **All:** Integration testing before 1:30 PM

---

## Hard Deadline

**2:00 PM EDT — Code Freeze**
Submit: team name, deployed app link or demo video, 
brief description. Post to #submissions-on-site on Discord.

Target 1:30 PM for first full demo run-through.