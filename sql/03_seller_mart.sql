-- One row per seller-order to avoid item-weighted service metrics.
CREATE OR REPLACE TABLE mart_seller_orders AS
SELECT seller_id, order_id, month, SUM(price) AS gmv,
       MAX(CAST(is_late AS INTEGER)) AS is_late, MAX(review_score) AS review_score,
       MAX(order_purchase_timestamp) AS purchased_at
FROM mart_items
WHERE order_status = 'delivered' AND month >= DATE '2017-01-01' AND month < DATE '2018-09-01'
GROUP BY 1,2,3;

CREATE OR REPLACE TABLE mart_sellers AS
SELECT seller_id, SUM(gmv) AS gmv, COUNT(*) AS seller_orders,
       COUNT(DISTINCT month) AS active_months,
       COUNT(DISTINCT CAST(purchased_at AS DATE)) AS active_days,
       AVG(is_late) AS late_rate, COUNT(is_late) AS delivery_observations,
       AVG(review_score) AS review_score, COUNT(review_score) AS review_observations,
       MIN(month) AS first_observed_month, MAX(month) AS last_observed_month
FROM mart_seller_orders GROUP BY 1;

CREATE OR REPLACE TABLE mart_seller_retention AS
WITH activity AS (
    SELECT DISTINCT seller_id, month FROM mart_seller_orders
)
SELECT a.month, COUNT(*) AS active_sellers,
       COUNT(b.seller_id) AS retained_next_month,
       COUNT(b.seller_id)::DOUBLE / COUNT(*) AS retention
FROM activity a LEFT JOIN activity b
ON a.seller_id = b.seller_id AND b.month = a.month + INTERVAL '1 month'
WHERE a.month < DATE '2018-08-01'
GROUP BY a.month ORDER BY a.month;

CREATE OR REPLACE TABLE mart_seller_bridge AS
WITH m AS (
    SELECT seller_id, month, SUM(gmv) AS gmv FROM mart_seller_orders GROUP BY 1,2
), periods AS (
    SELECT DISTINCT month FROM m WHERE month > DATE '2017-01-01'
), grid AS (
    SELECT p.month, s.seller_id,
           COALESCE(prev.gmv, 0) AS previous_gmv, COALESCE(curr.gmv, 0) AS current_gmv
    FROM periods p CROSS JOIN (SELECT DISTINCT seller_id FROM m) s
    LEFT JOIN m prev ON prev.seller_id=s.seller_id AND prev.month=p.month-INTERVAL '1 month'
    LEFT JOIN m curr ON curr.seller_id=s.seller_id AND curr.month=p.month
)
SELECT *, current_gmv - previous_gmv AS delta,
       CASE WHEN previous_gmv=0 AND current_gmv>0 THEN 'new_or_reactivated'
            WHEN previous_gmv>0 AND current_gmv=0 THEN 'inactive_this_month'
            ELSE 'continuing' END AS seller_status
FROM grid WHERE previous_gmv>0 OR current_gmv>0;
