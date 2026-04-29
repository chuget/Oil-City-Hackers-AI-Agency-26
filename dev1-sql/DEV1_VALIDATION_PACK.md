# Dev 1 Validation Pack (Canonical Lane)

## Scope

- Canonical source: `public.contracts`
- Filter contract:
  - strict numeric parse for `original_value`, `amendment_value`, and `contract_value`
  - `original_value > 10000`
  - `amendment_value > 0`
- Ratio definition:
  - `amendment_ratio = (amendment_value / original_value) - 1`
  - `0.25` = amendment is 25% of original value

## Snapshot metrics

- Total rows in `public.contracts`: **153,455**
- Total candidates after filter: **27,251**
- Threshold buckets:
  - `amendment_ratio > 25%`: **5,410**
  - `amendment_ratio > 100%`: **2,322**
  - `amendment_ratio > 300%`: **714**

## Top ranked examples (sample for demo)

1. `C-2023-2024-Q1-00033`  
   Vendor: DESIRE2LEARN INCORPORATED  
   Department: Canada School of Public Service  
   Original: 33,900.00 | Amendment: 7,528,627.72 | Ratio: 221.083

2. `C-2024-2025-Q1-00013`  
   Vendor: Desire2Learn Incorporated  
   Department: Canada School of Public Service  
   Original: 33,900.00 | Amendment: 6,820,055.15 | Ratio: 200.182

3. `C-2024-2025-Q4-00047`  
   Vendor: Desire2Learn Incorporated  
   Department: Canada School of Public Service  
   Original: 33,900.00 | Amendment: 6,656,053.78 | Ratio: 195.344

## Quick QA spot checks (3)

- Spot check 1: ratios recomputed as `(amendment_value / original_value) - 1` match output ordering.
- Spot check 2: sampled rows are parse-valid numerics and satisfy `original_value > 10000` and `amendment_value > 0`.
- Spot check 3: sampled rows preserve required frontend fields (`vendor`, `department`, values, ratio, procedure, date, source, record_id`).

## Caveats to carry into demo language

- `solicitation_procedure` codes are mapped to labels in the canonical SQL output, and raw code is kept as `solicitation_procedure_raw`.
- This ranking is pattern detection only and not a misconduct determination.
