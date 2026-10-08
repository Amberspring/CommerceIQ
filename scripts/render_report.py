"""Generate an offline interactive dashboard and numerical evidence memo."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import html
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.warehouse import ROOT

def load(dataset,name):
    return pd.read_csv(ROOT/'outputs'/dataset/f'{name}.csv')

def doc(dataset,name):
    return json.loads((ROOT/'outputs'/dataset/f'{name}.json').read_text(encoding='utf-8'))

def main():
    case=doc('olist','case'); ab=doc('x5','ab_result'); card=doc('x5','model_card')
    figures=[]
    def fig(figure):
        figure.update_layout(template='plotly_white',height=380,font=dict(family='Arial'),
                             margin=dict(t=55,b=35,l=45,r=25),colorway=['#2563eb','#14b8a6','#f59e0b','#ef4444'])
        rendered=figure.to_html(full_html=False,include_plotlyjs=True if not figures else False,
                               config={'displaylogo':False,'responsive':True})
        figures.append(figure)
        return rendered
    def tbl(df):
        return '<div class="table">'+df.to_html(index=False,border=0,float_format=lambda x:f'{x:,.4f}')+'</div>'
    def note(text): return f'<p class="note">{html.escape(text)}</p>'
    def cards(values):
        return '<div class="cards">'+''.join(f'<div class="card"><span>{html.escape(k)}</span><strong>{html.escape(v)}</strong></div>' for k,v in values)+'</div>'
    monthly=load('olist','monthly');monthly=monthly[monthly.month.between('2017-01-01','2018-08-01')]
    bridge=load('olist','dimension_bridge')
    factor=load('olist','factor_bridge')
    sensitivity=load('olist','sensitivity')
    rfm=load('olist','rfm')
    segments=rfm.groupby('segment').agg(buyers=('frequency','size'),gmv=('monetary','sum')).reset_index()
    segments.to_csv(ROOT/'outputs/olist/rfm_segments.csv',index=False)
    retention=load('olist','customer_retention')
    sellers=load('olist','sellers')
    top30=card['test_policy']
    panels={}
    panels['overview']=('<h2>经营总览</h2>'+cards([('商品 GMV / BRL',f'{monthly.gmv.sum():,.0f}'),('完成订单',f'{monthly.orders.sum():,}'),('商品客单价 / BRL',f'{monthly.gmv.sum()/monthly.orders.sum():.2f}')])
                        +fig(px.line(monthly,x='month',y='gmv',markers=True,title='Olist 月度 GMV · 2017.01—2018.08'))
                        +note('金额为最终完成订单的商品金额，不含运费；导出窗口和最终状态产生观察偏差，末月需谨慎。'))
    panels['attribution']=('<h2>GMV 异动复盘</h2>'+cards([('比较窗口',f'{case["before"][:7]} → {case["after"][:7]}'),('GMV 变化',f'{case["change_pct"]:.2f}%'),('变化金额 / BRL',f'{case["delta"]:,.0f}')])
                           +fig(go.Figure(go.Waterfall(x=['上期']+factor.factor.tolist()+['本期'],y=[case['before_gmv']]+factor.delta.tolist()+[0],measure=['absolute']+['relative']*3+['total'])).update_layout(title='GMV = Buyers × Frequency × AOV / Shapley 分解'))
                           +fig(px.bar(bridge[bridge.dimension=='customer_state'].head(8),x='segment',y='contribution_pp',title='地区贡献 · 百分点'))
                           +fig(px.bar(bridge[bridge.dimension=='category'].head(8),x='segment',y='contribution_pp',title='品类贡献 · 百分点'))
                           +tbl(sensitivity)+note('各维度分别加总到同一个 GMV 变化，不能跨维度加总。贡献是算术拆解，不是因果根因。'))
    panels['customers']=('<h2>用户分层与留存</h2>'+cards([('窗口内购买用户',f'{len(rfm):,}'),('重复购买用户比例',f'{(rfm.frequency>=2).mean():.2%}'),('快照', '2018-09-01')])
                         +fig(px.bar(segments,x='segment',y='buyers',title='RFM 规则分层：人数'))+tbl(segments)
                         +fig(px.imshow(retention.pivot(index='cohort',columns='month_index',values='retention'),aspect='auto',color_continuous_scale='Blues',title='购买 Cohort 留存 · 未来月份留空'))
                         +note('使用 customer_unique_id；低复购率限制精细分层。首次观测不等于新注册，RFM 金额不等于利润或预测 CLV。'))
    if (ROOT/'outputs/olist/diagnosis.json').exists():
        diagnosis=doc('olist','diagnosis')
        panels['attribution']+=('<h3>业务假设验证与 AI 辅助审核</h3>'
            +note(f'相同星期结构下的日均 GMV 变化 {diagnosis["weekday_standardized_change_pct"]:.2f}%。只调整星期构成，未控制节假日或趋势。')
            +tbl(load('olist','cross_diagnostics').head(10))
            +tbl(load('olist','seller_diagnostics'))+tbl(load('olist','service_diagnostics'))
            +note('Seller 活跃状态是交易观察；履约指标发生于下单之后，不能当作同期下单原因。')
            +tbl(load('olist','ai_sql_audit'))
            +note('AI 生成与审核由同一 Codex 助手完成；失败项为主动构造的 JOIN 反例。确定性脚本不执行模型推理。'))
    eligible=sellers[sellers.seller_orders>=30]
    seller_bridge=load('olist','seller_bridge')
    status=seller_bridge[seller_bridge.month==case['after']].groupby('seller_status').delta.sum().reset_index()
    panels['sellers']=('<h2>Seller 经营</h2>'+fig(px.scatter(eligible,x='late_rate',y='review_score',size='gmv',hover_name='seller_id',size_max=40,title='迟到率与评价 / 至少 30 个 Seller 订单'))
                       +fig(px.line(load('olist','seller_retention'),x='month',y='retention',markers=True,title='活跃 Seller 次月留存'))
                       +fig(px.bar(status,x='seller_status',y='delta',title='当月活跃状态 GMV 桥接'))
                       +note('首单不等于入驻，当月无单不等于永久退出。多卖家订单的整单评价无法独立归责。'))
    panels['ab']=('<h2>RetailHero · AB Test 历史复盘</h2>'+cards([('Control 购买率',f'{ab["control_rate"]:.2%}'),('Treatment 购买率',f'{ab["treatment_rate"]:.2%}'),('购买率差',f'{ab["effect"]*100:.2f} pp')])
                  +note(f'95% CI [{ab["ci_low"]*100:.2f}, {ab["ci_high"]*100:.2f}] pp。随机分配协议与结局窗口未独立审计，因果解释需前提假设。')
                  +fig(px.bar(load('x5','balance'),x='smd',y='feature',orientation='h',title='干预前协变量平衡 / 标准化均值差'))
                  +tbl(load('x5','exploratory_subgroups'))+note('年龄子群是探索性结果；BH 校正不能消除数据选择与随机化不明的问题。'))
    panels['uplift']=('<h2>RetailHero · 增量营销排序</h2>'+cards([('验证集选定',card['selected_model']),('独立 Test Top30 差',f'{top30["effect"]*100:.2f} pp'),('95% bootstrap CI',f'{top30["bootstrap_ci"][0]*100:.2f}—{top30["bootstrap_ci"][1]*100:.2f} pp')])
                      +tbl(load('x5','test_models'))+fig(px.line(load('x5','qini_curves'),x='fraction',y='incremental_responses',color='model',title='测试集 Qini 曲线'))
                      +fig(px.bar(load('x5','test_deciles'),x='decile',y='effect',title='选定模型十分位观测购买率差'))
                      +note('60/20/20 用户互斥划分；验证集选模，测试集只评估。历史 holdout 不等于新策略上线收益；成本/毛利须另行验证。'))
    buttons=''.join(f'<button data-page="{k}" onclick="showPage(\'{k}\')">{v}</button>' for k,v in [('overview','经营总览'),('attribution','GMV 归因'),('customers','用户分析'),('sellers','Seller 分析'),('ab','AB Test'),('uplift','Uplift')])
    content=''.join(f'<section id="{k}" class="panel">{v}</section>' for k,v in panels.items())
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CommerceIQ · Real Data Analytics</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#17243a;font-family:"Microsoft YaHei",Arial,sans-serif}header{background:#10243f;color:white;padding:28px 6vw}header small{color:#99b9df;letter-spacing:3px}h1{font-size:36px;margin:12px 0}header p{color:#b9cbe3}nav{display:flex;gap:8px;padding:18px 6vw;background:white;position:sticky;top:0;z-index:10;flex-wrap:wrap;border-bottom:1px solid #e3e8f0}button{border:0;border-radius:8px;padding:10px 18px;background:#edf2f8;color:#253c5c;cursor:pointer;font:inherit}button.active{background:#2563eb;color:white}main{max-width:1240px;margin:auto;padding:24px}h2{font-size:26px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:20px 0}.card{padding:22px;background:white;border-radius:14px;border:1px solid #e2e8f0}.card span{display:block;color:#697c94;font-size:13px}.card strong{display:block;margin-top:14px;font-size:28px}.plotly-graph-div{border-radius:12px;overflow:hidden;margin:18px 0}.note{background:#e9f0fc;border-left:4px solid #2563eb;padding:16px;line-height:1.7;font-size:14px}.panel{display:none}.panel.active{display:block}.table{overflow:auto;background:white;border-radius:10px;margin:18px 0}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:12px;border-bottom:1px solid #edf1f6}footer{padding:24px;color:#697c94;font-size:12px}@media(max-width:720px){.cards{grid-template-columns:1fr}h1{font-size:28px}main{padding:12px}}
    </style><header><small>COMMERCE INTELLIGENCE / PORTFOLIO</small><h1>CommerceIQ</h1><p>真实交易经营诊断 + 独立营销增量评估 · Olist & X5 RetailHero</p></header><nav>'''+buttons+'</nav><main>'+content+'''<footer>个人学习作品集，与同名公司无关联。交易/实验数据独立，不拼接用户；所有结果来自本地原始数据运行。图表可缩放、悬停、导出。</footer></main><script>
    function showPage(id){document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id===id));document.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.page===id));setTimeout(()=>document.querySelectorAll('#'+id+' .js-plotly-plot').forEach(p=>Plotly.Plots.resize(p)),20)}showPage('overview');
    </script></html>'''
    (ROOT/'dashboard/CommerceIQ.html').write_text(page,encoding='utf-8')
    category=bridge[bridge.dimension=='category'].iloc[0]
    state=bridge[bridge.dimension=='customer_state'].iloc[0]
    memo=f'''# CommerceIQ：真实数据分析结论

由 scripts/render_report.py 从已运行产物生成；禁止将探索性贡献写成因果结论。

## Olist 异动案例：{case['before'][:7]} → {case['after'][:7]}

- 完成订单商品 GMV：BRL {case['before_gmv']:,.2f} → {case['after_gmv']:,.2f}，变化 {case['change_pct']:.2f}%（BRL {case['delta']:,.2f}）。
- 订单：{case['before_orders']:,} → {case['after_orders']:,}；购买人数：{case['before_buyers']:,} → {case['after_buyers']:,}；AOV：{case['before_aov']:.2f} → {case['after_aov']:.2f}。
- Shapley 金额：人数 {case['shapley']['buyers']:,.2f}，频次 {case['shapley']['frequency']:,.2f}，AOV {case['shapley']['aov']:,.2f}；加总到整体差。
- 地区最大下降项：{state.segment}，BRL {state.delta:,.2f}，贡献 {state.contribution_pp:.2f}pp；品类最大下降项：{category.segment}，BRL {category.delta:,.2f}，贡献 {category.contribution_pp:.2f}pp。两项重叠，不能相加。
- 相同前28天口径变化 {sensitivity.iloc[1].change_pct:.2f}%，未取消口径 {sensitivity.iloc[2].change_pct:.2f}%。口径影响幅度，没有改变方向。
- 主窗口购买用户 {len(rfm):,}，重复购买用户占比 {(rfm.frequency>=2).mean():.2%}。RFM 用于描述，不能宣称高精度 CLV 或营销 uplift。

业务行动：交叉下钻、Seller桥接、星期结构与履约核查见 [完整业务诊断](BUSINESS_CASE.md)；可复现脚本为 scripts/run_diagnostics.py。根据证据确定排查优先级，再索取曝光、库存、活动与源系统日志，不能确认天气、流量分配或缺货的净影响。

## RetailHero：独立实验扩展

- 200,039 位标签客户，全部 45,786,568 条历史商品明细聚合，没有 purchases 截取前 N 行。
- Control {ab['n_control']:,} 人，购买率 {ab['control_rate']:.2%}；Treatment {ab['n_treatment']:,} 人，购买率 {ab['treatment_rate']:.2%}。
- 两组差 {ab['effect']*100:.2f}pp，相对差 {ab['relative_lift']:.2%}，Wald 95% CI [{ab['ci_low']*100:.2f}, {ab['ci_high']*100:.2f}]pp。
- 验证集选定 {card['selected_model']}；独立测试集 Top30 共 {top30['selected_customers']:,} 人，购买率差 {top30['effect']*100:.2f}pp，bootstrap 95% CI [{top30['bootstrap_ci'][0]*100:.2f}, {top30['bootstrap_ci'][1]*100:.2f}]pp。
- 区间条件于当前训练/策略，未纳入训练变化；随机分配协议与结局窗口未独立审计。历史 holdout 结果不构成已上线的收益证明。

业务行动：固定覆盖率与成本预算，进行新的策略随机实验；收集利润、券成本、退订和投诉，评估每位资格用户的增量贡献利润。不能将此购买率差乘上 Olist GMV 宣称财务收益。
'''
    (ROOT/'docs/FINDINGS.md').write_text(memo,encoding='utf-8')
    print('Generated offline dashboard and evidence memo',flush=True)

if __name__=='__main__':
    main()
