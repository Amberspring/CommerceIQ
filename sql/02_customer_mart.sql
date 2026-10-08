-- Fixed observation window [2017-01-01, 2018-09-01); snapshot 2018-09-01.
-- Customer unique ID is the identity across orders; never customer_id.
CREATE OR REPLACE TABLE mart_rfm AS
WITH rfm AS (
    SELECT customer_unique_id,
           DATE_DIFF('day', MAX(CAST(order_purchase_timestamp AS DATE)), DATE '2018-09-01') AS recency,
           COUNT(*) AS frequency, SUM(item_gmv) AS monetary
    FROM mart_orders
    WHERE order_status = 'delivered'
      AND order_purchase_timestamp >= TIMESTAMP '2017-01-01'
      AND order_purchase_timestamp < TIMESTAMP '2018-09-01'
    GROUP BY 1
)
SELECT *,
    CASE WHEN frequency >= 2 AND recency <= 90 THEN 'loyal_recent'
         WHEN frequency >= 2 THEN 'repeat_at_risk'
         WHEN recency <= 90 THEN 'new_or_recent_single'
         ELSE 'inactive_single' END AS segment
FROM rfm;

-- Explicit observed zeros; future cells remain absent (right censoring).
CREATE OR REPLACE TABLE mart_customer_retention AS
WITH activity AS (
    SELECT DISTINCT customer_unique_id, month FROM mart_orders
    WHERE order_status = 'delivered' AND month >= DATE '2017-01-01' AND month < DATE '2018-09-01'
), firsts AS (
    SELECT customer_unique_id, MIN(month) AS cohort FROM activity GROUP BY 1
), sizes AS (
    SELECT cohort, COUNT(*) AS cohort_size FROM firsts GROUP BY 1
), counts AS (
    SELECT f.cohort, DATE_DIFF('month', f.cohort, a.month) AS month_index,
           COUNT(*) AS active_buyers
    FROM firsts f JOIN activity a USING(customer_unique_id) GROUP BY 1,2
), grid AS (
    SELECT cohort, cohort_size, UNNEST(RANGE(0, DATE_DIFF('month', cohort, DATE '2018-08-01') + 1)) AS month_index
    FROM sizes
)
SELECT g.*, COALESCE(c.active_buyers, 0) AS active_buyers,
       COALESCE(c.active_buyers, 0)::DOUBLE / g.cohort_size AS retention
FROM grid g LEFT JOIN counts c USING(cohort, month_index) ORDER BY cohort, month_index;
