from datetime import datetime, date
import streamlit as st
import pandas as pd
from services.project_service import (
    get_all_projects,
    get_active_staff_options,
    get_staff_uuid_map,
    _resolve_display_staff_name,
    normalize_status_display,
    bulk_update_projects_inline,
    update_project_status,
    PROJECT_STATUSES,
)

st.title("🏗️ Quản lý & Điều phối Công trình (Smart Workspace)")

# 1. Lấy danh sách nhân sự động từ bảng profiles + ánh xạ UUID
DYNAMIC_STAFF_OPTIONS = get_active_staff_options(include_unassigned=True, unassigned_label="Chưa phân công")
UUID_MAP = get_staff_uuid_map()


# 2. Hộp thoại Popup (Modal Dialog) xem & cập nhật sâu công trình ngay trên màn hình
@st.dialog("🔍 Chi tiết & Cập nhật Công trình", width="large")
def open_project_quick_modal(proj_row):
    p_code = proj_row.get("project_code", "N/A")
    st.markdown(f"### 🏗️ `{p_code}` — {proj_row.get('project_name', '')}")

    with st.form(f"modal_form_{proj_row.get('id')}"):
        c1, c2 = st.columns(2)
        with c1:
            ed_name = st.text_input("Tên công trình", value=proj_row.get("project_name", ""))
            ed_cust = st.text_input("Khách hàng", value=proj_row.get("customer_name", ""))
            curr_staff = proj_row.get("staff_name", "Chưa phân công")
            staff_choices = list(DYNAMIC_STAFF_OPTIONS)
            if curr_staff not in staff_choices:
                staff_choices.append(curr_staff)
            ed_staff = st.selectbox(
                "Nhân viên phụ trách",
                staff_choices,
                index=staff_choices.index(curr_staff),
            )
        with c2:
            curr_st = proj_row.get("status", "Đang thực hiện")
            st_choices = list(PROJECT_STATUSES)
            if curr_st not in st_choices:
                st_choices.append(curr_st)
            ed_status = st.selectbox(
                "Trạng thái công trình",
                st_choices,
                index=st_choices.index(curr_st),
            )
            ed_due = st.text_input(
                "Hạn hoàn thành (YYYY-MM-DD)",
                value=str(proj_row.get("due_date") or "")[:10],
            )
            ed_rec = st.text_input(
                "Ngày tiếp nhận",
                value=str(proj_row.get("received_date") or "")[:10],
                disabled=True,
            )

        ed_req = st.text_area(
            "Nội dung yêu cầu / Ghi chú kỹ thuật",
            value=str(proj_row.get("request_content") or ""),
            height=110,
        )
        ed_note = st.text_input(
            "Ghi chú nhật ký tiến độ lần này",
            placeholder="VD: Đã giao nhân sự xử lý phương án phối màu...",
        )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            btn_save_modal = st.form_submit_button("💾 Lưu Cập nhật", type="primary", width="stretch")
        with col_b2:
            btn_open_full = st.form_submit_button("🚀 Mở Trang Hồ sơ Chi tiết", width="stretch")

        if btn_save_modal:
            ok = update_project_status(
                project_code_or_id=proj_row.get("id") or p_code,
                new_status=ed_status,
                note=ed_note or f"Cập nhật từ hộp thoại nhanh ({ed_staff})",
                assigned_to=ed_staff,
                due_date=ed_due if ed_due else None,
                project_name=ed_name,
                customer_name=ed_cust,
                request_content=ed_req,
            )
            if ok:
                st.toast(f"✅ Đã cập nhật công trình {p_code}!", icon="🎉")
                st.rerun()
            else:
                st.error("❌ Không thể lưu thay đổi.")

        if btn_open_full:
            st.session_state["selected_project_code"] = p_code
            st.switch_page("modules/projects/detail.py")


# 3. Tải dữ liệu Công trình và tính toán Cảnh báo SLA / Trễ hạn
projects_data = get_all_projects()

