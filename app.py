import streamlit as st
import os

st.set_page_config(page_title="Quản lý công trình", layout="wide")

# Hàm kiểm tra file tồn tại để tránh lỗi crash toàn bộ web
def safe_page(file_path, title, icon, default=False):
    if os.path.exists(file_path):
        return st.Page(file_path, title=title, icon=icon, default=default)
    else:
        # Nếu file chưa tồn tại, tạm thời trỏ về một trang ảo hoặc bỏ qua
        return None

dashboard_page = safe_page("modules/dashboard/view.py", title="Dashboard", icon="📊", default=True)
projects_page = safe_page("modules/projects/view.py", title="Quản lý công trình", icon="🏗️")
projects_create_page = safe_page("modules/projects/create.py", title="Tạo công trình", icon="➕")

# Chỉ thêm các trang đã thực sự tồn tại file vật lý
pages = {"Tổng quan": [], "Nghiệp vụ cốt lõi": []}

if dashboard_page: pages["Tổng quan"].append(dashboard_page)
if projects_page: pages["Nghiệp vụ cốt lõi"].append(projects_page)
if projects_create_page: pages["Nghiệp vụ cốt lõi"].append(projects_create_page)

# Xóa các nhóm rỗng để menu gọn gàng
pages = {k: v for k, v in pages.items() if v}

pg = st.navigation(pages)
pg.run()
