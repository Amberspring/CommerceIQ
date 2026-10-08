# 数据来源、口径与限制

## Olist

官方来源：[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)。从官方 Kaggle 下载接口获取，9 张原始 CSV；下载包 SHA256 在 `data/manifest.json`。官方 Kaggle API 的许可元数据为 **CC BY-NC-SA 4.0**，不是某些第三方镜像标注的 CC0。学习作品集使用需保留数据来源，衍生数据发布遵循原许可。

主指标：**按下单月归属、最终状态 delivered 的商品金额 SUM(price)**。不含运费，不是平台营收、净收入或利润；包含多商品、多卖家订单。一行 item 代表一个售出 item，不存在可直接再乘的数量列。支付表聚合金额另存，仅用来核对，并不强制等于商品金额。

主观察窗口 `[2017-01-01, 2018-09-01)`。2016 年样本很少、2018 年 9/10 月几乎没有完成订单，不进入主要经营比较。**窗口内并不保证抽样完整；尤其 2018-08 和最终完成状态存在右删失。** 选 2018-05/06 作为可复盘的异动案例，不称为事先预注册的假设检验。

`customer_id` 为订单关联键，`customer_unique_id` 才是跨订单用户键。首次观测购买不等于注册/平台获客；RFM 与 cohort 的首次定义是主窗口内首次完成购买。`buyer_type` 使用全导出完成订单中的首次月份。两者观测范围不同，应分别解释。新客月内第二单仍计入该月 new cohort。

Seller 服务指标先聚合至 seller-order；一个多卖家订单可同时进入多个 Seller 订单数，因此不能相加推回平台订单数。评价去重取最新观测记录，服务分析是最终快照；若模拟当时决策，需按 as-of 日期截断评价。整单评分不能明确归责给某一个 Seller。

Olist 无曝光、广告、营销分组、优惠券成本、利润、完整退货流水、真实入驻/退出日期、天气与缺货数据。不能从掉单直接认定流量被压制，也不能做真实 coupon ROI。

## X5 RetailHero

来源：[官方竞赛与字段说明](https://ods.ai/competitions/x5-retailhero-uplift-modeling/data)、[scikit-uplift 官方加载器与数据说明](https://www.uplift-modeling.com/en/latest/api/datasets/fetch_x5.html)。实际下载的是其公开 S3 文件，三个文件均验证上游 MD5，再记录 SHA256。

- `clients.csv.gz`：400,162 位客户；
- `uplift_train.csv.gz`：200,039 位带标签客户，`client_id / treatment_flg / target`；
- `purchases.csv.gz`：45,786,568 条干预前商品购买明细。

实际字段是 **client_id**（部分加载器 docstring 写 customer_id）。`treatment_flg` 官方定义为是否进行了触达；`target` 为之后是否购买。历史数据截止 2019-03-18，官方称为干预前购买。3 月 19 日作为特征截止代理日期，**不是已验证的短信发送日期**。

公开页面未提供可独立审计的随机分配协议、分配/曝光区别、短信执行日志、精确结局窗口和退出数据。因此本项目给出两组购买率差、置信区间和 uplift 排序评估；**因果解读以随机分配、可比结局窗口、无干扰等假设为前提**。50/50 SRM 与特征平衡正常也不能证明随机化。

`purchase_sum` 为 basket 总额，会重复在多个商品行；先 `(client_id, transaction_id)` 取 MAX 再按客户 SUM，同时核对 basket 金额是否一致。`first_redeem_date` 被排除，防止其语义/时间可用性不明导致泄漏。模型只用年龄、性别、截至历史末的发卡时长与历史交易特征，不用 ID/target/treatment 作为普通特征。S-learner 特别添加 treatment 用于估计潜在结果。

X5 原始数据的单独再分发许可证在已查阅材料中未明确确认。下载使用官方竞赛公开镜像，仓库不提交原始数据或带客户 ID 的模型预测；公开发布前核实原始竞赛使用条款。sklift 的 MIT 不代表 X5 数据是 MIT。

## 两套数据的关系

Olist 为经营分析案例，X5 为独立营销评估案例，品牌、地域、时间、用户完全不同，不拼接、不把 X5 的购买 uplift 套成 Olist GMV/利润提升。
