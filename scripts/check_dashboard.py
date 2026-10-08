"""Exercise all Streamlit views and controls without a desktop browser."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
app=AppTest.from_file(str(ROOT/'dashboard/app.py'),default_timeout=45).run()
for page in ['经营总览','GMV 异动归因','用户分层与留存','Seller 经营','AB Test','Uplift Modeling']:
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, [(x.message) for x in app.exception]
    if page=='GMV 异动归因':
        app.selectbox[0].set_value('category').run()
    elif page=='Seller 经营':
        app.slider[0].set_value(50).run()
    elif page=='AB Test':
        app.number_input[1].set_value(2.).run()
    elif page=='Uplift Modeling':
        app.number_input[1].set_value(30.).run()
    assert not app.exception, [(x.message) for x in app.exception]
    print('PASS:',page,flush=True)