if projects_data:
    df_proj = pd.DataFrame(projects_data)

    df_proj["staff_name"] = (
        df_proj["assigned_to"].apply(lambda x: _resolve_display_staff_name(x, UUID_MAP))
        if "assigned_to" in df_proj.columns
        else "Chưa phân công"
    )
    df_proj["status"] = (
        df_proj["status"].apply(normalize_status_display)
        if "status" in df_proj.columns
        else "Đang thực hiện"
    )

    for col_needed in ["project_code", "project_name", "customer_name", "received_date", "due_date", "completed_date", "request_content"]:
        if col_needed not in df_proj.columns:
            df_proj[col_needed] = ""

    df_proj = df_proj.fillna("")

    # Tính toán nhãn Cảnh báo SLA tự động cho từng công trình
    today_str = date.today().strftime("%Y-%m-%d")

    def compute_sla_badge(row):
        st_val = str(row.get("status", ""))
        sf_val = str(row.get("staff_name", ""))
        due_val = str(row.get("due_date", ""))[:10]

        if st_val == "Hoàn thành":
            return "✅ Hoàn tất"
        if st_val == "Tạm dừng":
            return "⏸️ Tạm dừng"
        if sf_val == "Chưa phân công":
            return "🚨 Chưa giao việc"
        if due_val and len(due_val) == 10:
            if due_val < today_str:
                return "🔥 Quá hạn"
            elif due_val == today_str:
                return "⏳ Hạn hôm nay"
        if st_val == "Cần chỉnh sửa":
            return "🛠️ Cần sửa lại"
        return "🟢 Đang chạy"

    df_proj["sla_badge"] = df_proj.apply(compute_sla_badge, axis=1)

    # 4. Thanh KPI Cảnh báo Nhanh
    total_cnt = len(df_proj)
    unassigned_cnt = len(df_proj[df_proj["staff_name"] == "Chưa phân công"])
    overdue_cnt = len(df_proj[df_proj["sla_badge"] == "🔥 Quá hạn"])
    doing_cnt = len(df_proj[df_proj["status"].isin(["Đang thực hiện", "Mới tiếp nhận", "Chờ khách duyệt", "Cần chỉnh sửa"])])
    done_cnt = len(df_proj[df_proj["status"] == "Hoàn thành"])

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🏗️ Tổng Công trình", total_cnt)
    k2.metric("🚨 Chưa phân công", unassigned_cnt)
    k3.metric("🔥 Quá hạn (Overdue)", overdue_cnt)
    k4.metric("⚡ Đang triển khai", doing_cnt)
    k5.metric("✅ Đã hoàn thành", done_cnt)

    st.divider()

    # 5. Bộ lọc đa chiều & Thanh công cụ
    f1, f2, f3, f4, f5 = st.columns([2.2, 1.3, 1.3, 1.2, 1])
    with f1:
        search = st.text_input(
            "🔍 Tìm nhanh (Mã CT, Tên công trình, Khách hàng)...",
            placeholder="Nhập từ khóa...",
        )
    with f2:
        staff_filter = st.selectbox("👤 Lọc Nhân viên", ["Tất cả"] + DYNAMIC_STAFF_OPTIONS)
    with f3:
        status_filter = st.selectbox("📌 Lọc Trạng thái", ["Tất cả"] + PROJECT_STATUSES)
    with f4:
        sla_filter = st.selectbox(
            "🚦 Lọc Cảnh báo SLA",
            ["Tất cả", "🚨 Chưa giao việc", "🔥 Quá hạn", "⏳ Hạn hôm nay", "🛠️ Cần sửa lại", "🟢 Đang chạy", "✅ Hoàn tất"],
        )
    with f5:
        st.write("")
        st.write("")
        if st.button("➕ Tạo CT Mới", type="primary", width="stretch"):
            st.switch_page("modules/projects/create.py")

    df_view = df_proj.copy()
    if staff_filter != "Tất cả":
        df_view = df_view[df_view["staff_name"] == staff_filter]
    if status_filter != "Tất cả":
        df_view = df_view[df_view["status"] == status_filter]
    if sla_filter != "Tất cả":
        df_view = df_view[df_view["sla_badge"] == sla_filter]
    if search:
        kw = search.lower().strip()
        df_view = df_view[
            df_view["project_name"].astype(str).str.lower().str.contains(kw, na=False)
            | df_view["project_code"].astype(str).str.lower().str.contains(kw, na=False)
            | df_view["customer_name"].astype(str).str.lower().str.contains(kw, na=False)
            | df_view["staff_name"].astype(str).str.lower().str.contains(kw, na=False)
        ]

    # Đảm bảo mọi giá trị đang có trong dữ liệu đều nằm trong options của SelectboxColumn
    all_staff_in_df = list(DYNAMIC_STAFF_OPTIONS)
    for sv in df_view["staff_name"].unique():
        if sv and sv not in all_staff_in_df:
            all_staff_in_df.append(sv)

    all_status_in_df = list(PROJECT_STATUSES)
    for stv in df_view["status"].unique():
        if stv and stv not in all_status_in_df:
            all_status_in_df.append(stv)

    # 6. BẢNG SỬA TRỰC TIẾP NHƯ EXCEL (st.data_editor)
    col_hdr1, col_hdr2 = st.columns([3, 1])
    with col_hdr1:
        st.markdown(
            f"### 📋 Bảng Điều phối Trực tiếp ({len(df_view)} công trình) "
            "— *Click đúp vào ô **Nhân viên** hoặc **Trạng thái** để đổi ngay*"
        )
    with col_hdr2:
        auto_save = st.toggle("⚡ Tự động lưu ngay khi đổi ô", value=True)

    editor_source_df = df_view[
        [
            "id",
            "sla_badge",
            "project_code",
            "project_name",
            "customer_name",
            "staff_name",
            "status",
            "received_date",
            "due_date",
        ]
    ].copy()
    editor_source_df["received_date"] = editor_source_df["received_date"].astype(str).str[:10].replace("", "Chưa cập nhật")
    editor_source_df["due_date"] = editor_source_df["due_date"].astype(str).str[:10]

    edited_df = st.data_editor(
        editor_source_df,
        key="projects_inline_editor",
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=["id", "sla_badge", "project_code", "received_date"],
        column_order=[
            "sla_badge",
            "project_code",
            "project_name",
            "customer_name",
            "staff_name",
            "status",
            "received_date",
            "due_date",
        ],
        column_config={
            "sla_badge": st.column_config.TextColumn("🚦 Cảnh báo SLA", width="small"),
            "project_code": st.column_config.TextColumn("Mã CT", width="small"),
            "project_name": st.column_config.TextColumn("Tên công trình (Sửa trực tiếp)", width="large"),
            "customer_name": st.column_config.TextColumn("Khách hàng", width="medium"),
            "staff_name": st.column_config.SelectboxColumn(
                "👤 Nhân viên phụ trách",
                help="Click để chọn nhân viên phụ trách (Danh sách tự động đồng bộ từ mục Quản trị)",
                options=all_staff_in_df,
                required=True,
                width="medium",
            ),
            "status": st.column_config.SelectboxColumn(
                "📌 Trạng thái",
                help="Click để đổi nhanh trạng thái công trình",
                options=all_status_in_df,
                required=True,
                width="medium",
            ),
            "received_date": st.column_config.TextColumn("Ngày nhận", width="small"),
            "due_date": st.column_config.TextColumn("Hạn hoàn thành (YYYY-MM-DD)", width="small"),
        },
    )

    # Phát hiện các dòng vừa được chỉnh sửa trên bảng
    changed_rows = []
    for idx in range(len(editor_source_df)):
        orig = editor_source_df.iloc[idx]
        curr = edited_df.iloc[idx]
        if (
            orig["staff_name"] != curr["staff_name"]
            or orig["status"] != curr["status"]
            or orig["project_name"] != curr["project_name"]
            or orig["customer_name"] != curr["customer_name"]
            or orig["due_date"] != curr["due_date"]
        ):
            changed_rows.append(
                {
                    "id": orig["id"],
                    "project_code": orig["project_code"],
                    "project_name": curr["project_name"],
                    "customer_name": curr["customer_name"],
                    "staff_name": curr["staff_name"],
                    "old_status": orig["status"],
                    "status": curr["status"],
                    "due_date": curr["due_date"] if curr["due_date"] else None,
                }
            )

    if changed_rows:
        if auto_save:
            res = bulk_update_projects_inline(changed_rows)
            if res["success"]:
                st.toast(res["message"], icon="✅")
                st.rerun()
            else:
                st.error(res["message"])
        else:
            st.warning(f"✏️ Bạn vừa thay đổi **{len(changed_rows)} dòng** trên bảng. Nhấn nút bên dưới để lưu xuống CSDL:")
            if st.button(f"💾 Lưu {len(changed_rows)} thay đổi xuống CSDL ngay", type="primary"):
                res = bulk_update_projects_inline(changed_rows)
                if res["success"]:
                    st.success(res["message"])
                    st.rerun()
                else:
                    st.error(res["message"])

    # 7. Thanh Truy cập Nhanh Hồ sơ Chi tiết / Mở Popup (Không cần cuộn xa)
    st.divider()
    q_col1, q_col2, q_col3 = st.columns([3, 1, 1])
    proj_lookup = {
        f"{r['project_code']} — {r['project_name']} ({r['staff_name']})": r
        for _, r in df_view.iterrows()
    }
    with q_col1:
        selected_label = st.selectbox(
            "🔍 Chọn nhanh công trình để mở Cửa sổ Chi tiết hoặc Hồ sơ:",
            list(proj_lookup.keys()) if proj_lookup else ["Không có công trình"],
        )
    with q_col2:
        st.write("")
        st.write("")
        if st.button("🪟 Xem / Sửa Nhanh (Popup)", width="stretch", disabled=not proj_lookup):
            open_project_quick_modal(proj_lookup[selected_label])
    with q_col3:
        st.write("")
        st.write("")
        if st.button("🚀 Mở Trang Chi tiết", type="primary", width="stretch", disabled=not proj_lookup):
            chosen_row = proj_lookup[selected_label]
            st.session_state["selected_project_code"] = chosen_row["project_code"]
            st.switch_page("modules/projects/detail.py")

else:
    st.info("📭 Chưa có công trình nào trên hệ thống.")
