# 本地验证记录

日期：2026-10-04。运行环境：Windows、Python 3.12.2；精确版本见 `requirements-lock.txt`。

| 验证 | 结果 |
|---|---|
| Olist 原始官方 ZIP | 已下载，9 个 CSV；SHA256 见 manifest |
| X5 三个官方加载器镜像文件 | 上游 MD5 全部匹配；SHA256 见 manifest |
| Olist marts 数据质量 | 16 项全部通过：唯一键、FK、订单/item 粒度、GMV/支付守恒 |
| 各维度归因 | 州、品类、买家类型、Seller 分别守恒到同一个 GMV 差 |
| X5 历史完整性 | 45,786,568 条明细、200,039 标签客户全覆盖、basket 金额不一致数0 |
| Feature leakage / holdout | 客户 split 唯一，train/validation/test 互斥；排除 ID/target/redeem 等普通特征 |
| pytest | **10 passed**，未跳过本地真实数据产物检查 |
| Streamlit AppTest | **6 页通过**；另外切换品类、Seller样本阈值、MDE、毛利输入均无异常 |
| 离线 Dashboard | 已由真实 outputs 生成自包含 HTML，内嵌 Plotly，无外部 CDN |
| Streamlit 本地服务 | 已在 http://127.0.0.1:8501 启动 |

源码按版本锁定运行；sklift 调用 sklearn 的 stable_cumsum 触发弃用警告，不影响当前结果，依赖范围已限制 sklearn<1.10。CI 配置已创建，但未发布远程 GitHub 仓库，也未声称远程 CI 运行成功。

本记录不代表已独立审计 RetailHero 的随机分配协议，也不代表营销策略已上线。测试验证计算与数据契约，不能替代业务因果证据。

## 2026-10-05 业务诊断与 AI 辅助补充

- 已运行 `scripts/run_diagnostics.py`：交叉切面与Seller状态桥接分别守恒到整体GMV变化，星期标准化覆盖全部7个星期组和零单日。
- SQL候选在只读连接中审核：主动生成的JOIN反例未通过金额契约，订单粒度查询通过。提示词、SQL与用途保存在 `docs/ai_review_input.json`；不冒充API推理日志或历史生产故障。
- `pytest`：11 passed，包含新增真实产物检查；Streamlit AppTest六页与原有交互全部通过，GMV页新增业务核查和AI审核展示。
- 离线HTML已重新生成；完整业务报告与中英文简历段落已保存。没有新增数据集、外部服务或未经观测的业务收益。
