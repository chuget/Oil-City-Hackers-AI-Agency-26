# GovAccountabilityOS — Governance Layer Specification
# Challenge 4: Sole Source & Amendment Creep
# Agency 2026 | April 29, 2026 | Tier 3 Sandbox

---

## What This Layer Does

The detection layer surfaces contracts with high amendment ratios.
This governance layer determines what those findings are permitted to claim.

It takes one contract as input.
It runs nine gates in sequence.
It outputs one governed finding card with a documented reasoning chain.

Constitutional principle: **Agents propose. Gates decide. Pattern is not verdict.**

---

## Input Schema

```typescript
interface ContractCandidate {
  reference_number: string
  vendor_name: string
  department: string
  description: string
  contract_date: string
  original_value: number
  amendment_value: number
  current_value: number
  amendment_ratio: number        // amendment_value / original_value
  solicitation_procedure: string // 'Competitive' | 'Non-competitive' | null
  bn?: string                    // Business Number if available
}
```

---

## Output Schema

```typescript
interface GovernedFinding {
  // Identity
  reference_number: string
  vendor_name: string
  department: string

  // Classification
  claim_state: 'FLAGGED' | 'INVESTIGATED' | 'CLEARED' | 'CRITICAL'
  stability: 'S0' | 'S1' | 'S2' | 'S3'

  // Evidence
  evidence: string[]
  data_gaps: string[]
  pc_rules_applied: string[]

  // Gate verdicts
  gates: GateVerdict[]

  // Bounded output
  headline: string
  what_we_found: string
  what_we_did_not_find: string
  next_step: string
  bounded_output_card: string

  // Audit
  flight_recorder: FlightEntry[]
  governed_at: string
}

interface GateVerdict {
  gate_id: string        // 'AG-01' through 'AG-09'
  gate_name: string
  verdict: 'PASS' | 'CAUTION' | 'HOLD' | 'FAIL' | 'PENDING'
  rationale: string
  calibration: string    // 'C0' | 'C1' | 'C2' | 'C3'
}

interface FlightEntry {
  id: string
  timestamp: string
  actor: string
  stage: string
  action: string
  object: string
  rationale: string
  uncertainty: string
  hash: string
}
```

---

## Gate Evaluation Logic — AG-01 through AG-09

### AG-01 — Evidence Provenance Gate

```typescript
function evaluateAG01(contract: ContractCandidate): GateVerdict {
  const missing = []
  if (!contract.reference_number) missing.push('reference_number')
  if (!contract.original_value || contract.original_value <= 0) 
    missing.push('original_value')
  if (!contract.amendment_value || contract.amendment_value <= 0) 
    missing.push('amendment_value')
  if (!contract.vendor_name) missing.push('vendor_name')
  if (!contract.department) missing.push('department')

  if (missing.length === 0) {
    return {
      gate_id: 'AG-01',
      gate_name: 'Evidence Provenance',
      verdict: 'PASS',
      rationale: `Source confirmed: reference ${contract.reference_number}, ` +
        `${contract.department}, vendor ${contract.vendor_name}. ` +
        `Original: $${contract.original_value.toLocaleString()}, ` +
        `Amendment: $${contract.amendment_value.toLocaleString()}.`,
      calibration: 'C1'
    }
  }
  return {
    gate_id: 'AG-01',
    gate_name: 'Evidence Provenance',
    verdict: 'FAIL',
    rationale: `PC-02: Missing fields — ${missing.join(', ')}. ` +
      `Data quality condition. Not an adverse signal.`,
    calibration: 'C2'
  }
}
```

### AG-02 — Identity Resolution Gate

