"""Build validated marts and evidence tables from the original Olist CSVs."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import json
import numpy as np
import pandas as pd
from src.warehouse import ROOT, build, quality
from src.attribution import shapley_product, dimension_bridge, daily_alerts

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--before', default='2018-05-01')
    p.add_argument('--after', default='2018-06-01')
    args = p.parse_args()
    before, after = pd.Timestamp(args.before), pd.Timestamp(args.after)
    if before.day != 1 or after.day != 1 or before == after:
        raise ValueError('Use distinct month start dates')
    if not all(pd.Timestamp('2017-01-01') <= d <= pd.Timestamp('2018-08-01') for d in [before, after]):
        raise ValueError('Use primary observation window 2017-01 through 2018-08')
    out = ROOT / 'outputs/olist'
    out.mkdir(parents=True, exist_ok=True)
    con = build()
    checks = quality(con)
    (out / 'quality.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
    for table in ['monthly','rfm','customer_retention','sellers','seller_retention','seller_bridge']:
        df = con.execute(f'SELECT * FROM mart_{table}').df()
        df.to_csv(out / f'{table}.csv', index=False)
    monthly = con.execute('SELECT * FROM mart_monthly').df().set_index('month')
    factors = ['buyers', 'frequency', 'aov']
    a, b = monthly.loc[before], monthly.loc[after]
    values = shapley_product(a[factors].to_dict(), b[factors].to_dict())
    delta = float(b.gmv-a.gmv)
    assert np.isclose(sum(values.values()), delta)
    factor_table = pd.DataFrame({'factor': values.keys(), 'delta': values.values()})
    factor_table['contribution_pp'] = factor_table.delta/a.gmv*100
    factor_table.to_csv(out/'factor_bridge.csv', index=False)
    items = con.execute("SELECT * FROM mart_items WHERE order_status='delivered'").df()
    bridges = []
    for dimension in ['customer_state','category','buyer_type','seller_id']:
        bridge = dimension_bridge(items, dimension, before, after)
        assert np.isclose(bridge.delta.sum(), delta)
        bridges.append(bridge)
    pd.concat(bridges).to_csv(out/'dimension_bridge.csv', index=False)
    delivered = con.execute("SELECT * FROM mart_orders WHERE order_status='delivered' AND month >= '2017-01-01' AND month < '2018-09-01'").df()
    daily_alerts(delivered).to_csv(out/'daily_alerts.csv', index=False)
    # Different month lengths and status conditioning are separate sensitivities.
    sensitivity = []
    for label, window, status in [('delivered_full_month','full','delivered'),
                                   ('delivered_first_28_days','28','delivered'),
                                   ('non_cancelled_full_month','full','non_cancelled')]:
        query = "SELECT month, SUM(item_gmv) AS gmv, COUNT(*) AS orders FROM mart_orders WHERE month IN (?, ?)"
        query += " AND order_status='delivered'" if status=='delivered' else " AND order_status NOT IN ('canceled', 'unavailable')"
        if window=='28':
            query += " AND EXTRACT(day FROM order_purchase_timestamp)<=28"
        df = con.execute(query+' GROUP BY month ORDER BY month', [before, after]).df().set_index('month')
        sensitivity.append({'definition': label, 'before_gmv': float(df.loc[before].gmv),
                            'after_gmv': float(df.loc[after].gmv),
                            'change_pct': float((df.loc[after].gmv/df.loc[before].gmv-1)*100)})
    pd.DataFrame(sensitivity).to_csv(out/'sensitivity.csv', index=False)
    con.execute("SELECT month, order_status, COUNT(*) AS orders FROM mart_orders GROUP BY 1,2 ORDER BY 1,2").df().to_csv(out/'status_coverage.csv', index=False)
    con.execute("SELECT month, buyer_type, COUNT(*) AS orders, COUNT(DISTINCT customer_unique_id) AS buyers, SUM(item_gmv) AS gmv FROM mart_orders WHERE order_status='delivered' GROUP BY 1,2 ORDER BY 1,2").df().to_csv(out/'buyer_monthly.csv', index=False)
    con.execute("SELECT is_late, COUNT(*) AS orders, COUNT(review_score) AS reviews, AVG(review_score) AS review_score FROM mart_orders WHERE order_status='delivered' AND month BETWEEN '2017-01-01' AND '2018-08-01' GROUP BY 1").df().to_csv(out/'delivery_reviews.csv', index=False)
    case = {'before': str(before.date()), 'after': str(after.date()),
            'before_gmv': float(a.gmv), 'after_gmv': float(b.gmv), 'delta': delta,
            'change_pct': float(delta/a.gmv*100), 'shapley': values,
            'before_orders': int(a.orders), 'after_orders': int(b.orders),
            'before_buyers': int(a.buyers), 'after_buyers': int(b.buyers),
            'before_aov': float(a.aov), 'after_aov': float(b.aov),
            'quality_checks': len(checks), 'causal_claim': False}
    (out/'case.json').write_text(json.dumps(case, indent=2), encoding='utf-8')
    con.close()
    print(json.dumps(case, indent=2), flush=True)

if __name__ == '__main__':
    main()
