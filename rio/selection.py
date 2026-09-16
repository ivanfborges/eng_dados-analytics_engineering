"""Train-only candidate comparison. This module cannot load external holdouts."""
import json
import platform
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits
from rio.baselines import PROTOCOL, folds, metrics, bootstrap_mean
from rio.eda import load_training
from rio.models import make_model
from rio.prepare import ROOT, digest, price_value, save_immutable

OUTPUT = ROOT / 'reports/generated/selection'


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8')


def choose(scores, order):
    if set(scores) != set(order) or not all(np.isfinite(v) for v in scores.values()):
        raise ValueError('Incomplete or invalid candidate scores')
    best = min(scores.values())
    return next(name for name in order if scores[name] <= best + 1e-9)


def main():
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    baseline = json.loads((ROOT/'docs/baselines/metrics.json').read_text(encoding='utf-8'))
    frame, frozen = load_training()
    frame['target'] = pd.to_numeric(frame.price.map(price_value), errors='coerce')
    frame = frame[frame.target.notna()].reset_index(drop=True)
    if digest(PROTOCOL) != baseline['protocol_sha256'] or frozen['artifacts']['train.csv'] != baseline['training_sha256']:
        raise ValueError('Baseline/protocol/source mismatch')
    run = {'protocol_sha256':digest(PROTOCOL), 'training_sha256':frozen['artifacts']['train.csv'],
           'models_code_sha256':digest(ROOT/'rio/models.py'), 'lock_sha256':digest(ROOT/'requirements-model-lock.txt'),
           'versions':{'python':platform.python_version(),'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__}}
    save_immutable(OUTPUT/'run.json', encode(run))
    report = {'run':run, 'evaluations':{}}
    for mode in ['host','spatial']:
        results = {k:dict(v) for k,v in baseline['evaluations'][mode]['pooled_metrics'].items()}
        fold_reports = {}
        for name in protocol['candidate_order'][2:]:
            output = OUTPUT/f'{mode}_{name}.csv'
            if output.exists():
                raise ValueError('Candidate output already exists; review stored results instead of silently rerunning')
            predictions = np.full(len(frame),np.nan)
            seen = np.zeros(len(frame),dtype=int)
            details=[]
            for fold, fit, held, purged in folds(frame,mode,protocol['spatial_mapping']):
                model=make_model(name,protocol)
                with threadpool_limits(limits=2):
                    model.fit(frame.iloc[fit],frame.iloc[fit].target)
                    predictions[held]=model.predict(frame.iloc[held])
                seen[held]+=1
                details.append({'fold':fold,'fitting_rows':len(fit),'evaluation_rows':len(held),
                                'purged_fitting_rows':purged,'metrics':metrics(frame.iloc[held].target,predictions[held],frame.iloc[held].host_id)})
                print(f'{mode} {name} fold {fold} completed',flush=True)
            if not (seen==1).all():
                raise ValueError('OOF coverage failure')
            result=metrics(frame.target,predictions,frame.host_id)
            result['mae_host_bootstrap_95ci']=bootstrap_mean(abs(frame.target.to_numpy()-predictions),frame.host_id)
            private=frame[['id','host_id','target']].copy()
            private['prediction']=predictions
            save_immutable(output,private.to_csv(index=False,lineterminator='\n').encode())
            results[name]=result
            fold_reports[name]={'folds':details,'prediction_sha256':digest(output)}
        report['evaluations'][mode]={'pooled_metrics':results,'candidate_details':fold_reports}
    scores={name:result['mae_brl'] for name,result in report['evaluations']['host']['pooled_metrics'].items()}
    report['selected']=choose(scores,protocol['candidate_order'])
    report['selection_scope']='Host CV only. Validation not loaded. Final test reserved.'
    save_immutable(OUTPUT/'comparison.json',encode(report))
    save_immutable(OUTPUT/'decision.json',encode({'candidate':report['selected'],'run':run,'comparison_sha256':digest(OUTPUT/'comparison.json')}))
    print(json.dumps({'selected':report['selected'],'host_mae':scores},indent=2),flush=True)


if __name__=='__main__':
    main()