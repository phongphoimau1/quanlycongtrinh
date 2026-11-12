import streamlit as st
import os
import traceback

st.set_page_config(page_title="Quản lý công trình", layout="wide")

try:
    # 1. Khóa mục tiêu bằng đường dẫn tuyệt đối của môi trường Linux
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    path_dashboard = os.path.join(BASE_DIR, "modules", "dashboard", "view.py")
    path_project_view = os.path.join(BASE_DIR, "modules", "projects", "view.py")
    path_project_create = os.path.join(BASE_DIR, "modules", "projects", "create.py")

    # 2. Khai báo các trang
    page_dashboard = st.Page(path_dashboard, title="Dashboard", icon="📊", default=True)
    page_project_view = st.Page(path_project_view, title="Quản lý công trình", icon="🏗️")
    page_project_create = st.Page(path_project_create, title="Tạo công trình", icon="➕")

    pages = {
        "Tổng quan": [page_dashboard],
        "Nghiệp vụ": [page_project_view, page_project_create]
    }

    # 3. Kích hoạt điều hướng
    pg = st.navigation(pages)
    pg.run()

except Exception as e:
    # 4. ÉP HIỂN THỊ LỖI THẬT SỰ LÊN MÀN HÌNH WEB
    st.error("🚨 HỆ THỐNG ĐÃ BẮT ĐƯỢC LỖI ẨN TRÊN STREAMLIT CLOUD:")
    st.code(traceback.format_exc())