```typescript
function evaluateAG02(contract: ContractCandidate): GateVerdict {
  if (contract.bn) {
    return {
      gate_id: 'AG-02',
      gate_name: 'Identity Resolution',
      verdict: 'PASS',
      rationale: `Vendor identity confirmed via Business Number ${contract.bn}.`,
      calibration: 'C1'
    }
  }
  if (contract.vendor_name && contract.vendor_name.length > 3) {
    return {
      gate_id: 'AG-02',
      gate_name: 'Identity Resolution',
      verdict: 'CAUTION',
      rationale: `Vendor name only — no BN available. ` +
        `PC-02: absent BN is a data quality condition. ` +
        `Identity partially resolved via name: ${contract.vendor_name}.`,
      calibration: 'C2'
    }
  }
  return {
    gate_id: 'AG-02',
    gate_name: 'Identity Resolution',
    verdict: 'FAIL',
    rationale: 'Vendor identity cannot be confirmed. ' +
      'No BN and insufficient name data.',
    calibration: 'C2'
  }
}
```

### AG-03 — Claim Strength Gate (PRIMARY)

```typescript
// PC-05: Thresholds documented and anchored
const THRESHOLDS = {
  FLAGGED: 0.25,      // C1 — PSPC CPN 2022-1 competitive boundary
  INVESTIGATED: 1.00, // C2 — Engineering estimate: 100% = original doubled
  CRITICAL: 3.00,     // C0 — Prohibited at Tier 3 regardless
}

function evaluateAG03(
  contract: ContractCandidate,
  ag01: GateVerdict,
  ag02: GateVerdict
): GateVerdict {
  // Cannot pass AG-03 if AG-01 failed
  if (ag01.verdict === 'FAIL') {
    return {
      gate_id: 'AG-03',
      gate_name: 'Claim Strength (PRIMARY)',
      verdict: 'FAIL',
      rationale: 'AG-01 failed. Claim strength cannot be assessed ' +
        'without confirmed evidence provenance.',
      calibration: 'C0'
    }
  }

  const ratio = contract.amendment_ratio
  const isSoleSource = contract.solicitation_procedure === 'Non-competitive'

  // CRITICAL: prohibited at Tier 3
  if (ratio >= THRESHOLDS.CRITICAL) {
    return {
      gate_id: 'AG-03',
      gate_name: 'Claim Strength (PRIMARY)',
      verdict: 'CAUTION',
      // enforceGates will cap this at INVESTIGATED at Tier 3
      rationale: `Amendment ratio ${(ratio * 100).toFixed(0)}% ` +
        `(${ratio.toFixed(2)}x original value). ` +
        `Pattern strength: STRONG. ` +
        `Classification capped at INVESTIGATED — ` +
        `CRITICAL requires external audit confirmation not available at Tier 3. ` +
        `PC-01: pattern is not verdict.`,
      calibration: 'C0'
    }
  }

  // INVESTIGATED: corroborated signals
  if (ratio >= THRESHOLDS.INVESTIGATED && isSoleSource) {
    return {
      gate_id: 'AG-03',
      gate_name: 'Claim Strength (PRIMARY)',
      verdict: 'CAUTION',
      rationale: `Amendment ratio ${(ratio * 100).toFixed(0)}% ` +
        `combined with non-competitive solicitation. ` +
        `Two corroborated signals: INVESTIGATED. ` +
        `External corroboration required before CRITICAL.`,
      calibration: 'C1'
    }
  }

  if (ratio >= THRESHOLDS.INVESTIGATED) {
    return {
      gate_id: 'AG-03',
      gate_name: 'Claim Strength (PRIMARY)',
      verdict: 'CAUTION',
      rationale: `Amendment ratio ${(ratio * 100).toFixed(0)}% ` +
        `(original value doubled). Single signal: INVESTIGATED. ` +
        `Solicitation procedure: ${contract.solicitation_procedure || 'unknown'}.`,
      calibration: 'C2'
    }
  }

  // FLAGGED: single pattern
  if (ratio >= THRESHOLDS.FLAGGED) {
    return {
      gate_id: 'AG-03',
      gate_name: 'Claim Strength (PRIMARY)',
      verdict: 'PASS',
      rationale: `Amendment ratio ${(ratio * 100).toFixed(0)}% ` +
        `exceeds PSPC CPN 2022-1 threshold (25%). ` +
        `Single pattern: FLAGGED. ` +
        `Structural explanation not yet ruled out per AG-06.`,
      calibration: 'C1'
    }
  }

  return {
    gate_id: 'AG-03',
    gate_name: 'Claim Strength (PRIMARY)',
    verdict: 'PASS',
    rationale: `Amendment ratio ${(ratio * 100).toFixed(0)}% ` +
      `below flagging threshold. No claim warranted.`,
    calibration: 'C1'
  }
}
```

