import streamlit as st
import os
import traceback

st.set_page_config(page_title="Quản lý công trình", layout="wide")

try:
    # 1. Khóa mục tiêu bằng đường dẫn tuyệt đối
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Khai báo toàn bộ đường dẫn file
    path_dashboard = os.path.join(BASE_DIR, "modules", "dashboard", "view.py")
    path_project_view = os.path.join(BASE_DIR, "modules", "projects", "view.py")
    path_project_create = os.path.join(BASE_DIR, "modules", "projects", "create.py")
    path_project_detail = os.path.join(BASE_DIR, "modules", "projects", "detail.py")

    # 3. Khởi tạo các trang với url_path duy nhất
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

    page_project_detail = st.Page(
        path_project_detail, 
        title="Chi tiết công trình", 
        icon="🔎", 
        url_path="project-detail"
    )

    # 4. Gom nhóm menu hợp nhất
    pages = {
        "Tổng quan": [page_dashboard],
        "Nghiệp vụ": [page_project_view, page_project_create, page_project_detail]
    }

    # 5. Kích hoạt điều hướng
    pg = st.navigation(pages)
    pg.run()

except Exception as e:
    st.error("🚨 HỆ THỐNG ĐÃ BẮT ĐƯỢC LỖI ẨN TRÊN STREAMLIT CLOUD:")
    st.code(traceback.format_exc())
