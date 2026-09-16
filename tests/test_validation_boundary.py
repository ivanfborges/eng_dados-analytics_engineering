import unittest
from unittest.mock import patch
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from rio.models import NonnegativeHistGradientBoostingRegressor
from rio.prepare import host_partition, FIELDS
from rio.validate_selection import validation_rows


class ValidationBoundaryTests(unittest.TestCase):
    def test_nonnegative_tree_output(self):
        with patch.object(HistGradientBoostingRegressor,'predict',return_value=np.array([-12.,0.,30.])):
            result=NonnegativeHistGradientBoostingRegressor().predict(None)
        np.testing.assert_array_equal(result,[0,0,30])

    def test_loader_skips_nonvalidation_before_accessing_target(self):
        host={split:next(str(i) for i in range(100) if host_partition(str(i))==split)
              for split in ['train','validation','test']}
        valid={field:'' for field in FIELDS}
        valid.update(id='001',host_id=host['validation'],price='$100.00')
        # Other splits intentionally have no price/predictor keys: accessing them would fail.
        rows=[{'host_id':host['train']},{'host_id':host['test']},valid]
        result=validation_rows(rows)
        self.assertEqual(result.id.tolist(),['001'])
        self.assertEqual(result.target.tolist(),[100.])


if __name__=='__main__': unittest.main()