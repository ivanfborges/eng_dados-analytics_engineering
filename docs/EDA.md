# Training exploration: prices, missingness and geography

[Português](EDA.pt-BR.md) · [Protocol](STUDY.md) · [Home](../README.md)

**Stage 3.2 complete. No model has been trained. The final test is reserved.**

The training data show a long price tail, unequal representation of hosts and substantial differences in data completeness. These findings guide the next experiment; they do not measure predictive performance or establish why prices differ.

## Frozen partitions

Hosts are assigned using the SHA256 rule declared before EDA in the protocol. Listing IDs remain strings. No host or listing is shared between partitions. Supervised eligibility requires a finite positive price; missing predictors do not remove an otherwise eligible listing. No upper price cutoff was applied.

| Partition | All listings | All hosts | Priced listings | Hosts with priced listings |
|---|---:|---:|---:|---:|
| Training | 34,557 | 19,455 | 31,636 | 17,912 |
| Validation | 7,062 | 4,083 | 6,391 | 3,699 |
| Final test | 7,094 | 4,150 | 6,515 | 3,827 |

[Partition metadata](eda/partitions.json) contains source/export hashes and aggregate counts. Individual assignments stay local. The preparation step checks target presence/validity for eligibility, but produces no validation/test target statistics or target-bearing exports. EDA reads only the hash-verified training export and neighbourhood geometry. It refuses non-training hosts or modified inputs.

## What the training data show

Among 31,636 priced listings, the median is **BRL 454.97**, the mean **BRL 875.69**, and the middle half spans **BRL 297–756**. The 99th percentile is BRL 7,411.14. These describe asking prices at collection, not transactions. No trimming was applied; unusually high values remain unverified asking prices, not validated market transactions.

![Training distribution and missing prices](eda/training_overview.png)

| Room type | Priced listings | Median BRL | Missing price among all listings of this type |
|---|---:|---:|---:|
| Entire home/apt | 25,673 | 490.71 | 8.32% |
| Private room | 5,495 | 297.00 | 9.37% |
| Shared room | 444 | 119.00 | 3.27% |

One room-type group was suppressed for insufficient support. Every published price group requires at least 30 priced listings and 10 distinct hosts. Listing counts weight the summaries: the largest 1% of eligible training hosts (180 hosts, rounded up) account for **16.97%** of priced listings. This supports reporting both listing-weighted and host-weighted errors later.

## Missingness and selection

2,921 of 34,557 training listings (**8.45%**) have no usable target. Attribute completeness differs sharply:

| Attribute | Missing among priced listings | Missing among listings without price |
|---|---:|---:|
| bedrooms | 14.77% | 15.41% |
| beds | 3.76% | 87.74% |
| bathrooms | 8.28% | 88.67% |

This is evidence of different observed data profiles, not a formal diagnosis of the missing-data mechanism. Removing rows without a target changes the represented population. Possible collection/availability effects need investigation; we cannot infer the unseen prices or claim that the model will generalize to these rows. Preserve missingness indicators and fit imputation inside training folds. Bedrooms/beds must be nonnegative integers; bathrooms nonnegative finite numbers; capacity/minimum nights positive integers. Invalid values become missing during future preprocessing; no observed nonmissing training values violated these rules.

## Spatial checks and coverage

The source contains 160 nonempty MultiPolygons. With no explicit CRS member, coordinates are interpreted as WGS84 longitude/latitude under [GeoJSON RFC 7946](https://www.rfc-editor.org/rfc/rfc7946). Listing coordinates follow the source dictionary. All coordinates and polygon bounds pass geographic range checks. This is consistency validation, not an independent survey of boundary accuracy.

Caju had one ring self-intersection. [Shapely make_valid](https://shapely.readthedocs.io/en/stable/reference/shapely.make_valid.html), using linework, produced a valid MultiPolygon; relative planar area change was 1.27e-15. Raw geometry remains unchanged. Repairs requiring non-polygon output or relative planar area change above 1e-8 fail for review. This degree-based ratio is only a repair diagnostic, not a land-area estimate.

The [covers predicate](https://shapely.readthedocs.io/en/stable/reference/shapely.covers.html) includes boundaries. Points intersecting multiple polygons, outside all polygons or inconsistent with their named neighbourhood are separately flagged. All **34,557 training points** match exactly one polygon with the source neighbourhood name; none are ambiguous. This does not establish exact addresses: source coordinates are approximate, and the neighbourhood labels themselves derive from coordinates.

![Neighbourhood median prices](eda/neighbourhood_prices.png)

The map shows **53 neighbourhoods**, representing **30,727 priced listings (97.13% of priced training listings)**. The other 107 polygons are grey because of insufficient support or no eligible training listings. Grey is not zero price or proof of no short-term rentals. The 909 priced listings outside publishable groups remain in the modeling population. Medians pool property types and sizes; the map cannot isolate a causal neighbourhood effect.

The six neighbourhoods with the most priced training listings are shown for orientation, not as a price ranking:

| Neighbourhood | Priced training listings | Median BRL |
|---|---:|---:|
| Copacabana | 9,938 | 452.67 |
| Ipanema | 2,584 | 696.23 |
| Barra da Tijuca | 2,393 | 640.00 |
| Centro | 2,137 | 278.00 |
| Recreio dos Bandeirantes | 1,603 | 457.00 |
| Botafogo | 1,328 | 384.33 |

## Reproduce

Python 3.11.14 was used. Create an isolated environment and install `requirements-eda-lock.txt`; the older `requirements.txt` belongs to the academic workflow.

```sh
python -m venv .venv
# Activate .venv using your shell, then:
python -m pip install -r requirements-eda-lock.txt
python -m unittest discover -s tests -v
python -m rio.prepare
python -m rio.eda
```

Obtain the two exact files in [snapshot.json](snapshot.json) once, as explained in the README. Preparation writes immutable files to `data/processed/rio-v1/`; rerunning identical inputs preserves their content and different content is refused. The checked-in partition metadata anchors the training export. EDA writes to `reports/generated/eda/`; publication of selected aggregate outputs is a separate review step. Raw files, assignments and individual rows are ignored by Git. Tests use synthetic data and require no source downloads.

[Machine-readable results](eda/summary.json) record package versions, missingness, publication support and geographic checks. All figures and summaries here derive from training only. Source: [Inside Airbnb](https://insideairbnb.com/get-the-data/), snapshot 2026-06-24, CC BY 4.0; see its [assumptions](https://insideairbnb.com/data-assumptions/). Dates unavailable in a calendar do not confirm bookings; asking prices do not establish revenue.

## Implications for stage 3.3

Compare the predefined baselines and a small frozen model set; test the added value of geography against property-only inputs. Keep all learned transforms inside grouped training folds. Freeze the spatial fold mapping and purge overlapping hosts before that secondary evaluation. Investigate error concentration and missingness, then choose using development data. Evaluate the reserved final test only after the complete decision is frozen. No future-time, causal or deployment claims are supported by this EDA.
