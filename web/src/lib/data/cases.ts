import { mockCases } from "@/lib/fixtures/contracts";
import { hasDatabaseUrl } from "@/lib/db";
import { getAlbertaCases } from "@/lib/data/albertaCases";
import { getFederalCases } from "@/lib/data/federalCases";
import type { ContractCandidate } from "@/types/governance";

export type CaseDataset = "mock" | "alberta" | "federal";

export async function getCases(limit = 20): Promise<{
  cases: ContractCandidate[];
  dataset: CaseDataset;
  source: "database" | "fixture";
}> {
  const dataset = (process.env.CASE_DATASET ?? "mock") as CaseDataset;

  if (!hasDatabaseUrl() || dataset === "mock") {
    return { cases: mockCases.slice(0, limit), dataset: "mock", source: "fixture" };
  }

  if (dataset === "alberta") {
    return { cases: await getAlbertaCases(limit), dataset, source: "database" };
  }

  if (dataset === "federal") {
    return { cases: await getFederalCases(limit), dataset, source: "database" };
  }

  return { cases: mockCases.slice(0, limit), dataset: "mock", source: "fixture" };
}

export async function getCaseByReference(referenceNumber: string) {
  const { cases, dataset, source } = await getCases(50);
  const contract = cases.find((candidate) => candidate.reference_number === referenceNumber);
  return { contract: contract ?? null, dataset, source };
}
