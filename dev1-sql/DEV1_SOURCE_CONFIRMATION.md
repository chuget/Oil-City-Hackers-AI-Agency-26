# Dev 1 Source Confirmation (Immediate)

## Decision

Canonical lane for this demo is `public.contracts`.
This decision supersedes conflicting one-off guidance in other notes that suggest an Alberta-first lane for this specific Dev 1 deliverable.

## Evidence

Live read-only probes confirmed all relevant tables exist:

- `public.contracts`
- `fed.grants_contributions`
- `ab.ab_contracts`
- `ab.ab_sole_source`

Row counts observed during verification:

- `public.contracts`: 153,455
- `fed.grants_contributions`: 1,275,521
- `ab.ab_contracts`: 67,079
- `ab.ab_sole_source`: 15,533

## Why this lane

- Challenge scope is contract amendment/sole-source behavior; `public.contracts` directly includes:
  - `reference_number`
  - `vendor_name`
  - `owner_org_title`
  - `original_value`
  - `amendment_value`
  - `contract_value`
  - `solicitation_procedure`
  - `contract_date`
- This avoids semantic mismatch from federal grants data, where amendment summation has strict caveats.

## Rejected as primary lane (for now)

- `fed.grants_contributions`: strong for grants/contributions analysis, but not the primary contract table for this challenge narrative.
- `ab.*` (`ab_contracts`, `ab_sole_source`): useful fallback/proxy for follow-on risk, but not true amendment lineage.

## Guardrails

- If fallback to Alberta is needed, phrase findings as "sole-source follow-on risk" and not amendment lineage.
- Keep one frontend contract output schema regardless of lane to avoid UI branching.
- Use robust numeric parsing and explicit ratio semantics in SQL artifacts to keep threshold buckets meaningful.
