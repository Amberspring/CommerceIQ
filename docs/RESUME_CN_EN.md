# CommerceIQ 中英文简历部分

只展示一个项目。正文按业务诊断、分析流程、工具能力与实际 AI 辅助组织；X5 作为项目扩展保留在仓库与面试材料中，简历主段不必铺开。日期以真实开始时间为准，本地项目当前为 2026 年 10 月构建。没有企业上线收益，不写效果提升或生产 API。

## 中文：可手动复制到“项目经历”

**CommerceIQ 电商经营异动诊断与 AI 辅助分析 | 个人项目**　**2026.10—今**

- **订单建模与分析工作流：** 基于 Olist 约10万笔真实订单，运用 SQL、Python 与 DuckDB 整合9张数据表，按订单粒度预聚合支付、商品与评价数据，完成16项质量校验；建立“指标口径—数据核查—异动拆解—假设验证—建议输出”的分析流程。
- **GMV异动拆解与业务诊断：** 复盘月度商品GMV下降12.43%的案例，用Shapley分解购买人数、频次与客单价，量化购买人数变化占净下降的74.7%；按地区、品类、购买群体与Seller交叉下钻，通过等长窗口、星期结构及订单状态检查验证下降方向。
- **用户分层与Seller经营分析：** 构建RFM规则分层、购买Cohort留存与Seller次月活跃留存，结合卖家活跃状态、迟到率与评价筛选业务解释；搭建Streamlit交互看板，支持经营趋势监测、贡献下钻与后续取证优先级判断。
- **AI辅助SQL与证据审核：** 使用Codex辅助SQL编写、排查假设和报告草稿，保存提示词、候选查询与审核记录；通过金额守恒校验拦截JOIN重复计数反例，区分数据支持的结论与待验证机制，形成可复现的业务诊断报告。

## English: copy into “Academic & Applied Projects”

**CommerceIQ: E-Commerce Performance Diagnostics & AI-Assisted Analytics | Independent Project**　**Oct 2026 – Present**

- **Order Modeling and Analytics Workflow:** Integrated 9 Olist tables covering approximately 100,000 real orders using SQL, Python and DuckDB; pre-aggregated item, payment and review data to the order grain and completed 16 data-quality checks, connecting metric definitions, data validation, anomaly decomposition, hypothesis checks and recommendations.
- **GMV Decomposition and Business Diagnostics:** Investigated a 12.43% monthly decline in merchandise GMV using Shapley decomposition of buyers, purchase frequency and AOV; quantified buyer-count changes as 74.7% of the net decline and drilled into region, category, buyer cohort and seller segments, checking equal-length windows, weekday composition and order-status definitions.
- **Customer and Seller Analytics:** Built rule-based RFM segments, purchase-cohort retention and next-month seller activity retention; examined seller activity, delivery delays and reviews to assess business explanations, and developed a Streamlit dashboard for trend monitoring, contribution analysis and investigation prioritization.
- **AI-Assisted SQL and Evidence Review:** Used Codex to assist SQL development, hypothesis generation and report drafting; retained prompts, candidate queries and review records, rejected a JOIN double-counting test case through amount-reconciliation checks, and documented supported findings separately from unverified mechanisms in a reproducible diagnostic report.

## 面试使用前手动检查

1. 自己复跑 `run_olist.py` 与 `run_diagnostics.py`，解释 customer_unique_id、订单粒度与金额口径。
2. 能讲清74.7%是购买人数的 Shapley 金额贡献／净 GMV 下降，不是流量下降、人数下降幅度或因果解释比例。
3. 能解释新购买群体不是新注册、Seller无单不是退出、评分与履约发生在购买之后。
4. AI使用是本轮编码助手协助，并非自建生产LLM系统；反例是主动校验样例，不是实际生产故障。
