import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client
from services.project_service import get_all_projects
from services.progress_service import get_project_status_logs, update_project_progress

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📈 Theo dõi Tiến độ & Lịch sử Công trình")

# 1. Tải dữ liệu Công trình và Profiles để hiển thị chuẩn tên nhân sự
try:
    projects_data = get_all_projects()
    prof_res = supabase.table('profiles').select('id, full_name, email').execute()
    uuid_to_name = {
        str(p['id']): (p.get('full_name') or p.get('email') or "Chưa rõ")
        for p in (prof_res.data or [])
    }
except Exception as e:
    st.error(f"❌ Lỗi kết nối CSDL: {e}")
    projects_data = []
    uuid_to_name = {}

def resolve_display_staff(val):
    if not val or pd.isna(val):
        return "Chưa phân công"
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["none", "nan", "null"]:
        return "Chưa phân công"
    if val_str in uuid_to_name:
        return uuid_to_name[val_str]
    return val_str

if projects_data:
    df_proj = pd.DataFrame(projects_data)
    df_proj['staff_name'] = df_proj['assigned_to'].apply(resolve_display_staff) if 'assigned_to' in df_proj.columns else "Chưa phân công"
    df_proj['status'] = df_proj.get('status', 'Mới tiếp nhận').fillna("Mới tiếp nhận").replace("", "Mới tiếp nhận")
    df_proj = df_proj.fillna("")

    # 2. Thống kê tổng quan Tiến độ (KPI Cards)
    total_cnt = len(df_proj)
    new_cnt = len(df_proj[df_proj['status'].isin(['Mới tiếp nhận', 'Chưa xử lý'])])
    doing_cnt = len(df_proj[df_proj['status'].isin(['Đang thực hiện', 'Đang xử lý'])])
    done_cnt = len(df_proj[df_proj['status'].isin(['Hoàn thành', 'Đã hoàn thành', 'Đã giao'])])
    pause_cnt = total_cnt - (new_cnt + doing_cnt + done_cnt)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🏗️ Tổng công trình", total_cnt)
    m2.metric("🆕 Mới tiếp nhận", new_cnt)
    m3.metric("⚡ Đang thực hiện", doing_cnt)
    m4.metric("✅ Đã hoàn thành", done_cnt)
    m5.metric("⏸️ Tạm dừng / Khác", max(0, pause_cnt))

    st.divider()

    # 3. Bộ lọc tìm kiếm Tiến độ
    c_f1, c_f2, c_f3 = st.columns([2, 1, 1])
    with c_f1:
        kw_search = st.text_input("🔍 Tìm kiếm mã CT, tên công trình, khách hàng...", placeholder="Nhập từ khóa...")
    with c_f2:
        status_filter = st.selectbox("Lọc theo Trạng thái", ["Tất cả", "Mới tiếp nhận", "Đang thực hiện", "Hoàn thành", "Tạm dừng"])
    with c_f3:
        staff_filter = st.selectbox("Lọc theo Nhân sự", ["Tất cả", "Ms Hân", "Mr Thái", "Mr Thịnh", "Ms Hương", "Ms Hiếu", "Chưa phân công"])

    df_filtered = df_proj.copy()
    if status_filter != "Tất cả":
        df_filtered = df_filtered[df_filtered['status'] == status_filter]
    if staff_filter != "Tất cả":
        df_filtered = df_filtered[df_filtered['staff_name'] == staff_filter]
    if kw_search:
        kw = kw_search.lower()
        df_filtered = df_filtered[
            df_filtered['project_code'].astype(str).str.lower().str.contains(kw, na=False) |
            df_filtered['project_name'].astype(str).str.lower().str.contains(kw, na=False) |
            df_filtered['customer_name'].astype(str).str.lower().str.contains(kw, na=False)
        ]

    st.markdown("### 📋 Bảng Điều phối & Theo dõi Tiến độ (Click chọn 1 công trình để cập nhật)")

    for col_needed in ["project_code", "project_name", "customer_name", "staff_name", "status", "received_date", "due_date", "completed_date"]:
        if col_needed not in df_filtered.columns:
            df_filtered[col_needed] = ""

    display_prog_df = df_filtered[[
        "project_code",
        "project_name",
        "customer_name",
        "staff_name",
        "status",
        "received_date",
        "due_date",
        "completed_date"
    ]].rename(columns={
        "project_code": "Mã CT",
        "project_name": "Tên công trình",
        "customer_name": "Khách hàng",
        "staff_name": "Nhân viên phụ trách",
        "status": "Trạng thái hiện tại",
        "received_date": "Ngày nhận",
        "due_date": "Hạn hoàn thành",
        "completed_date": "Ngày hoàn tất"
    }).replace("", "Chưa cập nhật")

    event = st.dataframe(
        display_prog_df,
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # 4. Form Cập nhật Tiến độ & Xem Lịch sử của Công trình đang chọn
    selected_rows = event.selection.rows
    if selected_rows:
        sel_idx = selected_rows[0]
        sel_proj = df_filtered.iloc[sel_idx]

        st.divider()
        col_up, col_his = st.columns([1, 1])

        with col_up:
            st.subheader(f"🛠️ Cập nhật Tiến độ: `{sel_proj['project_code']}`")
            with st.form(f"form_update_progress_{sel_proj['id']}"):
                status_list = ["Mới tiếp nhận", "Đang thực hiện", "Hoàn thành", "Tạm dừng"]
                curr_st = sel_proj['status'] if sel_proj['status'] in status_list else "Đang thực hiện"
                new_status = st.selectbox("Chuyển sang Trạng thái mới", status_list, index=status_list.index(curr_st))

                staff_options = ["Chưa phân công", "Ms Hân", "Mr Thái", "Mr Thịnh", "Ms Hương", "Ms Hiếu"]
                curr_staff = sel_proj['staff_name'] if sel_proj['staff_name'] in staff_options else "Chưa phân công"
                new_staff = st.selectbox("Nhân viên phụ trách", staff_options, index=staff_options.index(curr_staff))

                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    due_val = st.text_input("Hạn hoàn thành (YYYY-MM-DD)", value=str(sel_proj.get('due_date', ''))[:10])
                with c_d2:
                    comp_val = st.text_input("Ngày hoàn tất thực tế", value=str(sel_proj.get('completed_date', ''))[:10])

                note = st.text_area("Ghi chú tiến độ / Vướng mắc kỹ thuật", placeholder="Nhập nội dung cập nhật tiến độ...")

                btn_submit_prog = st.form_submit_button("💾 Lưu Cập nhật Tiến độ", type="primary", width='stretch')
                if btn_submit_prog:
                    res = update_project_progress(
                        project_id=sel_proj['id'],
                        old_status=sel_proj['status'],
                        new_status=new_status,
                        assigned_to_name=new_staff,
                        due_date=due_val,
                        completed_date=comp_val,
                        note=note,
                        actor_name=new_staff if new_staff != "Chưa phân công" else "Quản trị viên"
                    )
                    if res["success"]:
                        st.success(res["message"])
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(res["message"])

        with col_his:
            st.subheader(f"🕒 Nhật ký Tiến độ (`{sel_proj['project_code']}`)")
            logs = get_project_status_logs(project_id=sel_proj['id'])
            if logs:
                df_logs = pd.DataFrame(logs)[[
                    "changed_at", "old_status", "new_status", "changed_by_name", "note"
                ]].rename(columns={
                    "changed_at": "Thời gian",
                    "old_status": "Trạng thái cũ",
                    "new_status": "Trạng thái mới",
                    "changed_by_name": "Người cập nhật",
                    "note": "Ghi chú"
                })
                st.dataframe(df_logs, width='stretch', hide_index=True)
            else:
                st.info("Chưa có lịch sử thay đổi trạng thái nào cho công trình này.")

    # 5. Toàn bộ lịch sử cập nhật tiến độ gần đây trên toàn hệ thống
    st.divider()
    with st.expander("📜 Xem toàn bộ Nhật ký Thay đổi Tiến độ gần đây trên Hệ thống", expanded=False):
        all_logs = get_project_status_logs()
        if all_logs:
            df_all_logs = pd.DataFrame(all_logs)[[
                "changed_at", "project_code", "project_name", "old_status", "new_status", "changed_by_name", "note"
            ]].rename(columns={
                "changed_at": "Thời gian",
                "project_code": "Mã CT",
                "project_name": "Tên công trình",
                "old_status": "Từ trạng thái",
                "new_status": "Sang trạng thái",
                "changed_by_name": "Nhân sự",
                "note": "Ghi chú chi tiết"
            })
            st.dataframe(df_all_logs, width='stretch', hide_index=True)
        else:
            st.info("Chưa có dữ liệu nhật ký tiến độ.")
else:
    st.info("📭 Chưa có công trình nào trên hệ thống.")
