import type { ContractCandidate } from "@/types/governance";

export const mockCases: ContractCandidate[] = [
  {
    reference_number: "DEMO-INV-001",
    vendor_name: "Northstar Systems Inc.",
    department: "Public Services and Procurement Canada",
    description: "IT professional services contract with major amendment growth.",
    contract_date: "2024-02-15",
    original_value: 125000,
    amendment_value: 285000,
    current_value: 410000,
    amendment_ratio: 2.28,
    solicitation_procedure: "Non-competitive",
    bn: "123456789",
  },
  {
    reference_number: "DEMO-FLG-002",
    vendor_name: "Prairie Analytics Ltd.",
    department: "Treasury Board Secretariat",
    description: "Advisory services contract above monitoring threshold.",
    contract_date: "2025-07-10",
    original_value: 200000,
    amendment_value: 72000,
    current_value: 272000,
    amendment_ratio: 0.36,
    solicitation_procedure: "Competitive",
  },
];
