Update 2026-09-17: [final evaluation completed](FINAL.md); final test consumed. Statements below about a reserved test describe the earlier development stage.

# Model selection and external validation

[Português](SELECTION.pt-BR.md) · [Protocol](baselines/protocol.json) · [Home](../README.md)

**Stage 3.3b complete. HistGradientBoosting with geography selected using training host-CV MAE. External validation evaluated once. Final test remains untouched.**

Training out-of-fold MAE was **BRL 445.07**, versus BRL 573.85 for the room-type median: 22.44% lower. Adding geography to the tree model reduced MAE from 475.70 to 445.07 (6.44%). These are development comparisons, not final-test or causal results.

![Candidate comparison](selection/comparison.png)

| Candidate | Host-CV MAE BRL | Spatial-CV MAE BRL |
|---|---:|---:|
| global_median | 584.42 | 600.94 |
| room_median | 573.85 | 592.14 |
| ridge_property | 520.35 | 555.61 |
| ridge_geo | 474.12 | 499.62 |
| histgb_property | 475.70 | 506.66 |
| histgb_geo | 445.07 | 485.78 |

All 31,636 eligible training listings receive one held-out prediction per design/candidate. Baseline results were reused. Five host folds separate fitting/evaluation hosts; five spatial folds also hold out neighbourhoods and purge shared hosts. Spatial folds are imbalanced, not contiguous or buffered; nearby-area dependence remains. See [baseline methodology](BASELINES.md).

Spatial MAE for the winner rises to 485.78. Geography helps these predefined candidates, but this does not establish transfer to arbitrary regions or future dates. Selecting the minimum of six CV scores also makes that score optimistic as a final estimate.

## Frozen pipeline and recorded correction

Configuration: absolute-error loss, 200 iterations, 15 leaves, learning rate 0.05, minimum leaf size 20, L2 1, no early stopping, seed 42. Numeric validity rules, median imputation and all-field missingness indicators operate inside fitting folds. Categories use one-hot encoding with unknown values ignored. IDs and target-derived aggregates are excluded. Ridge additionally standardizes numeric inputs and models log1p(price).

The initial run stopped on a negative prediction in HistGB property host fold 1. That attempt remains archived locally. HistGB predictions were then floored at zero, as already specified for Ridge. The complete comparison was rerun with a new code hash; folds, hyperparameters and selection rule were unchanged. This is an explicitly recorded post-failure implementation amendment, not an originally declared HistGB rule. Neither external holdout had been used. See [implementation record](selection/IMPLEMENTATION.md).

The winner was fitted on **31,636 training rows only**, serialized and hashed **before opening external validation**. No train+validation refit, re-ranking or expanded search occurred. The [artifact manifest](selection/selected_artifact.json) links model, decision, code and dependency hashes. Model bytes remain private.

## External validation: 6,391 listings / 3,699 hosts

| Metric | Selected model | Room-type median |
|---|---:|---:|
| MAE BRL | 434.08 | 548.00 |
| Median absolute error BRL | 123.55 | 181.71 |
| RMSE BRL | 2251.50 | 2460.72 |
| RMSLE | 0.6124 | 0.8035 |
| Host-weighted MAE BRL | 418.33 | 522.33 |

MAE reduction: **20.79%**. Selected-model MAE 95% host-bootstrap interval: [365.91, 506.29] BRL. Paired selected-minus-baseline difference: -113.93 BRL, interval [-144.25, -89.53]. Intervals use 1,000 host resamples, seed 42, fixed predictions; they exclude refitting uncertainty and dependence between different hosts. Different RMSE in training CV and validation reflects different samples, not temporal improvement.

## Error variation and limits

| Room type | Listings | Hosts | MAE BRL | RMSLE |
|---|---:|---:|---:|---:|
| Entire home/apt | 5127 | 3094 | 457.39 | 0.565 |
| Private room | 1180 | 738 | 343.48 | 0.752 |
| Shared room | 83 | 34 | 285.93 | 1.041 |

Shared rooms have higher relative/log error; their host-weighted MAE is BRL 477.44. Joá has validation MAE BRL 3,202.45 on 30 listings/16 hosts; São Conrado, BRL 1,810.68 on 104 listings/72 hosts. These supported groups still have uncertainty and mix property types/sizes. They are diagnostics, not causal effects or justification for further tuning.

[Validation aggregates](selection/validation.json) suppress groups with fewer than 30 eligible listings or 10 hosts: one room-type group and 90 neighbourhood groups. Missing prices and incomplete predictors limit representativeness, as shown in [EDA](EDA.md). Asking prices are not transactions, revenue or optimal pricing advice. The upper price tail remains untrimmed.

## Reproduction and boundaries

Use Python 3.11 and `requirements-model-lock.txt`, preserving EDA pins and adding scikit-learn 1.9.1 and dependencies. Tests use synthetic data; experiments require the exact source/train files from the earlier setup.

```sh
python -m pip install -r requirements-model-lock.txt
python -m unittest discover -s tests -v
# Fresh reproduction only, after preparing frozen source/train files:
python -m rio.selection
python -m rio.validate_selection
python -m rio.plot_selection
```

Experiment commands refuse existing outputs or previously started validation. On this workspace, inspect stored results rather than repeat training/validation. Validation filters hosts before parsing their prices and verifies exact membership against frozen assignments. No final-test loader exists in this delivery.

Thirty synthetic tests passed, covering fold-local preprocessing, unknown categories, new missingness, nonnegative output, selection ties and skipping non-validation rows before target access. [Comparison details](selection/comparison.json) include per-fold scores, uncertainty and provenance. Individual predictions, raw data, binary model and interrupted run remain ignored locally; only aggregates and plots are published.

Next: stage 3.3c, verify the frozen artifact and evaluate the final test once without refitting. Report final metrics and limitations separately from development results.
