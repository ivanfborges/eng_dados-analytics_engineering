# Rio de Janeiro Airbnb: listed prices and geography

[Português](README.pt-BR.md)

An applied data science study asking: **how well can property characteristics and location estimate advertised nightly prices for listings from hosts unseen during training, within one Rio de Janeiro snapshot?**

**Status:** training EDA and two out-of-fold median baselines complete; host partitions and the ML comparison protocol are frozen. The four ML candidates are next. The final test remains reserved; no predictive performance or production deployment is claimed.

The June 24, 2026 Inside Airbnb snapshot contains 48,713 listings and 27,688 hosts. Prices are present and positive for 44,542 listings; 4,171 lack a price. Snapshot labels are not observation timestamps: actual scrape dates range from June 25 to July 1. These are structural checks, not model results.

## Read the study

- [Baselines, uncertainty and frozen model comparison](docs/BASELINES.md)
- [Training exploration: findings, maps and reproducible execution](docs/EDA.md)
- [Study protocol, data contract and evaluation plan](docs/STUDY.md)
- [Source manifest and structural audit](docs/snapshot.json)
- [Original academic description, preserved in Portuguese](docs/ACADEMIC-ORIGINAL.pt-BR.md)

## Reproduce the source audit

Python 3.11 or later; standard library only. Download each file **once** from the exact URLs in `docs/snapshot.json`, then place them in:

```text
data/raw/2026-06-24/listings.csv.gz
data/raw/2026-06-24/neighbourhoods.geojson
```

```sh
python scripts/audit_snapshot.py
```

Compare file hashes and counts with the manifest. A changed upstream file is a new source version and requires review. The recorded retrieval date describes the original acquisition, not the time you rerun the audit. Raw files are ignored by Git. No PostgreSQL server or historical dependencies are needed for this audit.

## Training findings

Median listed price: BRL 454.97; mean: BRL 875.69. Missing prices affect 8.45% of training listings and coincide with much greater missingness in beds and bathrooms. The map covers 53 neighbourhoods with sufficient support. These are descriptive training results, not model performance.

![Training neighbourhood medians](docs/eda/neighbourhood_prices.png)

See the [EDA report](docs/EDA.md) for population limits, geometry repair, frozen partitions and the isolated environment used by the synthetic tests.

## Academic foundation and current scope

This repository began as a postgraduate analytics engineering study using PostgreSQL, Docker, dbt, Great Expectations and notebooks. Those files remain available as historical material; their workflows have not been rerun or validated in this revision. The old importer independently reads the first 1,000 rows of each table, which does not guarantee representative or relationally consistent samples. The new study uses the complete listings snapshot and does not inherit that sampling procedure.

The new analysis will separate hosts between training and evaluation, compare simple baselines with ML, and test whether geography adds useful predictive information. Spatial transfer will be assessed separately. There is no future-price forecast or causal claim in the current design.

## Data and limits

Data: [Inside Airbnb](https://insideairbnb.com/get-the-data/), distributed under CC BY 4.0. Consult its [data policies](https://insideairbnb.com/data-policies/), [assumptions](https://insideairbnb.com/data-assumptions/) and [dictionary](https://docs.google.com/spreadsheets/d/1iWCNJcSutYqpULSQHlNyGInUvHg2BoUGoNRIGa6Szc4/edit).

Advertised price is not transaction price, revenue or an optimal pricing recommendation. Calendar unavailability cannot establish bookings. Coordinates are approximate. New outputs will contain aggregate analysis rather than host identities, review text or individual listing maps. The source license does not establish a license for this repository's code.