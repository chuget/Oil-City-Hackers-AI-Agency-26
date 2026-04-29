import { query } from "@/lib/db";
import type { ContractCandidate } from "@/types/governance";

export async function getAlbertaCases(limit = 20): Promise<ContractCandidate[]> {
  return query<ContractCandidate>(
    `
    SELECT
      ss.contract_number AS reference_number,
      ss.vendor AS vendor_name,
      ss.ministry AS department,
      CONCAT(
        ss.contract_services,
        ' | Matched original contract by exact vendor + ministry; original fiscal year: ',
        COALESCE(c.display_fiscal_year::text, 'unknown')
      ) AS description,
      COALESCE(ss.start_date::text, ss.display_fiscal_year::text, '') AS contract_date,
      c.amount::float AS original_value,
      ss.amount::float AS amendment_value,
      (c.amount + ss.amount)::float AS current_value,
      ROUND((ss.amount / c.amount)::numeric, 3)::float AS amendment_ratio,
      'Non-competitive' AS solicitation_procedure
    FROM ab.ab_sole_source ss
    JOIN LATERAL (
      SELECT amount, display_fiscal_year
      FROM ab.ab_contracts c
      WHERE UPPER(TRIM(c.recipient)) = UPPER(TRIM(ss.vendor))
        AND c.ministry = ss.ministry
        AND c.amount IS NOT NULL
        AND c.amount >= 10000
      ORDER BY c.display_fiscal_year DESC NULLS LAST
      LIMIT 1
    ) c ON true
    WHERE ss.amount IS NOT NULL
      AND ss.amount > 0
      AND ss.amount > c.amount
    ORDER BY amendment_ratio DESC NULLS LAST, ss.amount DESC NULLS LAST
    LIMIT $1
    `,
    [limit],
  );
}