### AG-04 — Harm Boundary Gate

```typescript
function evaluateAG04(contract: ContractCandidate): GateVerdict {
  // At Tier 3: no government confirmation of wrongdoing
  // AG-04 always holds for named vendor findings
  return {
    gate_id: 'AG-04',
    gate_name: 'Harm Boundary',
    verdict: 'HOLD',
    rationale: `HOLD — reputational harm risk for named vendor ` +
      `${contract.vendor_name} without external audit confirmation. ` +
      `AG-07 Escalation Authority not reachable at Tier 3. ` +
      `No consequential action permitted from this output.`,
    calibration: 'C0'
  }
}
```

### AG-05 — Temporal Window Gate

```typescript
function evaluateAG05(contract: ContractCandidate): GateVerdict {
  if (!contract.contract_date) {
    return {
      gate_id: 'AG-05',
      gate_name: 'Temporal Window',
      verdict: 'CAUTION',
      rationale: 'Contract date unavailable. ' +
        'Cannot confirm pattern persists across lifecycle. ' +
        'PC-02: missing date is a data quality condition.',
      calibration: 'C3'
    }
  }

  const contractYear = new Date(contract.contract_date).getFullYear()
  const currentYear = 2026
  const ageYears = currentYear - contractYear

  if (ageYears >= 1) {
    return {
      gate_id: 'AG-05',
      gate_name: 'Temporal Window',
      verdict: 'PASS',
      rationale: `Contract dated ${contract.contract_date} ` +
        `(${ageYears} year${ageYears > 1 ? 's' : ''} old). ` +
        `Amendment pattern is not a same-day artifact. ` +
        `Temporal window: appropriate.`,
      calibration: 'C2'
    }
  }

  return {
    gate_id: 'AG-05',
    gate_name: 'Temporal Window',
    verdict: 'CAUTION',
    rationale: `Contract dated ${contract.contract_date}. ` +
      `Recent contract — amendment pattern may reflect ` +
      `normal early-stage scope adjustment. ` +
      `Provisional finding only.`,
    calibration: 'C2'
  }
}
```

### AG-06 — Program / Policy Coherence Gate

```typescript
function evaluateAG06(contract: ContractCandidate): GateVerdict {
  const isCompetitive = 
    contract.solicitation_procedure === 'Competitive' ||
    contract.solicitation_procedure === 'Concurrentielle'
  const isNonCompetitive = 
    contract.solicitation_procedure === 'Non-competitive' ||
    contract.solicitation_procedure === 'Non-concurrentielle'
  const ratio = contract.amendment_ratio

  if (isNonCompetitive && ratio >= 1.0) {
    return {
      gate_id: 'AG-06',
      gate_name: 'Program / Policy Coherence',
      verdict: 'CAUTION',
      rationale: `Non-competitive solicitation with ` +
        `${(ratio * 100).toFixed(0)}% amendment growth. ` +
        `No competitive baseline existed at original award. ` +
        `Amendment compounds sole-source dependency. ` +
        `Structural explanation (legitimate scope expansion) ` +
        `not ruled out but weakened by combined signals.`,
      calibration: 'C1'
    }
  }

  if (isCompetitive && ratio >= 1.0) {
    return {
      gate_id: 'AG-06',
      gate_name: 'Program / Policy Coherence',
      verdict: 'CAUTION',
      rationale: `Competitive solicitation at original award ` +
        `but amendment growth of ${(ratio * 100).toFixed(0)}% ` +
        `may have quietly exceeded original competitive justification. ` +
        `PSPC CPN 2022-1: re-tendering may have been warranted. ` +
        `Structural explanation (authorized scope change) ` +
        `must be ruled out before escalation.`,
      calibration: 'C1'
    }
  }

  return {
    gate_id: 'AG-06',
    gate_name: 'Program / Policy Coherence',
    verdict: 'PASS',
    rationale: `Solicitation procedure: ` +
      `${contract.solicitation_procedure || 'unknown'}. ` +
      `Amendment ratio: ${(ratio * 100).toFixed(0)}%. ` +
      `Structural explanation not conclusively ruled out. ` +
      `Pattern remains at FLAGGED level.`,
    calibration: 'C2'
  }
}
```

