-- Top 3 sellers by GMV in each seller state and month. Ties retained.
WITH sales AS (
    SELECT seller_state, month, seller_id, SUM(price) AS gmv,
           COUNT(DISTINCT order_id) AS orders
    FROM mart_items WHERE order_status='delivered' GROUP BY 1,2,3
)
SELECT *, DENSE_RANK() OVER (PARTITION BY seller_state, month ORDER BY gmv DESC) AS rank
FROM sales QUALIFY rank <= 3;

-- Buyer first-month vs returning contribution. Order GMV avoids category duplication.
SELECT month, buyer_type, COUNT(*) AS orders, COUNT(DISTINCT customer_unique_id) AS buyers,
       SUM(item_gmv) AS gmv
FROM mart_orders WHERE order_status='delivered' GROUP BY 1,2 ORDER BY 1,2;

-- Daily data coverage / order status check before explaining a fall in GMV.
SELECT CAST(order_purchase_timestamp AS DATE) AS day, order_status, COUNT(*) AS orders
FROM mart_orders GROUP BY 1,2 ORDER BY 1,2;

-- Multi-seller orders mean seller order counts do NOT sum to platform orders.
SELECT month, COUNT(*) AS orders, SUM(seller_count) AS seller_orders,
       SUM(CASE WHEN seller_count>1 THEN 1 ELSE 0 END) AS multi_seller_orders
FROM mart_orders WHERE order_status='delivered' GROUP BY 1 ORDER BY 1;
