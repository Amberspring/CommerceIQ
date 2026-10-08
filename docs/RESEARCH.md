# GitHub 调研与复用决策

调研日期：2026-10-04。实时 GitHub API 元数据、固定 commit 与查阅路径见 `research/repositories.json`。星数只反映关注度，不能证明代码质量；README 中的性能数字没有在本项目中独立复现。

| 项目 | 实际用途与可复用部分 | 评价与本项目决策 |
|---|---|---|
| [scikit-uplift](https://github.com/maks-sh/scikit-uplift) | `sklift/datasets/datasets.py` 的 X5 来源/MD5；`sklift/metrics/metrics.py` 的 Qini/AUUC/曲线 | 818 stars，MIT，成熟专用包；最近 push 2023，维护较慢。**直接调用 metrics API**；流式下载自行实现，保留上游校验值 |
| [Uber CausalML](https://github.com/uber/causalml) | README 的 meta-learner 方法选择，LICENSE 原文 | 6015 stars，Apache-2.0 原文（GitHub API 返回 NOASSERTION）。算法范围广，安装负担较高；首版用 sklearn 实现 S/T，作为后续 DR/X 扩展候选 |
| [feldlime/X5RetailHeroUplift](https://github.com/feldlime/X5RetailHeroUplift) | `load_and_prepare.py`、`features/` 结构；客户、交易、商品特征组织 | 3 stars，MIT，2020 年比赛方案；仓库自报 private #4，**非独立验证**。有业务特征参考价值，不视作生产系统；不复制整套旧代码 |
| [michaelf108/ecommerce-analytics-dbt](https://github.com/michaelf108/ecommerce-analytics-dbt) | staging/intermediate/marts 分层；订单粒度先聚合再 JOIN；唯一键与 FK 检查 | 1 star，MIT；完整作品集结构可参考，但不是广泛验证的工业框架。其统计结论不直接引用。本项目自行实现 SQL，避免依赖 dbt 才能入门 |
| [miguelvotre/olist-ecommerce-analytics](https://github.com/miguelvotre/olist-ecommerce-analytics) | dbt + DuckDB + Streamlit semantic 层组织 | 3 stars，MIT；学习目录与 dashboard 分页，不引入云仓/LLM 密钥等额外依赖 |
| [Ucazin/olist-ecommerce-analytics](https://github.com/Ucazin/olist-ecommerce-analytics) | 搜索缓存中的 README 指明 synthetic generator | GitHub API 当前 404。仅搜索预览，不能确认当前仓库。排除为真实数据来源，不使用其结果 |

结论：没有找到能够一站式覆盖真实交易、可核对归因、独立实验和严谨 holdout uplift 的现成项目。成熟库用于指标评估；业务模型、SQL、实验统计与 Dashboard 自行编写。这样能复用可信组件，又能解释自己的设计。

## 复用边界

- 运行时依赖并调用 `sklift.metrics.qini_auc_score / uplift_auc_score / qini_curve`，没有把上游源码改名粘贴。
- `scripts/download_data.py` 的 X5 URL 与 MD5 来源于上述固定版本的数据加载器；下载方式与文件清单由本项目实现。
- 调研下载的代码/许可证是本地参考缓存，已 gitignore，不混进项目源码。固定链接记录可审阅。
- Olist 与 X5 数据各自受原始数据条款约束；开源库许可证不授权再分发数据。见 `DATA_SOURCES.md`。

## 为什么首版不用更重的技术栈

DuckDB 可直接查询原始 CSV/gzip，并把 4 GB 的 X5 历史分组成用户级特征；Streamlit 读取聚合产物，无需云账户。首版目标是可跑、口径正确、可解释，后续迁移 dbt、CI 调度、DR Learner 时保留相同数据契约。
