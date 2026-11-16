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
        st.switch_page("modules/projects/create.py")

# 3. Lấy danh sách công trình và profiles từ CSDL và thực hiện Left Join chuẩn quan hệ
try:
    # Lấy danh sách projects
    projects_data = get_all_projects() 
    
    # Lấy trực tiếp danh sách profiles để ánh xạ quan hệ khóa ngoại assigned_to -> profiles.id
    profiles_res = supabase.table('profiles').select('id, full_name, email').execute()
    profiles_data = profiles_res.data if profiles_res.data else []

except Exception as e:
    st.error(f"❌ Lỗi tải dữ liệu CSDL: {e}")
    projects_data = []
    profiles_data = []

if projects_data:
    df_proj = pd.DataFrame(projects_data)
    df_prof = pd.DataFrame(profiles_data) if profiles_data else pd.DataFrame(columns=['id', 'full_name', 'email'])

    # Chuẩn hóa cột tên nhân viên từ bảng profiles
    if not df_prof.empty and 'id' in df_prof.columns:
        df_prof['staff_display_name'] = df_prof['full_name'].fillna(df_prof['email']).fillna("Chưa rõ")
        # Đổi tên cột id thành assigned_to để chuẩn bị merge
        df_prof = df_prof.rename(columns={'id': 'profile_id'})
    else:
        df_prof['profile_id'] = []
        df_prof['staff_display_name'] = []

    # Thực hiện Left Join giữa projects và profiles dựa trên mối quan hệ assigned_to = profiles.id
    if 'assigned_to' in df_proj.columns and not df_prof.empty:
        df_proj = pd.merge(
            df_proj, 
            df_prof[['profile_id', 'staff_display_name']], 
            left_on='assigned_to', 
            right_on='profile_id', 
            how='left'
        )
        # Gán tên nhân sự, nếu không khớp hoặc trống thì hiển thị "Chưa phân công"
        df_proj['staff_name'] = df_proj['staff_display_name'].fillna("Chưa phân công")
    else:
        # Trường hợp dữ liệu cũ lưu trực tiếp dạng chuỗi tên hoặc chưa có profile
        def fallback_name(val):
            if not val or pd.isna(val) or str(val).lower() in ["none", "nan", "null"]:
                return "Chưa phân công"
            return str(val)
        df_proj['staff_name'] = df_proj['assigned_to'].apply(fallback_name) if 'assigned_to' in df_proj.columns else "Chưa phân công"

    # Làm sạch toàn bộ DataFrame tránh lỗi NaN hiển thị trên giao diện
    df_proj = df_proj.fillna("")

    # Lọc theo từ khóa tìm kiếm nếu có
    if search:
        keyword = search.lower()
        df_proj = df_proj[
            df_proj['project_name'].astype(str).str.lower().str.contains(keyword, na=False) |
            df_proj['project_code'].astype(str).str.lower().str.contains(keyword, na=False) |
            df_proj['customer_name'].astype(str).str.lower().str.contains(keyword, na=False) |
            df_proj['staff_name'].astype(str).str.lower().str.contains(keyword, na=False)
        ]

    st.markdown("### 📋 Danh sách Công trình (Click vào dòng để xem & cập nhật chi tiết)")

    # Chuẩn hóa DataFrame hiển thị đúng các cột
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
        "staff_name": "Nhân viên phụ trách", 
        "status": "Trạng thái",
        "received_date": "Ngày nhận"
    }).fillna("Chưa cập nhật").replace("", "Chưa cập nhật")

    # 4. BẢNG DỮ LIỆU TƯƠNG TÁC
    event = st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )
    
    # 5. XỬ LÝ KHI CLICK CHỌN DÒNG
    selected_rows = event.selection.rows
    if selected_rows:
        selected_index = selected_rows[0]
        selected_row_data = df_proj.iloc[selected_index]
        proj_code = selected_row_data.get('project_code')
        
        if proj_code:
            st.session_state["selected_project_code"] = proj_code
            st.toast(f"Đang mở chi tiết công trình: {proj_code}", icon="🚀")
            st.switch_page("modules/projects/detail.py") 
else:
    st.info("📭 Chưa có công trình nào trên hệ thống.")
