"""Single-use final evaluation of the frozen Airbnb model; never refits it."""
import argparse
import csv
from datetime import datetime, timezone
import gzip
from importlib.metadata import version
import json
import platform

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from rio.baselines import PROTOCOL, metrics, bootstrap_mean, predict_medians
from rio.eda import load_training
from rio.models import NonnegativeHistGradientBoostingRegressor
from rio.prepare import ROOT, RAW, OUTPUT as PREPARED, FIELDS, digest, host_partition, price_value, save_immutable
from rio.selection import encode

OUTPUT = ROOT/'reports/generated/final'
SELECTION = ROOT/'reports/generated/selection'
PUBLIC = ROOT/'docs/selection'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require_hash(path, expected):
    if digest(path) != expected:
        raise ValueError('Hash mismatch: '+path.name)


def verify_model(model, protocol):
    if list(model.named_steps) != ['clean','preprocess','estimator']:
        raise ValueError('Unexpected pipeline steps')
    estimator=model.named_steps['estimator']
    if type(estimator) is not NonnegativeHistGradientBoostingRegressor:
        raise ValueError('Unexpected estimator class')
    for key,value in protocol['histgb'].items():
        if key!='target' and estimator.get_params()[key]!=value:
            raise ValueError('Unexpected estimator parameter: '+key)
    if estimator.categorical_features is not None or estimator.n_iter_!=protocol['histgb']['max_iter']:
        raise ValueError('Unexpected fitted estimator state')
    cleaner=model.named_steps['clean']
    if cleaner.numeric!=protocol['numeric_property']+['latitude','longitude'] or cleaner.categorical!=protocol['categorical_property']+['neighbourhood_cleansed']:
        raise ValueError('Unexpected model feature list')


def preflight():
    artifact=read(PUBLIC/'selected_artifact.json')
    decision=read(PUBLIC/'decision.json')
    validation=read(PUBLIC/'validation.json')
    frozen=read(ROOT/'docs/eda/partitions.json')
    run=artifact['run']
    require_hash(PUBLIC/'selected_artifact.json',validation['selected_artifact_sha256'])
    require_hash(PUBLIC/'decision.json',artifact['decision_sha256'])
    require_hash(PUBLIC/'comparison.json',decision['comparison_sha256'])
    require_hash(SELECTION/'selected_pipeline.joblib',artifact['model_sha256'])
    require_hash(PROTOCOL,run['protocol_sha256'])
    require_hash(ROOT/'rio/models.py',run['models_code_sha256'])
    require_hash(ROOT/'requirements-model-lock.txt',run['lock_sha256'])
    require_hash(PREPARED/'train.csv',run['training_sha256'])
    require_hash(PREPARED/'assignments.csv',frozen['artifacts']['assignments.csv'])
    for filename,sha in frozen['source_hashes'].items():
        require_hash(RAW/filename,sha)
    if platform.python_version()!=run['versions']['python']:
        raise ValueError('Python version differs from frozen environment')
    for line in (ROOT/'requirements-model-lock.txt').read_text().splitlines():
        package,pinned=line.split('==')
        if version(package)!=pinned:
            raise ValueError('Dependency mismatch: '+package)
    if artifact['candidate']!='histgb_geo' or decision['candidate']!=artifact['candidate']:
        raise ValueError('Unexpected selected candidate')
    protocol=read(PROTOCOL)
    model=joblib.load(SELECTION/'selected_pipeline.joblib')
    verify_model(model,protocol)
    train,loaded=load_training()
    if loaded!=frozen:
        raise ValueError('Partition metadata mismatch')
    train['target']=pd.to_numeric(train.price.map(price_value),errors='coerce')
    train=train[train.target.notna()].reset_index(drop=True)
    if len(train)!=artifact['training_rows']:
        raise ValueError('Training count mismatch')
    return model,train,frozen,artifact


def test_rows(reader):
    rows=[]
    for row in reader:
        if host_partition(row['host_id'])!='test':
            continue
        target=price_value(row['price'])
        if target is not None:
            item={key:row[key] for key in FIELDS}
            item['target']=target
            rows.append(item)
    if not rows:
        raise ValueError('No eligible test rows')
    return pd.DataFrame(rows).sort_values('id').reset_index(drop=True)


def verify_membership(frame, assignments, frozen):
    expected=assignments[(assignments.partition=='test') & (assignments.eligible_target=='1')]
    observed=dict(zip(frame.id,frame.host_id))
    if len(observed)!=len(frame) or observed!=dict(zip(expected.id,expected.host_id)):
        raise ValueError('Test membership mismatch')
    if len(frame)!=frozen['counts']['test']['eligible_rows'] or frame.host_id.nunique()!=frozen['counts']['test']['eligible_hosts']:
        raise ValueError('Test counts mismatch')
    other=assignments[assignments.partition!='test']
    if set(frame.host_id)&set(other.host_id) or set(frame.id)&set(other.id):
        raise ValueError('Holdout overlap')


