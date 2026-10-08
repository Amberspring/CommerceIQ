from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.experiments import sample_size, profit_scenario
from src.warehouse import ROOT

st.set_page_config(page_title='CommerceIQ · Commerce Analytics', page_icon='◈', layout='wide')
st.markdown('''<style>
.stApp {background:#f6f7fb;color:#162238}
div[data-testid="stMetric"] {background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px}
h1 {letter-spacing:-1.5px} h3 {letter-spacing:-.4px}
</style>''', unsafe_allow_html=True)

@st.cache_data
def table(dataset, name):
    return pd.read_csv(ROOT/'outputs'/dataset/f'{name}.csv')

def document(dataset, name):
    return json.loads((ROOT/'outputs'/dataset/f'{name}.json').read_text(encoding='utf-8'))

def chart(fig):
    fig.update_layout(template='plotly_white', font=dict(family='Arial',color='#162238'),
                      margin=dict(l=15,r=15,t=40,b=20),paper_bgcolor='rgba(0,0,0,0)',
                      colorway=['#2563eb','#14b8a6','#f59e0b','#ef4444'])
    st.plotly_chart(fig, width='stretch')

st.sidebar.title('◈ CommerceIQ')
st.sidebar.caption('真实交易 · 经营诊断 · 增量营销')
page=st.sidebar.radio('分析工作台',['经营总览','GMV 异动归因','用户分层与留存','Seller 经营','AB Test','Uplift Modeling'])
st.sidebar.divider()
st.sidebar.markdown('**数据边界**\n\nOlist：巴西电商，BRL\n\nRetailHero：独立零售短信任务\n\n两套数据不关联用户，不合并收益。')

if not (ROOT/'outputs/olist/case.json').exists():
    st.error('请先运行 python scripts/run_olist.py')
    st.stop()
case=document('olist','case')
if page=='经营总览':
    st.title('CommerceIQ / 经营总览')
    st.caption('Olist 原始公开交易 · 完成订单商品金额 · 2017.01—2018.08')
    monthly=table('olist','monthly')
    monthly=monthly[(monthly.month>='2017-01-01')&(monthly.month<='2018-08-01')]
    selected=st.select_slider('观察月份范围',options=monthly.month.tolist(),value=(monthly.month.iloc[0],monthly.month.iloc[-1]))
    period=monthly[monthly.month.between(*selected)]
    cols=st.columns(3)
    cols[0].metric('商品 GMV · BRL',f'{period.gmv.sum():,.0f}')
    cols[1].metric('完成订单',f'{period.orders.sum():,}')
    cols[2].metric('客单价 · BRL',f'{period.gmv.sum()/period.orders.sum():.2f}')
    chart(px.line(period,x='month',y='gmv',markers=True,title='GMV 月度趋势'))
    a,b=st.columns(2)
    with a: chart(px.bar(period,x='month',y='orders',title='订单量'))
    with b: chart(px.line(period,x='month',y='late_rate',markers=True,title='迟到订单占比'))
    st.info('按下单月归属，使用数据导出时的最终状态。首尾月与未完成订单存在观察偏差；2018 年 8 月也需谨慎解释。')
    alerts=table('olist','daily_alerts')
    with st.expander('日级异常提示：同星期几、过去 8 周中位数/MAD'):
        st.dataframe(alerts[alerts.alert==True],hide_index=True)
        st.caption('阈值 |robust z|>3.5，为排查提示；节假日、趋势与多重扫描可引起误报。')
