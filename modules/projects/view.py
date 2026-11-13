import streamlit as st
import pandas as pd
from services.project_service import get_all_projects
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🏗️ Quản lý Công trình")

# 1. Thanh tìm kiếm
search = st.text_input("🔍 Tìm kiếm công trình (Nhập tên, mã hoặc khách hàng)...", placeholder="Nhập từ khóa...")

# 2. Nút tạo công trình mới
col_t1, col_t2 = st.columns([5, 1])
with col_t2:
    if st.button("➕ Tạo công trình", type="primary", width='stretch'):
        # Chuyển hướng sang trang tạo mới nếu có
        st.switch_page("modules/projects/create.py")

# 3. Lấy danh sách công trình và danh sách nhân sự từ CSDL
try:
    projects_data = get_all_projects() 
    
    # Truy vấn bảng profiles để map ID nhân viên phụ trách sang Tên nhân sự
    profiles_res = supabase.table('profiles').select('id, full_name, email').execute()
    profiles_list = profiles_res.data if profiles_res.data else []
    # Tạo dictionary map: UUID -> Tên nhân viên
    id_to_staff_name = {p['id']: (p.get('full_name') or p.get('email', 'Chưa rõ')) for p in profiles_list}

except Exception as e:
    st.error(f"❌ Lỗi tải dữ liệu CSDL: {e}")
    projects_data = []
    id_to_staff_name = {}

if projects_data:
    df_proj = pd.DataFrame(projects_data)
    
    # Mapping cột Nhân viên phụ trách từ ID sang Tên thực tế
    df_proj['staff_name'] = df_proj['assigned_to'].map(id_to_staff_name).fillna("Chưa phân công")
    
    # Lọc theo từ khóa tìm kiếm nếu có
    if search:
        keyword = search.lower()
        df_proj = df_proj[
            df_proj['project_name'].str.lower().str.contains(keyword, na=False) |
            df_proj['project_code'].str.lower().str.contains(keyword, na=False) |
            df_proj['customer_name'].str.lower().str.contains(keyword, na=False) |
            df_proj['staff_name'].str.lower().str.contains(keyword, na=False)
        ]

    st.markdown("### 📋 Danh sách Công trình (Click vào dòng để xem & cập nhật chi tiết)")

    # Chuẩn hóa DataFrame hiển thị đầy đủ các cột: Mã, Tên, Khách hàng, Nhân sự phụ trách, Trạng thái, Ngày nhận
    display_df = df_proj[[
        "project_code", 
        "project_name", 
        "customer_name", 
        "staff_name", 
        "status", 
        "received_date"
    ]].rename(columns={
        "project_code": "Mã CT",
        "project_name": "Tên công trình",
        "customer_name": "Khách hàng",
        "staff_name": "Nhân viên phụ trách", # <-- Cột nhân viên phụ trách độc lập, chính xác tuyệt đối
        "status": "Trạng thái",
        "received_date": "Ngày nhận"
    })

    # 4. BẢNG DƯ LIỆU TƯƠNG TÁC (Tích hợp Selection bắt sự kiện click dòng)
    event = st.dataframe(
        display_df,
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
            
            # Chuyển hướng sang trang chi tiết
            st.switch_page("modules/projects/detail.py") 
else:
    st.info("📭 Chưa có công trình nào trên hệ thống.")
