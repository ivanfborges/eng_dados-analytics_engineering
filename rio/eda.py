"""Training-only exploration. No validation/test target file is opened."""
import json
import math
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape
from shapely.plotting import patch_from_polygon

from rio.prepare import ROOT, RAW, OUTPUT, digest, host_partition, price_value

RESULTS = ROOT / 'reports/generated/eda'
NUMERIC = ['accommodates', 'bedrooms', 'beds', 'bathrooms', 'minimum_nights']


def load_training():
    frozen = json.loads((ROOT / 'docs/eda/partitions.json').read_text(encoding='utf-8'))
    if digest(OUTPUT / 'train.csv') != frozen['artifacts']['train.csv']:
        raise ValueError('Training export differs from frozen manifest')
    if digest(RAW / 'neighbourhoods.geojson') != frozen['source_hashes']['neighbourhoods.geojson']:
        raise ValueError('Geometry source differs from frozen manifest')
    frame = pd.read_csv(OUTPUT / 'train.csv', dtype=str, keep_default_na=False)
    if not frame['host_id'].map(host_partition).eq('train').all():
        raise ValueError('Non-training host in EDA input')
    if frame['id'].duplicated().any() or len(frame) != frozen['counts']['train']['rows']:
        raise ValueError('Invalid training export')
    return frame, frozen


def load_geometries(path):
    obj = json.loads(Path(path).read_text(encoding='utf-8'))
    # RFC 7946: absent CRS means WGS84 longitude/latitude, not inferred metres.
    if obj.get('crs') is not None:
        raise ValueError('Unexpected CRS declaration; review explicitly')
    if obj.get('type') != 'FeatureCollection' or not obj.get('features'):
        raise ValueError('Expected a nonempty GeoJSON FeatureCollection')
    geometries, repairs = {}, []
    for feature in obj['features']:
        name = feature['properties']['neighbourhood']
        geom = shape(feature['geometry'])
        if name in geometries or geom.is_empty or geom.geom_type not in {'Polygon', 'MultiPolygon'}:
            raise ValueError('Duplicate name, empty or non-polygon geometry')
        x1, y1, x2, y2 = geom.bounds
        if not (-180 <= x1 <= x2 <= 180 and -90 <= y1 <= y2 <= 90):
            raise ValueError('Geometry outside longitude/latitude bounds')
        if not geom.is_valid:
            fixed = shapely.make_valid(geom, method='linework')
            change = abs(fixed.area - geom.area) / geom.area if geom.area else math.inf
            if not fixed.is_valid or fixed.is_empty or fixed.geom_type not in {'Polygon', 'MultiPolygon'} or change > 1e-8:
                raise ValueError('Geometry repair requires review')
            repairs.append({'neighbourhood': name, 'reason': shapely.is_valid_reason(geom),
                            'method': 'make_valid/linework', 'relative_planar_area_change': change})
            geom = fixed
        geometries[name] = geom
    return geometries, repairs


def locate(frame, geometries):
    lon = pd.to_numeric(frame['longitude'], errors='coerce').to_numpy(dtype=float)
    lat = pd.to_numeric(frame['latitude'], errors='coerce').to_numpy(dtype=float)
    valid = np.isfinite(lon) & np.isfinite(lat) & (abs(lon) <= 180) & (abs(lat) <= 90)
    points = shapely.points(np.where(valid, lon, 0), np.where(valid, lat, 0))
    hits = np.zeros(len(frame), dtype=int)
    named = np.zeros(len(frame), dtype=bool)
    labels = frame['neighbourhood_cleansed'].to_numpy()
    for name, polygon in geometries.items():
        covered = np.asarray(shapely.covers(polygon, points)) & valid
        hits += covered
        named |= covered & (labels == name)
    status = np.full(len(frame), 'outside_polygons', dtype=object)
    status[(hits == 1) & ~named] = 'different_neighbourhood'
    status[(hits == 1) & named] = 'consistent'
    status[hits > 1] = 'multiple_polygons'
    status[~valid] = 'invalid_coordinates'
    return pd.Series(status, index=frame.index)


def numeric_quality(frame):
    result = {}
    for field in NUMERIC:
        original = frame[field]
        parsed = pd.to_numeric(original, errors='coerce')
        minimum = 1 if field in {'accommodates', 'minimum_nights'} else 0
        invalid = ~np.isfinite(parsed) | (parsed < minimum)
        if field != 'bathrooms':
            invalid |= parsed.mod(1).ne(0)
        result[field] = {'missing': int(original.eq('').sum()),
                         'invalid_nonmissing': int((original.ne('') & invalid).sum()),
                         'usable': int((~invalid).sum())}
    return result


def aggregate_groups(frame, key):
    """Suppress price summaries unless both row and host support are sufficient."""
    records = []
    for name, group in frame.groupby(key, sort=True):
        eligible = group[group['target'].notna()]
        if len(group) < 30 or group.host_id.nunique() < 10 or len(eligible) < 30 or eligible.host_id.nunique() < 10:
            continue
        records.append({'group': str(name), 'rows': len(group), 'hosts': int(group.host_id.nunique()),
                        'priced_rows': len(eligible), 'priced_hosts': int(eligible.host_id.nunique()),
                        'missing_price_rate': float(group.target.isna().mean()),
                        'median_brl': float(eligible.target.median()),
                        'q25_brl': float(eligible.target.quantile(.25)),
                        'q75_brl': float(eligible.target.quantile(.75))})
    return records


