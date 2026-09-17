# Final evaluation protocol — frozen before test access, 2026-09-17

Evaluate the exact histgb_geo artifact identified by docs/selection/selected_artifact.json, SHA256 a68512f4942bf396ccd0452496edd409334827043416927272d42512161d3a32. Preserve the recorded nonnegative output correction. Do not fit or modify the selected pipeline; do not rerank candidates or revise preprocessing from final results.

Population: the existing rio-v1 test partition, finite positive advertised prices. Expected 6,515 eligible listings / 3,827 hosts, from 7,094 total listings. Do not trim high prices. Missing targets remain excluded, not imputed. Verify exact ID/host membership and no overlap with other partitions.

Primary: listing-weighted MAE in BRL. Also median absolute error, RMSE, RMSLE and equal-host-weighted MAE. Compare with room-type medians computed exclusively from the frozen training partition, using global training median for unseen room types. Report 95% percentile intervals from 1,000 host-cluster resamples (seed 42), for selected MAE and paired selected-minus-reference MAE. Fixed predictions: intervals exclude model-refit uncertainty and dependence between different hosts.

Segments: room_type and neighbourhood_cleansed, report only groups with >=30 eligible listings and >=10 distinct hosts. Report suppressed-group counts. Interpret segment errors as diagnostics, not causal evidence or a reason for new tuning.

Verify hashes of model, manifests, training data, source files, assignments, implementation and dependency lock, installed package versions, Python version and actual estimator configuration before reading test targets. Write an exclusive test-start marker before accessing targets. Save individual predictions privately before summarization. No second prediction run: interrupted report generation can read hash-verified saved predictions. Consider the test consumed after access starts, even if interrupted. Report final findings separately from validation.

No new hyperparameters, models, thresholds or feature changes are authorized by this evaluation protocol. Next delivery uses this same artifact for inference/examples and packaging.