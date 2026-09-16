"""Fit the CV-selected candidate on training only, then validate once. No test loader."""
import csv
import gzip
import io
import json
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from rio.baselines import PROTOCOL, metrics, bootstrap_mean
from rio.eda import load_training
from rio.models import make_model
from rio.prepare import ROOT, RAW, OUTPUT as PREPARED, FIELDS, digest, host_partition, price_value, save_immutable
from rio.selection import OUTPUT, encode


def validation_rows(reader):
    # Discard non-validation rows before parsing their price or copying predictors.
    rows=[]
    for row in reader:
        if host_partition(row['host_id']) != 'validation':
            continue
        target=price_value(row['price'])
        if target is not None:
            item={key:row[key] for key in FIELDS}
            item['target']=target
            rows.append(item)
    return pd.DataFrame(rows).sort_values('id').reset_index(drop=True)


def load_validation(frozen):
    source=RAW/'listings.csv.gz'
    if digest(source)!=frozen['source_hashes']['listings.csv.gz']:
        raise ValueError('Raw source hash mismatch')
    if digest(PREPARED/'assignments.csv')!=frozen['artifacts']['assignments.csv']:
        raise ValueError('Assignments hash mismatch')
    with gzip.open(source,'rt',encoding='utf-8',newline='') as stream:
        frame=validation_rows(csv.DictReader(stream))
    assignments=pd.read_csv(PREPARED/'assignments.csv',dtype=str,keep_default_na=False)
    expected=assignments[(assignments.partition=='validation') & (assignments.eligible_target=='1')]
    observed=dict(zip(frame.id,frame.host_id))
    if len(observed)!=len(frame) or observed!=dict(zip(expected.id,expected.host_id)):
        raise ValueError('Validation membership mismatch')
    if len(frame)!=frozen['counts']['validation']['eligible_rows']:
        raise ValueError('Validation count mismatch')
    return frame


def main():
    if (OUTPUT/'validation.json').exists() or (OUTPUT/'validation_started.json').exists():
        raise ValueError('Validation already completed or started; review saved artifacts before retrying')
    decision=json.loads((OUTPUT/'decision.json').read_text(encoding='utf-8'))
    run=decision['run']
    if digest(PROTOCOL)!=run['protocol_sha256'] or digest(ROOT/'rio/models.py')!=run['models_code_sha256'] or digest(ROOT/'requirements-model-lock.txt')!=run['lock_sha256']:
        raise ValueError('Frozen implementation mismatch')
    if digest(OUTPUT/'comparison.json')!=decision['comparison_sha256']:
        raise ValueError('Comparison changed after selection')
    protocol=json.loads(PROTOCOL.read_text(encoding='utf-8'))
    train,frozen=load_training()
    train['target']=pd.to_numeric(train.price.map(price_value),errors='coerce')
    train=train[train.target.notna()].reset_index(drop=True)
    if frozen['artifacts']['train.csv']!=run['training_sha256']:
        raise ValueError('Training changed after selection')
    chosen=make_model(decision['candidate'],protocol)
    with threadpool_limits(limits=2):
        chosen.fit(train,train.target)
    buffer=io.BytesIO(); joblib.dump(chosen,buffer)
    save_immutable(OUTPUT/'selected_pipeline.joblib',buffer.getvalue())
    artifact={'candidate':decision['candidate'],'model_sha256':digest(OUTPUT/'selected_pipeline.joblib'),
              'decision_sha256':digest(OUTPUT/'decision.json'),'training_rows':len(train),
              'fit_scope':'Outer training partition only; no train+validation refit.', 'run':run}
    save_immutable(OUTPUT/'selected_artifact.json',encode(artifact))
    save_immutable(OUTPUT/'validation_started.json',encode({'artifact_sha256':digest(OUTPUT/'selected_artifact.json')}))
    valid=load_validation(frozen)
    if set(train.host_id)&set(valid.host_id):
        raise ValueError('Train-validation host overlap')
    with threadpool_limits(limits=2):
        prediction=chosen.predict(valid)
    reference=make_model('room_median',protocol).fit(train,train.target).predict(valid)
    error=abs(valid.target.to_numpy()-prediction)
    delta=error-abs(valid.target.to_numpy()-reference)
    report={'candidate':decision['candidate'],'rows':len(valid),'hosts':int(valid.host_id.nunique()),
            'selected_artifact_sha256':digest(OUTPUT/'selected_artifact.json'),
            'metrics':metrics(valid.target,prediction,valid.host_id),
            'mae_host_bootstrap_95ci':bootstrap_mean(error,valid.host_id),
            'room_median_metrics':metrics(valid.target,reference,valid.host_id),
            'selected_minus_room_mae':float(delta.mean()),
            'paired_delta_host_bootstrap_95ci':bootstrap_mean(delta,valid.host_id),
            'segments':{},'test_status':'Final test untouched. Validation not used to re-rank candidates.'}
    for field in ['room_type','neighbourhood_cleansed']:
        groups=[]; suppressed=0
        for name, indices in valid.groupby(field).groups.items():
            sub=valid.loc[indices]
            if len(sub)<30 or sub.host_id.nunique()<10:
                suppressed+=1; continue
            groups.append({'group':str(name),'rows':len(sub),'hosts':int(sub.host_id.nunique()),
                           'metrics':metrics(sub.target,prediction[indices],sub.host_id)})
        report['segments'][field]={'groups':groups,'suppressed_groups':suppressed}
    private=valid[['id','host_id','target']].copy()
    private['prediction']=prediction; private['room_median']=reference
    save_immutable(OUTPUT/'validation_predictions.csv',private.to_csv(index=False,lineterminator='\n').encode())
    report['private_predictions_sha256']=digest(OUTPUT/'validation_predictions.csv')
    save_immutable(OUTPUT/'validation.json',encode(report))
    print(json.dumps({key:value for key,value in report.items() if key!='segments'},indent=2))


if __name__=='__main__': main()