def make_plots(frame, geometries, spatial_groups, report, folder):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.spines.top': False,
                         'axes.spines.right': False, 'figure.facecolor': '#f7f9fc'})
    prices = frame.target.dropna()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout='constrained')
    axes[0].hist(prices, bins=np.geomspace(prices.min(), prices.max() * 1.001, 45), color='#246b8e')
    axes[0].set(xscale='log', xlabel='Listed nightly price (BRL, log scale)', ylabel='Training listings',
                title='A long upper tail; no price trimming')
    groups = report['room_types']
    axes[1].barh([r['group'] for r in groups], [100*r['missing_price_rate'] for r in groups], color='#bb623f')
    axes[1].set(xlabel='Missing price (%)', title='Target availability differs by room type')
    fig.suptitle('Rio Airbnb | training data only', fontsize=16)
    fig.savefig(folder / 'training_overview.png', dpi=180)
    plt.close(fig)

    values = {r['group']: r['median_brl'] for r in spatial_groups}
    if not values:
        raise ValueError('No neighbourhoods meet publication thresholds')
    norm = LogNorm(min(values.values()), max(values.values()))
    cmap = plt.get_cmap('viridis')
    fig, ax = plt.subplots(figsize=(11, 6.2), layout='constrained')
    for name, geom in geometries.items():
        colour = cmap(norm(values[name])) if name in values else '#dce1e8'
        ax.add_patch(patch_from_polygon(geom, facecolor=colour, edgecolor='white', linewidth=.35))
    ax.autoscale_view()
    ax.set_aspect(1 / math.cos(math.radians(-23)))
    ax.set(xlabel='Longitude (WGS84)', ylabel='Latitude (WGS84)',
           title='Rio | median listed nightly price by neighbourhood\nTraining only; prices in BRL; logarithmic colour scale')
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, label='Median BRL', shrink=.75)
    fig.text(.12, .015, 'Grey: insufficient support or no eligible rows. Minimum 30 listings / 10 hosts.\nOnly unambiguous coordinate/name matches. Source: Inside Airbnb, 2026-06-24; CC BY 4.0.', fontsize=8)
    fig.savefig(folder / 'neighbourhood_prices.png', dpi=180, bbox_inches='tight')
    plt.close(fig)


def main():
    frame, frozen = load_training()
    geometries, repairs = load_geometries(RAW / 'neighbourhoods.geojson')
    frame['target'] = pd.to_numeric(frame.price.map(price_value), errors='coerce')
    frame['spatial_status'] = locate(frame, geometries)
    eligible = frame[frame.target.notna()]
    prices = eligible.target
    geo_frame = frame[frame.spatial_status.eq('consistent')]
    spatial_groups = aggregate_groups(geo_frame, 'neighbourhood_cleansed')
    published_names = {r['group'] for r in spatial_groups}
    rooms = aggregate_groups(frame, 'room_type')
    by_neighbourhood = aggregate_groups(frame, 'neighbourhood_cleansed')
    host_counts = eligible.groupby('host_id').size().sort_values(ascending=False)
    top_n = max(1, math.ceil(len(host_counts) * .01))
    report = {
        'scope': 'Training only; validation/test targets not loaded by EDA.',
        'versions': {'python': platform.python_version(), 'pandas': pd.__version__,
                     'numpy': np.__version__, 'shapely': shapely.__version__,
                     'geos': shapely.geos_version_string, 'matplotlib': matplotlib.__version__},
        'training_sha256': frozen['artifacts']['train.csv'],
        'training_rows': len(frame), 'priced_rows': len(eligible),
        'missing_price_rows': int(frame.target.isna().sum()),
        'missing_price_rate': float(frame.target.isna().mean()),
        'price_summary_brl': {'median': float(prices.median()), 'mean': float(prices.mean()),
            'q25': float(prices.quantile(.25)), 'q75': float(prices.quantile(.75)),
            'p90': float(prices.quantile(.90)), 'p99': float(prices.quantile(.99))},
        'numeric_quality': numeric_quality(frame),
        'numeric_quality_by_target_availability': {
            'observed_price': numeric_quality(eligible),
            'missing_price': numeric_quality(frame[frame.target.isna()])},
        'room_types': rooms,
        'room_type_groups_suppressed': int(frame.room_type.nunique() - len(rooms)),
        'neighbourhoods_source_labels': by_neighbourhood,
        'source_label_groups_suppressed': int(frame.neighbourhood_cleansed.nunique() - len(by_neighbourhood)),
        'geography': {'crs': 'WGS84 lon/lat; RFC7946 default, source has no CRS member',
            'features': len(geometries), 'repairs': repairs,
            'training_status_counts': {str(k): int(v) for k, v in frame.spatial_status.value_counts().items()},
            'map_neighbourhoods': len(spatial_groups),
            'map_priced_rows': int((geo_frame.target.notna() & geo_frame.neighbourhood_cleansed.isin(published_names)).sum()),
            'map_groups': spatial_groups},
        'concentration': {'largest_one_percent_hosts_count': top_n,
            'share_priced_listings_from_largest_one_percent_hosts': float(host_counts.iloc[:top_n].sum()/len(eligible))},
        'publication_rule': 'Every published price group has >=30 priced rows and >=10 distinct priced hosts.'}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / 'summary.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    make_plots(frame, geometries, spatial_groups, report, RESULTS)
    print(json.dumps({k: v for k, v in report.items() if k not in {'neighbourhoods_source_labels', 'geography'}}, indent=2))
    print(json.dumps({k: v for k, v in report['geography'].items() if k != 'map_groups'}, indent=2))


if __name__ == '__main__':
    main()