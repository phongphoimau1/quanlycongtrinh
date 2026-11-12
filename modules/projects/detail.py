import streamlit as st
from services.project_service import get_project_by_code, update_project_status
import time

st.title("🔎 Chi tiết Công trình")

# Lấy mã công trình từ Query Parameters (URL)
query_params = st.query_params
project_code = query_params.get("code")

if not project_code:
    st.warning("Không tìm thấy mã công trình. Vui lòng chọn công trình từ danh sách.")
    if st.button("⬅️ Trở về danh sách"):
        st.switch_page("modules/projects/view.py")
else:
    project = get_project_by_code(project_code)
    
    if not project:
        st.error(f"Không tìm thấy dữ liệu cho mã: {project_code}")
    else:
        # Bố cục 2 cột (Trái: Thông tin, Phải: Thao tác tiến độ)
        col_info, col_action = st.columns([6, 4])
        
        with col_info:
            st.subheader("Thông tin chung")
            st.write(f"**Mã CT:** {project['project_code']}")
            st.write(f"**Tên công trình:** {project['project_name']}")
            st.write(f"**Khách hàng:** {project['customer_name']}")
            st.write(f"**Thương hiệu:** {project.get('brand', 'Không có')}")
            st.write(f"**Nội dung yêu cầu:** {project.get('request_content', 'Không có')}")
            
        with col_action:
            st.subheader("⏳ Quản lý Tiến độ")
            current_status = project['status']
            
            # Danh sách trạng thái chuẩn hóa
            status_options = ["Mới tiếp nhận", "Đang xử lý", "Chờ bổ sung", "Hoàn thành", "Đã hủy"]
            try:
                default_idx = status_options.index(current_status)
            except ValueError:
                default_idx = 0
                
            new_status = st.selectbox("Cập nhật trạng thái:", status_options, index=default_idx)
            
            if st.button("Lưu thay đổi", type="primary", use_container_width=True):
                if new_status == current_status:
                    st.info("Trạng thái không thay đổi.")
                else:
                    with st.spinner("Đang cập nhật..."):
                        update_project_status(project['id'], new_status)
                        st.success("Cập nhật thành công! Lịch sử đã được tự động ghi nhận.")
                        time.sleep(1)
                        st.rerun() # Tải lại trang để cập nhật UI
                        
        st.write("---")
        if st.button("⬅️ Trở về danh sách"):
            st.switch_page("modules/projects/view.py")
