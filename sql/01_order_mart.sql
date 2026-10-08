-- Grain: one row per order. Child tables are reduced BEFORE joining.
CREATE OR REPLACE TABLE mart_orders AS
WITH items AS (
    SELECT order_id, SUM(price) AS item_gmv, SUM(freight_value) AS freight,
           COUNT(*) AS units, COUNT(DISTINCT seller_id) AS seller_count
    FROM raw_order_items GROUP BY order_id
), payments AS (
    SELECT order_id, SUM(payment_value) AS payment_value,
           COUNT(*) AS payment_records
    FROM raw_order_payments GROUP BY order_id
), reviews AS (
    SELECT order_id, review_score
    FROM raw_order_reviews
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY order_id ORDER BY review_creation_date DESC,
        review_answer_timestamp DESC, review_id DESC, review_score DESC
    ) = 1
), first_purchase AS (
    SELECT c.customer_unique_id, MIN(o.order_purchase_timestamp) AS first_purchase
    FROM raw_orders o JOIN raw_customers c USING(customer_id)
    WHERE o.order_status = 'delivered'
    GROUP BY 1
)
SELECT o.*, c.customer_unique_id, c.customer_state, c.customer_city,
       CAST(DATE_TRUNC('month', o.order_purchase_timestamp) AS DATE) AS month,
       COALESCE(i.item_gmv, 0) AS item_gmv, COALESCE(i.freight, 0) AS freight,
       COALESCE(i.units, 0) AS units, COALESCE(i.seller_count, 0) AS seller_count,
       p.payment_value, p.payment_records, r.review_score,
       DATE_DIFF('day', o.order_purchase_timestamp, o.order_delivered_customer_date) AS delivery_days,
       CASE WHEN o.order_delivered_customer_date IS NULL THEN NULL
            ELSE CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE)
       END AS is_late,
       CASE WHEN DATE_TRUNC('month', o.order_purchase_timestamp) = DATE_TRUNC('month', f.first_purchase)
            THEN 'new' ELSE 'returning' END AS buyer_type
FROM raw_orders o
JOIN raw_customers c USING(customer_id)
LEFT JOIN items i USING(order_id)
LEFT JOIN payments p USING(order_id)
LEFT JOIN reviews r USING(order_id)
LEFT JOIN first_purchase f USING(customer_unique_id);

-- Grain: order item. GMV can be summed; order-level review/late flags repeat.
CREATE OR REPLACE TABLE mart_items AS
SELECT i.*, o.month, o.order_purchase_timestamp, o.order_status,
       o.customer_unique_id, o.customer_state, o.customer_city, o.buyer_type,
       o.is_late, o.review_score,
       COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
       s.seller_state, s.seller_city
FROM raw_order_items i
JOIN mart_orders o USING(order_id)
LEFT JOIN raw_products p USING(product_id)
LEFT JOIN raw_category_translation t USING(product_category_name)
LEFT JOIN raw_sellers s USING(seller_id);

CREATE OR REPLACE TABLE mart_monthly AS
SELECT month, SUM(item_gmv) AS gmv, COUNT(*) AS orders,
       COUNT(DISTINCT customer_unique_id) AS buyers,
       COUNT(*)::DOUBLE / COUNT(DISTINCT customer_unique_id) AS frequency,
       SUM(item_gmv) / COUNT(*) AS aov,
       AVG(CAST(is_late AS INTEGER)) AS late_rate,
       AVG(review_score) AS review_score
FROM mart_orders WHERE order_status = 'delivered'
GROUP BY month ORDER BY month;
