-- Receipts, not visitors: all quantities below describe observed purchases.
CREATE OR REPLACE TABLE mart_state_category AS
SELECT month, customer_state, category, buyer_type,
       SUM(price) AS gmv, COUNT(DISTINCT order_id) AS orders,
       COUNT(DISTINCT customer_unique_id) AS buyers
FROM mart_items WHERE order_status='delivered'
GROUP BY 1,2,3,4;

-- Include zero-order calendar days; equal weighting of weekdays removes only
-- weekday composition, not holidays, trends, outages or missing source rows.
CREATE OR REPLACE TABLE mart_weekday_sales AS
WITH calendar AS (
    SELECT CAST(d AS DATE) AS day FROM generate_series(
        TIMESTAMP '2017-01-01', TIMESTAMP '2018-08-31', INTERVAL '1 day') t(d)
), daily AS (
    SELECT CAST(order_purchase_timestamp AS DATE) AS day,
           SUM(item_gmv) AS gmv, COUNT(*) AS orders
    FROM mart_orders WHERE order_status='delivered' GROUP BY 1
)
SELECT CAST(DATE_TRUNC('month', c.day) AS DATE) AS month,
       EXTRACT(dow FROM c.day) AS weekday, COUNT(*) AS calendar_days,
       SUM(COALESCE(d.gmv,0)) AS gmv,
       AVG(COALESCE(d.gmv,0)) AS mean_daily_gmv
FROM calendar c LEFT JOIN daily d USING(day) GROUP BY 1,2;

-- Final delivery/review outcomes for purchase cohorts; these may occur later
-- than the purchase month and cannot explain that month's purchases causally.
CREATE OR REPLACE TABLE mart_service_monthly AS
SELECT month, COUNT(*) AS all_orders,
       COUNT(*) FILTER (WHERE order_status='delivered') AS delivered_orders,
       COUNT(*) FILTER (WHERE order_status IN ('canceled','unavailable')) AS failed_orders,
       COUNT(*) FILTER (WHERE order_status='delivered' AND is_late IS NOT NULL) AS delivery_observations,
       AVG(CAST(is_late AS INTEGER)) FILTER (WHERE order_status='delivered') AS late_rate,
       AVG(delivery_days) FILTER (WHERE order_status='delivered') AS mean_delivery_days,
       AVG(review_score) FILTER (WHERE order_status='delivered') AS mean_review,
       COUNT(review_score) FILTER (WHERE order_status='delivered') AS review_observations
FROM mart_orders GROUP BY 1;
