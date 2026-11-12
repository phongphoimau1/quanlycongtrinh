import streamlit as st
import os
import traceback

st.set_page_config(page_title="Hệ thống Quản lý", layout="wide")

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # --- ĐỊNH NGHĨA ĐƯỜNG DẪN FILE ---
    path_dashboard = os.path.join(BASE_DIR, "modules", "dashboard", "view.py")
    path_project_view = os.path.join(BASE_DIR, "modules", "projects", "view.py")
    path_project_create = os.path.join(BASE_DIR, "modules", "projects", "create.py")
    path_project_detail = os.path.join(BASE_DIR, "modules", "projects", "detail.py")
    path_email_view = os.path.join(BASE_DIR, "modules", "emails", "view.py")

    # --- KHỞI TẠO CÁC TRANG ---
    page_dashboard = st.Page(path_dashboard, title="Dashboard", icon="📊", default=True, url_path="dashboard")
    page_project_view = st.Page(path_project_view, title="Danh sách công trình", icon="🏗️", url_path="projects")
    page_email_view = st.Page(path_email_view, title="Quản lý email", icon="📧", url_path="emails")
    
    # (Các trang tạo/chi tiết công trình vẫn được nạp để hệ thống router hoạt động, 
    # nhưng sẽ được đặt vào một nhóm riêng để không làm rối menu chính)
    page_project_create = st.Page(path_project_create, title="Tạo công trình", icon="➕", url_path="create-project")
    page_project_detail = st.Page(path_project_detail, title="Chi tiết công trình", icon="🔎", url_path="project-detail")

    # --- XÂY DỰNG CẤU TRÚC MENU THEO THIẾT KẾ ---
    pages = {
        "TỔNG QUAN": [
            page_dashboard
        ],
        "NGHIỆP VỤ": [
            page_project_view,
            page_email_view
        ],
        "CÁC TRANG CHỨC NĂNG (ẨN)": [
            page_project_create,
            page_project_detail
        ]
    }

    # Kích hoạt điều hướng
    pg = st.navigation(pages)
    pg.run()

except Exception as e:
    st.error("🚨 HỆ THỐNG ĐÃ BẮT ĐƯỢC LỖI ẨN TRÊN STREAMLIT CLOUD:")
    st.code(traceback.format_exc())
