import { query } from "@/lib/db";
import type { ContractCandidate } from "@/types/governance";

export async function getAlbertaCases(limit = 20): Promise<ContractCandidate[]> {
  return query<ContractCandidate>(
    `
    SELECT
      ss.contract_number AS reference_number,
      ss.vendor AS vendor_name,
      ss.ministry AS department,
      ss.contract_services AS description,
      COALESCE(ss.start_date::text, ss.display_fiscal_year::text, '') AS contract_date,
      COALESCE(c.amount, 0)::float AS original_value,
      ss.amount::float AS amendment_value,
      (COALESCE(c.amount, 0) + ss.amount)::float AS current_value,
      CASE
        WHEN COALESCE(c.amount, 0) > 0 THEN ROUND((ss.amount / c.amount)::numeric, 3)::float
        ELSE 1
      END AS amendment_ratio,
      'Non-competitive' AS solicitation_procedure
    FROM ab.ab_sole_source ss
    LEFT JOIN LATERAL (
      SELECT amount
      FROM ab.ab_contracts c
      WHERE UPPER(TRIM(c.recipient)) = UPPER(TRIM(ss.vendor))
        AND c.ministry = ss.ministry
      ORDER BY c.display_fiscal_year DESC NULLS LAST
      LIMIT 1
    ) c ON true
    WHERE ss.amount IS NOT NULL
    ORDER BY ss.amount DESC NULLS LAST
    LIMIT $1
    `,
    [limit],
  );
}
