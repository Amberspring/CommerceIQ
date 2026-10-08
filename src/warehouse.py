from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data/warehouse/commerceiq.duckdb'
TABLES = {
    'orders': 'olist_orders_dataset.csv',
    'customers': 'olist_customers_dataset.csv',
    'order_items': 'olist_order_items_dataset.csv',
    'order_payments': 'olist_order_payments_dataset.csv',
    'order_reviews': 'olist_order_reviews_dataset.csv',
    'products': 'olist_products_dataset.csv',
    'sellers': 'olist_sellers_dataset.csv',
    'category_translation': 'product_category_name_translation.csv',
    'geolocation': 'olist_geolocation_dataset.csv',
}

def build():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    con.execute("SET memory_limit='2GB'")
    for table, name in TABLES.items():
        path = ROOT / 'data/raw/olist' / name
        if not path.exists():
            raise FileNotFoundError(f'Original CSV missing: {path}. Run scripts/download_data.py')
        # Strings preserve leading-zero ZIP prefixes. Timestamp fields cast explicitly.
        con.execute(f'CREATE OR REPLACE TABLE raw_{table} AS SELECT * FROM read_csv(?, all_varchar=true)', [str(path)])
    numeric = {
        'order_items': ['order_item_id', 'price', 'freight_value'],
        'order_payments': ['payment_sequential', 'payment_installments', 'payment_value'],
        'order_reviews': ['review_score'],
    }
    for table, fields in numeric.items():
        for field in fields:
            con.execute(f'ALTER TABLE raw_{table} ALTER {field} TYPE DOUBLE USING CAST({field} AS DOUBLE)')
    for field in ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date',
                  'order_delivered_customer_date', 'order_estimated_delivery_date']:
        con.execute(f'ALTER TABLE raw_orders ALTER {field} TYPE TIMESTAMP USING CAST({field} AS TIMESTAMP)')
    for field in ['review_creation_date', 'review_answer_timestamp']:
        con.execute(f'ALTER TABLE raw_order_reviews ALTER {field} TYPE TIMESTAMP USING CAST({field} AS TIMESTAMP)')
    for name in ['01_order_mart.sql', '02_customer_mart.sql', '03_seller_mart.sql']:
        con.execute((ROOT / 'sql' / name).read_text(encoding='utf-8'))
    return con

def quality(con):
    checks = []
    def check(name, value, expected):
        passed = abs(value-expected) < 0.01
        checks.append({'check': name, 'actual': value, 'expected': expected, 'passed': passed})
        if not passed:
            raise AssertionError(f'{name}: {value} != {expected}')
    for table, key in [('orders','order_id'), ('customers','customer_id'), ('products','product_id'),
                       ('sellers','seller_id'), ('category_translation','product_category_name')]:
        row = con.execute(f'SELECT COUNT(*), COUNT(DISTINCT {key}) FROM raw_{table}').fetchone()
        check(f'{table} unique key', *row)
    check('item composite key', *con.execute('SELECT COUNT(*), COUNT(DISTINCT (order_id, order_item_id)) FROM raw_order_items').fetchone())
    for child, parent, key in [('order_items','orders','order_id'), ('order_payments','orders','order_id'),
                               ('order_reviews','orders','order_id'), ('orders','customers','customer_id'),
                               ('order_items','products','product_id'), ('order_items','sellers','seller_id')]:
        n = con.execute(f'SELECT COUNT(*) FROM raw_{child} c LEFT JOIN raw_{parent} p USING({key}) WHERE p.{key} IS NULL').fetchone()[0]
        check(f'{child}->{parent} FK', n, 0)
    check('order mart cardinality', con.execute('SELECT COUNT(*) FROM mart_orders').fetchone()[0],
          con.execute('SELECT COUNT(*) FROM raw_orders').fetchone()[0])
    check('item mart cardinality', con.execute('SELECT COUNT(*) FROM mart_items').fetchone()[0],
          con.execute('SELECT COUNT(*) FROM raw_order_items').fetchone()[0])
    check('GMV reconciliation all statuses', con.execute('SELECT SUM(item_gmv) FROM mart_orders').fetchone()[0],
          con.execute('SELECT SUM(price) FROM raw_order_items').fetchone()[0])
    check('payment reconciliation', con.execute('SELECT SUM(payment_value) FROM mart_orders').fetchone()[0],
          con.execute('SELECT SUM(payment_value) FROM raw_order_payments').fetchone()[0])
    return checks