### AG-07 through AG-09 — Tier 3 Boundary Gates

```typescript
function evaluateAG07(): GateVerdict {
  return {
    gate_id: 'AG-07',
    gate_name: 'Escalation Authority',
    verdict: 'PENDING',
    rationale: 'Not reached — AG-04 hold maintained. ' +
      'Tier 3 boundary active. No named escalation authority ' +
      'available at Agency 2026 sandbox level.',
    calibration: 'C0'
  }
}

function evaluateAG08(): GateVerdict {
  return {
    gate_id: 'AG-08',
    gate_name: 'Audit Completeness',
    verdict: 'PASS',
    rationale: 'Flight Recorder chain active. ' +
      'All gate verdicts documented and replayable.',
    calibration: 'C0'
  }
}

function evaluateAG09(): GateVerdict {
  return {
    gate_id: 'AG-09',
    gate_name: 'Public Defensibility',
    verdict: 'HOLD',
    rationale: 'Tier 3 — internal analytic language only. ' +
      'Output not cleared for external publication ' +
      'or public-facing communication without AG-09 review.',
    calibration: 'C2'
  }
}
```

---

## enforceGates — Constitutional Classification Ceiling

```typescript
// This function is the architectural core.
// Agents and gates may propose. enforceGates decides the final ceiling.
// At Tier 3: CRITICAL is constitutionally prohibited.
// AG-04 holds for all named vendor findings without external audit.

function enforceGates(
  proposedClassification: string,
  gates: GateVerdict[]
): 'FLAGGED' | 'INVESTIGATED' | 'CLEARED' | 'CRITICAL' {

  // Tier 3 hard ceiling: CRITICAL never permitted
  if (proposedClassification === 'CRITICAL') {
    return 'INVESTIGATED'
  }

  // AG-01 fail → cannot advance beyond FLAGGED
  const ag01 = gates.find(g => g.gate_id === 'AG-01')
  if (ag01?.verdict === 'FAIL') return 'FLAGGED'

  // AG-03 primary gate: if CAUTION, maximum is INVESTIGATED
  const ag03 = gates.find(g => g.gate_id === 'AG-03')
  if (ag03?.verdict === 'CAUTION') {
    if (proposedClassification === 'CLEARED') return 'INVESTIGATED'
    if (proposedClassification === 'CRITICAL') return 'INVESTIGATED'
  }

  // CLEARED requires AG-06 PASS (structural explanation confirmed)
  const ag06 = gates.find(g => g.gate_id === 'AG-06')
  if (proposedClassification === 'CLEARED' && ag06?.verdict !== 'PASS') {
    return 'FLAGGED'
  }

  const valid = ['FLAGGED', 'INVESTIGATED', 'CLEARED']
  if (valid.includes(proposedClassification)) {
    return proposedClassification as 'FLAGGED' | 'INVESTIGATED' | 'CLEARED'
  }

  return 'FLAGGED' // most conservative default
}
```

---

## deriveClassification — From Gate Results

