"""User-level binary-outcome inference; random assignment is a required assumption."""
import math
import numpy as np
from scipy.stats import norm, chisquare

def binary_effect(y, t):
    y, t = np.asarray(y), np.asarray(t)
    if not set(np.unique(y)).issubset({0, 1}) or set(np.unique(t)) != {0, 1}:
        raise ValueError('Binary outcome and both treatment arms required')
    y0, y1 = y[t==0], y[t==1]
    p0, p1 = y0.mean(), y1.mean()
    effect = p1-p0
    se = np.sqrt(p1*(1-p1)/len(y1) + p0*(1-p0)/len(y0))
    pooled = y.mean()
    null_se = np.sqrt(pooled*(1-pooled)*(1/len(y0)+1/len(y1)))
    p = 2*norm.sf(abs(effect/null_se)) if null_se else (1.0 if effect==0 else 0.0)
    return {'n_control': len(y0), 'n_treatment': len(y1), 'control_rate': float(p0),
            'treatment_rate': float(p1), 'effect': float(effect),
            'relative_lift': float(effect/p0) if p0 else None,
            'ci_low': float(effect-1.96*se), 'ci_high': float(effect+1.96*se), 'p_value': float(p)}

def sample_size(p0, absolute_mde, alpha=0.05, power=0.8):
    p1 = p0+absolute_mde
    if not 0 < p0 < p1 < 1 or not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError('Invalid planning parameters')
    avg = (p0+p1)/2
    num = norm.ppf(1-alpha/2)*np.sqrt(2*avg*(1-avg)) + norm.ppf(power)*np.sqrt(p0*(1-p0)+p1*(1-p1))
    return math.ceil((num/absolute_mde)**2)

def srm(t, expected_treatment=0.5):
    n = len(t)
    counts = [int((np.asarray(t)==0).sum()), int((np.asarray(t)==1).sum())]
    return float(chisquare(counts, [n*(1-expected_treatment), n*expected_treatment]).pvalue)

def bootstrap_effect(y, t, seed=42, n_boot=2000):
    """Binomial bootstrap is exact for resampling binary observations within arms."""
    stats = binary_effect(y, t)
    rng = np.random.default_rng(seed)
    n0, n1 = stats['n_control'], stats['n_treatment']
    samples = rng.binomial(n1, stats['treatment_rate'], n_boot)/n1 - rng.binomial(n0, stats['control_rate'], n_boot)/n0
    return [float(x) for x in np.quantile(samples, [.025, .975])]

def top_policy(y, t, scores, fraction=.3):
    # stable sort: input rows are randomized by the split, ties deterministic.
    n = math.ceil(len(y)*fraction)
    ids = np.argsort(-np.asarray(scores), kind='stable')[:n]
    result = binary_effect(np.asarray(y)[ids], np.asarray(t)[ids])
    result['selected_customers'] = n
    result['fraction'] = fraction
    result['bootstrap_ci'] = bootstrap_effect(np.asarray(y)[ids], np.asarray(t)[ids])
    return result

def profit_scenario(effect, audience, margin_per_incremental_buyer, cost_per_contact):
    """Assumptions supplied by caller; not measured historical ROI."""
    cost = audience*cost_per_contact
    gain = audience*effect*margin_per_incremental_buyer
    return {'incremental_buyers': audience*effect, 'incremental_margin': gain,
            'contact_cost': cost, 'net_profit': gain-cost,
            'roi': (gain-cost)/cost if cost>0 else None}
