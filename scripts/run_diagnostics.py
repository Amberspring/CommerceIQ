"""Reproduce one business diagnosis and audit this session's AI-authored SQL.

No inference is performed by this script. Model-authored prompts/candidates are
in docs/ai_review_input.json; this is the deterministic verification stage.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import numpy as np
import pandas as pd
import duckdb
from src.warehouse import ROOT, DB


def main():
    out = ROOT / 'outputs/olist'
    case = json.loads((out / 'case.json').read_text(encoding='utf-8'))
    before, after = case['before'], case['after']
    con = duckdb.connect(str(DB))
    con.execute((ROOT / 'sql/06_business_diagnostics.sql').read_text(encoding='utf-8'))
    params = [before, after]
    cross = con.execute('''SELECT customer_state,category,buyer_type,
        SUM(CASE WHEN month=?::DATE THEN gmv ELSE 0 END) AS before_gmv,
        SUM(CASE WHEN month=?::DATE THEN gmv ELSE 0 END) AS after_gmv
        FROM mart_state_category WHERE month IN (?::DATE,?::DATE)
        GROUP BY 1,2,3''', params * 2).df()
    cross['delta'] = cross.after_gmv - cross.before_gmv
    cross['contribution_pp'] = cross.delta / case['before_gmv'] * 100
    cross = cross.sort_values('delta')
    assert np.isclose(cross.delta.sum(), case['delta'])
    cross.to_csv(out / 'cross_diagnostics.csv', index=False)
    weekday = con.execute('''SELECT month,COUNT(*) AS weekday_groups,
        SUM(calendar_days) AS calendar_days,AVG(mean_daily_gmv) AS standardized_daily_gmv
        FROM mart_weekday_sales WHERE month IN (?::DATE,?::DATE)
        GROUP BY 1 ORDER BY 1''', params).df()
    assert weekday.weekday_groups.eq(7).all()
    weekday.to_csv(out / 'weekday_diagnostics.csv', index=False)
    service = con.execute('''SELECT *,failed_orders::DOUBLE/all_orders AS failed_share
        FROM mart_service_monthly WHERE month IN (?::DATE,?::DATE) ORDER BY month''', params).df()
    service.to_csv(out / 'service_diagnostics.csv', index=False)
    seller = con.execute('''SELECT seller_status,COUNT(*) AS sellers,
        SUM(previous_gmv) AS before_gmv,SUM(current_gmv) AS after_gmv,
        SUM(delta) AS delta FROM mart_seller_bridge WHERE month=?::DATE
        GROUP BY 1 ORDER BY delta''', [after]).df()
    assert np.isclose(seller.delta.sum(), case['delta'])
    seller.to_csv(out / 'seller_diagnostics.csv', index=False)
    # Candidate SQL is evaluated with a read-only connection: generated queries
    # cannot mutate the raw data or marts during evidence review.
    con.close()
    con = duckdb.connect(str(DB), read_only=True)
    # Fixed demonstration window: never silently apply the saved candidate to
    # a different case. The rest of the diagnostics support other month pairs.
    review = json.loads((ROOT / 'docs/ai_review_input.json').read_text(encoding='utf-8'))
    audit = []
    if params == ['2018-05-01', '2018-06-01']:
        for candidate in review['sql_candidates']:
            result = con.execute(candidate['sql']).df()
            values = result.gmv.tolist()
            matches = len(values) == 2 and np.allclose(
                values, [case['before_gmv'], case['after_gmv']], rtol=0, atol=.01)
            audit.append({'candidate': candidate['id'], 'purpose': candidate['purpose'],
                          'before_gmv': values[0], 'after_gmv': values[1],
                          'passed_amount_contract': bool(matches)})
        assert audit[0]['passed_amount_contract'] is False
        assert audit[1]['passed_amount_contract'] is True
    buyer = pd.read_csv(out / 'dimension_bridge.csv')
    buyer = buyer[buyer.dimension == 'buyer_type']
    top = cross.iloc[0]
    change = (weekday.standardized_daily_gmv.iloc[1] /
              weekday.standardized_daily_gmv.iloc[0] - 1) * 100
    evidence = {
        'before': before, 'after': after,
        'weekday_standardized_change_pct': float(change),
        'top_cross_segment': top.to_dict(),
        'buyer_bridge': buyer.to_dict('records'),
        'seller_bridge': seller.to_dict('records'),
        'ai_provenance': review['provenance'], 'ai_sql_audit': audit,
        'claims_scope': 'Arithmetic contributions and observational diagnostics; not proven causal mechanisms.'
    }
    (out / 'diagnosis.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    pd.DataFrame(audit).to_csv(out / 'ai_sql_audit.csv', index=False)
    con.close()
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
