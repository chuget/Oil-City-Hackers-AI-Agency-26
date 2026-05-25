# Agency 2026: challenge picks for a one-day build

Internal notes from early planning. We chose **Sole Source and Amendment Creep** for the hackathon.

## How we ranked options

- Data had to exist in the warehouse and be queryable in a day
- Demo had to be explainable in under five minutes
- Logic could be mostly SQL and rules, not a custom ML pipeline

## Our top three

### 1. Sole Source and Amendment Creep (what we built)

- Contract and amendment fields are structured in `public.contracts`
- Judges understand “small award, large amendments” quickly
- Ranked table + one contract drill-down is enough for a demo
- Governance gates give a clear story beyond charts

### 2. Vendor Concentration

- Mostly group-bys and charts (HHI, top vendors by department)
- Useful even with partial data
- Less unique than amendment creep for this event

### 3. Zombie Recipients

- Strong headline (“money went to entities that shut down”)
- Needs better entity matching; riskier in 24 hours

## Passed for now

- **Funding Loops:** interesting graphs, harder to explain fast
- **Adverse Media:** depends on news APIs and false-positive control
- **Duplicative Funding:** cross-program matching is messy on a short clock

## Bottom line

Stick with **Amendment Creep** for a reliable demo. Consider **Vendor Concentration** as a stretch chart. **Zombie Recipients** only if entity resolution is already working.
