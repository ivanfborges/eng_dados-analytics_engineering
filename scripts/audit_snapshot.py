import csv, gzip, hashlib, json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/2026-06-24'
REQUIRED = {'id', 'host_id', 'last_scraped', 'price', 'latitude', 'longitude', 'neighbourhood_cleansed', 'room_type', 'property_type', 'accommodates', 'bedrooms', 'beds', 'bathrooms', 'minimum_nights'}

def audit():
    path = RAW / 'listings.csv.gz'
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        if not columns or len(columns) != len(set(columns)) or REQUIRED - set(columns):
            raise ValueError('Missing or duplicate required columns')
        rows = list(reader)
    if not rows or any(None in row or None in row.values() for row in rows):
        raise ValueError('Empty or malformed CSV')
    ids = [r['id'] for r in rows]
    hosts = [r['host_id'] for r in rows]
    if any(not re.fullmatch(r'[0-9]+', value) for value in ids + hosts) or len(ids) != len(set(ids)):
        raise ValueError('Invalid identifiers or duplicate listing IDs')
    geo = json.loads((RAW / 'neighbourhoods.geojson').read_text(encoding='utf-8'))
    if geo['type'] != 'FeatureCollection' or not geo['features']:
        raise ValueError('Invalid neighbourhood collection')
    names = {f['properties']['neighbourhood'] for f in geo['features']}
    price_status = Counter()
    for row in rows:
        value = row['price'].strip()
        if not value:
            price_status['missing'] += 1
        elif not re.fullmatch(r'\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?', value):
            price_status['malformed'] += 1
        elif float(value.replace('$','').replace(',','')) <= 0:
            price_status['nonpositive'] += 1
        else:
            price_status['positive'] += 1
    invalid_coords = 0
    for row in rows:
        try:
            lat, lon = float(row['latitude']), float(row['longitude'])
            valid = -90 <= lat <= 90 and -180 <= lon <= 180
        except ValueError:
            valid = False
        invalid_coords += not valid
    sources = []
    for filename, folder in [('listings.csv.gz','data'), ('neighbourhoods.geojson','visualisations')]:
        content = (RAW / filename).read_bytes()
        sources.append({'file':filename,'url':f'https://data.insideairbnb.com/brazil/rj/rio-de-janeiro/2026-06-24/{folder}/{filename}', 'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    return {'snapshot':'2026-06-24','retrieved_on':'2026-09-16','source':'Inside Airbnb','license':'CC BY 4.0','sources':sources,'structural_audit':{'rows':len(rows),'columns':len(columns),'unique_listing_ids':len(set(ids)),'unique_hosts':len(set(hosts)),'scrape_dates':dict(sorted(Counter(r['last_scraped'] for r in rows).items())),'price_status':dict(sorted(price_status.items())),'invalid_world_coordinates':invalid_coords,'neighbourhood_features':len(geo['features']),'rows_without_matching_neighbourhood_name':sum(r['neighbourhood_cleansed'] not in names for r in rows),'missing_candidate_features':{c:sum(not r[c].strip() for r in rows) for c in sorted(REQUIRED - {'price'})}},'scope':'Structural checks only; no EDA, model fitting or holdout evaluation.'}

if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, ensure_ascii=False))