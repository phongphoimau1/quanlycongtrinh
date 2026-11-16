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

# 3. Lấy danh sách công trình và profiles để ánh xạ ngược UUID -> Tên nhân viên
try:
    projects_data = get_all_projects() 
    
    # Truy vấn bảng profiles để lấy danh sách ánh xạ id -> full_name
    profiles_res = supabase.table('profiles').select('id, full_name, email').execute()
    profiles_list = profiles_res.data if profiles_res.data else []
    
    # Tạo dictionary dịch ngược: UUID hoặc chuỗi ID -> Tên nhân viên
    uuid_to_name = {}
    for p in profiles_list:
        p_id = str(p.get('id'))
        p_name = p.get('full_name') or p.get('email') or "Chưa rõ"
        uuid_to_name[p_id] = p_name

except Exception as e:
    st.error(f"❌ Lỗi tải dữ liệu CSDL: {e}")
    projects_data = []
    uuid_to_name = {}

if projects_data:
    df_proj = pd.DataFrame(projects_data)
    
    # 1. Xử lý an toàn cột nhân sự phụ trách, loại bỏ hoàn toàn khả năng sinh ra NaN
    def get_staff_display_name(val):
        if not val or pd.isna(val):
            return "Chưa phân công"
        val_str = str(val).strip()
        if val_str in uuid_to_name:
            return uuid_to_name[val_str]
        return val_str

    if 'assigned_to' in df_proj.columns:
        df_proj['staff_name'] = df_proj['assigned_to'].apply(get_staff_display_name)
    else:
        df_proj['staff_name'] = "Chưa phân công"
    
    # 2. Thay thế toàn bộ các giá trị NaN/None/NaT trong toàn bộ DataFrame thành chuỗi rỗng hoặc giá trị hiển thị đẹp mắt
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

    # Chuẩn hóa DataFrame hiển thị đúng các cột và làm sạch NaN cuối cùng bằng .replace()
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

    # 4. BẢNG DỮ LIỆU TƯƠNG TÁC (Đã sạch bóng NaN)
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
