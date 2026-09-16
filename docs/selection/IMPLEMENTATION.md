# Implementation details frozen before ML fitting

The original candidate list and selection rule in docs/baselines/protocol.json are unchanged.
Ridge uses the deterministic lsqr solver, tolerance 1e-6 and maximum 10,000 iterations. All numeric missingness indicators exist even when a field is complete in a fitting fold; an entirely missing column is filled with zero. Median imputation and scaling are fitted in each fold. One-hot output is dense for both algorithms. HistGradientBoosting categorical_features=None because categoricals are already one-hot encoded. Unknown categories become all-zero vectors. No rare-category aggregation is used. Thread pools are limited to two threads for local resource control.

Versioned requirements-model-lock.txt adds scikit-learn and its dependencies while preserving all EDA package pins. models.py and the dependency lock have LF endings to preserve provenance hashes across checkouts. Tests passed before actual-data fitting. Validation is loaded only after selection and fitting of the frozen chosen configuration; final-test targets are excluded from this delivery.
## Numerical output amendment before completing comparison

The first run stopped at host-CV HistGB property fold 1 because a prediction was negative. Completed Ridge OOF files and the interrupted run metadata remain private in selection-pre-floor. The nonnegative price domain is now enforced for HistGB as well as Ridge: maximum(0, prediction). No hyperparameter, fold, loss or selection criterion changed. The complete comparison is rerun under the amended code hash; neither external validation nor final test had been used. This is a recorded post-failure output correction, not an originally declared HistGB rule.
