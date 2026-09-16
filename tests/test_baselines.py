import unittest
import numpy as np
import pandas as pd
from rio.baselines import folds, predict_medians, metrics, bootstrap_mean, evaluate


class BaselineTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame({'id': [str(i) for i in range(100)],
                             'host_id': [str(i // 2) for i in range(100)],
                             'neighbourhood_cleansed': [str(i % 10) for i in range(100)],
                             'room_type': ['Entire home/apt']*100,
                             'target': np.arange(100, 200, dtype=float)})

    def test_room_median_uses_only_fitting_targets_and_falls_back(self):
        fit = pd.DataFrame({'room_type':['A','A','B'], 'target':[10.,30.,90.]})
        result = predict_medians(fit, pd.Series(['A','B','unseen']))
        np.testing.assert_array_equal(result['room_median'], [20,90,30])
        np.testing.assert_array_equal(result['global_median'], [30,30,30])

    def test_host_folds_have_no_overlap_and_cover_every_row_once(self):
        frame = self.frame()
        seen = []
        for _, fit, held, purged in folds(frame, 'host', {}):
            self.assertFalse(set(frame.iloc[fit].host_id) & set(frame.iloc[held].host_id))
            self.assertEqual(purged, 0)
            seen.extend(held)
        self.assertEqual(sorted(seen), list(range(len(frame))))

    def test_spatial_folds_purge_hosts_crossing_neighbourhoods(self):
        frame = self.frame()
        purged_total = 0
        for _, fit, held, purged in folds(frame, 'spatial', {str(i):i % 5 for i in range(10)}):
            self.assertFalse(set(frame.iloc[fit].host_id) & set(frame.iloc[held].host_id))
            self.assertFalse(set(frame.iloc[fit].neighbourhood_cleansed) & set(frame.iloc[held].neighbourhood_cleansed))
            purged_total += purged
        self.assertGreater(purged_total, 0)
        with self.assertRaisesRegex(ValueError, 'mapping'):
            list(folds(frame, 'spatial', {}))

    def test_metrics_distinguish_listing_and_host_weights(self):
        result = metrics([100,100,100], [110,110,140], ['a','a','b'])
        self.assertEqual(result['mae_brl'], 20)
        self.assertEqual(result['host_weighted_mae_brl'], 25)
        self.assertEqual(result['median_absolute_error_brl'], 10)
        with self.assertRaises(ValueError):
            metrics([100], [float('nan')], ['a'])

    def test_host_bootstrap_preserves_constant_error(self):
        self.assertEqual(bootstrap_mean([2,2,2], ['a','a','b'], repeats=40), [2,2])

    def test_oof_predictions_are_not_in_sample_medians(self):
        frame = self.frame()
        report, private = evaluate(frame, 'host', {}, {'replicates':10, 'seed':42})
        self.assertEqual(report['coverage'], 1.0)
        self.assertEqual(len(private), len(frame))
        for _, fit, held, _ in folds(frame, 'host', {}):
            expected = float(frame.iloc[fit].target.median())
            np.testing.assert_array_equal(private.iloc[held].global_median.to_numpy(), np.full(len(held),expected))


if __name__ == '__main__':
    unittest.main()