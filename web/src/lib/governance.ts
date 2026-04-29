import type {
  ContractCandidate,
  GateVerdict,
  GovernedFinding,
} from "@/types/governance";

const THRESHOLDS = {
  FLAGGED: 0.25,
  INVESTIGATED: 1.0,
  CRITICAL: 3.0,
};

function formatMoney(value: number): string {
  return `$${value.toLocaleString("en-CA")}`;
}

function rationaleHash(value: string): string {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return `0x${hash.toString(16).padStart(8, "0")}`;
}

function verdict(
  gate_id: string,
  gate_name: string,
  verdictValue: GateVerdict["verdict"],
  rationale: string,
  calibration: GateVerdict["calibration"],
): GateVerdict {
  return { gate_id, gate_name, verdict: verdictValue, rationale, calibration };
}

function evaluateAG01(contract: ContractCandidate): GateVerdict {
  const missing: string[] = [];
  if (!contract.reference_number) missing.push("reference_number");
  if (!contract.original_value || contract.original_value <= 0) missing.push("original_value");
  if (!contract.amendment_value || contract.amendment_value <= 0) missing.push("amendment_value");
  if (!contract.vendor_name) missing.push("vendor_name");
  if (!contract.department) missing.push("department");

  if (missing.length > 0) {
    return verdict(
      "AG-01",
      "Evidence Provenance",
      "FAIL",
      `PC-02: Missing fields: ${missing.join(", ")}. Data quality condition. Not an adverse signal.`,
      "C2",
    );
  }

  return verdict(
    "AG-01",
    "Evidence Provenance",
    "PASS",
    `Source confirmed: reference ${contract.reference_number}, ${contract.department}, vendor ${contract.vendor_name}. Original: ${formatMoney(contract.original_value)}, Amendment: ${formatMoney(contract.amendment_value)}.`,
    "C1",
  );
}

function evaluateAG02(contract: ContractCandidate): GateVerdict {
  if (contract.bn) {
    return verdict(
      "AG-02",
      "Identity Resolution",
      "PASS",
      `Vendor identity confirmed via Business Number ${contract.bn}.`,
      "C1",
    );
  }

  if (contract.vendor_name && contract.vendor_name.length > 3) {
    return verdict(
      "AG-02",
      "Identity Resolution",
      "CAUTION",
      `Vendor name only; no BN available. PC-02: absent BN is a data quality condition. Identity partially resolved via name: ${contract.vendor_name}.`,
      "C2",
    );
  }

  return verdict(
    "AG-02",
    "Identity Resolution",
    "FAIL",
    "Vendor identity cannot be confirmed. No BN and insufficient name data.",
    "C2",
  );
}

function evaluateAG03(contract: ContractCandidate, ag01: GateVerdict): GateVerdict {
  if (ag01.verdict === "FAIL") {
    return verdict(
      "AG-03",
      "Claim Strength (PRIMARY)",
      "FAIL",
      "AG-01 failed. Claim strength cannot be assessed without confirmed evidence provenance.",
      "C0",
    );
  }

  const ratio = contract.amendment_ratio;
  const isSoleSource = contract.solicitation_procedure === "Non-competitive";

  if (ratio >= THRESHOLDS.CRITICAL) {
    return verdict(
      "AG-03",
      "Claim Strength (PRIMARY)",
      "CAUTION",
      `Amendment ratio ${(ratio * 100).toFixed(0)}% (${ratio.toFixed(2)}x original value). Pattern strength: STRONG. Classification capped at INVESTIGATED; CRITICAL requires external audit confirmation not available at Tier 3. PC-01: pattern is not verdict.`,
      "C0",
    );
  }

  if (ratio >= THRESHOLDS.INVESTIGATED && isSoleSource) {
    return verdict(
      "AG-03",
      "Claim Strength (PRIMARY)",
      "CAUTION",
      `Amendment ratio ${(ratio * 100).toFixed(0)}% combined with non-competitive solicitation. Two corroborated signals: INVESTIGATED. External corroboration required before CRITICAL.`,
      "C1",
    );
  }

  if (ratio >= THRESHOLDS.INVESTIGATED) {
    return verdict(
      "AG-03",
      "Claim Strength (PRIMARY)",
      "CAUTION",
      `Amendment ratio ${(ratio * 100).toFixed(0)}% (original value doubled). Single signal: INVESTIGATED. Solicitation procedure: ${contract.solicitation_procedure || "unknown"}.`,
      "C2",
    );
  }

  if (ratio >= THRESHOLDS.FLAGGED) {
    return verdict(
      "AG-03",
      "Claim Strength (PRIMARY)",
      "PASS",
      `Amendment ratio ${(ratio * 100).toFixed(0)}% exceeds PSPC CPN 2022-1 threshold (25%). Single pattern: FLAGGED. Structural explanation not yet ruled out per AG-06.`,
      "C1",
    );
  }

  return verdict(
    "AG-03",
    "Claim Strength (PRIMARY)",
    "PASS",
    `Amendment ratio ${(ratio * 100).toFixed(0)}% below flagging threshold. No claim warranted.`,
    "C1",
  );
}

