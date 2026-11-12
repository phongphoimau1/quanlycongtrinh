import streamlit as st

st.set_page_config(page_title="Quản lý công trình", layout="wide")

# Khai báo các trang
dashboard_page = st.Page("modules/dashboard/view.py", title="Dashboard", icon="📊", default=True)
projects_page = st.Page("modules/projects/view.py", title="Quản lý công trình", icon="🏗️")
projects_create_page = st.Page("modules/projects/create.py", title="Tạo công trình", icon="➕")

# Nhóm các trang (Trang create được gán nhưng không cần hiện nổi bật)
pages = {
    "Tổng quan": [dashboard_page],
    "Nghiệp vụ cốt lõi": [projects_page, projects_create_page]
}

pg = st.navigation(pages)
pg.run()
