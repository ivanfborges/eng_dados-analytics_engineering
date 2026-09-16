import json
import unittest
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from rio.models import make_model, SemanticCleaner, inverse_price
from rio.selection import choose
from rio.baselines import PROTOCOL


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.protocol=json.loads(PROTOCOL.read_text(encoding='utf-8'))
        self.frame=pd.DataFrame({'accommodates':['2']*50,'bedrooms':['1']*50,'beds':['1']*50,
            'bathrooms':['1']*50,'minimum_nights':['2']*50,'room_type':['A']*50,'property_type':['flat']*50,
            'latitude':['-23']*50,'longitude':['-43']*50,'neighbourhood_cleansed':['one']*50,
            'id':[str(i) for i in range(50)], 'price':['999']*50})
        self.y=np.arange(100,150,dtype=float)

    def test_semantic_rules_and_no_unapproved_columns(self):
        cleaner=SemanticCleaner(['accommodates','bedrooms','bathrooms'],['room_type'])
        frame=self.frame.iloc[:2].copy()
        frame.loc[0,['accommodates','bedrooms','bathrooms']]=['0','1.5','inf']
        frame.loc[1,['accommodates','bedrooms','bathrooms']]=['2','0','0.5']
        clean=cleaner.fit_transform(frame)
        self.assertTrue(clean.iloc[0,:3].isna().all())
        self.assertEqual(clean.loc[1,'bedrooms'],0)
        self.assertEqual(set(clean),{'accommodates','bedrooms','bathrooms','room_type'})

    def test_imputation_is_fitted_on_training_and_flags_all_fields(self):
        model=make_model('histgb_property',self.protocol)
        self.frame.loc[0,'beds']=''
        with threadpool_limits(limits=2): model.fit(self.frame,self.y)
        numeric=model.named_steps['preprocess'].named_transformers_['numeric']
        union=numeric.named_steps['impute_and_flag']
        imputer=union.transformer_list[0][1]
        self.assertEqual(imputer.statistics_[2],1)
        held=self.frame.iloc[:1].copy()
        held['beds']='1000'; held['bedrooms']=''
        cleaned=model.named_steps['clean'].transform(held)
        values=numeric.transform(cleaned[self.protocol['numeric_property']])
        self.assertEqual(values.shape,(1,10))
        self.assertEqual(values[0,6],1)
        self.assertEqual(imputer.statistics_[2],1)

    def test_four_candidates_accept_unknown_categories_and_new_missingness(self):
        held=self.frame.iloc[:2].copy()
        held['room_type']='unseen'; held['neighbourhood_cleansed']='unseen'; held['beds']=''
        for name in self.protocol['candidate_order'][2:]:
            with self.subTest(name=name),threadpool_limits(limits=2):
                model=make_model(name,self.protocol).fit(self.frame,self.y)
                prediction=model.predict(held)
                self.assertTrue(np.isfinite(prediction).all())
                self.assertTrue((prediction>=0).all())

    def test_property_model_ignores_coordinates_and_ids(self):
        with threadpool_limits(limits=2):
            model=make_model('ridge_property',self.protocol).fit(self.frame,self.y)
            changed=self.frame.copy(); changed['id']='x'; changed['latitude']='90'; changed['price']='0'
            np.testing.assert_array_equal(model.predict(self.frame),model.predict(changed))

    def test_inverse_floor(self):
        np.testing.assert_allclose(inverse_price(np.array([-2,0,np.log1p(100)])),[0,0,100])

    def test_selection_uses_declared_order_only_for_ties(self):
        self.assertEqual(choose({'a':10.,'b':9.},['a','b']),'b')
        self.assertEqual(choose({'a':10.,'b':10.-1e-10},['a','b']),'a')
        with self.assertRaises(ValueError): choose({'a':10.},['a','b'])


if __name__=='__main__': unittest.main()