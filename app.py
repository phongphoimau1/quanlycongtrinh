import streamlit as st

st.set_page_config(page_title="Quản lý công trình", layout="wide")

# Khai báo trực tiếp không qua biến trung gian
pages = {
    "Tổng quan": [
        st.Page("modules/dashboard/view.py", title="Dashboard", icon="📊", default=True)
    ],
    "Nghiệp vụ": [
        st.Page("modules/projects/view.py", title="Quản lý công trình", icon="🏗️"),
        st.Page("modules/projects/create.py", title="Tạo công trình", icon="➕")
    ]
}

pg = st.navigation(pages)
pg.run()
