# Study protocol — version 1, 2026-09-16

[Português](STUDY.pt-BR.md) · [Home](../README.md)

## Question and intended use

Estimate advertised nightly price from property attributes and geography for listings belonging to hosts absent from training, within the same Rio snapshot. Intended audience: analysts examining the short-term rental market and reviewers of an applied ML study. Outputs describe associations and predictive error, not investment returns, housing-market causality or pricing advice.

Unit: one listing ID in one snapshot. Target: `price`, interpreted as local-currency nightly price (BRL for Rio), following the [source dictionary](https://docs.google.com/spreadsheets/d/1iWCNJcSutYqpULSQHlNyGInUvHg2BoUGoNRIGa6Szc4/edit). The dollar marker alone is not evidence of USD. This is the listed price, not a total guest invoice or a booking transaction.

## Source and audit

Use the complete detailed listings file and neighbourhood GeoJSON linked in [snapshot.json](snapshot.json). Source: Inside Airbnb, snapshot label 2026-06-24; downloaded 2026-09-16. Actual scrape dates: June 25, June 26 and July 1. Do not silently substitute newer downloads. Check byte hashes before analysis.

The original code references 2023-09-22. That historical download has not been recovered or used here. The current download page lists quarterly availability for the recent year; this revision acquired exactly one snapshot. No temporal panel has been validated.

Audit results: 48,713 distinct listing IDs, 27,688 host IDs, 90 columns; 44,542 positive prices and 4,171 missing prices. No malformed or nonpositive nonmissing prices were found. All neighbourhood names match one of 160 GeoJSON features. Coordinates pass world-range checks only: polygon containment, geometry validity, CRS consistency and boundary ambiguity remain tasks for stage 3.2. Missing bathrooms: 7,424; bedrooms: 7,099; beds: 5,282; minimum nights: 7.

The audit reads all rows and verifies CSV shape, required column names and identifier validity/uniqueness. It reports other quality issues rather than certifying model readiness. It does not inspect price distributions, rank features or consume a model test set.

## Data contract and feature policy

| Fields | Role and rule |
|---|---|
| `id`, `host_id` | Nonempty digit strings; unique listing ID. Preserve as strings. Host ID controls partitions, never a predictor. |
| `last_scraped` | Observation-date provenance; retain separately from snapshot label. |
| `price` | Parse source formatting, require finite positive target. Exclude missing/invalid targets from supervised learning; retain exclusion counts. Never impute the target. |
| `room_type`, `property_type`, `accommodates`, `bedrooms`, `beds`, `bathrooms`, `minimum_nights` | Initial property-only feature set. Validate types and ranges, encode unknown categories safely, fit imputation only on training folds. |
| `latitude`, `longitude`, `neighbourhood_cleansed` | Geographic extension for an ablation against the property-only model. Validate spatial alignment first. |
| All remaining fields | Excluded by default. Any feature extension requires a documented protocol revision. |

Exclude IDs, names, URLs, free text, host biography, reviews, calendar prices, inferred income/occupancy and any target-derived statistic computed outside training folds. Amenities and review scores are not part of the initial feature set. Geographic coefficients or importance are not causal effects.

Do not reuse historical quantile trimming: valid expensive listings belong to the population. Any necessary validity rule must be declared using source semantics before model comparison. Training-only transformations can address skew; evaluate predictions in original BRL as well.

No independent `head(1000)` sampling. Initial study uses all listings. If calendar/review extensions become necessary, first select listing IDs, then filter related tables by those IDs and compatible dates; check orphan keys, calendar `(listing_id, date)` uniqueness and review IDs. Aggregate child tables before joining to prevent row multiplication. These extensions are not yet acquired or implemented.

## Evaluation plan — implement before exploratory analysis

1. After structural eligibility checks, assign each host deterministically with SHA256 of UTF-8 `rio-v1|` plus its original `host_id`. Interpret the first eight digest bytes as an unsigned big-endian integer, divided by 2**64. Values below 0.70 go to training, below 0.85 to validation, the rest to final test. All listings from a host inherit the assignment. Fractions are approximate by host, not exact by row.
2. Save the source hash, protocol version, partition counts and a private listing-to-partition manifest. Assert zero listing/host overlap and nonempty partitions. Investigate structural failures without choosing a seed based on target distributions. Explore training data only; use validation for explicit model selection. Do not plot final-test targets or adjust decisions from final-test summaries.
3. Compare training-median and room-type median baselines (global fallback), a regularized model and one tree-based candidate. All learned preprocessing stays inside host-grouped cross-validation on training data. Fix the small candidate list and selection rule in stage 3.3 before fitting.
4. Primary metric: listing-weighted MAE in BRL. Also report median absolute error, RMSE, log-scale error, host-weighted MAE and a host-cluster bootstrap interval. Report coverage and eligible counts. Inspect development errors by room type and neighbourhood; publish aggregates only for groups with at least 30 listings and 10 hosts.
5. Secondary spatial stress test: on development data only, use five deterministic neighbourhood-group folds; purge training hosts appearing in each evaluation fold. Keep neighbourhoods intact, report training/evaluation coverage and acknowledge nearby-area dependence. This measures transfer to held-out neighbourhoods, not future time periods. Specify and freeze the neighbourhood-to-fold mapping before fitting in stage 3.3.
6. Freeze features, transformations, hyperparameters and selection rule before evaluating the final host-held-out test once. That test supports same-snapshot unseen-host performance only. Future-price claims require separately acquired, temporally ordered snapshots and an entity-overlap policy.

Stage 3.2 update: the split is now created and frozen in [partition metadata](eda/partitions.json). Training-only EDA and spatial validation are documented in [EDA.md](EDA.md). The target-presence check establishes eligibility; missing predictors do not remove listings. Stage 3.3a update: two median baselines have been evaluated within training folds; see [BASELINES.md](BASELINES.md) for the frozen comparison protocol. Stage 3.3b: the four ML candidates have been compared; histgb_geo was selected and external validation evaluated once. See [SELECTION.md](SELECTION.md). The trained artifact is frozen and final test remains reserved.

## Source conditions and publication

[Inside Airbnb downloads](https://insideairbnb.com/get-the-data/) identify the dataset as CC BY 4.0. Its [data policies](https://insideairbnb.com/data-policies/) request attribution, minimal acquisition, downloading once and avoiding republication. Keep raw files and individual derived rows local; publish source URLs, hashes, code and aggregate findings. No paid archive requests are needed for this scope.

The [source assumptions](https://insideairbnb.com/data-assumptions/) explain that coordinates are displaced and unavailable dates do not distinguish bookings from host blocks. Avoid precise address interpretation, individual host identification and occupancy/revenue claims. Existing academic notebooks and reports remain historical artifacts; this revision does not certify or republish their outputs as current findings.

## Acceptance and next delivery

Stage 3.1 delivers this scope, source manifest, structural audit and bilingual entry points. Stage 3.2 must create/check partitions, validate spatial inputs, investigate training-set missingness and selection bias, then produce aggregate EDA and maps. Stage 3.3 implements the frozen evaluation plan. Stage 3.4 packages the report and demonstration.