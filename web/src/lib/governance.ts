import type {
  ContractCandidate,
  GateVerdict,
  GovernedFinding,
} from "@/types/governance";

function gate(gate_id: string, gate_name: string, verdict: GateVerdict["verdict"], rationale: string): GateVerdict {
  return { gate_id, gate_name, verdict, rationale, calibration: verdict === "PASS" ? "C1" : "C2" };
}

export async function governContract(contract: ContractCandidate): Promise<GovernedFinding> {
  const ratio = contract.amendment_ratio;
  const isSoleSource = contract.solicitation_procedure === "Non-competitive";
  const claim_state = ratio >= 1 || (ratio >= 0.25 && isSoleSource) ? "INVESTIGATED" : "FLAGGED";
  const governedAt = new Date().toISOString();

  const gates: GateVerdict[] = [
    gate("AG-01", "Evidence Provenance", contract.reference_number && contract.original_value > 0 ? "PASS" : "FAIL", "Required contract fields were checked."),
    gate("AG-02", "Identity Resolution", contract.bn ? "PASS" : "CAUTION", contract.bn ? "Business number is available." : "Vendor name only; no BN available."),
    gate("AG-03", "Claim Strength (PRIMARY)", claim_state === "INVESTIGATED" ? "CAUTION" : "PASS", "Claim strength is bounded by amendment ratio and solicitation context."),
    gate("AG-04", "Harm Boundary", "HOLD", "No consequential action without external audit confirmation."),
    gate("AG-05", "Temporal Window", contract.contract_date ? "PASS" : "CAUTION", "Contract date checked for temporal context."),
    gate("AG-06", "Program / Policy Coherence", ratio >= 1 ? "CAUTION" : "PASS", "Structural explanation has not been ruled out."),
    gate("AG-07", "Escalation Authority", "PENDING", "Tier 3 boundary active."),
    gate("AG-08", "Audit Completeness", "PASS", "Gate verdicts are documented and replayable."),
    gate("AG-09", "Public Defensibility", "HOLD", "Output is not cleared for public-facing communication."),
  ];

  return {
    reference_number: contract.reference_number,
    vendor_name: contract.vendor_name,
    department: contract.department,
    claim_state,
    stability: "S1",
    evidence: [
      `Contract: ${contract.reference_number}`,
      `Vendor: ${contract.vendor_name}`,
      `Department: ${contract.department}`,
      `Original value: $${contract.original_value.toLocaleString("en-CA")}`,
      `Current value: $${contract.current_value.toLocaleString("en-CA")}`,
      `Amendment ratio: ${(contract.amendment_ratio * 100).toFixed(0)}%`,
    ],
    data_gaps: contract.bn ? [] : ["PC-02: No BN available - data quality condition"],
    pc_rules_applied: [
      "PC-01: Pattern is not verdict",
      "PC-02: Missingness is not guilt",
      "PC-03: Claim strength matches evidence strength",
      "PC-05: Threshold documented",
    ],
    gates,
    headline: `${contract.vendor_name} contract pattern classified as ${claim_state}.`,
    what_we_found: `Contract ${contract.reference_number} shows amendment growth of ${(ratio * 100).toFixed(0)}%.`,
    what_we_did_not_find: "The data does not confirm misconduct or rule out authorized scope expansion.",
    next_step: "Request amendment history and scope change documentation before escalation.",
    bounded_output_card: `Classification: ${claim_state}. Pattern detected; structural explanation not yet ruled out.`,
    flight_recorder: [
      {
        id: "FR-DEMO-001",
        timestamp: governedAt,
        actor: "GateService/Stub",
        stage: "V4 Gate",
        action: "CLASSIFICATION_FINAL",
        object: contract.reference_number,
        rationale: "Stub governance response until Dev 3 lands full implementation.",
        uncertainty: "C2",
        hash: "0xstub",
      },
    ],
    governed_at: governedAt,
  };
}