def start_once(folder, metadata):
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/'test_started.json').open('x',encoding='utf-8') as stream:
        json.dump(metadata,stream,indent=2)


def summarize(frame):
    y=frame.target.to_numpy(); prediction=frame.prediction.to_numpy(); reference=frame.room_median.to_numpy()
    error=abs(y-prediction); difference=error-abs(y-reference)
    report={'rows':len(frame),'hosts':int(frame.host_id.nunique()),
            'metrics':metrics(y,prediction,frame.host_id),
            'room_median_metrics':metrics(y,reference,frame.host_id),
            'mae_host_bootstrap_95ci':bootstrap_mean(error,frame.host_id),
            'selected_minus_room_mae':float(difference.mean()),
            'paired_delta_host_bootstrap_95ci':bootstrap_mean(difference,frame.host_id),'segments':{}}
    for field in ['room_type','neighbourhood_cleansed']:
        groups=[]; suppressed=0
        for name,indices in frame.groupby(field).groups.items():
            sub=frame.loc[indices]
            if len(sub)<30 or sub.host_id.nunique()<10:
                suppressed+=1; continue
            groups.append({'group':str(name),'rows':len(sub),'hosts':int(sub.host_id.nunique()),
                           'metrics':metrics(sub.target,sub.prediction,sub.host_id)})
        report['segments'][field]={'groups':groups,'suppressed_groups':suppressed}
    return report


def summarize_saved():
    receipt=read(OUTPUT/'prediction_receipt.json')
    require_hash(OUTPUT/'test_predictions.csv',receipt['predictions_sha256'])
    require_hash(OUTPUT/'test_started.json',receipt['start_sha256'])
    frame=pd.read_csv(OUTPUT/'test_predictions.csv',dtype={'id':str,'host_id':str},keep_default_na=False,float_precision='round_trip')
    report=summarize(frame)
    report.update({'provenance':read(OUTPUT/'test_started.json'),'prediction_receipt':receipt,
                   'test_status':'CONSUMED. No candidate or preprocessing change after final evaluation.',
                   'uncertainty':'1000 host bootstrap resamples, seed 42, fixed predictions; excludes refitting and dependence between hosts.'})
    save_immutable(OUTPUT/'metrics.json',encode(report))
    print(json.dumps({key:value for key,value in report.items() if key not in {'segments','provenance'}},indent=2))


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--check-only',action='store_true')
    group.add_argument('--summarize-saved',action='store_true')
    args=parser.parse_args()
    if args.summarize_saved:
        summarize_saved(); return
    if not args.check_only and (OUTPUT/'test_started.json').exists():
        raise ValueError('Final test already started/consumed. Use saved predictions only; never remove the marker to rerun.')
    model,train,frozen,artifact=preflight()
    if args.check_only:
        print('Preflight passed: frozen artifact, environment, source and partitions verified. No test targets read.'); return
    metadata={'started_utc':datetime.now(timezone.utc).isoformat(),'candidate':artifact['candidate'],
              'model_sha256':artifact['model_sha256'],'artifact_sha256':digest(PUBLIC/'selected_artifact.json'),
              'validation_sha256':digest(PUBLIC/'validation.json'),'partitions_sha256':digest(ROOT/'docs/eda/partitions.json'),
              'evaluator_sha256':digest(ROOT/'rio/final_evaluation.py'),'source_hashes':frozen['source_hashes'],
              'status':'Test access started; considered consumed even if interrupted. No model refit.'}
    start_once(OUTPUT,metadata)
    with gzip.open(RAW/'listings.csv.gz','rt',encoding='utf-8',newline='') as stream:
        frame=test_rows(csv.DictReader(stream))
    assignments=pd.read_csv(PREPARED/'assignments.csv',dtype=str,keep_default_na=False)
    verify_membership(frame,assignments,frozen)
    with threadpool_limits(limits=2):
        prediction=model.predict(frame)
    reference=predict_medians(train,frame.room_type)['room_median']
    private=frame[['id','host_id','room_type','neighbourhood_cleansed','target']].copy()
    private['prediction']=prediction; private['room_median']=reference
    save_immutable(OUTPUT/'test_predictions.csv',private.to_csv(index=False,lineterminator='\n').encode())
    save_immutable(OUTPUT/'prediction_receipt.json',encode({'predictions_sha256':digest(OUTPUT/'test_predictions.csv'),
                   'start_sha256':digest(OUTPUT/'test_started.json')}))
    require_hash(SELECTION/'selected_pipeline.joblib',artifact['model_sha256'])
    summarize_saved()


if __name__=='__main__': main()