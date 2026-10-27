import unittest

from ultrasonic_lab.evaluation import aggregate_specimens, evaluate, fit_threshold
from ultrasonic_lab.synthetic import generate_dataset


class EvaluationTests(unittest.TestCase):
    def test_calibration_cannot_consume_test_or_reflector_labels(self):
        rows = [
            {"specimen_id": f"cal-{i}", "split": "calibration", "label": 0, "score": i / 100}
            for i in range(20)
        ]
        self.assertAlmostEqual(fit_threshold(rows), 0.19)
        for changed in [{**rows[0], "split": "evaluation"}, {**rows[0], "label": 1}]:
            with self.assertRaises(ValueError):
                fit_threshold([*rows[1:], changed])

    def test_indeterminate_specimens_have_explicit_denominators(self):
        rows = [
            {"specimen_id": str(i), "split": "evaluation", "label": label, "score": score}
            for i, (label, score) in enumerate([(0, 0.1), (0, 0.8), (1, 0.9), (1, None)])
        ]
        result = evaluate(rows, 0.5)
        self.assertEqual(result["confusion"], {"tn": 1, "fp": 1, "fn": 0, "tp": 1})
        self.assertEqual(result["determinate_specimens"], 3)
        self.assertEqual(result["indeterminate_by_label"], {"normal": 0, "reflector": 1})
        self.assertEqual(result["sensitivity_denominator"], 1)
        self.assertEqual(result["false_positive_rate_denominator"], 2)
        self.assertEqual(result["coverage"], 0.75)
        all_missing = evaluate([{**rows[0], "score": None}], 0.5)
        self.assertIsNone(all_missing["sensitivity"])
        self.assertIsNone(all_missing["false_positive_rate"])

    def test_specimen_aggregation_requires_two_valid_repeats_and_same_split_label(self):
        rows = [
            {"specimen_id": "s1", "split": "evaluation", "label": 1, "repeat": i, "score": score}
            for i, score in enumerate([0.2, 0.4, None])
        ]
        self.assertAlmostEqual(aggregate_specimens(rows)[0]["score"], 0.3)
        rows[1]["score"] = None
        self.assertIsNone(aggregate_specimens(rows)[0]["score"])
        with self.assertRaises(ValueError):
            aggregate_specimens([rows[0], {**rows[1], "split": "calibration"}])

    def test_synthetic_generator_is_reproducible_and_specimens_do_not_cross_splits(self):
        first, second = generate_dataset(), generate_dataset()
        self.assertEqual(len(first), 552)
        seen = {}
        for a, b in zip(first, second, strict=True):
            self.assertEqual(a["specimen_id"], b["specimen_id"])
            self.assertEqual(a["volts"].tobytes(), b["volts"].tobytes())
            self.assertEqual(seen.setdefault(a["specimen_id"], a["split"]), a["split"])
        self.assertEqual(len(seen), 184)
        calibration = [x for x in first if x["split"] == "calibration"]
        self.assertTrue(all(x["label"] == 0 for x in calibration))


if __name__ == "__main__":
    unittest.main()
