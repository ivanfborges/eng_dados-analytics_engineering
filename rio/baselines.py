"""Out-of-fold median baselines on the frozen training partition only."""
import hashlib
import json
import platform

import numpy as np
import pandas as pd

from rio.eda import load_training
from rio.prepare import ROOT, digest, price_value, save_immutable

PROTOCOL = ROOT / 'docs/baselines/protocol.json'
RESULTS = ROOT / 'reports/generated/baselines'


def host_fold(host_id):
    return int.from_bytes(hashlib.sha256(('rio-cv-v1|' + host_id).encode('utf-8')).digest()[:8], 'big') % 5


def folds(frame, mode, mapping):
    if mode == 'host':
        labels = frame.host_id.map(host_fold).to_numpy()
    elif mode == 'spatial':
        labels = frame.neighbourhood_cleansed.map(mapping).to_numpy()
        if pd.isna(labels).any():
            raise ValueError('Neighbourhood missing from frozen mapping')
    else:
        raise ValueError('Unknown evaluation mode')
    for fold in range(5):
        evaluate = np.flatnonzero(labels == fold)
        fitting = np.flatnonzero(labels != fold)
        before = len(fitting)
        evaluation_hosts = set(frame.iloc[evaluate].host_id)
        if mode == 'spatial':
            fitting = fitting[~frame.iloc[fitting].host_id.isin(evaluation_hosts).to_numpy()]
        if not len(fitting) or not len(evaluate):
            raise ValueError('Empty fitting/evaluation fold')
        if set(frame.iloc[fitting].host_id) & evaluation_hosts:
            raise ValueError('Host leakage')
        if mode == 'spatial' and set(frame.iloc[fitting].neighbourhood_cleansed) & set(frame.iloc[evaluate].neighbourhood_cleansed):
            raise ValueError('Neighbourhood leakage')
        yield fold, fitting, evaluate, before - len(fitting)


def predict_medians(fitting, room_types):
    if fitting.empty or not np.isfinite(fitting.target).all() or (fitting.target <= 0).any():
        raise ValueError('Expected nonempty positive training targets')
    global_value = float(fitting.target.median())
    by_room = fitting.groupby('room_type').target.median()
    return {'global_median': np.full(len(room_types), global_value),
            'room_median': room_types.map(by_room).fillna(global_value).to_numpy(dtype=float)}


def metrics(y, prediction, hosts):
    y, prediction = np.asarray(y, dtype=float), np.asarray(prediction, dtype=float)
    if y.ndim != 1 or y.shape != prediction.shape or len(y) != len(hosts) or not len(y):
        raise ValueError('Incompatible metric inputs')
    if not np.isfinite(y).all() or not np.isfinite(prediction).all() or (y <= 0).any() or (prediction < 0).any():
        raise ValueError('Nonfinite or invalid metric inputs')
    error = np.abs(y - prediction)
    host_means = pd.DataFrame({'host': np.asarray(hosts), 'error': error}).groupby('host').error.mean()
    return {'mae_brl': float(error.mean()), 'median_absolute_error_brl': float(np.median(error)),
            'rmse_brl': float(np.sqrt(np.mean((y - prediction)**2))),
            'rmsle': float(np.sqrt(np.mean((np.log1p(y) - np.log1p(prediction))**2))),
            'host_weighted_mae_brl': float(host_means.mean())}


def bootstrap_mean(values, hosts, repeats=1000, seed=42):
    grouped = pd.DataFrame({'host': np.asarray(hosts), 'value': np.asarray(values)}).groupby('host').value.agg(['sum', 'count'])
    sums, counts = grouped['sum'].to_numpy(), grouped['count'].to_numpy()
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(repeats):
        sampled = rng.integers(0, len(grouped), len(grouped))
        means.append(sums[sampled].sum() / counts[sampled].sum())
    return [float(x) for x in np.quantile(means, [.025, .975])]


def evaluate(frame, mode, mapping, bootstrap):
    predictions = {name: np.full(len(frame), np.nan) for name in ['global_median', 'room_median']}
    assignments = np.full(len(frame), -1)
    seen = np.zeros(len(frame), dtype=int)
    fold_reports = []
    for fold, fitting, evaluation, purged in folds(frame, mode, mapping):
        fit = frame.iloc[fitting]
        held = frame.iloc[evaluation]
        predicted = predict_medians(fit, held.room_type)
        report = {'fold': fold, 'fitting_rows': len(fit), 'fitting_hosts': int(fit.host_id.nunique()),
                  'evaluation_rows': len(held), 'evaluation_hosts': int(held.host_id.nunique()),
                  'purged_fitting_rows': purged, 'host_overlap': 0, 'metrics': {}}
        for name, values in predicted.items():
            predictions[name][evaluation] = values
            report['metrics'][name] = metrics(held.target, values, held.host_id)
        fold_reports.append(report)
        assignments[evaluation] = fold
        seen[evaluation] += 1
    if not (seen == 1).all():
        raise ValueError('Each eligible training row must be evaluated once')
    results = {}
    for name, values in predictions.items():
        results[name] = metrics(frame.target, values, frame.host_id)
        results[name]['mae_host_bootstrap_95ci'] = bootstrap_mean(np.abs(frame.target.to_numpy() - values), frame.host_id,
                                                               bootstrap['replicates'], bootstrap['seed'])
    difference = np.abs(frame.target.to_numpy() - predictions['room_median']) - np.abs(frame.target.to_numpy() - predictions['global_median'])
    report = {'evaluated_rows': len(frame), 'evaluated_hosts': int(frame.host_id.nunique()),
              'coverage': 1.0, 'folds': fold_reports, 'pooled_metrics': results,
              'room_minus_global_mae_brl': float(difference.mean()),
              'paired_delta_host_bootstrap_95ci': bootstrap_mean(difference, frame.host_id, bootstrap['replicates'], bootstrap['seed'])}
    private = frame[['id', 'host_id']].copy()
    private['fold'] = assignments
    private['target'] = frame.target
    for name, values in predictions.items():
        private[name] = values
    return report, private


def main():
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    frame, frozen = load_training()
    frame['target'] = pd.to_numeric(frame.price.map(price_value), errors='coerce')
    frame = frame[frame.target.notna()].reset_index(drop=True)
    if len(frame) != frozen['counts']['train']['eligible_rows']:
        raise ValueError('Eligible training count differs from frozen metadata')
    report = {'protocol_sha256': digest(PROTOCOL), 'training_sha256': frozen['artifacts']['train.csv'],
              'scope': 'Training-only out-of-fold predictions. Validation and final test remain unused.',
              'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__},
              'bootstrap_note': 'Host resampling conditional on fixed OOF predictions; excludes model refitting and neighbourhood-cluster uncertainty.',
              'evaluations': {}, 'private_artifact_sha256': {}}
    for mode in ['host', 'spatial']:
        summary, individual = evaluate(frame, mode, protocol['spatial_mapping'], protocol['bootstrap'])
        content = individual.to_csv(index=False, lineterminator='\n').encode('utf-8')
        save_immutable(RESULTS / f'{mode}_oof.csv', content)
        report['private_artifact_sha256'][f'{mode}_oof.csv'] = hashlib.sha256(content).hexdigest()
        report['evaluations'][mode] = summary
    content = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
    save_immutable(RESULTS / 'metrics.json', content)
    print(json.dumps({mode: summary['pooled_metrics'] for mode, summary in report['evaluations'].items()}, indent=2))


if __name__ == '__main__':
    main()