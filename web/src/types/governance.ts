export type ClaimState = "FLAGGED" | "INVESTIGATED" | "CLEARED" | "CRITICAL";
export type Stability = "S0" | "S1" | "S2" | "S3";
export type GateVerdictValue = "PASS" | "CAUTION" | "HOLD" | "FAIL" | "PENDING";

export interface ContractCandidate {
  reference_number: string;
  vendor_name: string;
  department: string;
  description: string;
  contract_date: string;
  original_value: number;
  amendment_value: number;
  current_value: number;
  amendment_ratio: number;
  solicitation_procedure: "Competitive" | "Non-competitive" | string | null;
  bn?: string;
}

export interface GateVerdict {
  gate_id: string;
  gate_name: string;
  verdict: GateVerdictValue;
  rationale: string;
  calibration: "C0" | "C1" | "C2" | "C3" | string;
}

export interface FlightEntry {
  id: string;
  timestamp: string;
  actor: string;
  stage: string;
  action: string;
  object: string;
  rationale: string;
  uncertainty: string;
  hash: string;
}

export interface GovernedFinding {
  reference_number: string;
  vendor_name: string;
  department: string;
  claim_state: ClaimState;
  stability: Stability;
  evidence: string[];
  data_gaps: string[];
  pc_rules_applied: string[];
  gates: GateVerdict[];
  headline: string;
  what_we_found: string;
  what_we_did_not_find: string;
  next_step: string;
  bounded_output_card: string;
  flight_recorder: FlightEntry[];
  governed_at: string;
}