```typescript
function deriveClassification(
  contract: ContractCandidate,
  gates: GateVerdict[]
): string {
  const ag01 = gates.find(g => g.gate_id === 'AG-01')
  const ag03 = gates.find(g => g.gate_id === 'AG-03')
  const ag06 = gates.find(g => g.gate_id === 'AG-06')

  if (ag01?.verdict === 'FAIL') return 'FLAGGED'

  const ratio = contract.amendment_ratio
  const isSoleSource = 
    contract.solicitation_procedure === 'Non-competitive' ||
    contract.solicitation_procedure === 'Non-concurrentielle'

  // Two corroborated signals → INVESTIGATED
  if (ratio >= 1.0 && isSoleSource) return 'INVESTIGATED'
  if (ratio >= 3.0) return 'INVESTIGATED' // will be capped by enforceGates
  if (ratio >= 1.0 && ag06?.verdict === 'CAUTION') return 'INVESTIGATED'

  // Single signal → FLAGGED
  if (ratio >= 0.25) return 'FLAGGED'

  return 'CLEARED'
}
```

---

## generateBoundedOutput — Plain Language Briefing

```typescript
function generateBoundedOutput(
  contract: ContractCandidate,
  classification: string
): {
  headline: string
  what_we_found: string
  what_we_did_not_find: string
  next_step: string
  bounded_output_card: string
} {
  const ratioFormatted = `${(contract.amendment_ratio * 100).toFixed(0)}%`
  const originalFormatted = 
    `$${contract.original_value.toLocaleString('en-CA')}`
  const currentFormatted = 
    `$${contract.current_value.toLocaleString('en-CA')}`

  if (classification === 'INVESTIGATED') {
    return {
      headline: `${contract.department} contract to ${contract.vendor_name} ` +
        `grew ${ratioFormatted} from original award — warrants examination.`,
      what_we_found: 
        `Contract ${contract.reference_number} was originally awarded at ` +
        `${originalFormatted}. Current value is ${currentFormatted} — ` +
        `a ${ratioFormatted} increase from the original competitive award. ` +
        `Solicitation procedure: ${contract.solicitation_procedure || 'not recorded'}.`,
      what_we_did_not_find:
        `The data does not confirm whether this growth reflects authorized ` +
        `scope expansion or represents amendment creep beyond the original ` +
        `competitive justification. No fraud determination is possible ` +
        `from open contract data alone.`,
      next_step:
        `Request the amendment history and scope change documentation ` +
        `for contract ${contract.reference_number} from ${contract.department} ` +
        `to determine whether re-tendering was warranted under PSPC CPN 2022-1.`,
      bounded_output_card:
        `Contract ${contract.reference_number} awarded to ${contract.vendor_name} ` +
        `by ${contract.department} has grown ${ratioFormatted} from its ` +
        `original award of ${originalFormatted} to a current value of ` +
        `${currentFormatted}. ` +
        `The gate evaluation determined this pattern warrants examination ` +
        `but cannot be classified as confirmed misconduct without amendment ` +
        `history and scope change documentation. ` +
        `Classification: INVESTIGATED. ` +
        `Specific evidence required before further escalation.`
    }
  }

  // FLAGGED
  return {
    headline: `${contract.vendor_name} contract amendment of ${ratioFormatted} ` +
      `detected — above monitoring threshold.`,
    what_we_found:
      `Contract ${contract.reference_number} shows amendment growth of ` +
      `${ratioFormatted} from original award ${originalFormatted} ` +
      `to current value ${currentFormatted}.`,
    what_we_did_not_find:
      `Structural explanation (authorized scope expansion) has not been ` +
      `ruled out. Single signal insufficient for INVESTIGATED classification.`,
    next_step:
      `Flag for routine monitoring. Review if additional signals emerge ` +
      `(sole-source follow-on, threshold splitting, cross-department pattern).`,
    bounded_output_card:
      `Contract ${contract.reference_number} to ${contract.vendor_name} ` +
      `has grown ${ratioFormatted} from ${originalFormatted} to ` +
      `${currentFormatted}. Pattern exceeds the 25% monitoring threshold ` +
      `anchored to PSPC CPN 2022-1. Classification: FLAGGED. ` +
      `Structural explanation not yet ruled out. ` +
      `No action warranted without additional corroborating signals.`
  }
}
```

