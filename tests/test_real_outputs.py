"""Optional integration contracts against locally generated real-data artifacts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]

def test_real_bridges_reconcile():
    out=ROOT/'outputs/olist'
    if not (out/'case.json').exists(): pytest.skip('Run Olist pipeline')
    case=json.loads((out/'case.json').read_text())
    bridge=pd.read_csv(out/'dimension_bridge.csv')
    for _,group in bridge.groupby('dimension'):
        assert np.isclose(group.delta.sum(),case['delta'])
        assert np.isclose(group.contribution_pp.sum(),case['change_pct'])
    assert all(x['passed'] for x in json.loads((out/'quality.json').read_text()))

def test_no_future_retention_zeros():
    path=ROOT/'outputs/olist/customer_retention.csv'
    if not path.exists(): pytest.skip('Run Olist pipeline')
    df=pd.read_csv(path)
    months=pd.to_datetime(df.cohort).dt.year*12+pd.to_datetime(df.cohort).dt.month+df.month_index
    assert (months <= 2018*12+8).all()
    assert (df[df.month_index==0].retention==1).all()

def test_x5_client_holdout_and_feature_exclusions():
    path=ROOT/'data/processed/x5_holdout.parquet'
    if not path.exists(): pytest.skip('Run X5 pipeline')
    holdout=pd.read_parquet(path)
    card=json.loads((ROOT/'outputs/x5/model_card.json').read_text())
    assert holdout.client_id.is_unique
    splits=pd.read_parquet(ROOT/'data/processed/x5_splits.parquet')
    assert splits.client_id.is_unique
    assert set(holdout.client_id)==set(splits[splits.split=='test'].client_id)
    assert len(holdout)==card['test_n']
    assert not {'client_id','target','treatment_flg','first_redeem_date'}.intersection(card['features'])
    validation=pd.read_csv(ROOT/'outputs/x5/validation_models.csv')
    selected=validation[validation.model.isin(['s_learner','t_learner'])].sort_values('uplift_at_30',ascending=False).iloc[0].model
    assert selected==card['selected_model']
