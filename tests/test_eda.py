import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from shapely.geometry import Polygon, mapping

from rio import prepare, eda


class PreparationTests(unittest.TestCase):
    def row(self, listing, host, price='$100.00'):
        row = {field: '' for field in prepare.FIELDS}
        row.update(id=listing, host_id=host, price=price)
        return row

    def test_split_is_order_independent_and_groups_hosts(self):
        rows = [self.row(str(i), str(i // 2)) for i in range(60)]
        forward, _ = prepare.partition_rows(rows)
        reverse, _ = prepare.partition_rows(reversed(rows))
        self.assertEqual({r['id']: r['partition'] for r in forward},
                         {r['id']: r['partition'] for r in reverse})
        hosts = {}
        for row in forward:
            hosts.setdefault(row['host_id'], set()).add(row['partition'])
        self.assertTrue(all(len(values) == 1 for values in hosts.values()))
        self.assertEqual({r['partition'] for r in forward}, {'train', 'validation', 'test'})

    def test_exact_protocol_and_leading_zero_preservation(self):
        for host in ['0', '01', '1234567890123456789']:
            expected_hash = hashlib.sha256(('rio-v1|' + host).encode('utf-8')).hexdigest()
            fraction = int(expected_hash[:16], 16) / 2**64
            expected = 'train' if fraction < .7 else 'validation' if fraction < .85 else 'test'
            self.assertEqual(prepare.host_partition(host), expected)
        assignments, _ = prepare.partition_rows([self.row('001', '01')])
        self.assertEqual(assignments[0]['id'], '001')
        self.assertEqual(assignments[0]['host_id'], '01')

    def test_training_export_excludes_other_partitions_and_keeps_missing_targets(self):
        hosts = {split: next(str(i) for i in range(100) if prepare.host_partition(str(i)) == split)
                 for split in ['train', 'validation', 'test']}
        rows = [self.row(str(i), host, '') for i, host in enumerate(hosts.values())]
        assignments, train = prepare.partition_rows(rows)
        self.assertEqual(len(train), 1)
        self.assertEqual(train[0]['host_id'], hosts['train'])
        self.assertTrue(all(r['eligible_target'] == '0' for r in assignments))
        self.assertNotIn('price', assignments[0])

    def test_invalid_identifiers_and_duplicate_listings_fail(self):
        for rows in [[self.row('1', 'x')], [self.row('1', '1'), self.row('1', '2')]]:
            with self.assertRaises(ValueError):
                prepare.partition_rows(rows)

    def test_target_parser_rejects_invalid_values_without_upper_price_cutoff(self):
        for value in ['', 'nan', 'Infinity', '-1', '$0.00', '$1,2.00']:
            self.assertIsNone(prepare.price_value(value))
        self.assertEqual(prepare.price_value('$1,000,000.00'), 1000000)

    def test_frozen_artifact_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'frozen.csv'
            prepare.save_immutable(path, b'original')
            prepare.save_immutable(path, b'original')
            with self.assertRaises(ValueError):
                prepare.save_immutable(path, b'changed')
            self.assertEqual(path.read_bytes(), b'original')


class ExplorationTests(unittest.TestCase):
    def test_spatial_boundaries_holes_and_invalid_coordinates(self):
        a = Polygon([(0,0),(2,0),(2,2),(0,2)], holes=[[(.5,.5),(1,.5),(1,1),(.5,1)]])
        b = Polygon([(2,0),(3,0),(3,2),(2,2)])
        frame = pd.DataFrame({'longitude': ['.2', '.75', '2', '2.5', 'nan'],
                              'latitude': ['.2', '.75', '1', '1', '1'],
                              'neighbourhood_cleansed': ['A'] * 5})
        self.assertEqual(eda.locate(frame, {'A': a, 'B': b}).tolist(),
                         ['consistent', 'outside_polygons', 'multiple_polygons',
                          'different_neighbourhood', 'invalid_coordinates'])

    def test_groups_require_distinct_hosts_and_priced_rows(self):
        frame = pd.DataFrame({'kind': ['A']*30 + ['B']*30 + ['C']*29,
                              'host_id': [str(i % 10) for i in range(30)] + ['one']*30 + [str(i) for i in range(29)],
                              'target': [100.0]*89})
        self.assertEqual([r['group'] for r in eda.aggregate_groups(frame, 'kind')], ['A'])
        frame.loc[0, 'target'] = float('nan')
        self.assertEqual(eda.aggregate_groups(frame, 'kind'), [])

    def test_numeric_rules_allow_zero_bedrooms_but_not_zero_capacity(self):
        frame = pd.DataFrame({k: ['0', '', '1.5'] for k in eda.NUMERIC})
        quality = eda.numeric_quality(frame)
        self.assertEqual(quality['bedrooms']['usable'], 1)
        self.assertEqual(quality['bathrooms']['usable'], 2)
        self.assertEqual(quality['accommodates']['invalid_nonmissing'], 2)

    def test_geojson_rejects_unreviewed_crs(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'geometry.json'
            path.write_text(json.dumps({'crs': {'name': 'EPSG:3857'}}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'CRS'):
                eda.load_geometries(path)

    def test_training_loader_rejects_nontraining_host_even_with_matching_hash(self):
        host = next(str(i) for i in range(100) if prepare.host_partition(str(i)) == 'test')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'docs/eda').mkdir(parents=True)
            (root/'train.csv').write_text(f'id,host_id\n1,{host}\n', encoding='utf-8')
            (root/'neighbourhoods.geojson').write_text('{}', encoding='utf-8')
            meta = {'artifacts': {'train.csv': prepare.digest(root/'train.csv')},
                    'source_hashes': {'neighbourhoods.geojson': prepare.digest(root/'neighbourhoods.geojson')},
                    'counts': {'train': {'rows': 1}}}
            (root/'docs/eda/partitions.json').write_text(json.dumps(meta), encoding='utf-8')
            with patch.object(eda, 'ROOT', root), patch.object(eda, 'RAW', root), patch.object(eda, 'OUTPUT', root):
                with self.assertRaisesRegex(ValueError, 'Non-training'):
                    eda.load_training()
                (root/'train.csv').write_text('changed', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'frozen manifest'):
                    eda.load_training()


if __name__ == '__main__':
    unittest.main()