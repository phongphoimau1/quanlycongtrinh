import streamlit as st
import pandas as pd
from services.project_service import get_all_projects # hoặc hàm lấy danh sách công trình của bạn

st.title("🏗️ Quản lý Công trình")

# 1. Thanh tìm kiếm
search = st.text_input("🔍 Tìm kiếm công trình (Nhập tên hoặc mã)...", placeholder="Nhập từ khóa...")

# 2. Nút tạo công trình mới
col_t1, col_t2 = st.columns([5, 1])
with col_t2:
    if st.button("➕ Tạo công trình", type="primary", width='stretch'):
        # Chuyển hướng sang trang tạo mới nếu có
        pass

# 3. Lấy danh sách công trình từ CSDL
try:
    # Lấy dữ liệu dự án (thay thế bằng hàm service thực tế của bạn)
    projects_data = get_all_projects() 
except Exception as e:
    st.error(f"❌ Lỗi tải dữ liệu công trình: {e}")
    projects_data = []

if projects_data:
    df_proj = pd.DataFrame(projects_data)
    
    # Lọc theo từ khóa tìm kiếm nếu có
    if search:
        df_proj = df_proj[
            df_proj['project_name'].str.contains(search, case=False, na=False) |
            df_proj['project_code'].str.contains(search, case=False, na=False) |
            df_proj['customer_name'].str.contains(search, case=False, na=False)
        ]

    st.markdown("### 📋 Danh sách Công trình (Click vào dòng để xem & cập nhật chi tiết)")

    # 4. BẢNG DƯ LIỆU TƯƠNG TÁC (Tích hợp Selection bắt sự kiện click dòng)
    event = st.dataframe(
        df_proj[["project_code", "project_name", "customer_name", "status", "received_date"]].rename(columns={
            "project_code": "Mã CT",
            "project_name": "Tên công trình",
            "customer_name": "Khách hàng",
            "status": "Trạng thái",
            "received_date": "Ngày nhận"
        }),
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # 5. XỬ LÝ KHI NGƯỜI DÙNG CLICK CHỌN 1 DÒNG TRÊN BẢNG
    selected_rows = event.selection.rows
    if selected_rows:
        selected_index = selected_rows[0]
        selected_row_data = df_proj.iloc[selected_index]
        proj_code = selected_row_data.get('project_code')
        
        if proj_code:
            # Lưu mã công trình vào Session State
            st.session_state["selected_project_code"] = proj_code
            
            # Hiển thị thông báo nhỏ và điều hướng tự động sang trang chi tiết
            st.toast(f"Đang mở chi tiết công trình: {proj_code}", icon="🚀")
            
            # Chuyển hướng sang trang chi tiết (Điều chỉnh lại đường dẫn file detail của bạn nếu cần)
            st.switch_page("modules/projects/detail.py") 
else:
    st.info("📭 Chưa có công trình nào trên hệ thống.")
