# Data Source Implementation Tickets

This document turns the top three roadmap priorities into concrete build tickets.

## Ticket 1: Assessment Roll ingestion and tract structural features

### Goal

Bring the City of Buffalo assessment roll into the warehouse so we can build parcel-derived tract features such as owner occupancy, exempt share, assessed value patterns, and parcel condition mix.

### Source

- Dataset: `2025 Final Assessment Roll (Current)`
- OpenData Buffalo dataset ID: `4t8s-9yih`

### Scope

Phase A:

- add raw ingest ETL
- load into `raw.buffalo_assessment_roll`
- preserve source metadata and ingestion timestamp

Phase B:

- inspect schema and identify parcel identifier fields
- create parcel-to-tract mapping strategy
- build tract-level structural feature mart

### Deliverables

- [x] config entry for dataset ID
- [x] raw ETL script
- [x] data profiling notebook or SQL audit
- [x] tract structural feature SQL mart
- [x] documentation of key fields used for modeling
- [x] assessment features integrated into tract ML backtest and live-scoring marts
- [x] model retrain completed and compared to prior baseline

### Acceptance criteria

- ETL loads the full source into `raw.buffalo_assessment_roll`
- ingestion is repeatable
- row count is logged
- source dataset ID and ingest timestamp are stored
- parcel identifier strategy is documented before feature engineering starts

### Candidate features

- owner-occupied parcel share
- absentee-owner parcel share
- residential parcel count
- exempt parcel share
- poor-condition parcel share
- median and total assessed value
- assessed value concentration

### Risks / notes

- parcel-to-tract join may require a separate parcel geometry or address normalization step
- field names should be profiled from the actual source before feature logic is finalized

## Ticket 2: Permits ingestion and reinvestment features

### Goal

Add a protective and reinvestment signal so the model can distinguish active decline from areas receiving real rehabilitation activity.

### Source

- Dataset: `Permits`
- OpenData Buffalo dataset ID: `9p2d-f3yt`

### Scope

- add raw ingest ETL
- normalize permit type fields
- aggregate to tract-month features

### Deliverables

- [x] config entry for dataset ID
- [ ] raw ETL script
- [ ] permit-type mapping logic
- [ ] tract-month permit features

### Acceptance criteria

- ETL loads the full source into a raw table
- permit issue / effective dates are standardized
- high-value rehab categories are separated from minor permits
- tract-month outputs are available for modeling

### Candidate features

- permits per 1,000 parcels
- rehab permits share
- major-work permits count
- permit dollar trend
- 3m and 12m permit momentum

## Ticket 3: Rental Registry ingestion and landlord concentration features

### Goal

Bring in registered rental property coverage to improve interpretation of renter-market concentration and landlord exposure.

### Source

- Dataset: `Rental Registry`
- OpenData Buffalo dataset ID: `hpqg-ihzt`

### Scope

- add raw ingest ETL
- identify rental property and owner fields
- aggregate registration coverage and concentration metrics at tract level

### Deliverables

- [x] config entry for dataset ID
- [ ] raw ETL script
- [ ] tract-level registration coverage mart
- [ ] landlord concentration feature logic

### Acceptance criteria

- ETL loads the source into a raw table
- registration records can be linked to parcels or addresses consistently
- tract-level rental concentration metrics are reproducible

### Candidate features

- registered rental parcel share
- rental registration coverage growth
- landlord concentration proxy
- repeat-owner parcel concentration
- rental-density interaction features

## Immediate next step

Ticket 1 has now been carried through the first modeling integration with:

- [src/etl/extract/load_assessment_roll.py](C:/Users/Matt/OneDrive/Documents/BuffaloEvictions/src/etl/extract/load_assessment_roll.py)
- [src/etl/extract/socrata.py](C:/Users/Matt/OneDrive/Documents/BuffaloEvictions/src/etl/extract/socrata.py)
- [sql/marts/create_housing_risk_features_v2.sql](C:/Users/Matt/OneDrive/Documents/BuffaloEvictions/sql/marts/create_housing_risk_features_v2.sql)
- [sql/marts/create_tract_ml_features.sql](C:/Users/Matt/OneDrive/Documents/BuffaloEvictions/sql/marts/create_tract_ml_features.sql)
- [sql/marts/create_tract_ml_scoring_features.sql](C:/Users/Matt/OneDrive/Documents/BuffaloEvictions/sql/marts/create_tract_ml_scoring_features.sql)
- [src/ml/train_logistic_regression.py](C:/Users/Matt/OneDrive/Documents/BuffaloEvictions/src/ml/train_logistic_regression.py)

Supporting profiling and feature-engineering notes are captured in:

- [docs/assessment_roll_profile_and_join_design.md](C:/Users/Matt/OneDrive/Documents/BuffaloEvictions/docs/assessment_roll_profile_and_join_design.md)
- [sql/marts/create_tract_assessment_features_current.sql](C:/Users/Matt/OneDrive/Documents/BuffaloEvictions/sql/marts/create_tract_assessment_features_current.sql)

### Ticket 1 modeling result

Assessment-derived structural features are now available in both:

- `analytics.tract_ml_features`
- `analytics.tract_ml_scoring_features`

The retrained model version is `v4_time_aware_live_scoring_assessment`.

Compared with the prior calibrated baseline, the assessment features had a mixed effect:

- `1m`: ROC-AUC changed from `0.9704` to `0.9701`, while Brier improved from `0.0945` to `0.0944`
- `3m`: ROC-AUC changed from `0.9527` to `0.9519`, while Brier improved from `0.1044` to `0.1039`
- `6m`: ROC-AUC changed from `0.9385` to `0.9343`, while Brier improved from `0.1107` to `0.1086`
- `12m`: ROC-AUC changed from `0.9126` to `0.9089`, while Brier improved from `0.1212` to `0.1202`

Interpretation:

- the new structural features added modest calibration value
- they did not improve rank-order discrimination enough to beat the existing baseline
- the strongest new signals were `residential_vacant_land_share`, `missing_condition_share`, `fair_or_worse_condition_share`, `residential_parcel_share`, and `pre_1940_residential_share`

Recommended next step:

- keep the assessment mart in the warehouse and dashboard context layer
- consider a smaller retained subset for ML or use these fields mainly for interpretation, segmentation, and case review
- proceed to Ticket 2 so we can test whether reinvestment / permit signals add more predictive lift
