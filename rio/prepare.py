"""Frozen host split; only the training export contains target values."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/2026-06-24'
OUTPUT = ROOT / 'data/processed/rio-v1'
FEATURES = ['room_type', 'property_type', 'accommodates', 'bedrooms', 'beds',
            'bathrooms', 'minimum_nights', 'latitude', 'longitude', 'neighbourhood_cleansed']
FIELDS = ['id', 'host_id', 'last_scraped', 'price'] + FEATURES
PRICE_PATTERN = re.compile(r'\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def host_partition(host_id):
    if not re.fullmatch(r'[0-9]+', host_id):
        raise ValueError('Invalid host identifier')
    value = int.from_bytes(hashlib.sha256(('rio-v1|' + host_id).encode()).digest()[:8], 'big') / 2**64
    return 'train' if value < .70 else 'validation' if value < .85 else 'test'


def price_value(text):
    value = text.strip()
    if not PRICE_PATTERN.fullmatch(value):
        return None
    number = float(value.replace('$', '').replace(',', ''))
    return number if math.isfinite(number) and number > 0 else None


def check_sources(raw=RAW):
    manifest = json.loads((ROOT / 'docs/snapshot.json').read_text(encoding='utf-8'))
    for source in manifest['sources']:
        if digest(raw / source['file']) != source['sha256']:
            raise ValueError('Source hash mismatch: ' + source['file'])
    return manifest


def partition_rows(rows):
    assignments, training = [], []
    ids = set()
    for row in rows:
        listing_id = row['id']
        if not re.fullmatch(r'[0-9]+', listing_id) or listing_id in ids:
            raise ValueError('Invalid or duplicate listing ID')
        ids.add(listing_id)
        split = host_partition(row['host_id'])
        eligible = price_value(row['price']) is not None
        assignments.append({'id': listing_id, 'host_id': row['host_id'],
                            'partition': split, 'eligible_target': str(int(eligible))})
        if split == 'train':
            training.append({key: row[key] for key in FIELDS})
    return assignments, training


def csv_bytes(rows, fields):
    import io
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda row: row['id']))
    return out.getvalue().encode('utf-8')


def save_immutable(path, content):
    if path.exists() and path.read_bytes() != content:
        raise ValueError('Refusing to replace frozen artifact: ' + path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)


def main():
    sources = check_sources()
    with gzip.open(RAW / 'listings.csv.gz', 'rt', encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or set(FIELDS) - set(reader.fieldnames):
            raise ValueError('Invalid input schema')
        rows = list(reader)
        if any(None in row or None in row.values() for row in rows):
            raise ValueError('Malformed CSV')
    assignments, training = partition_rows(rows)
    counts = {}
    host_sets = []
    for split in ['train', 'validation', 'test']:
        subset = [r for r in assignments if r['partition'] == split]
        hosts = {r['host_id'] for r in subset}
        eligible = [r for r in subset if r['eligible_target'] == '1']
        if not hosts or not eligible:
            raise ValueError('Empty partition')
        host_sets.append(hosts)
        counts[split] = {'rows': len(subset), 'hosts': len(hosts),
                         'eligible_rows': len(eligible),
                         'eligible_hosts': len({r['host_id'] for r in eligible})}
    if any(host_sets[i] & host_sets[j] for i in range(3) for j in range(i)):
        raise ValueError('Host overlap')
    files = {'assignments.csv': csv_bytes(assignments, ['id', 'host_id', 'partition', 'eligible_target']),
             'train.csv': csv_bytes(training, FIELDS)}
    metadata = {'protocol': 'rio-v1', 'source_hashes': {s['file']: s['sha256'] for s in sources['sources']},
                'counts': counts, 'host_overlap': 0,
                'artifacts': {name: hashlib.sha256(value).hexdigest() for name, value in files.items()},
                'eligibility': 'Finite positive price; missing predictors retained for training-only imputation.',
                'test_status': 'Reserved; no target summaries or model evaluation.'}
    for name, content in files.items():
        save_immutable(OUTPUT / name, content)
    encoded = (json.dumps(metadata, indent=2) + '\n').encode()
    save_immutable(OUTPUT / 'partitions.json', encoded)
    print(encoded.decode())


if __name__ == '__main__':
    main()