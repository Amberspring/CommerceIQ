import numpy as np
import pandas as pd
import pytest
from src.attribution import shapley_product, dimension_bridge
from src.experiments import binary_effect, sample_size, profit_scenario, top_policy

def test_shapley_interaction_symmetry_and_reconciliation():
    result=shapley_product({'x':2,'y':3},{'x':4,'y':5})
    assert result=={'x':8.,'y':6.}
    assert sum(result.values())==20-6

def test_shapley_unchanged_factor_and_zero_baseline():
    result=shapley_product({'buyers':0,'freq':1,'aov':100},{'buyers':10,'freq':1,'aov':120})
    assert result['freq']==0
    assert sum(result.values())==1200

def test_dimension_new_lost_and_negative():
    a,b=pd.Timestamp('2018-05-01'),pd.Timestamp('2018-06-01')
    items=pd.DataFrame({'month':[a,a,b,b],'state':['lost','same','same','new'],'price':[100,50,20,10]})
    result=dimension_bridge(items,'state',a,b)
    assert result.delta.sum()==-120
    assert np.isclose(result.contribution_pp.sum(),-80)

def test_binary_effect_known_answer_and_symmetric_null():
    result=binary_effect([0,0,1,1,0,1,1,1],[0,0,0,0,1,1,1,1])
    assert result['effect']==.25
    assert result['relative_lift']==.5
    assert binary_effect([0,1,0,1],[0,0,1,1])['p_value']==1

def test_sample_size_scales_with_mde():
    small=sample_size(.6,.01); large=sample_size(.6,.02)
    assert 3.8 < small/large < 4.2
    with pytest.raises(ValueError): sample_size(.99,.02)

def test_profit_is_incremental_and_cost_covers_all_contacts():
    result=profit_scenario(.05,1000,20,1)
    assert result['incremental_buyers']==50
    assert result['net_profit']==0
    assert profit_scenario(-.01,1000,20,1)['net_profit']==-1200

def test_top_policy_uses_scores_without_outcome_leakage():
    y=np.array([0,1,0,1,1,1,1,1]);t=np.array([0,1,0,1,0,1,0,1])
    result=top_policy(y,t,np.arange(8),fraction=.5)
    assert result['selected_customers']==4
    assert result['effect']==0
