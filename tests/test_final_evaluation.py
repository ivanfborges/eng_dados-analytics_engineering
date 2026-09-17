import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from rio import final_evaluation as final
from rio.prepare import FIELDS, host_partition
from rio.models import make_model
from rio.baselines import PROTOCOL


class FinalEvaluationTests(unittest.TestCase):
    def test_filters_non_test_before_reading_targets(self):
        hosts={split:next(str(i) for i in range(100) if host_partition(str(i))==split) for split in ['train','validation','test']}
        row={key:'' for key in FIELDS}; row.update(id='001',host_id=hosts['test'],price='$200.00')
        result=final.test_rows([{'host_id':hosts['train']},{'host_id':hosts['validation']},row])
        self.assertEqual(result.id.tolist(),['001'])
        self.assertEqual(result.target.tolist(),[200.])

    def test_membership_rejects_duplicate_and_overlapping_hosts(self):
        frame=pd.DataFrame({'id':['1'],'host_id':['10']})
        assignments=pd.DataFrame({'id':['1','2'],'host_id':['10','20'],'partition':['test','train'],'eligible_target':['1','1']})
        frozen={'counts':{'test':{'eligible_rows':1,'eligible_hosts':1}}}
        final.verify_membership(frame,assignments,frozen)
        with self.assertRaises(ValueError): final.verify_membership(pd.concat([frame,frame]),assignments,frozen)
        assignments.loc[1,'host_id']='10'
        with self.assertRaisesRegex(ValueError,'overlap'): final.verify_membership(frame,assignments,frozen)

    def test_consumption_marker_is_exclusive(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            final.start_once(path,{'run':1})
            with self.assertRaises(FileExistsError): final.start_once(path,{'run':2})
            self.assertEqual(json.loads((path/'test_started.json').read_text()),{'run':1})

    def test_second_run_stops_before_preflight(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder); final.start_once(path,{'run':1})
            with patch.object(final,'OUTPUT',path),patch('sys.argv',['final']),patch.object(final,'preflight') as check:
                with self.assertRaisesRegex(ValueError,'consumed'): final.main()
                check.assert_not_called()

    def test_changed_artifact_hash_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'model'; path.write_bytes(b'original')
            expected=final.digest(path); final.require_hash(path,expected)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError): final.require_hash(path,expected)

    def test_changed_model_parameter_rejected(self):
        protocol=json.loads(PROTOCOL.read_text(encoding='utf-8'))
        model=make_model('histgb_geo',protocol)
        model.named_steps['estimator'].set_params(max_iter=5)
        with self.assertRaisesRegex(ValueError,'parameter'): final.verify_model(model,protocol)


if __name__=='__main__': unittest.main()