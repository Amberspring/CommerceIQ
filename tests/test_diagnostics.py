"""One real-data check for diagnosis reconciliation and AI SQL rejection."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest


def test_business_diagnosis_and_ai_contract():
    out = Path(__file__).resolve().parents[1] / 'outputs/olist'
    if not (out / 'diagnosis.json').exists():
        pytest.skip('Run scripts/run_diagnostics.py')
    case = json.loads((out / 'case.json').read_text(encoding='utf-8'))
    diagnosis = json.loads((out / 'diagnosis.json').read_text(encoding='utf-8'))
    for name in ['cross_diagnostics', 'seller_diagnostics']:
        df = pd.read_csv(out / f'{name}.csv')
        assert np.isclose(df.delta.sum(), case['delta'])
    weekday = pd.read_csv(out / 'weekday_diagnostics.csv')
    assert weekday.weekday_groups.eq(7).all()
    expected = (weekday.standardized_daily_gmv.iloc[1] /
                weekday.standardized_daily_gmv.iloc[0] - 1) * 100
    assert np.isclose(expected, diagnosis['weekday_standardized_change_pct'])
    if case['before'] == '2018-05-01' and case['after'] == '2018-06-01':
        assert [row['passed_amount_contract'] for row in diagnosis['ai_sql_audit']] == [False, True]
