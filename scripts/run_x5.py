"""Retrospective experiment readout + frozen validation-selected uplift policy."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import joblib
import numpy as np
import pandas as pd
from scipy.stats import false_discovery_control
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklift.metrics import qini_auc_score, uplift_auc_score, qini_curve
from src.warehouse import ROOT
from src.experiments import binary_effect, bootstrap_effect, sample_size, srm, top_policy

def main():
    out = ROOT/'outputs/x5'
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(ROOT/'data/processed/x5_features.parquet')
    y = df.target.to_numpy()
    t = df.treatment_flg.to_numpy()
    overall = binary_effect(y,t)
    overall['bootstrap_ci'] = bootstrap_effect(y,t)
    overall['srm_p_assuming_50_50'] = srm(t)
    overall['n_per_arm_for_1pp_mde'] = sample_size(float(overall['control_rate']), .01)
    overall['causal_interpretation'] = 'Conditional on random assignment, no interference and comparable observation windows; assignment protocol not independently audited.'
    (out/'ab_result.json').write_text(json.dumps(overall, indent=2), encoding='utf-8')
    # Balance diagnostics cannot establish randomization.
    balance = []
    for name in df.select_dtypes(include='number').columns:
        if name in ['target','treatment_flg']:
            continue
        a,b = df.loc[t==0,name].dropna(),df.loc[t==1,name].dropna()
        sd = np.sqrt((a.var()+b.var())/2)
        balance.append({'feature':name,'control_mean':a.mean(),'treatment_mean':b.mean(),
                        'smd':(b.mean()-a.mean())/sd if sd else 0,
                        'control_missing':df.loc[t==0,name].isna().mean(),
                        'treatment_missing':df.loc[t==1,name].isna().mean()})
    for gender in sorted(df.gender.dropna().unique()):
        a=(df.loc[t==0,'gender']==gender).mean(); b=(df.loc[t==1,'gender']==gender).mean()
        sd=np.sqrt((a*(1-a)+b*(1-b))/2)
        balance.append({'feature':'gender_'+gender,'control_mean':a,'treatment_mean':b,
                        'smd':(b-a)/sd if sd else 0,'control_missing':0,'treatment_missing':0})
    pd.DataFrame(balance).to_csv(out/'balance.csv',index=False)
    groups=[]
    for name,mask in [('age18_39',df.age.between(18,39)), ('age40_59',df.age.between(40,59)),
                       ('age60_100',df.age.between(60,100)), ('age_missing',df.age.isna())]:
        if mask.sum()>100 and df.loc[mask,'treatment_flg'].nunique()==2:
            groups.append({'segment':name,**binary_effect(y[mask],t[mask])})
    adjusted=false_discovery_control([g['p_value'] for g in groups],method='bh')
    for g,p in zip(groups,adjusted):
        g['bh_adjusted_p']=p
    pd.DataFrame(groups).to_csv(out/'exploratory_subgroups.csv',index=False)
    X=df.drop(columns=['client_id','treatment_flg','target'])
    # Joint stratification gives both arms and both outcomes in each split.
    train,rest=train_test_split(np.arange(len(df)),test_size=.4,random_state=42,stratify=2*t+y)
    val,test=train_test_split(rest,test_size=.5,random_state=43,stratify=(2*t+y)[rest])
    assert not (set(train)&set(val) or set(train)&set(test) or set(val)&set(test))
    split_names=np.empty(len(df),dtype=object)
    split_names[train]='train';split_names[val]='validation';split_names[test]='test'
    pd.DataFrame({'client_id':df.client_id,'split':split_names}).to_parquet(ROOT/'data/processed/x5_splits.parquet',index=False)
    numerical=X.select_dtypes(include='number').columns.tolist()
    prep=ColumnTransformer([('num',make_pipeline(SimpleImputer(strategy='median',add_indicator=True)),numerical),
                            ('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['gender'])])
    A=prep.fit_transform(X.iloc[train]); V=prep.transform(X.iloc[val]); E=prep.transform(X.iloc[test])
    def estimator():
        return HistGradientBoostingClassifier(max_iter=120,max_leaf_nodes=15,min_samples_leaf=200,
                                              l2_regularization=10,random_state=42)
    models={}
    scores={}
    # Response baseline learns P(Y=1|X), ignoring treatment.
    response=estimator().fit(A,y[train])
    models['response_baseline']=response
    scores['response_baseline']=(response.predict_proba(V)[:,1],response.predict_proba(E)[:,1])
    s=estimator().fit(np.column_stack([A,t[train]]),y[train])
    models['s_learner']=s
    def s_predict(Z):
        return s.predict_proba(np.column_stack([Z,np.ones(len(Z))]))[:,1]-s.predict_proba(np.column_stack([Z,np.zeros(len(Z))]))[:,1]
    scores['s_learner']=(s_predict(V),s_predict(E))
    m0=estimator().fit(A[t[train]==0],y[train][t[train]==0])
    m1=estimator().fit(A[t[train]==1],y[train][t[train]==1])
    models['t_learner']=(m0,m1)
    scores['t_learner']=(m1.predict_proba(V)[:,1]-m0.predict_proba(V)[:,1],
                         m1.predict_proba(E)[:,1]-m0.predict_proba(E)[:,1])
    # Random targeting baseline: reproducible random ranking unrelated to outcome.
    rng=np.random.default_rng(44)
    scores['random_baseline']=(rng.random(len(val)),rng.random(len(test)))
    val_results=[]
    for name,(sv,_) in scores.items():
        val_results.append({'model':name, 'uplift_at_30':top_policy(y[val],t[val],sv)['effect'],
                            'qini_auc':float(qini_auc_score(y[val],sv,t[val]))})
    # Only uplift learners compete. Freeze criterion before reading test metrics.
    winner=max([r for r in val_results if r['model'] in ['s_learner','t_learner']],key=lambda r:r['uplift_at_30'])['model']
    pd.DataFrame(val_results).to_csv(out/'validation_models.csv',index=False)
    test_results=[]; curves=[]
    for name,(_,st) in scores.items():
        policy=top_policy(y[test],t[test],st)
        test_results.append({'model':name,'selected_on_validation':name==winner,
                             'uplift_at_30':policy['effect'],'ci_low':policy['bootstrap_ci'][0],
                             'ci_high':policy['bootstrap_ci'][1],
                             'qini_auc':float(qini_auc_score(y[test],st,t[test])),
                             'uplift_auc':float(uplift_auc_score(y[test],st,t[test]))})
        cx,cy=qini_curve(y[test],st,t[test])
        stride=max(1,len(cx)//200)
        idx=np.unique(np.append(np.arange(0,len(cx),stride),len(cx)-1))
        curves.append(pd.DataFrame({'model':name,'fraction':cx[idx]/len(test),'incremental_responses':cy[idx]}))
    pd.DataFrame(test_results).to_csv(out/'test_models.csv',index=False)
    pd.concat(curves).to_csv(out/'qini_curves.csv',index=False)
    st=scores[winner][1]
    ranking=np.argsort(-st,kind='stable')
    deciles=[]
    for k,ids in enumerate(np.array_split(ranking,10),1):
        result=binary_effect(y[test][ids],t[test][ids])
        deciles.append({'decile':k,'predicted_uplift':float(st[ids].mean()),**result})
    pd.DataFrame(deciles).to_csv(out/'test_deciles.csv',index=False)
    policy=top_policy(y[test],t[test],st)
    plan={'seed':42,'split':'60/20/20 stratified on treatment × target, distinct client IDs',
          'train_n':len(train),'validation_n':len(val),'test_n':len(test),
          'features':X.columns.tolist(),'selected_model':winner,'selection_metric':'validation uplift at top 30%',
          'policy_fraction':.3,'test_policy':policy,'test_all_customers':binary_effect(y[test],t[test]),
          'uncertainty':'Bootstrap CI conditional on fitted model and selected policy; training variation excluded',
          'limitations':'Retrospective holdout, not a new randomized targeting experiment; no measured campaign profit'}
    (out/'model_card.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    pd.DataFrame({'client_id':df.iloc[test].client_id,'uplift':st,'treatment':t[test],'target':y[test]}).to_parquet(ROOT/'data/processed/x5_holdout.parquet',index=False)
    joblib.dump({'preprocessor':prep,'model':models[winner],'model_name':winner},ROOT/'data/processed/uplift_model.joblib')
    print(json.dumps({'ab':overall,'selected_model':winner,'test_top30':policy},indent=2),flush=True)

if __name__=='__main__':
    main()
