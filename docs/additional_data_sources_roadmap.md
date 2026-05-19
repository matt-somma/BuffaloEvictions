# Additional Data Sources Roadmap

This roadmap is for the next generation of the Buffalo housing instability platform.
It is designed around the current tract-month pipeline, where new data sources should be transformed into features that are available **as of each month** and safe to use for forecasting without target leakage.

## Current foundation

The current platform already has a strong base:

- ACS tract demographics
- Buffalo code violations
- tract geometry and adjacency
- trajectory / persistence features
- neighborhood spillover features
- tract-level forecast scoring

The most valuable new sources are the ones that improve one of these three jobs:

1. earlier warning before distress is already obvious
2. stronger explanation of *why* a tract is deteriorating
3. better separation between chronic vulnerability and active worsening

## Prioritization logic

Use this order when deciding what to build next:

1. public local administrative data that is already available now
2. partner or FOIL-based local data with strong early-warning value
3. commercial or harder-to-maintain feeds that add precision but increase operating cost

## Phase 1: Highest-ROI sources available now

These are the best next additions because they appear to have official local availability and can likely be integrated into the current monthly tract feature pipeline.

| Priority | Source | Why it matters | Likely Buffalo / Erie availability | Example tract-month features | Implementation difficulty |
|---|---|---|---|---|---|
| 1 | Assessment Roll | Adds parcel condition, owner occupancy, property class, assessed value, and property characteristics that help separate structural vulnerability from temporary case spikes | City of Buffalo assessment roll is available in OpenData Buffalo | owner-occupied share, absentee-owner share, residential parcel count, assessed value trend, poor-condition parcel share, exempt parcel share | Medium |
| 2 | Permits | Adds a protective / reinvestment signal that can distinguish decline from recovery or active stabilization | City of Buffalo permits data is available in OpenData Buffalo | permits per 1,000 parcels, rehab permits share, major-work permits count, permit dollar trend, permits lagged 3m / 12m | Medium |
| 3 | Rental Registry | Adds direct rental market and landlord-registration coverage that can improve interpretation of renter stress | City of Buffalo rental registry appears available in OpenData Buffalo | registered rental parcel share, registry growth rate, rental concentration, landlord concentration proxy | Medium |
| 4 | Housing Court Cases | Adds pre-eviction and landlord-tenant enforcement dynamics that are closer to instability than demographic proxies alone | City of Buffalo housing court cases appear available in OpenData Buffalo | housing court filings per 1,000 units, repeat-case parcel count, filing trend 3m / 12m | Medium |
| 5 | 311 Cases | Good emerging-disorder and nuisance signal, especially when categorized into housing, sanitation, vacancy, and exterior condition complaints | OpenData Buffalo has 311 datasets | housing-related 311 rate, sanitation complaint rate, repeat-complaint parcel count, unresolved complaint share | Medium |
| 6 | Crime Incidents | Useful contextual signal for neighborhood disorder, especially property crime and nuisance patterns around deterioration clusters | Crime incidents appear available in OpenData Buffalo | property-crime rate, disorder-call density, recent crime acceleration, nearby-crime spillover features | Medium |
| 7 | Foreclosure / Tax Foreclosure Lists | Strong owner-distress signal and a high-value event source for identifying structural stress at the parcel level | Erie County publishes foreclosure / auction information and delinquent-tax foreclosure materials | parcels entering foreclosure, foreclosure count per tract, months since first foreclosure filing, foreclosure persistence | Medium / High |

## Phase 1 build sequence

Recommended order:

1. Assessment Roll
2. Permits
3. Rental Registry
4. Housing Court Cases
5. 311 Cases
6. Foreclosure / tax foreclosure events
7. Crime incidents

Why this order:

- `Assessment Roll` and `Permits` add the biggest structural + protective value.
- `Rental Registry` and `Housing Court Cases` are especially relevant to your existing housing-instability framing.
- `311` is high-value but needs careful complaint-type filtering.
- `Foreclosure` is very important, but likely needs more cleaning and parcel matching.
- `Crime` helps context and clustering, but it is usually a second-order explanatory source rather than the first source I would add.

## Phase 2: Partner / FOIL sources with very high early-warning value

These are likely worth pursuing, but they may require agency relationships, FOIL, aggregation rules, or privacy review.

| Priority | Source | Why it matters | Availability expectation | Example tract-month features | Difficulty |
|---|---|---|---|---|---|
| 1 | Utility arrears / shutoffs | One of the strongest early-warning indicators of household and building stress | Likely not open; utility or city-partner access needed | shutoffs per 1,000 accounts, arrears rate, repeat shutoff parcels, shutoff acceleration | High |
| 2 | Tax delinquency balances | Better than annual foreclosure events because it captures stress before the legal process advances | Could require county or city partnership, clerk access, or custom extract | delinquent parcel share, median delinquency age, delinquent balance per parcel, repeat delinquency rate | High |
| 3 | Fire incidents / arson / structure fires | Strong for severe distress, vacant structures, and localized collapse risk | May exist in public or FOILable form depending on granularity | structure fires rate, vacant-structure fire count, fire recurrence by parcel | Medium / High |
| 4 | Demolition / condemnation / boarding actions | Highly relevant to neighborhood decline and vacancy pathways | Could be public, hidden inside permits, or available by FOIL | demolitions per tract, condemned parcel count, boarding actions rate | Medium / High |
| 5 | Shelter entry / homelessness service utilization | Helps identify neighborhood-to-household distress connections | Likely partnership-only and privacy-sensitive | tract-level service-entry rates, concentration of prior-address origins | High |

## Phase 3: Advanced / commercial sources

These are useful, but I would not prioritize them before the local administrative sources above.