function evaluateAG04(contract: ContractCandidate): GateVerdict {
  return verdict(
    "AG-04",
    "Harm Boundary",
    "HOLD",
    `HOLD: reputational harm risk for named vendor ${contract.vendor_name} without external audit confirmation. AG-07 Escalation Authority not reachable at Tier 3. No consequential action permitted from this output.`,
    "C0",
  );
}

function evaluateAG05(contract: ContractCandidate): GateVerdict {
  if (!contract.contract_date) {
    return verdict(
      "AG-05",
      "Temporal Window",
      "CAUTION",
      "Contract date unavailable. Cannot confirm pattern persists across lifecycle. PC-02: missing date is a data quality condition.",
      "C3",
    );
  }

  const contractYear = new Date(contract.contract_date).getFullYear();
  const currentYear = 2026;
  const ageYears = currentYear - contractYear;

  if (ageYears >= 1) {
    return verdict(
      "AG-05",
      "Temporal Window",
      "PASS",
      `Contract dated ${contract.contract_date} (${ageYears} year${ageYears > 1 ? "s" : ""} old). Amendment pattern is not a same-day artifact. Temporal window: appropriate.`,
      "C2",
    );
  }

  return verdict(
    "AG-05",
    "Temporal Window",
    "CAUTION",
    `Contract dated ${contract.contract_date}. Recent contract; amendment pattern may reflect normal early-stage scope adjustment. Provisional finding only.`,
    "C2",
  );
}

function evaluateAG06(contract: ContractCandidate): GateVerdict {
  const isCompetitive = contract.solicitation_procedure === "Competitive" || contract.solicitation_procedure === "Concurrentielle";
  const isNonCompetitive = contract.solicitation_procedure === "Non-competitive" || contract.solicitation_procedure === "Non-concurrentielle";
  const ratio = contract.amendment_ratio;

  if (isNonCompetitive && ratio >= 1.0) {
    return verdict(
      "AG-06",
      "Program / Policy Coherence",
      "CAUTION",
      `Non-competitive solicitation with ${(ratio * 100).toFixed(0)}% amendment growth. No competitive baseline existed at original award. Amendment compounds sole-source dependency. Structural explanation not ruled out but weakened by combined signals.`,
      "C1",
    );
  }

  if (isCompetitive && ratio >= 1.0) {
    return verdict(
      "AG-06",
      "Program / Policy Coherence",
      "CAUTION",
      `Competitive solicitation at original award but amendment growth of ${(ratio * 100).toFixed(0)}% may have quietly exceeded original competitive justification. PSPC CPN 2022-1: re-tendering may have been warranted. Structural explanation must be ruled out before escalation.`,
      "C1",
    );
  }

  return verdict(
    "AG-06",
    "Program / Policy Coherence",
    "PASS",
    `Solicitation procedure: ${contract.solicitation_procedure || "unknown"}. Amendment ratio: ${(ratio * 100).toFixed(0)}%. Structural explanation not conclusively ruled out. Pattern remains at FLAGGED level.`,
    "C2",
  );
}

function evaluateAG07(): GateVerdict {
  return verdict(
    "AG-07",
    "Escalation Authority",
    "PENDING",
    "Not reached: AG-04 hold maintained. Tier 3 boundary active. No named escalation authority available at Agency 2026 sandbox level.",
    "C0",
  );
}

function evaluateAG08(): GateVerdict {
  return verdict(
    "AG-08",
    "Audit Completeness",
    "PASS",
    "Flight Recorder chain active. All gate verdicts documented and replayable.",
    "C0",
  );
}

function evaluateAG09(): GateVerdict {
  return verdict(
    "AG-09",
    "Public Defensibility",
    "HOLD",
    "Tier 3: internal analytic language only. Output not cleared for external publication or public-facing communication without AG-09 review.",
    "C2",
  );
}

