import streamlit as st

st.set_page_config(page_title="Quản lý công trình", layout="wide")

pages = {
    "Tổng quan": [st.Page("modules/dashboard/view.py", title="Dashboard", default=True)]
}

pg = st.navigation(pages)
pg.run()
