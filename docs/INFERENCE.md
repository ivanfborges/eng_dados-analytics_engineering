# Inference with the frozen model

[Português](INFERENCE.pt-BR.md) · [Study](../README.md) · [Final evaluation](FINAL.md)

This CLI estimates advertised nightly prices in BRL with the already fitted `histgb_geo` pipeline. It does not train, select or evaluate a model. Validation and final test are consumed. The binary and individual source data are not distributed.

## Public quickstart: no private data needed

From a clean checkout, use Python **3.11.14**, create an environment, and install the model lock (the root `requirements.txt` belongs to the historical academic project):

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell:
.venv/Scripts/Activate.ps1
python -m pip install -r requirements-model-lock.txt
python -m unittest discover -s tests -v
python -m rio.predict --input examples/fictional_listings.csv --check-input
```

Expected: 46 tests pass and `valid_cases: 3`. The tests use synthetic fixtures. Schema validation loads no model, raw snapshot or partition files. Read the public [illustrative predictions](../examples/fictional_predictions.csv) alongside their [fictional inputs](../examples/fictional_listings.csv). These three cases were invented for this interface; none was copied from an actual listing. They have no observed target, so they provide no accuracy evidence.

## Full inference: trusted local artifact required

The maintainer's local artifact is `reports/generated/selection/selected_pipeline.joblib`. An ordinary public clone does **not** contain it. There is no automatic download or retraining fallback. With access to that trusted artifact, use its explicit path and an unused output filename:

```sh
python -m rio.predict --input examples/fictional_listings.csv --model /path/to/selected_pipeline.joblib --output predictions.csv
```

The output preserves input order and `case_id`, with `estimated_nightly_price_brl` rounded to two decimals. Existing files are never overwritten; the parent directory must exist. Keep any predictions for real listings private (for example under the ignored `reports/generated/` directory).

Before deserialization, the CLI verifies the model SHA256 against the [frozen manifest](selection/selected_artifact.json), its links to the decision and validation records, the comparison, model implementation, protocol, lock file, Python version and installed package versions. Expected model SHA256: `a68512f4942bf396ccd0452496edd409334827043416927272d42512161d3a32`. It then checks the fitted estimator's parameters. Use only trusted joblib files; hashes establish consistency with trusted repository records, not independent authenticity. No training or holdout files are read.

## Input contract

UTF-8 comma-separated CSV, one header row, exactly these unique columns (column order may vary):

| Field | Accepted values |
|---|---|
| `case_id` | Nonempty unique string; preserved in output, excluded from model features |
| `accommodates`, `minimum_nights` | Integers >= 1, or blank |
| `bedrooms`, `beds` | Integers >= 0, or blank |
| `bathrooms` | Finite number >= 0, or blank |
| `latitude`, `longitude` | Finite WGS84 degrees in [-90,90] / [-180,180], or blank |
| `room_type`, `property_type`, `neighbourhood_cleansed` | Case-sensitive strings or blank; unknown categories accepted |

Use a dot for decimals and an empty cell for missing values. `NaN`, infinity, malformed numbers, duplicate IDs, inconsistent row lengths, extra columns (including prices or host IDs) and missing columns fail validation. Leading/trailing whitespace is stripped. Missing numeric values use the fitted training medians and missingness indicators; missing categories use the frozen missing token, and categories unseen during training produce all-zero one-hot blocks. The CLI rejects invalid numeric values rather than silently imputing them; valid/missing inputs use unchanged model preprocessing.

The first two examples illustrate ordinary property fields; the third deliberately exercises missing fields and invented categories. Its numerical output is only a software demonstration. Schema validation does not verify neighbourhood/coordinate consistency, geographic coverage, market plausibility or predictive reliability. World-coordinate bounds are format checks, not proof that the study applies outside Rio.

## Interpretation and limits

These estimates describe a single Rio snapshot, not future prices, transactions, revenue or optimal pricing. The final holdout MAE was BRL 482.67 (95% host-bootstrap interval 366.38–632.28), versus BRL 620.57 for the room-type baseline. This is an aggregate error measure, **not** a prediction interval for a new property. Errors vary substantially by segment and high-price outliers remain difficult. No production suitability or uncertainty guarantee for an individual prediction is established. See the [full final report](FINAL.md).

Checkout integrity: `.gitattributes` preserves the protocol's original CRLF bytes because its frozen hash was recorded in that form. This changes no protocol content or experimental decision. A regression test checks that hash in fresh checkouts.