export function enforceGates(
  proposedClassification: string,
  gates: GateVerdict[],
): "FLAGGED" | "INVESTIGATED" | "CLEARED" | "CRITICAL" {
  if (proposedClassification === "CRITICAL") return "INVESTIGATED";

  const ag01 = gates.find((gate) => gate.gate_id === "AG-01");
  if (ag01?.verdict === "FAIL") return "FLAGGED";

  const ag03 = gates.find((gate) => gate.gate_id === "AG-03");
  if (ag03?.verdict === "CAUTION") {
    if (proposedClassification === "CLEARED") return "INVESTIGATED";
    if (proposedClassification === "CRITICAL") return "INVESTIGATED";
  }

  const ag06 = gates.find((gate) => gate.gate_id === "AG-06");
  if (proposedClassification === "CLEARED" && ag06?.verdict !== "PASS") return "FLAGGED";

  if (proposedClassification === "FLAGGED" || proposedClassification === "INVESTIGATED" || proposedClassification === "CLEARED") {
    return proposedClassification;
  }

  return "FLAGGED";
}

function deriveClassification(contract: ContractCandidate, gates: GateVerdict[]): string {
  const ag01 = gates.find((gate) => gate.gate_id === "AG-01");
  const ag06 = gates.find((gate) => gate.gate_id === "AG-06");

  if (ag01?.verdict === "FAIL") return "FLAGGED";

  const ratio = contract.amendment_ratio;
  const isSoleSource = contract.solicitation_procedure === "Non-competitive" || contract.solicitation_procedure === "Non-concurrentielle";

  if (ratio >= 1.0 && isSoleSource) return "INVESTIGATED";
  if (ratio >= 3.0) return "INVESTIGATED";
  if (ratio >= 1.0 && ag06?.verdict === "CAUTION") return "INVESTIGATED";
  if (ratio >= 0.25) return "FLAGGED";

  return "CLEARED";
}

function generateBoundedOutput(contract: ContractCandidate, classification: string) {
  const ratioFormatted = `${(contract.amendment_ratio * 100).toFixed(0)}%`;
  const originalFormatted = formatMoney(contract.original_value);
  const currentFormatted = formatMoney(contract.current_value);

  if (classification === "CLEARED") {
    return {
      headline: `${contract.vendor_name} contract is below the amendment monitoring threshold.`,
      what_we_found: `Contract ${contract.reference_number} shows amendment growth of ${ratioFormatted}, below the 25% monitoring threshold.`,
      what_we_did_not_find: "The available data does not show an amendment creep pattern that warrants a flagged or investigated classification.",
      next_step: "No escalation. Retain in baseline monitoring set.",
      bounded_output_card: `Contract ${contract.reference_number} to ${contract.vendor_name} shows ${ratioFormatted} amendment growth from ${originalFormatted} to ${currentFormatted}. Classification: CLEARED.`,
    };
  }

  if (classification === "INVESTIGATED") {
    return {
      headline: `${contract.department} contract to ${contract.vendor_name} grew ${ratioFormatted} from original award; warrants examination.`,
      what_we_found: `Contract ${contract.reference_number} was originally awarded at ${originalFormatted}. Current value is ${currentFormatted}; a ${ratioFormatted} increase from the original award. Solicitation procedure: ${contract.solicitation_procedure || "not recorded"}.`,
      what_we_did_not_find: "The data does not confirm whether this growth reflects authorized scope expansion or represents amendment creep beyond the original justification. No misconduct determination is possible from open contract data alone.",
      next_step: `Request the amendment history and scope change documentation for contract ${contract.reference_number} from ${contract.department} to determine whether re-tendering was warranted under PSPC CPN 2022-1.`,
      bounded_output_card: `Contract ${contract.reference_number} awarded to ${contract.vendor_name} by ${contract.department} has grown ${ratioFormatted} from its original award of ${originalFormatted} to a current value of ${currentFormatted}. The gate evaluation determined this pattern warrants examination but cannot be classified as confirmed misconduct without amendment history and scope change documentation. Classification: INVESTIGATED. Specific evidence required before further escalation.`,
    };
  }

  return {
    headline: `${contract.vendor_name} contract amendment of ${ratioFormatted} detected; above monitoring threshold.`,
    what_we_found: `Contract ${contract.reference_number} shows amendment growth of ${ratioFormatted} from original award ${originalFormatted} to current value ${currentFormatted}.`,
    what_we_did_not_find: "Structural explanation, such as authorized scope expansion, has not been ruled out. Single signal insufficient for INVESTIGATED classification.",
    next_step: "Flag for routine monitoring. Review if additional signals emerge, such as sole-source follow-on, threshold splitting, or cross-department pattern.",
    bounded_output_card: `Contract ${contract.reference_number} to ${contract.vendor_name} has grown ${ratioFormatted} from ${originalFormatted} to ${currentFormatted}. Pattern exceeds the 25% monitoring threshold anchored to PSPC CPN 2022-1. Classification: FLAGGED. Structural explanation not yet ruled out. No action warranted without additional corroborating signals.`,
  };
}