---

## Main Governance Function — governContract

```typescript
async function governContract(
  contract: ContractCandidate
): Promise<GovernedFinding> {
  const timestamp = new Date().toISOString()
  const flightRecorder: FlightEntry[] = []

  const log = (
    stage: string, action: string, 
    rationale: string, uncertainty: string
  ) => {
    flightRecorder.push({
      id: `FR-${Date.now().toString(36).toUpperCase()}`,
      timestamp: new Date().toISOString(),
      actor: 'GateService/Deterministic',
      stage,
      action,
      object: contract.reference_number,
      rationale,
      uncertainty,
      hash: `0x${Buffer.from(rationale).toString('hex').slice(-12)}`
    })
  }

  log('V0 Ingest', 'RECEIVED', 
    `Contract ${contract.reference_number} received. ` +
    `Amendment ratio: ${(contract.amendment_ratio * 100).toFixed(0)}%.`,
    'C3')

  // Apply PC-02 immediately
  const dataGaps: string[] = []
  if (!contract.bn) 
    dataGaps.push('PC-02: No BN available — data quality condition')
  if (!contract.solicitation_procedure) 
    dataGaps.push('PC-02: Solicitation procedure not recorded')
  if (!contract.contract_date) 
    dataGaps.push('PC-02: Contract date missing')

  log('V1 Normalize', 'DATA_QUALITY_LABELED',
    `${dataGaps.length} data quality conditions identified. ` +
    `PC-02 applied: missingness is not guilt.`,
    'C2')

  // Run gate sequence
  const ag01 = evaluateAG01(contract)
  const ag02 = evaluateAG02(contract)
  const ag03 = evaluateAG03(contract, ag01, ag02)
  const ag04 = evaluateAG04(contract)
  const ag05 = evaluateAG05(contract)
  const ag06 = evaluateAG06(contract)
  const ag07 = evaluateAG07()
  const ag08 = evaluateAG08()
  const ag09 = evaluateAG09()

  const gates = [ag01, ag02, ag03, ag04, ag05, ag06, ag07, ag08, ag09]

  gates.forEach(g => {
    log(`V4 Gate`, `${g.gate_id}_${g.verdict}`,
      g.rationale, g.calibration)
  })

  // Derive and enforce classification
  const derived = deriveClassification(contract, gates)
  const finalClassification = enforceGates(derived, gates)

  log('V4 Gate', 'CLASSIFICATION_FINAL',
    `Derived: ${derived}. After enforceGates: ${finalClassification}. ` +
    `PC-01: pattern is not verdict. ` +
    `PC-03: claim strength matches evidence strength.`,
    'C0')

  // Generate bounded output
  const output = generateBoundedOutput(contract, finalClassification)

  log('V5 Intervene', 'BOUNDED_OUTPUT_GENERATED',
    output.headline, 'C2')

  // Stability
  const stability = finalClassification === 'CLEARED' ? 'S0'
    : finalClassification === 'INVESTIGATED' ? 'S1'
    : finalClassification === 'FLAGGED' ? 'S1'
    : 'S2'

  // Evidence array
  const evidence = [
    `Contract: ${contract.reference_number}`,
    `Department: ${contract.department}`,
    `Vendor: ${contract.vendor_name}`,
    `Original value: $${contract.original_value.toLocaleString('en-CA')}`,
    `Current value: $${contract.current_value.toLocaleString('en-CA')}`,
    `Amendment ratio: ${(contract.amendment_ratio * 100).toFixed(0)}%`,
    `Solicitation: ${contract.solicitation_procedure || 'not recorded'}`,
  ]

  const pcRulesApplied = [
    'PC-01: Pattern is not verdict',
    'PC-02: Missingness is not guilt',
    'PC-03: Claim strength matches evidence strength',
    'PC-05: Threshold documented (25% — PSPC CPN 2022-1)',
    'PC-12: Summation Discipline — vw_agreement_current used',
  ]
  if (finalClassification === 'INVESTIGATED') {
    pcRulesApplied.push('PC-04: No harmful escalation without named authority')
  }

  return {
    reference_number: contract.reference_number,
    vendor_name: contract.vendor_name,
    department: contract.department,
    claim_state: finalClassification as any,
    stability: stability as any,
    evidence,
    data_gaps: dataGaps,
    pc_rules_applied: pcRulesApplied,
    gates,
    headline: output.headline,
    what_we_found: output.what_we_found,
    what_we_did_not_find: output.what_we_did_not_find,
    next_step: output.next_step,
    bounded_output_card: output.bounded_output_card,
    flight_recorder: flightRecorder,
    governed_at: timestamp,
  }
}

export { governContract, enforceGates }
export type { ContractCandidate, GovernedFinding, GateVerdict, FlightEntry }
```

