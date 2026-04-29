import { query } from "@/lib/db";
import type { ContractCandidate } from "@/types/governance";

export async function getFederalCases(limit = 20): Promise<ContractCandidate[]> {
  return query<ContractCandidate>(
    `
    SELECT
      reference_number,
      vendor_name,
      owner_org_title AS department,
      description_en AS description,
      contract_date::text AS contract_date,
      CAST(NULLIF(original_value, '') AS DECIMAL(15,2))::float AS original_value,
      CAST(NULLIF(amendment_value, '') AS DECIMAL(15,2))::float AS amendment_value,
      CAST(NULLIF(contract_value, '') AS DECIMAL(15,2))::float AS current_value,
      ROUND((
        CAST(NULLIF(amendment_value, '') AS DECIMAL(15,2)) /
        NULLIF(CAST(NULLIF(original_value, '') AS DECIMAL(15,2)), 0)
      )::numeric, 3)::float AS amendment_ratio,
      solicitation_procedure
    FROM public.contracts
    WHERE original_value ~ '^[0-9]'
      AND amendment_value ~ '^[0-9]'
      AND CAST(NULLIF(original_value, '') AS DECIMAL(15,2)) > 10000
      AND CAST(NULLIF(amendment_value, '') AS DECIMAL(15,2))
        > CAST(NULLIF(original_value, '') AS DECIMAL(15,2))
    ORDER BY amendment_ratio DESC NULLS LAST
    LIMIT $1
    `,
    [limit],
  );
}
