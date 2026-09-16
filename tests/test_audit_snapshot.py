import csv
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_snapshot


class SnapshotAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raw = Path(self.temp.name)
        self.columns = sorted(audit_snapshot.REQUIRED)
        self.row = {key: '1' for key in self.columns}
        self.row.update(id='001', host_id='002', price='$1,200.50',
                        latitude='-22.9', longitude='-43.2',
                        neighbourhood_cleansed='Fictional', last_scraped='2026-06-25')
        (self.raw / 'neighbourhoods.geojson').write_text(json.dumps({
            'type': 'FeatureCollection', 'features': [
                {'properties': {'neighbourhood': 'Fictional'}}]}), encoding='utf-8')
        patcher = patch.object(audit_snapshot, 'RAW', self.raw)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_rows(self, rows):
        with gzip.open(self.raw / 'listings.csv.gz', 'wt', encoding='utf-8', newline='') as out:
            writer = csv.DictWriter(out, fieldnames=self.columns)
            writer.writeheader()
            writer.writerows(rows)

    def test_reports_quality_without_exporting_individual_rows(self):
        second = dict(self.row, id='003', price='', latitude='nan', bedrooms='')
        self.write_rows([self.row, second])
        result = audit_snapshot.audit()
        report = result['structural_audit']
        self.assertEqual(report['rows'], 2)
        self.assertEqual(report['unique_hosts'], 1)
        self.assertEqual(report['price_status'], {'missing': 1, 'positive': 1})
        self.assertEqual(report['invalid_world_coordinates'], 1)
        self.assertEqual(report['missing_candidate_features']['bedrooms'], 1)
        self.assertNotIn('Fictional', json.dumps(result))

    def test_rejects_duplicate_listing_ids(self):
        self.write_rows([self.row, self.row])
        with self.assertRaisesRegex(ValueError, 'duplicate listing'):
            audit_snapshot.audit()

    def test_rejects_missing_required_column(self):
        self.columns.remove('host_id')
        self.write_rows([{key: self.row[key] for key in self.columns}])
        with self.assertRaisesRegex(ValueError, 'required columns'):
            audit_snapshot.audit()

    def test_rejects_truncated_csv_row(self):
        with gzip.open(self.raw / 'listings.csv.gz', 'wt', encoding='utf-8') as out:
            out.write(','.join(self.columns) + '\n1,2\n')
        with self.assertRaisesRegex(ValueError, 'malformed CSV'):
            audit_snapshot.audit()

    def test_flags_invalid_and_nonpositive_prices(self):
        rows = [dict(self.row, id=str(i + 1), price=value)
                for i, value in enumerate(['$0.00', '$1,2.00', 'Infinity'])]
        self.write_rows(rows)
        self.assertEqual(audit_snapshot.audit()['structural_audit']['price_status'],
                         {'malformed': 2, 'nonpositive': 1})


if __name__ == '__main__':
    unittest.main()