import streamlit as st
import time
from services.project_service import create_project

st.title("➕ Tạo công trình mới")

# 1. KHỐI FORM: Chỉ chứa các trường nhập liệu và nút Submit
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

# 2. KHỐI XỬ LÝ LOGIC: Hoàn toàn độc lập, nằm ngoài form
if submitted:
    if not project_name or not customer_name:
        st.error("Vui lòng nhập các trường bắt buộc (*).")
    else:
        with st.spinner("Đang lưu dữ liệu..."):
            new_data = {
                "project_name": project_name,
                "customer_name": customer_name,
                "brand": brand,
                "request_content": request_content
            }
            result = create_project(new_data)
            
            if result:
                # Hiển thị thông báo thành công
                st.success(f"🎉 Tạo thành công! Mã công trình: {result[0]['project_code']}")
                
                # Tự động điều hướng về trang danh sách sau 1.5 giây (Trải nghiệm siêu mượt)
                time.sleep(1.5)
                st.switch_page("modules/projects/view.py")

# 3. NÚT TRỞ VỀ: Luôn hiển thị ở dưới cùng, nằm ngoài form
st.write("---")
if st.button("⬅️ Trở về danh sách"):
    st.switch_page("modules/projects/view.py")
