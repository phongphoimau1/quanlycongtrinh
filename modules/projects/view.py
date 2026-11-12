import streamlit as st
import pandas as pd
from services.project_service import get_projects

st.title("🏗️ Quản lý Công trình")

col1, col2 = st.columns([8, 2])
with col1:
    search = st.text_input("🔍 Tìm kiếm công trình (Nhập tên)...")
with col2:
    st.write("")
    if st.button("➕ Tạo công trình", use_container_width=True, type="primary"):
        st.switch_page("modules/projects/create.py")

data = get_projects(search_term=search)

if data:
    df = pd.DataFrame(data)
    df = df.rename(columns={
        "project_code": "Mã CT", 
        "project_name": "Tên công trình",
        "customer_name": "Khách hàng",
        "status": "Trạng thái",
        "created_at": "Ngày tạo"
    })
    df['Ngày tạo'] = pd.to_datetime(df['Ngày tạo']).dt.strftime('%d/%m/%Y %H:%M')
    
    st.dataframe(
        df[["Mã CT", "Tên công trình", "Khách hàng", "Trạng thái", "Ngày tạo"]],
        use_container_width=True,
        hide_index=True
    )
    
    st.write("---")
    col_sel, col_btn = st.columns([3, 1])
    
    with col_sel:
        selected_code = st.selectbox("Chọn công trình để xem chi tiết / cập nhật:", df["Mã CT"].tolist())
        
    with col_btn:
        st.write("")
        
        # 1. Hàm Callback khóa dữ liệu tuyệt đối vào bộ nhớ
        def save_code_to_state(code):
            st.session_state["selected_project_code"] = code
            
        # 2. Gắn callback vào nút bấm qua thuộc tính on_click và args
        if st.button("Mở chi tiết ➡️", use_container_width=True, on_click=save_code_to_state, args=(selected_code,)):
            st.switch_page("modules/projects/detail.py")
else:
    st.info("Không tìm thấy công trình nào.")
