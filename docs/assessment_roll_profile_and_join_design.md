# Assessment Roll Profile And Parcel-To-Tract Join Design

This document profiles `raw.buffalo_assessment_roll` and defines the recommended join strategy for the first tract-level structural feature mart.

## Executive summary

The assessment roll is much cleaner than expected for tract-level feature engineering.

Key takeaways:

- the table loaded successfully with `93,591` rows
- `print_key`, `sbl`, `address`, `census_tract`, `tractce20`, and `geoid20_tract` are fully populated
- `print_key` and `sbl` are unique at the row level in the current snapshot
- `geoid20_tract` is the correct tract join key for the existing tract analytics universe
- the source `neighborhood` field is **not** reliable enough to use as a grouping or join field
- no spatial join is required for the first mart because tract geography is already present in the source

## Profiling results

### Table shape

- source table: `raw.buffalo_assessment_roll`
- row count: `93,591`
- all business columns are stored as `text`, except `ingested_at`

### Parcel identifiers

- `print_key`: populated for all rows
- `sbl`: populated for all rows
- `print_key` distinct count: `93,591`
- `sbl` distinct count: `93,591`

Interpretation:

- this looks like a one-row-per-parcel snapshot
- `print_key` is the best primary parcel identifier for marts
- `sbl` should be retained as a secondary parcel identifier for audit and crosswalk work

### Geography coverage

- rows with `geoid20_tract`: `93,591`
- distinct `geoid20_tract`: `92`
- rows with `census_tract`: `93,591`
- rows with `census_block_group`: `93,591`
- missing `geoid20_tract`: `0`
- missing `census_tract`: `0`

Interpretation:

- tract geography is complete in the raw source
- the first structural mart should use `geoid20_tract` directly

### Tract-universe comparison

When compared to the current application tract universe, the assessment roll includes two tract codes that are not in `analytics.tract_state_history` or `analytics.tract_neighborhood_labels`:

- `36029980000`
- `36029980500`

It also contains `UNKNOWN` in the neighborhood field on a small number of rows.

Interpretation:

- the mart should filter to the existing analytic tract universe when producing model-ready tract features
- keep the raw table complete, but constrain the first structural mart to the same tract set used by the dashboard and model pipeline

### Neighborhood field quality

The raw `neighborhood` field is not stable within tract.

Examples from profiling:

- `36029000110` appears with `Hopkins-Tifft`, `UNKNOWN`, `Seneca Babcock`, and `Central`
- `36029000500` appears with `First Ward`, `Central`, `Hopkins-Tifft`, and `Seneca Babcock`
- there are `239` rows where `neighborhood` is `UNKNOWN`, blank, or null
- there are `36` distinct neighborhood values in the raw roll

Interpretation:

- do **not** use the assessment-roll `neighborhood` field to group parcel records
- if neighborhood labeling is needed, use the existing tract label table after tract aggregation

### Feature-oriented field quality

Numeric parse coverage:

- `total_value`: `93,591 / 93,591`
- `land_value`: `93,591 / 93,591`
- `acres`: `93,590 / 93,591`
- `total_living_area`: `93,591 / 93,591`
- `units`: `93,591 / 93,591`
- `year_built` with valid 4-digit year: `67,716 / 93,591`

Other useful categorical fields:

- `homestead_code`: values observed were `H` and `N`
  - `H`: `79,624`
  - `N`: `13,967`
- `overall_condition` / `overall_condition_description`
  - `3 / Normal`: `60,657`
  - `4 / Good`: `3,859`
  - `2 / Fair`: `2,909`
  - `1 / Poor`: `285`
  - `5 / Excellent`: `10`
  - missing condition: `25,871`

Interpretation:

- value, area, and unit fields are immediately usable after casting
- `year_built` is good enough for age-profile features, but not complete enough to be the only building-condition proxy
- `homestead_code` is a strong candidate owner-occupancy proxy
- `overall_condition` is useful, but missingness itself should become a feature
- `units` should not be treated as the primary multifamily flag because many clearly multifamily classes store `0` there

