# SQL 练习：能写、能解释粒度

用 `.venv/Scripts/python` 的 DuckDB 连接 `data/warehouse/commerceiq.duckdb`，或 SQL 客户端打开该文件。以下问题对应已建 marts；`sql/04_interview_queries.sql` 是可运行示例，不需要背诵。

| 练习 | 核心思路 | 常见错法 |
|---|---|---|
| 每个 Seller 州每月 GMV Top3 | item price 按州/月/seller 聚合，DENSE_RANK | 先排名商品行；未讲并列时可能超过3行 |
| Seller 次月活动留存 | 先 distinct seller/month，self JOIN 月+1 | 商品表直接 JOIN 放大分母；最后月都标流失 |
| 用户月度首购/复购贡献 | unique_id 找首次月，订单级 SUM GMV | customer_id 冒充用户；本月第二单错误标老用户 |
| 买家 cohort 第 k 月留存 | 首次月 cohort + 月差 + distinct用户 | 未观测未来格当0；用户每单重复计数 |
| 多表金额核对 | payments/items/reviews 各先聚合再连接 | SUM(DISTINCT price) 误删相同价格的不同商品 |
| 掉单 Seller 分类 | 上月/本月 GMV full bridge，新/持续/无单 | 首次有单=入驻；一个月无单=永久退出 |
| X5 历史消费额 | client/transaction 先 MAX(purchase_sum) | 在商品明细上直接 SUM 整单金额 |

若要求**严格3个**且不保留并列，用 `ROW_NUMBER() OVER (... ORDER BY gmv DESC, seller_id)`，明确稳定 tie-break；如果要求同值同名次，用 DENSE_RANK。它们回答不同需求。

## 手写：Seller 次月留存

```sql
WITH active AS (
  SELECT DISTINCT seller_id, month FROM mart_seller_orders
)
SELECT a.month,
       COUNT(*) AS active_sellers,
       COUNT(b.seller_id) AS retained,
       COUNT(b.seller_id)::DOUBLE / COUNT(*) AS retention
FROM active a
LEFT JOIN active b
  ON b.seller_id = a.seller_id
 AND b.month = a.month + INTERVAL '1 month'
WHERE a.month < DATE '2018-08-01'
GROUP BY a.month ORDER BY a.month;
```

为什么 LEFT JOIN：没有下月单的 Seller 仍保留在分母。为什么先 DISTINCT：一个 Seller 多单不会重复。为什么排最后月：其下一月不在主观察范围。

## 手写：交叉下钻 SP × watches_gifts

```sql
SELECT month, seller_id, SUM(price) AS gmv,
       COUNT(DISTINCT order_id) AS seller_orders
FROM mart_items
WHERE order_status = 'delivered'
  AND customer_state = 'SP'
  AND category = 'watches_gifts'
  AND month IN (DATE '2018-05-01', DATE '2018-06-01')
GROUP BY month, seller_id
ORDER BY seller_id, month;
```

这能定位交叉子群变化，不能证明 Seller 经营差、平台少给曝光或用户被新店分流。
