"""Exact arithmetic attribution. Contributions are NOT causal effects."""
from itertools import permutations
import numpy as np
import pandas as pd

def shapley_product(before, after):
    """Average all replacement orders; interactions shared symmetrically."""
    if set(before) != set(after):
        raise ValueError('Both periods need the same factors')
    names = list(before)
    result = dict.fromkeys(names, 0.0)
    paths = list(permutations(names))
    for path in paths:
        state = dict(before)
        for name in path:
            old = np.prod(list(state.values()))
            state[name] = after[name]
            result[name] += float(np.prod(list(state.values())) - old) / len(paths)
    return result

def dimension_bridge(items, dimension, before, after):
    periods = items[items['month'].isin([before, after])]
    totals = periods.groupby([dimension, 'month'], dropna=False)['price'].sum().unstack(fill_value=0)
    for period in [before, after]:
        if period not in totals:
            totals[period] = 0.0
    result = pd.DataFrame({'segment': totals.index.astype(str),
                           'before_gmv': totals[before].values, 'after_gmv': totals[after].values})
    baseline = result.before_gmv.sum()
    result['delta'] = result.after_gmv - result.before_gmv
    result['contribution_pp'] = result.delta / baseline * 100 if baseline else np.nan
    result['dimension'] = dimension
    # Each dimension independently reconciles to the same overall GMV delta.
    return result.sort_values('delta')

def daily_alerts(orders):
    """Same-weekday trailing 8-week median/MAD, including zero-order days."""
    dates = pd.to_datetime(orders.order_purchase_timestamp).dt.normalize()
    daily = orders.assign(day=dates).groupby('day').item_gmv.sum().asfreq('D', fill_value=0).to_frame('gmv')
    daily['weekday'] = daily.index.dayofweek
    daily['expected'] = np.nan
    daily['mad'] = np.nan
    for _, group in daily.groupby('weekday'):
        values = group.gmv
        median = values.shift(1).rolling(8, min_periods=6).median()
        mad = values.shift(1).rolling(8, min_periods=6).apply(lambda x: np.median(np.abs(x-np.median(x))))
        daily.loc[group.index, 'expected'] = median
        daily.loc[group.index, 'mad'] = mad
    daily['robust_z'] = (daily.gmv - daily.expected) / (1.4826 * daily.mad.replace(0, np.nan))
    daily['alert'] = daily.robust_z.abs() > 3.5
    return daily.reset_index()