| Priority | Source | Why it matters | Availability expectation | Example tract-month features | Difficulty |
|---|---|---|---|---|---|
| 1 | Rental listings / asking rents | Distinguishes weak-market decline from affordability pressure and displacement | Commercial scrape / third-party source likely needed | median asking rent, listing volume, rent growth, rent volatility | High |
| 2 | Deeds / mortgage recordings | Helps track investor churn, speculative acquisition, refinancing stress, and distressed transfer patterns | Erie County Clerk records exist, but tract-month pipeline may require purchase or heavy ETL | investor purchase share, rapid resale count, mortgage filing trend | High |
| 3 | USPS or similar vacancy indicators | Excellent vacancy signal if accessible | Usually not simple public local data | active vacancy share, persistent vacancy share, vacancy inflow | High |
| 4 | School mobility / absenteeism | Strong family-instability proxy | Likely district partnership needed | mobility rate, absenteeism rate, abrupt school-change concentration | High |

## Recommended feature families

Whatever source you add, try to derive features in these repeatable families:

### Level features

Examples:

- current count
- rate per 1,000 housing units
- rate per 1,000 parcels
- share of tract parcels affected

### Trend features

Examples:

- rolling 3-month count
- rolling 6-month count
- rolling 12-month count
- month-over-month change
- 3m vs 12m acceleration

### Persistence features

Examples:

- months with any event in the last 12 months
- share of prior 12 months with an event
- repeat-event parcel share

### Concentration features

Examples:

- top parcel concentration share
- events per affected parcel
- spatial clustering within tract

### Spillover features

Examples:

- neighbor average rate
- distressed-neighbor count
- border-weighted nearby-event score

## Recommended roadmap by quarter

### Wave 1

Goal: improve structural and protective signal.

- Assessment Roll
- Permits
- Rental Registry

Expected outcome:

- better distinction between chronic vulnerability and active decline
- stronger tract explainability
- better interpretation of stable-but-fragile tracts

### Wave 2

Goal: improve renter distress and emerging-warning signal.

- Housing Court Cases
- 311 Cases
- Foreclosure / tax foreclosure events

Expected outcome:

- earlier operational warning
- stronger connection to intervention use cases
- better medium-horizon forecast performance

### Wave 3

Goal: sharpen severe-distress pathways and vacancy dynamics.

- tax delinquency balances
- demolition / condemnation / boarding
- utility shutoffs / arrears

Expected outcome:

- better severe-state targeting
- better 6m / 12m forecasts
- stronger explanation of neighborhood deterioration pathways

## Suggested first three implementation tickets

### Ticket 1: Assessment Roll integration

Build:

- raw ingest table
- parcel-to-tract join
- monthly or annual snapshot logic
- tract-level structural features

Key outputs:

- absentee owner share
- owner-occupied share
- parcel condition mix
- assessed value distribution

### Ticket 2: Permits integration

Build:

- raw permits ingest
- permit-type normalization
- tract-month aggregation
- permit recency and volume features

Key outputs:

- rehab permits per 1,000 parcels
- high-value permit count
- permit momentum 3m / 12m

### Ticket 3: Housing Court + 311 integration

Build:

- category mapping tables
- parcel and tract geocoding
- monthly aggregation
- complaint / filing trend features

Key outputs:

- housing-court filings per 1,000 units
- unresolved 311 housing complaints
- repeat-complaint parcel concentration

## Guardrails

When adding any new source:

1. enforce strict `as-of month` logic to avoid leakage
2. keep parcel-level raw data internal and aggregate to tract-month for modeling
3. prefer both `burden` and `change` features, not just counts
4. add at least one interpretability field so the app can explain why the source matters
5. validate whether the source improves:
   - ROC-AUC
   - average precision
   - calibration
   - actionable ranking quality

## Official source links

These are the main official sources that look most relevant right now:

- City of Buffalo OpenData: [OpenData Buffalo](https://data.buffalony.gov/)
- Assessment Roll: [2025 Final Assessment Roll (Current)](https://data.buffalony.gov/Government/Current-2020-2021-Assessment-Roll/4t8s-9yih)
- Code Violations: [Code Violations](https://data.buffalony.gov/w/ivrf-k9vm/ixf7-aa9j?cur=MusyvjeVLo5)
- Active Code Violations: [Active Code Violations](https://data.buffalony.gov/widgets/abwd-pczc)
- Permits: [Permits](https://data.buffalony.gov/w/9p2d-f3yt/ixf7-aa9j?cur=PZ2qGYfA12A&from=12wEcJZsdOO)
- All permits since 2018: [All permits since 1/1/2018](https://data.buffalony.gov/w/e48j-dfaz/ixf7-aa9j?cur=WherANx2MjD&from=ETXZwj4dPIN)
- Rental Registry: [Rental Registry](https://data.buffalony.gov/w/hpqg-ihzt/ixf7-aa9j?cur=h_Vp6bcxkbb)
- Housing Court Cases: [Housing Court Cases](https://data.buffalony.gov/w/k3vq-gzry/ixf7-aa9j?cur=Z-gjn0smVS7)
- Crime Incidents: [Crime Incidents](https://data.buffalony.gov/widgets/d6g9-xbgu)
- Erie County foreclosure / auction information: [Auction & Foreclosure Information](https://www3.erie.gov/ecrpts/auction-foreclosure-information)
- Erie County parcel mapping / parcel viewer: [Map Gallery](https://www3.erie.gov/gis/map-gallery)

## Bottom line

If you want the highest-value next build with manageable complexity, I would start with:

1. Assessment Roll
2. Permits
3. Rental Registry
4. Housing Court Cases
5. 311 Cases

That combination is the best balance of:

- local relevance
- likely official availability
- early-warning value
- structural context
- interpretability for the dashboard