elif page=='GMV 异动归因':
    st.title('GMV 异动归因')
    st.caption(f'固定复盘：{case["before"][:7]} → {case["after"][:7]}。更换月份可重跑 scripts/run_olist.py。')
    a,b,c=st.columns(3)
    a.metric('上期 GMV · BRL',f'{case["before_gmv"]:,.0f}')
    b.metric('本期 GMV · BRL',f'{case["after_gmv"]:,.0f}',f'{case["change_pct"]:.2f}%')
    c.metric('绝对变化 · BRL',f'{case["delta"]:,.0f}')
    factor=table('olist','factor_bridge')
    chart(go.Figure(go.Waterfall(x=['上期']+factor.factor.tolist()+['本期'],
                                y=[case['before_gmv']]+factor.delta.tolist()+[0],
                                measure=['absolute']+['relative']*len(factor)+['total'],
                                decreasing=dict(marker=dict(color='#ef4444')),
                                increasing=dict(marker=dict(color='#14b8a6')))).update_layout(title='GMV = Buyers × Frequency × AOV / Shapley 精确分解'))
    bridge=table('olist','dimension_bridge')
    dim=st.selectbox('下钻维度',['customer_state','category','buyer_type','seller_id'])
    rows=bridge[bridge.dimension==dim].sort_values('delta')
    st.caption('各维度分别解释同一个总变化；不能把地区、品类、卖家贡献再次相加。')
    chart(px.bar(pd.concat([rows.head(8),rows.tail(4)]).drop_duplicates(),x='delta',y='segment',orientation='h',title='下降贡献与增长抵消 · BRL'))
    st.dataframe(rows,hide_index=True)
    st.subheader('口径敏感性')
    st.dataframe(table('olist','sensitivity'),hide_index=True)
    if (ROOT/'outputs/olist/diagnosis.json').exists():
        diagnosis=document('olist','diagnosis')
        st.subheader('业务假设验证')
        st.metric('按相同星期结构比较的日均 GMV 变化',
                  f'{diagnosis["weekday_standardized_change_pct"]:.2f}%')
        st.caption('各星期几的日均 GMV 等权平均；只调整星期构成，不控制节假日、趋势或缺失日志。')
        with st.expander('交叉下钻：地区 × 品类 × 首次／已有购买群体'):
            st.dataframe(table('olist','cross_diagnostics').head(20),hide_index=True)
        with st.expander('Seller 活跃状态与履约交叉检查'):
            st.dataframe(table('olist','seller_diagnostics'),hide_index=True)
            st.dataframe(table('olist','service_diagnostics'),hide_index=True)
            st.caption('履约与评分为下单后的最终结果；同期关联不能当作下单前原因。')
        with st.expander('AI 辅助 SQL 的金额契约审核'):
            st.dataframe(table('olist','ai_sql_audit'),hide_index=True)
            st.caption('同一 Codex 助手生成并审核。失败项为主动构造的 JOIN 反例；不是历史事故。此脚本执行确定性审核，不调用模型 API。')
    st.warning('以上是算术贡献。曝光、天气、竞品、活动、缺货与实际入驻日期未观测，不能据此宣布因果根因。')
elif page=='用户分层与留存':
    st.title('用户分层与留存')
    st.caption('customer_unique_id 跨订单识别人 · 2018-09-01 快照 · 窗口内完成订单')
    rfm=table('olist','rfm')
    grouped=rfm.groupby('segment').agg(buyers=('customer_unique_id','count'),gmv=('monetary','sum'),median_recency=('recency','median')).reset_index()
    a,b=st.columns(2)
    with a: chart(px.bar(grouped,x='segment',y='buyers',title='规则分层人数'))
    with b: chart(px.bar(grouped,x='segment',y='gmv',title='分层商品金额 · BRL'))
    st.dataframe(grouped,hide_index=True)
    retention=table('olist','customer_retention')
    matrix=retention.pivot(index='cohort',columns='month_index',values='retention')
    chart(px.imshow(matrix,color_continuous_scale='Blues',aspect='auto',title='首次观测购买 Cohort 留存：未来月份为空'))
    st.info(f'窗口内重复购买用户占比 {(rfm.frequency>=2).mean():.2%}。RFM 是行为描述，金额不是利润，也不是预测 CLV。新用户指本月首次观测完成购买，可能在导出窗口外已购买。')
elif page=='Seller 经营':
    st.title('Seller 经营诊断')
    sellers=table('olist','sellers')
    minimum=st.slider('服务指标最低订单样本',10,200,30,10)
    eligible=sellers[sellers.seller_orders>=minimum].copy()
    eligible['review_coverage']=eligible.review_observations/eligible.seller_orders
    chart(px.scatter(eligible,x='late_rate',y='review_score',size='gmv',hover_name='seller_id',
                     title='迟到率与评价关联 / 气泡为 GMV',size_max=40))
    st.dataframe(eligible.sort_values('gmv',ascending=False),hide_index=True)
    retention=table('olist','seller_retention')
    chart(px.line(retention,x='month',y='retention',markers=True,title='活跃 Seller 次月仍有完成订单的比例'))
    bridge=table('olist','seller_bridge')
    month=st.selectbox('Seller GMV 桥接月份',sorted(bridge.month.unique()),index=list(sorted(bridge.month.unique())).index(case['after']))
    groups=bridge[bridge.month==month].groupby('seller_status').delta.sum().reset_index()
    chart(px.bar(groups,x='seller_status',y='delta',title='进入/恢复、当月无单、持续活跃的 GMV 变化'))
    st.info('首单日期不等于入驻日期；当月无单不等于永久退出。订单整体评价不是独立卖家评价，多卖家订单须谨慎归责。')
