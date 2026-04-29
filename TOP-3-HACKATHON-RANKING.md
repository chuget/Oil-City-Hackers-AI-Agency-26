# Agency 2026 – Top 3 One-Day Hackathon Builds

## Ranking Criteria
- High signal with likely available data
- Buildable in one day by a small team
- Easy to demo clearly to judges
- Strong public-sector accountability story
- Lower dependency on hard-to-access external data

## 1. Sole Source and Amendment Creep
**Why it ranks #1:**
- Contract and amendment data is usually structured enough to analyze quickly
- The problem is intuitive for judges: small contract becomes large through amendments
- Easy to demo with before/after contract timelines and a ranked dashboard
- Strong accountability narrative without needing perfect ML

**Best build angle:**
Start with **Amendment Growth Tracker** and optionally add **Threshold Split Detector** if time allows.

**Why it’s hackathon-friendly:**
- Mostly deterministic analytics
- Clear visual output
- Doesn’t require heavy entity resolution to be useful

## 2. Vendor Concentration
**Why it ranks #2:**
- Straightforward aggregation problem with strong visuals
- Easy to explain: “government is overly dependent on a few vendors here”
- Good demo potential with HHI/top-share charts and dependency scenarios
- Can be valuable even with partial procurement data

**Best build angle:**
Start with **Concentration Index Dashboard** and add a lightweight **Dependency Shock Simulator** for demo flair.

**Why it’s hackathon-friendly:**
- Fast path from raw contract data to useful insight
- Minimal need for complex matching
- Judges can understand it in seconds

## 3. Zombie Recipients
**Why it ranks #3:**
- Strong narrative payoff: “public money went to entities that disappeared”
- Great accountability framing
- More ambitious than #1 and #2, but still feasible if entity matching is decent
- Timeline-based storytelling makes for a memorable demo

**Best build angle:**
Start with **Shutdown Risk Timeline Detector** and use simple rule-based scoring rather than a full predictive model.

**Why it’s hackathon-friendly:**
- Powerful story with relatively simple output
- Good candidate for combining structured data + evidence cards
- Harder than procurement challenges, but still very compelling

## Honorable Mentions
### Funding Loops
Very interesting and visually strong, but graph interpretation can get subtle fast. Great if the team has graph/data science strength.

### Adverse Media
Very demo-friendly, but quality depends heavily on article access, entity resolution, and false-positive control.

### Duplicative Funding
Potentially strong, but cross-government matching may become messy in a one-day window.

## Recommended Strategy
If the goal is **best chance of a polished, credible one-day demo**, I’d recommend:
1. **Sole Source and Amendment Creep**
2. **Vendor Concentration**
3. **Zombie Recipients**

If you want the safest path, pick **Sole Source and Amendment Creep**.
If you want the most emotionally compelling story, pick **Zombie Recipients**.
