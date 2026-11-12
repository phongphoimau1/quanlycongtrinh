import streamlit as st
from services.project_service import create_project

st.title("➕ Tạo công trình mới")

with st.form("create_project_form"):
    st.subheader("Thông tin cơ bản")
    project_name = st.text_input("Tên công trình (*)")
    customer_name = st.text_input("Tên khách hàng (*)")
    
    col1, col2 = st.columns(2)
    with col1:
        brand = st.text_input("Thương hiệu (Brand)")
    with col2:
        request_content = st.text_area("Nội dung yêu cầu")
        
    submitted = st.form_submit_button("Lưu công trình", type="primary")

    if submitted:
        if not project_name or not customer_name:
            st.error("Vui lòng nhập các trường bắt buộc (*).")
        else:
            with st.spinner("Đang xử lý..."):
                new_data = {
                    "project_name": project_name,
                    "customer_name": customer_name,
                    "brand": brand,
                    "request_content": request_content
                }
                result = create_project(new_data)
                if result:
                    st.success(f"Tạo thành công! Mã công trình: {result[0]['project_code']}")
                    st.button("Quay lại danh sách", on_click=lambda: st.switch_page("modules/projects/view.py"))

if st.button("Trở về"):
    st.switch_page("modules/projects/view.py")