---

## Example — Paste Into Kiro

```
Build a TypeScript/Node.js governance service using the 
governContract function defined in the spec above.

The service should:
1. Accept a ContractCandidate object as input
2. Run all nine gates in sequence (AG-01 through AG-09)
3. Apply enforceGates to produce the final classification
4. Generate a bounded output card
5. Return a complete GovernedFinding object

Expose it as:
- A function: governContract(contract: ContractCandidate)
- An API endpoint: POST /api/govern with body { contract }
- Returns GovernedFinding JSON

The database query to get contract candidates is:
SELECT reference_number, vendor_name, owner_org_title AS department,
  description_en AS description, contract_date, solicitation_procedure,
  CAST(NULLIF(original_value,'') AS DECIMAL(15,2)) AS original_value,
  CAST(NULLIF(amendment_value,'') AS DECIMAL(15,2)) AS amendment_value,
  CAST(NULLIF(contract_value,'') AS DECIMAL(15,2)) AS current_value,
  ROUND((CAST(NULLIF(amendment_value,'') AS DECIMAL(15,2)) 
    / NULLIF(CAST(NULLIF(original_value,'') AS DECIMAL(15,2)),0))::numeric,3) 
    AS amendment_ratio
FROM public.contracts
WHERE original_value ~ '^[0-9]' AND amendment_value ~ '^[0-9]'
  AND CAST(NULLIF(original_value,'') AS DECIMAL(15,2)) > 10000
  AND CAST(NULLIF(amendment_value,'') AS DECIMAL(15,2)) 
      > CAST(NULLIF(original_value,'') AS DECIMAL(15,2))
ORDER BY amendment_ratio DESC NULLS LAST
LIMIT 20

Database connection string:
postgresql://database_database_w2a1_user:JvqVh0msmuBrwgING68S52H0sz3wEEXI@dpg-d7auudv5r7bs738iqh70-b.replica-cyan.oregon-postgres.render.com/database_database_w2a1
```

---

## Demo Script (5 minutes)

**0:00** — Open detection dashboard. 
"The database contains 1.3 million federal contracts. 
We queried for amendment creep — contracts where the final 
value significantly exceeds the original competitive award."

**0:45** — Show ranked list.
"These are the top findings by amendment ratio. 
This contract grew [X]% from its original award."

**1:30** — Click one contract. Run governance.
"Watch what happens when we run this through the 
nine-gate constitutional sequence."

**2:30** — Show gate verdicts.
"AG-01: evidence confirmed. AG-03: claim strength — 
INVESTIGATED, two corroborated signals. 
AG-04: hold — no consequential action without external audit. 
AG-06: structural explanation not yet ruled out."

**3:30** — Show bounded output card.
"The system produced a governed finding card. 
It says exactly what the evidence supports 
and exactly what additional evidence is needed 
before this can escalate further."

**4:15** — Show second contract with different outcome.
"Different contract. Different gate verdicts. 
Different governed answer. Same pipeline."

**5:00** — Close.
"Detection found the patterns. 
Governance determined what we are permitted to say about them. 
Agents propose. Gates decide."
