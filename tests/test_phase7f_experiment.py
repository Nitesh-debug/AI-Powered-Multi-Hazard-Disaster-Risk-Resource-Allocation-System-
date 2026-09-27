from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from scripts import train_phase7d_baselines as phase7d
from scripts import tune_phase7f_models as phase7f


class Phase7FExperimentTests(unittest.TestCase):
    def test_expanding_date_folds_keep_each_date_cohort_together(self) -> None:
        dates = pd.Series(np.repeat(pd.date_range("2020-01-01", periods=16), 20))
        folds = phase7f.blocked_date_splits(dates)
        self.assertEqual(len(folds), 3)
        for train_indexes, validation_indexes in folds:
            train_dates = set(dates.iloc[train_indexes])
            validation_dates = set(dates.iloc[validation_indexes])
            self.assertTrue(train_dates.isdisjoint(validation_dates))
            self.assertLess(max(train_dates), min(validation_dates))
            self.assertEqual(len(validation_indexes) % 20, 0)

    def test_boosted_imbalance_weight_uses_current_fit_labels(self) -> None:
        labels = np.asarray([1] * 3 + [0] * 9, dtype=np.int8)
        xgb = phase7f.build_boosted_estimator("xgboost", {"n_estimators": 2}, labels)
        lgbm = phase7f.build_boosted_estimator("lightgbm", {"n_estimators": 2}, labels)
        self.assertEqual(xgb.get_params()["scale_pos_weight"], 3.0)
        self.assertEqual(lgbm.get_params()["scale_pos_weight"], 3.0)

    def test_threshold_search_uses_only_supplied_validation_scores(self) -> None:
        labels = np.asarray([0, 0, 0, 1, 1, 1], dtype=np.int8)
        scores = np.asarray([0.01, 0.10, 0.20, 0.70, 0.80, 0.90])
        selected, rows = phase7f.choose_threshold(labels, scores)
        self.assertEqual(len(rows), len(phase7f.THRESHOLDS))
        self.assertIn(selected["threshold"], phase7f.THRESHOLDS)
        self.assertEqual(selected["f1"], 1.0)

    def test_data_loader_exposes_only_train_and_validation_prefix(self) -> None:
        target = next(iter(phase7d.HAZARDS))
        frame, features, _ = phase7d.load_train_validation(target)
        self.assertEqual(len(frame), phase7d.READ_ROWS)
        self.assertEqual(set(frame.split.unique()), {"train", "validation"})
        self.assertEqual(len(features), 68)
        self.assertTrue(frame.feature_reference_date.eq(frame.target_date - pd.Timedelta(days=1)).all())

    def test_preserved_reference_matrix_is_complete(self) -> None:
        references = phase7f.reference_metrics()
        self.assertEqual(len(references), 6 * 7)
        self.assertEqual(references[("flood", "xgboost")]["experiment"], "phase7d_xgb_lgbm_v1")


if __name__ == "__main__":
    unittest.main()
