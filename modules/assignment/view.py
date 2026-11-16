import streamlit as st
import pandas as pd
from supabase import create_client
from services.project_service import get_all_projects
from services.assignment_service import assign_projects_bulk

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("👥 Phân công & Điều phối Công việc")

# 1. Tải dữ liệu Công trình và ánh xạ nhân sự từ bảng profiles
try:
    projects_data = get_all_projects()
    prof_res = supabase.table('profiles').select('id, full_name, email').execute()
    uuid_to_name = {
        str(p['id']): (p.get('full_name') or p.get('email') or "Chưa rõ")
        for p in (prof_res.data or [])
    }
except Exception as e:
    st.error(f"❌ Lỗi tải dữ liệu: {e}")
    projects_data = []
    uuid_to_name = {}

from services.project_service import get_active_staff_options
STAFF_LIST = get_active_staff_options(include_unassigned=False)

def get_clean_staff_name(val):
    if not val or pd.isna(val):
        return "Chưa phân công"
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["none", "nan", "null", "chưa phân nhân sự"]:
        return "Chưa phân công"
    if val_str in uuid_to_name:
        return uuid_to_name[val_str]
    return val_str

if projects_data:
    df_proj = pd.DataFrame(projects_data)
    df_proj['staff_name'] = df_proj['assigned_to'].apply(get_clean_staff_name) if 'assigned_to' in df_proj.columns else "Chưa phân công"
    df_proj['status'] = df_proj.get('status', 'Đang thực hiện').fillna("Đang thực hiện").replace("", "Đang thực hiện")
    df_proj = df_proj.fillna("")

    # 2. Thống kê Tải công việc (Workload Dashboard)
    st.markdown("### 📊 Tải công việc hiện tại theo Nhân sự (Các công trình đang chạy)")
    active_df = df_proj[~df_proj['status'].isin(['Hoàn thành', 'Đã hoàn thành'])]
    
    cols = st.columns(len(STAFF_LIST) + 1)
    unassigned_cnt = len(df_proj[df_proj['staff_name'] == "Chưa phân công"])
    cols[0].metric("🚨 Chưa phân công", unassigned_cnt)

    for idx, s_name in enumerate(STAFF_LIST):
        s_active = len(active_df[active_df['staff_name'] == s_name])
        s_total = len(df_proj[df_proj['staff_name'] == s_name])
        cols[idx + 1].metric(f"👤 {s_name}", f"{s_active} đang làm", f"Tổng: {s_total} CT")

    st.divider()

    # 3. Bộ lọc Điều phối
    c_f1, c_f2 = st.columns([1, 2])
    with c_f1:
        view_mode = st.radio(
            "Chế độ hiển thị:",
            ["🚨 Chỉ hiện CT Chưa phân công", "📋 Tất cả công trình"],
            horizontal=True
        )
    with c_f2:
        search_kw = st.text_input("🔍 Tìm kiếm mã CT, tên công trình, khách hàng...", placeholder="Nhập từ khóa...")

    df_view = df_proj.copy()
    if view_mode == "🚨 Chỉ hiện CT Chưa phân công":
        df_view = df_view[df_view['staff_name'] == "Chưa phân công"]

    if search_kw:
        kw = search_kw.lower()
        df_view = df_view[
            df_view['project_code'].astype(str).str.lower().str.contains(kw, na=False) |
            df_view['project_name'].astype(str).str.lower().str.contains(kw, na=False) |
            df_view['customer_name'].astype(str).str.lower().str.contains(kw, na=False) |
            df_view['staff_name'].astype(str).str.lower().str.contains(kw, na=False)
        ]

    st.markdown(f"### 📋 Danh sách Điều phối ({len(df_view)} công trình) - Tick chọn nhiều dòng để giao việc nhanh")

    for col_req in ["project_code", "project_name", "customer_name", "staff_name", "status", "received_date", "due_date"]:
        if col_req not in df_view.columns:
            df_view[col_req] = ""

    display_assign_df = df_view[[
        "project_code",
        "project_name",
        "customer_name",
        "staff_name",
        "status",
        "received_date",
        "due_date"
    ]].rename(columns={
        "project_code": "Mã CT",
        "project_name": "Tên công trình",
        "customer_name": "Khách hàng",
        "staff_name": "Nhân viên phụ trách",
        "status": "Trạng thái",
        "received_date": "Ngày nhận",
        "due_date": "Hạn hoàn thành"
    }).replace("", "Chưa cập nhật")

    # Cho phép chọn nhiều dòng cùng lúc (multi-row) để phân công hàng loạt
    event = st.dataframe(
        display_assign_df,
        width='stretch',
        hide_index=True,
        selection_mode="multi-row",
        on_select="rerun"
    )

    selected_indices = event.selection.rows
    if selected_indices:
        selected_rows_df = df_view.iloc[selected_indices]
        selected_ids = selected_rows_df['id'].tolist()
        selected_codes = ", ".join(selected_rows_df['project_code'].astype(str).tolist())

        st.divider()
        st.subheader(f"⚡ Giao việc cho {len(selected_ids)} công trình đã chọn: `{selected_codes}`")

        with st.form("bulk_assign_form"):
            c_a1, c_a2 = st.columns(2)
            with c_a1:
                target_staff = st.selectbox("Chọn Nhân sự nhận việc:", STAFF_LIST)
            with c_a2:
                new_due_date = st.date_input("Thiết lập Hạn hoàn thành (Tùy chọn):", value=None)

            assign_note = st.text_input("Chỉ đạo / Ghi chú giao việc:", placeholder="VD: Ưu tiên xử lý gấp phối màu mặt tiền...")

            btn_assign = st.form_submit_button("🚀 Xác nhận Phân công", type="primary", width='stretch')
            if btn_assign:
                res = assign_projects_bulk(
                    project_ids=selected_ids,
                    staff_name=target_staff,
                    due_date=str(new_due_date) if new_due_date else None,
                    note=assign_note
                )
                if res["success"]:
                    st.success(res["message"])
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(res["message"])
else:
    st.info("📭 Chưa có dữ liệu công trình trên hệ thống.")
