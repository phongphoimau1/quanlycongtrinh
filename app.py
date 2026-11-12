import streamlit as st
import os
import traceback

st.set_page_config(page_title="Quản lý công trình", layout="wide")

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    path_dashboard = os.path.join(BASE_DIR, "modules", "dashboard", "view.py")
    path_project_view = os.path.join(BASE_DIR, "modules", "projects", "view.py")
    path_project_create = os.path.join(BASE_DIR, "modules", "projects", "create.py")

    # Thêm tham số url_path định danh duy nhất cho từng trang
    page_dashboard = st.Page(
        path_dashboard, 
        title="Dashboard", 
        icon="📊", 
        default=True, 
        url_path="dashboard"
    )
    
    page_project_view = st.Page(
        path_project_view, 
        title="Quản lý công trình", 
        icon="🏗️", 
        url_path="projects"
    )
    
    page_project_create = st.Page(
        path_project_create, 
        title="Tạo công trình", 
        icon="➕", 
        url_path="create-project"
    )

    pages = {
        "Tổng quan": [page_dashboard],
        "Nghiệp vụ": [page_project_view, page_project_create]
    }

    pg = st.navigation(pages)
    pg.run()

except Exception as e:
    st.error("🚨 HỆ THỐNG ĐÃ BẮT ĐƯỢC LỖI ẨN TRÊN STREAMLIT CLOUD:")
    st.code(traceback.format_exc())