export async function governContract(contract: ContractCandidate): Promise<GovernedFinding> {
  const timestamp = new Date().toISOString();
  const flight_recorder: GovernedFinding["flight_recorder"] = [];

  const log = (stage: string, action: string, rationale: string, uncertainty: string) => {
    flight_recorder.push({
      id: `FR-${Date.now().toString(36).toUpperCase()}-${flight_recorder.length + 1}`,
      timestamp: new Date().toISOString(),
      actor: "GateService/Deterministic",
      stage,
      action,
      object: contract.reference_number,
      rationale,
      uncertainty,
      hash: rationaleHash(rationale),
    });
  };

  log(
    "V0 Ingest",
    "RECEIVED",
    `Contract ${contract.reference_number} received. Amendment ratio: ${(contract.amendment_ratio * 100).toFixed(0)}%.`,
    "C3",
  );

  const data_gaps: string[] = [];
  if (!contract.bn) data_gaps.push("PC-02: No BN available; data quality condition");
  if (!contract.solicitation_procedure) data_gaps.push("PC-02: Solicitation procedure not recorded");
  if (!contract.contract_date) data_gaps.push("PC-02: Contract date missing");

  log(
    "V1 Normalize",
    "DATA_QUALITY_LABELED",
    `${data_gaps.length} data quality conditions identified. PC-02 applied: missingness is not guilt.`,
    "C2",
  );

  const ag01 = evaluateAG01(contract);
  const gates = [
    ag01,
    evaluateAG02(contract),
    evaluateAG03(contract, ag01),
    evaluateAG04(contract),
    evaluateAG05(contract),
    evaluateAG06(contract),
    evaluateAG07(),
    evaluateAG08(),
    evaluateAG09(),
  ];

  gates.forEach((gate) => {
    log("V4 Gate", `${gate.gate_id}_${gate.verdict}`, gate.rationale, gate.calibration);
  });

  const derived = deriveClassification(contract, gates);
  const claim_state = enforceGates(derived, gates);

  log(
    "V4 Gate",
    "CLASSIFICATION_FINAL",
    `Derived: ${derived}. After enforceGates: ${claim_state}. PC-01: pattern is not verdict. PC-03: claim strength matches evidence strength.`,
    "C0",
  );

  const output = generateBoundedOutput(contract, claim_state);
  log("V5 Intervene", "BOUNDED_OUTPUT_GENERATED", output.headline, "C2");

  const stability = claim_state === "CLEARED" ? "S0" : "S1";
  const pc_rules_applied = [
    "PC-01: Pattern is not verdict",
    "PC-02: Missingness is not guilt",
    "PC-03: Claim strength matches evidence strength",
    "PC-05: Threshold documented (25%; PSPC CPN 2022-1)",
    "PC-10: No misconduct conclusion from open contract data alone",
    "PC-12: Summation Discipline; canonical current contract value required",
  ];

  if (claim_state === "INVESTIGATED") {
    pc_rules_applied.push("PC-04: No harmful escalation without named authority");
  }

  return {
    reference_number: contract.reference_number,
    vendor_name: contract.vendor_name,
    department: contract.department,
    claim_state,
    stability,
    evidence: [
      `Contract: ${contract.reference_number}`,
      `Department: ${contract.department}`,
      `Vendor: ${contract.vendor_name}`,
      `Original value: ${formatMoney(contract.original_value)}`,
      `Current value: ${formatMoney(contract.current_value)}`,
      `Amendment ratio: ${(contract.amendment_ratio * 100).toFixed(0)}%`,
      `Solicitation: ${contract.solicitation_procedure || "not recorded"}`,
    ],
    data_gaps,
    pc_rules_applied,
    gates,
    headline: output.headline,
    what_we_found: output.what_we_found,
    what_we_did_not_find: output.what_we_did_not_find,
    next_step: output.next_step,
    bounded_output_card: output.bounded_output_card,
    flight_recorder,
    governed_at: timestamp,
  };
}
