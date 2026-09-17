import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
from rio.predict import COLUMNS, ROOT, load_frozen, read_input, write_predictions


class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'input.csv'
        self.frame = read_input(ROOT / 'examples/fictional_listings.csv')

    def save(self, frame=None):
        (self.frame if frame is None else frame).to_csv(self.path, index=False)
        return self.path

    def test_missing_and_unknown_fields_preserve_case_order(self):
        self.assertEqual(self.frame.case_id.tolist(), ['fictional-001', 'fictional-002', 'fictional-003'])
        self.assertEqual(self.frame.iloc[2].bedrooms, '')
        self.assertEqual(self.frame.iloc[2].property_type, 'Imaginary property category')

    def test_exact_schema_rejects_target_missing_and_duplicate_columns(self):
        for columns in [COLUMNS + ['price'], COLUMNS[:-1], COLUMNS[:-1] + ['case_id']]:
            with self.subTest(columns=columns):
                self.path.write_text(','.join(columns) + '\n', encoding='utf-8')
                with self.assertRaises(ValueError):
                    read_input(self.path)

    def test_duplicate_or_empty_ids(self):
        for value in ['', 'fictional-001']:
            frame = self.frame.copy()
            frame.loc[1, 'case_id'] = value
            with self.assertRaises(ValueError):
                read_input(self.save(frame))

    def test_numeric_contract(self):
        for field, value in [('beds', '1.5'), ('bathrooms', '-1'), ('accommodates', '0'),
                             ('latitude', '91'), ('longitude', '-181'), ('beds', 'NaN'),
                             ('bedrooms', 'inf'), ('minimum_nights', 'text')]:
            with self.subTest(field=field, value=value):
                frame = self.frame.copy()
                frame.loc[0, field] = value
                with self.assertRaises(ValueError):
                    read_input(self.save(frame))

    def test_empty_and_malformed_rows(self):
        for body in ['', 'too,few,fields\n']:
            self.path.write_text(','.join(COLUMNS) + '\n' + body, encoding='utf-8')
            with self.assertRaises(ValueError):
                read_input(self.path)

    def test_wrong_hash_rejected_before_deserialization(self):
        self.path.write_bytes(b'not a model')
        with patch('rio.predict.joblib.load') as deserialize:
            with self.assertRaisesRegex(ValueError, 'Hash mismatch'):
                load_frozen(self.path)
            deserialize.assert_not_called()

    def test_predict_only_excludes_id_and_preserves_order(self):
        model = Mock()
        model.predict.return_value = np.array([125.125, 0, 500])
        write_predictions(model, self.frame, self.path)
        model.fit.assert_not_called()
        self.assertNotIn('case_id', model.predict.call_args.args[0].columns)
        with self.path.open(newline='', encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row['case_id'] for row in rows], self.frame.case_id.tolist())
        self.assertEqual(rows[1]['estimated_nightly_price_brl'], '0.00')

    def test_invalid_predictions_do_not_write(self):
        for values in [[1, 2], [1, -1, 2], [1, np.nan, 2], [1, np.inf, 2]]:
            model = Mock()
            model.predict.return_value = values
            with self.assertRaises(ValueError):
                write_predictions(model, self.frame, self.path)
            self.assertFalse(self.path.exists())

    def test_output_never_overwrites_input(self):
        self.save()
        original = self.path.read_bytes()
        model = Mock()
        model.predict.return_value = [1, 2, 3]
        with self.assertRaises(FileExistsError):
            write_predictions(model, self.frame, self.path)
        self.assertEqual(self.path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