### Property class mix

By first digit of `property_class_code`:

- `2`: `66,891`
- `3`: `16,361`
- `4`: `8,254`
- `6`: `902`
- `7`: `449`
- `8`: `434`
- `9`: `169`
- `5`: `131`

Largest detailed classes:

- `210` `ONE FAMILY DWELLING`: `37,995`
- `220` `TWO FAMILY DWELLING`: `26,407`
- `311` `RESIDENTIAL VACANT LAND`: `12,110`
- `330` `COMMERCIAL VACANT LAND`: `2,573`
- `411` `APARTMENT`: `2,568`
- `482` `DOWNTOWN ROW TYPE (DETACHED)`: `2,100`

Interpretation:

- the roll is rich enough to support residential mix, multifamily concentration, and vacant-land features

## Recommended join strategy

### Join design

Use this join strategy for the first tract structural mart:

1. Use `print_key` as the parcel-level primary key.
2. Keep `sbl` as a secondary audit identifier.
3. Use `geoid20_tract` as the tract join key.
4. Filter to the tract universe already used by the platform:
   - `analytics.tract_state_history`
   - or `analytics.tract_neighborhood_labels`
5. Ignore the raw `neighborhood` field for joins and grouping.

### Why no spatial join is needed

The source already contains:

- `tractce20`
- `geoid20_tract`
- `census_block_group`
- `geoid20_blockgroup`

That means a geometry overlay is unnecessary for the first mart.

A spatial join would only be needed later if:

- parcel geometry becomes available and you want geometry-based QA
- you need to resolve edge cases across geography vintages
- you need to validate geocoding quality independently

## Recommended staging pattern

Before building the tract mart, create a cleaned parcel staging layer with:

- one row per `print_key`
- parsed numeric fields
- tract filter applied
- normalized property class buckets
- normalized condition buckets
- normalized owner-occupancy proxy

Recommended derived staging fields:

- `parcel_id`
- `geoid`
- `property_class_group`
- `is_residential`
- `is_residential_vacant_land`
- `is_multifamily`
- `is_owner_occupied_proxy`
- `is_poor_condition`
- `is_fair_or_worse_condition`
- `has_missing_condition`
- `total_value_num`
- `land_value_num`
- `living_area_num`
- `units_num`
- `year_built_num`

## First mart design

The first structural mart should be a **current snapshot tract feature table** rather than a monthly table.

Recommended output grain:

- one row per `geoid`

Recommended output name:

- `analytics.tract_assessment_features_current`

Multifamily classification note:

- use `property_class_code` as the primary multifamily indicator
- use `units >= 2` only as a secondary supplement
- do not rely on `units` alone

Recommended first feature set:

- `parcel_count`
- `residential_parcel_count`
- `residential_parcel_share`
- `multifamily_parcel_count`
- `multifamily_share_of_residential`
- `residential_vacant_land_count`
- `residential_vacant_land_share`
- `owner_occupied_proxy_share`
- `non_owner_occupied_proxy_share`
- `poor_condition_share`
- `fair_or_worse_condition_share`
- `missing_condition_share`
- `avg_total_value`
- `avg_residential_total_value`
- `avg_land_value`
- `avg_residential_living_area`
- `avg_residential_units`
- `pre_1940_residential_share`

## Suggested implementation order

1. create cleaned parcel staging query
2. validate tract coverage against the existing tract universe
3. create the first `analytics.tract_assessment_features_current` mart
4. inspect correlation with:
   - `housing_instability_score_v2`
   - `combined_trajectory_score`
   - `future_distress_*`
5. decide which features graduate into the ML feature pipeline

## Bottom line

The assessment roll is ready for tract-level structural feature engineering now.

The right first move is:

- direct join on `geoid20_tract`
- dedupe on `print_key`
- filter to the existing tract universe
- do **not** rely on the raw neighborhood field

That gets us to the first structural mart quickly, with low join risk and very little additional preprocessing.
