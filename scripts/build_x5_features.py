"""Aggregate all historical rows in DuckDB without loading 4 GB into pandas."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import json
import duckdb
import pandas as pd
from src.warehouse import ROOT

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demographics-only', action='store_true')
    args = parser.parse_args()
    out = ROOT/'data/processed'
    out.mkdir(parents=True, exist_ok=True)
    labels = pd.read_csv(ROOT/'data/raw/x5/uplift_train.csv.gz', dtype={'client_id':str})
    clients = pd.read_csv(ROOT/'data/raw/x5/clients.csv.gz', dtype={'client_id':str})
    assert labels.client_id.is_unique and clients.client_id.is_unique
    assert labels.target.isin([0,1]).all() and labels.treatment_flg.isin([0,1]).all()
    df = labels.merge(clients, on='client_id', how='left', validate='one_to_one', indicator=True)
    assert df['_merge'].eq('both').all()
    df = df.drop(columns='_merge')
    # Calendar campaign date isn't published in these tables. For full history,
    # use end-of-history as proxy, since upstream explicitly calls it precommunication.
    cutoff = None
    audit = {'labeled_clients':len(labels), 'client_rows':len(clients),
             'feature_mode':'demographics_only' if args.demographics_only else 'full_history',
             'randomization_audit_available':False,
             'excluded_fields':['client_id (as predictor)', 'first_redeem_date', 'target', 'treatment_flg']}
    if not args.demographics_only:
        path = ROOT/'data/raw/x5/purchases.csv.gz'
        if not path.exists():
            raise FileNotFoundError('Fetch --x5-full; no silent sample or synthetic fallback')
        con = duckdb.connect(str(out/'x5_features.duckdb'))
        con.execute("SET memory_limit='2GB'")
        con.execute('SET threads=4')
        literal = str(path).replace("'", "''")
        con.execute(f"CREATE OR REPLACE VIEW purchases AS SELECT * FROM read_csv('{literal}', types={{'client_id':'VARCHAR','transaction_id':'VARCHAR','product_id':'VARCHAR','store_id':'VARCHAR','transaction_datetime':'TIMESTAMP'}})")
        con.register('labeled_clients', labels[['client_id']])
        coverage = con.execute('SELECT COUNT(*), MIN(transaction_datetime), MAX(transaction_datetime) FROM purchases').fetchone()
        cutoff = pd.Timestamp(coverage[2]).normalize()+pd.Timedelta(days=1)
        con.execute('CREATE OR REPLACE TABLE history_cutoff AS SELECT CAST(? AS TIMESTAMP) AS cutoff', [cutoff])
        print('History coverage:', coverage, flush=True)
        con.execute((ROOT/'sql/05_x5_features.sql').read_text(encoding='utf-8'))
        history = con.execute('SELECT * FROM x5_history JOIN x5_diversity USING(client_id)').df()
        df = df.merge(history, on='client_id', how='left', validate='one_to_one')
        audit.update({'purchase_rows':coverage[0], 'history_start':str(coverage[1]),
                      'history_end':str(coverage[2]), 'cutoff_proxy':str(cutoff),
                      'clients_with_history':len(history),
                      'inconsistent_basket_values':con.execute('SELECT COUNT(*) FROM x5_transactions WHERE basket_value_versions>1').fetchone()[0]})
        con.close()
    df['age'] = pd.to_numeric(df.age, errors='coerce').where(lambda x:x.between(18,100))
    if cutoff is not None:
        issued = pd.to_datetime(df.first_issue_date, errors='coerce')
        df['card_tenure_days'] = (cutoff-issued).dt.total_seconds()/86400
        df.loc[df.card_tenure_days<0, 'card_tenure_days'] = float('nan')
    df = df.drop(columns=['first_issue_date','first_redeem_date'])
    df.to_parquet(out/'x5_features.parquet', index=False)
    (ROOT/'outputs/x5').mkdir(parents=True, exist_ok=True)
    (ROOT/'outputs/x5/features_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit, indent=2), flush=True)

if __name__=='__main__':
    main()
