"""Validated batch inference for the frozen Rio study; never trains a model."""
import argparse
import csv
from importlib.metadata import version
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from rio.final_evaluation import read, require_hash, verify_model
from rio.prepare import ROOT

NUMERIC = ['accommodates', 'bedrooms', 'beds', 'bathrooms', 'minimum_nights', 'latitude', 'longitude']
CATEGORICAL = ['room_type', 'property_type', 'neighbourhood_cleansed']
COLUMNS = ['case_id'] + NUMERIC + CATEGORICAL


def read_input(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        if len(header) != len(COLUMNS) or set(header) != set(COLUMNS):
            raise ValueError('Expected exactly these unique columns: ' + ', '.join(COLUMNS))
        rows = []
        for line, values in enumerate(reader, 2):
            if len(values) != len(header):
                raise ValueError(f'Wrong number of fields on line {line}')
            rows.append(dict(zip(header, (value.strip() for value in values))))
    if not rows:
        raise ValueError('Input must contain at least one case')
    frame = pd.DataFrame(rows, columns=COLUMNS)
    if (frame.case_id == '').any() or frame.case_id.duplicated().any():
        raise ValueError('case_id must be nonempty and unique')
    for name in NUMERIC:
        present = frame[name] != ''
        numbers = pd.to_numeric(frame.loc[present, name], errors='coerce')
        if not np.isfinite(numbers).all():
            raise ValueError(f'{name}: use finite numbers or leave blank')
        if name in ['latitude', 'longitude']:
            valid = numbers.abs() <= (90 if name == 'latitude' else 180)
        else:
            valid = numbers >= (1 if name in ['accommodates', 'minimum_nights'] else 0)
            if name != 'bathrooms':
                valid &= numbers == np.floor(numbers)
        if not valid.all():
            raise ValueError(f'{name}: value outside the documented input contract')
    return frame


def load_frozen(model_path):
    public = ROOT / 'docs/selection'
    artifact = read(public / 'selected_artifact.json')
    validation = read(public / 'validation.json')
    require_hash(public / 'selected_artifact.json', validation['selected_artifact_sha256'])
    require_hash(public / 'decision.json', artifact['decision_sha256'])
    decision = read(public / 'decision.json')
    require_hash(public / 'comparison.json', decision['comparison_sha256'])
    if artifact['candidate'] != 'histgb_geo' or decision['candidate'] != artifact['candidate']:
        raise ValueError('Unexpected selected candidate')
    run = artifact['run']
    protocol = ROOT / 'docs/baselines/protocol.json'
    require_hash(protocol, run['protocol_sha256'])
    require_hash(ROOT / 'rio/models.py', run['models_code_sha256'])
    require_hash(ROOT / 'requirements-model-lock.txt', run['lock_sha256'])
    # Check bytes BEFORE unpickling. Only use a trusted local artifact.
    require_hash(Path(model_path), artifact['model_sha256'])
    if platform.python_version() != run['versions']['python']:
        raise ValueError('Use Python ' + run['versions']['python'])
    for line in (ROOT / 'requirements-model-lock.txt').read_text().splitlines():
        package, pinned = line.split('==')
        if version(package) != pinned:
            raise ValueError('Dependency mismatch: ' + package)
    model = joblib.load(model_path)
    verify_model(model, read(protocol))
    return model


def write_predictions(model, frame, output):
    with threadpool_limits(limits=1):
        predictions = np.asarray(model.predict(frame[NUMERIC + CATEGORICAL]), dtype=float)
    if predictions.shape != (len(frame),) or not np.isfinite(predictions).all() or (predictions < 0).any():
        raise ValueError('Model returned invalid predictions')
    # Exclusive creation protects existing results and the input file.
    with Path(output).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['case_id', 'estimated_nightly_price_brl'])
        writer.writerows(zip(frame.case_id, (f'{value:.2f}' for value in predictions)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--check-input', action='store_true', help='Validate only; no model or source data needed')
    parser.add_argument('--model', type=Path, help='Explicit path to the trusted frozen local joblib artifact')
    parser.add_argument('--output', type=Path, help='New CSV path; parent directory must exist')
    args = parser.parse_args()
    if args.check_input and (args.model or args.output):
        parser.error('--check-input cannot be combined with --model or --output')
    if not args.check_input and (not args.model or not args.output):
        parser.error('Inference requires --model and --output')
    try:
        frame = read_input(args.input)
        if args.check_input:
            print(json.dumps({'valid_cases': len(frame), 'mode': 'schema-only; no domain or accuracy guarantee'}))
            return
        if args.output.exists():
            raise ValueError('Output already exists; choose a new path')
        model = load_frozen(args.model)
        write_predictions(model, frame, args.output)
        print(f'Wrote {len(frame)} estimates in BRL to {args.output}')
    except (ValueError, OSError, csv.Error) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
