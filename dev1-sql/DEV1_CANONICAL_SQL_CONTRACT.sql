-- Dev 1 canonical SQL contract for frontend/demo consumption.
-- Canonical lane: public.contracts (verified live).

-- 1) Main ranked dataset
-- Required output fields:
-- vendor, department, original_value, current_value, amendment_value,
-- amendment_ratio, solicitation_procedure, contract_or_agreement_date,
-- source_system, record_id
-- Ratio definition used here:
-- amendment_ratio = (amendment_value / original_value) - 1
-- Example: 0.25 means amendment value is 25% of original value.
WITH typed AS (
  SELECT
    id,
    reference_number,
    vendor_name,
    owner_org_title AS department,
    contract_date,
    solicitation_procedure AS solicitation_procedure_raw,
    CASE
      WHEN TRIM(original_value) ~ '^[0-9]+(\\.[0-9]+)?$'
      THEN TRIM(original_value)::numeric(15,2)
    END AS original_value_num,
    CASE
      WHEN TRIM(amendment_value) ~ '^[0-9]+(\\.[0-9]+)?$'
      THEN TRIM(amendment_value)::numeric(15,2)
    END AS amendment_value_num,
    CASE
      WHEN TRIM(contract_value) ~ '^[0-9]+(\\.[0-9]+)?$'
      THEN TRIM(contract_value)::numeric(15,2)
    END AS current_value_num
  FROM public.contracts
),
scored AS (
  SELECT
    id,
    reference_number,
    vendor_name,
    department,
    contract_date,
    CASE solicitation_procedure_raw
      WHEN 'OB' THEN 'Open bidding'
      WHEN 'TC' THEN 'Traditional competitive'
      WHEN 'TN' THEN 'Traditional non-competitive'
      WHEN 'AC' THEN 'Advance contract award notice'
      WHEN 'ST' THEN 'Standing offer or supply arrangement'
      ELSE COALESCE(solicitation_procedure_raw, 'Unknown')
    END AS solicitation_procedure,
    solicitation_procedure_raw,
    original_value_num,
    amendment_value_num,
    current_value_num,
    ROUND(((amendment_value_num / NULLIF(original_value_num, 0)) - 1)::numeric, 3) AS amendment_ratio
  FROM typed
  WHERE original_value_num > 10000
    AND amendment_value_num IS NOT NULL
    AND current_value_num IS NOT NULL
    AND amendment_value_num > 0
)
SELECT
  vendor_name AS vendor,
  department,
  original_value_num AS original_value,
  current_value_num AS current_value,
  amendment_value_num AS amendment_value,
  amendment_ratio,
  solicitation_procedure,
  solicitation_procedure_raw,
  contract_date AS contract_or_agreement_date,
  'public.contracts'::text AS source_system,
  CONCAT('contracts:', id::text) AS record_id
FROM scored
ORDER BY amendment_ratio DESC NULLS LAST;


-- 2) Dashboard threshold counts using the same filter contract
WITH typed AS (
  SELECT
    CASE
      WHEN TRIM(original_value) ~ '^[0-9]+(\\.[0-9]+)?$'
      THEN TRIM(original_value)::numeric(15,2)
    END AS original_value_num,
    CASE
      WHEN TRIM(amendment_value) ~ '^[0-9]+(\\.[0-9]+)?$'
      THEN TRIM(amendment_value)::numeric(15,2)
    END AS amendment_value_num
  FROM public.contracts
),
scored AS (
  SELECT
    ((amendment_value_num / NULLIF(original_value_num, 0)) - 1) AS amendment_ratio
  FROM typed
  WHERE original_value_num > 10000
    AND amendment_value_num IS NOT NULL
    AND amendment_value_num > 0
)
SELECT
  COUNT(*)::bigint AS total_candidates,
  COUNT(*) FILTER (WHERE amendment_ratio > 0.25)::bigint AS gt_25,
  COUNT(*) FILTER (WHERE amendment_ratio > 1.0)::bigint AS gt_100,
  COUNT(*) FILTER (WHERE amendment_ratio > 3.0)::bigint AS gt_300
FROM scored;
