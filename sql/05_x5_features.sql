-- purchases is a view over original gzip, restricted to labeled clients.
-- purchase_sum repeats per product row; reduce to ONE basket before summing.
CREATE OR REPLACE TABLE x5_transactions AS
SELECT p.client_id, p.transaction_id,
       MIN(p.transaction_datetime) AS purchased_at,
       MAX(p.purchase_sum) AS basket_value,
       COUNT(DISTINCT p.purchase_sum) AS basket_value_versions
FROM purchases p JOIN labeled_clients l USING(client_id)
GROUP BY 1,2;

CREATE OR REPLACE TABLE x5_history AS
SELECT client_id, COUNT(*) AS historical_transactions,
       SUM(basket_value) AS historical_spend, AVG(basket_value) AS historical_aov,
       DATE_DIFF('day', MAX(purchased_at), (SELECT cutoff FROM history_cutoff)) AS historical_recency,
       DATE_DIFF('day', MIN(purchased_at), MAX(purchased_at)) AS history_span,
       SUM(CASE WHEN purchased_at >= (SELECT cutoff FROM history_cutoff) - INTERVAL '30 day'
                THEN 1 ELSE 0 END) AS transactions_last30
FROM x5_transactions GROUP BY 1;

CREATE OR REPLACE TABLE x5_diversity AS
SELECT p.client_id, COUNT(DISTINCT p.store_id) AS historical_stores,
       COUNT(DISTINCT p.product_id) AS historical_products,
       SUM(p.product_quantity) AS historical_units
FROM purchases p JOIN labeled_clients l USING(client_id) GROUP BY 1;