else:
    if not (ROOT/'outputs/x5/model_card.json').exists():
        st.warning('请先运行 build_x5_features.py 和 run_x5.py')
        st.stop()
    ab=document('x5','ab_result')
    model=document('x5','model_card')
    if page=='AB Test':
        st.title('RetailHero / 实验复盘')
        st.caption('用户级短信触达与之后是否购买 · 历史公开分组数据')
        a,b,c=st.columns(3)
        a.metric('Control 购买率',f'{ab["control_rate"]:.2%}',f'n={ab["n_control"]:,}')
        b.metric('Treatment 购买率',f'{ab["treatment_rate"]:.2%}',f'n={ab["n_treatment"]:,}')
        c.metric('购买率差',f'{ab["effect"]*100:.2f} pp')
        st.write(f'95% CI：[{ab["ci_low"]*100:.2f}, {ab["ci_high"]*100:.2f}] pp；两侧检验 p={ab["p_value"]:.3g}')
        st.warning('随机分配协议、执行日志与观察窗口未独立审计；因果解释依赖随机分配等假设。50/50 SRM 与协变量平衡只能作为诊断。')
        st.dataframe(table('x5','balance'),hide_index=True)
        st.subheader('下一轮实验：样本量规划')
        a,b=st.columns(2)
        baseline=a.number_input('基线购买率',min_value=.01,max_value=.95,value=.60,step=.01)
        mde=b.number_input('希望检出的绝对提升 · pp',min_value=.1,max_value=3.,value=1.,step=.1)
        st.metric('每组所需用户 · 80% power / 双侧 5%',f'{sample_size(baseline,mde/100):,}')
        with st.expander('探索性年龄分组（BH 校正，不能据此直接上线策略）'):
            st.dataframe(table('x5','exploratory_subgroups'),hide_index=True)
    else:
        st.title('RetailHero / Uplift Modeling')
        st.caption('60% 训练 / 20% 验证 / 20% 测试 · 用户互斥 · 只用干预前特征')
        policy=model['test_policy']
        a,b,c=st.columns(3)
        a.metric('验证集选定模型',model['selected_model'])
        b.metric('测试集 Top 30% 购买率差',f'{policy["effect"]*100:.2f} pp')
        c.metric('选中测试用户',f'{policy["selected_customers"]:,}')
        st.dataframe(table('x5','test_models'),hide_index=True)
        chart(px.line(table('x5','qini_curves'),x='fraction',y='incremental_responses',color='model',title='测试集 Qini 曲线'))
        chart(px.bar(table('x5','test_deciles'),x='decile',y='effect',title='选定模型十分位：观测组间差（探索性）'))
        st.info('模型按验证集 Top 30% uplift 选择；测试集不参与选模。置信区间条件于当前模型与策略，未包含重复训练的不确定性。不能给个人贴“必被说服”标签。')
        st.subheader('营销收益情景计算')
        st.caption('输入均为假设，非公开数据中的真实利润；按同一货币单位填写。')
        a,b,c=st.columns(3)
        audience=a.number_input('预计触达人数',min_value=100,value=10000,step=100)
        margin=b.number_input('每位增量买家的贡献毛利',min_value=0.,value=20.,step=1.)
        cost=c.number_input('每人触达成本',min_value=.01,value=.2,step=.01)
        scenarios=[]
        for label,effect in [('CI 下界',policy['bootstrap_ci'][0]),('点估计',policy['effect']),('CI 上界',policy['bootstrap_ci'][1])]:
            scenarios.append({'情景':label,**profit_scenario(effect,audience,margin,cost)})
        st.dataframe(pd.DataFrame(scenarios),hide_index=True)
        st.caption('历史 holdout 只提供策略评估证据；真正上线需新的 targeting 随机实验，并核实毛利、短信成本与促销补贴。')
