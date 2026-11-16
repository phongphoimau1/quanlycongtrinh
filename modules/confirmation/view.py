import streamlit as st
import pandas as pd
from supabase import create_client
from services.confirmation_service import (
    get_confirmation_dashboard_data,
    sync_unprocessed_emails_to_queue,
    reopen_processed_item,
    approve_and_create_project,
    approve_and_link_existing_project,
    reject_confirmation_item,
)
from services.project_service import get_all_projects

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

col_title, col_sync = st.columns([3, 1])
with col_title:
    st.title("⏳ Chờ xác nhận (AI & Điều phối Công trình)")
with col_sync:
    st.write("")
    if st.button("🤖 Quét & Bóc tách Email mới", type="primary", width="stretch"):
        sync_res = sync_unprocessed_emails_to_queue()
        if sync_res["success"]:
            st.toast(sync_res["message"], icon="🤖")
            st.rerun()
        else:
            st.error(sync_res["message"])

dash_data = get_confirmation_dashboard_data()
pending_matching = dash_data["pending_matching"]
pending_ai = dash_data["pending_ai"]
processed_items = dash_data["processed_items"]

k1, k2, k3 = st.columns(3)
k1.metric("🔗 Chờ ghép vào CT có sẵn", f"{len(pending_matching)} yêu cầu")
k2.metric("🤖 AI bóc tách chờ duyệt mới", f"{len(pending_ai)} bản ghi")
k3.metric("✅ Tổng đã xử lý", f"{len(processed_items)} mục")

st.divider()


def render_action_panel(selected_item, panel_key_prefix):
    st.divider()
    st.subheader(f"🛠️ Xử lý yêu cầu: `{selected_item['subject']}`")

    with st.expander("🤖 Xem dữ liệu JSON do AI bóc tách", expanded=False):
        st.json(selected_item.get("raw_extracted") or {"info": "Dữ liệu trích xuất tiêu chuẩn"})

    sub_tab1, sub_tab2, sub_tab3 = st.tabs(
        [
            "✨ Duyệt & Khởi tạo CT Mới",
            "🔗 Ghép vào Công trình Có sẵn",
            "🗑️ Từ chối / Bỏ qua",
        ]
    )

    with sub_tab1:
        try:
            cat_res = supabase.table("categories").select("id, category_name").execute()
            cat_dict = {c["category_name"]: c["id"] for c in (cat_res.data or [])}
        except Exception:
            cat_dict = {}

        with st.form(f"form_approve_{panel_key_prefix}_{selected_item['record_id']}"):
            c1, c2 = st.columns(2)
            with c1:
                customer_name = st.text_input("Tên khách hàng", value=selected_item["extracted_customer"])
                project_name = st.text_input("Tên công trình", value=selected_item["extracted_project"])
            with c2:
                project_code = st.text_input("Mã công trình (Để trống tự sinh)", value=selected_item["extracted_code"])
                cat_name = st.selectbox("Danh mục dự án", list(cat_dict.keys()) if cat_dict else ["Mặc định"])
                category_id = cat_dict.get(cat_name)

            c3, c4 = st.columns(2)
            with c3:
                received_date = st.text_input("Ngày nhận", value=str(selected_item["received_at"])[:10])
            with c4:
                due_date = st.date_input("Hạn hoàn thành")

            staff_options = ["Chưa phân nhân sự", "Ms Hân", "Mr Thái", "Mr Thịnh", "Ms Hương", "Ms Hiếu"]
            staff_name = st.selectbox("Phân công nhân viên phụ trách", staff_options)
            status = st.selectbox("Trạng thái khởi tạo", ["Đang thực hiện", "Mới tiếp nhận", "Hoàn thành"])
            request_content = st.text_area("Nội dung yêu cầu", value=selected_item["extracted_requirements"])

            if st.form_submit_button("✅ Phê duyệt & Tạo Công trình", type="primary", width="stretch"):
                assigned_val = staff_name if staff_name != "Chưa phân nhân sự" else None
                res = approve_and_create_project(
                    queue_id=selected_item.get("queue_id"),
                    email_id=selected_item.get("email_id"),
                    customer_name=customer_name,
                    project_name=project_name,
                    project_code=project_code,
                    category_id=category_id,
                    assigned_to=assigned_val,
                    received_date=received_date,
                    due_date=str(due_date),
                    request_content=request_content,
                    status=status,
                )
                if res["success"]:
                    st.success(res["message"])
                    st.rerun()
                else:
                    st.error(res["message"])

    with sub_tab2:
        projects_list = get_all_projects()
        if projects_list:
            proj_options = {
                f"{p.get('project_code', 'N/A')} - {p.get('project_name', 'Chưa đặt tên')} ({p.get('customer_name', '')})": p["id"]
                for p in projects_list
            }
            sel_proj_label = st.selectbox(
                "Chọn công trình hiện hữu để ghép nối email này:",
                list(proj_options.keys()),
                key=f"sel_link_{panel_key_prefix}_{selected_item['record_id']}",
            )
            if st.button(
                "🔗 Xác nhận Ghép nối vào Công trình này",
                type="primary",
                width="stretch",
                key=f"btn_link_{panel_key_prefix}_{selected_item['record_id']}",
            ):
                res = approve_and_link_existing_project(
                    queue_id=selected_item.get("queue_id"),
                    email_id=selected_item.get("email_id"),
                    existing_project_id=proj_options[sel_proj_label],
                )
                if res["success"]:
                    st.success(res["message"])
                    st.rerun()
                else:
                    st.error(res["message"])
        else:
            st.info("Hiện chưa có công trình nào để ghép nối.")

    with sub_tab3:
        reject_note = st.text_input(
            "Lý do từ chối:",
            value="Email không phải yêu cầu công trình / Trùng lặp",
            key=f"rej_note_{panel_key_prefix}_{selected_item['record_id']}",
        )
        if st.button(
            "🗑️ Xác nhận Từ chối",
            type="secondary",
            width="stretch",
            key=f"btn_rej_{panel_key_prefix}_{selected_item['record_id']}",
        ):
            res = reject_confirmation_item(
                queue_id=selected_item.get("queue_id"),
                email_id=selected_item.get("email_id"),
                reject_reason=reject_note,
            )
            if res["success"]:
                st.toast(res["message"], icon="🗑️")
                st.rerun()
            else:
                st.error(res["message"])


tab_match, tab_ai, tab_done = st.tabs(
    [
        f"🔗 Ghép nối Công trình ({len(pending_matching)})",
        f"🤖 Duyệt bóc tách AI ({len(pending_ai)})",
        f"✅ Đã xử lý ({len(processed_items)})",
    ]
)

with tab_match:
    if pending_matching:
        df_m = pd.DataFrame(pending_matching).fillna("")
        disp_m = df_m[
            ["sender_email", "subject", "candidate_project_display", "reason", "received_at"]
        ].rename(
            columns={
                "sender_email": "Người gửi",
                "subject": "Tiêu đề Email",
                "candidate_project_display": "Công trình gợi ý ghép",
                "reason": "Lý do chờ xác nhận",
                "received_at": "Thời gian nhận",
            }
        )
        ev_m = st.dataframe(
            disp_m,
            width="stretch",
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="df_match",
        )
        if ev_m.selection.rows:
            render_action_panel(df_m.iloc[ev_m.selection.rows[0]], "match")
    else:
        st.info("🎉 Không có yêu cầu ghép nối công trình nào đang chờ xác nhận.")

with tab_ai:
    if pending_ai:
        df_a = pd.DataFrame(pending_ai).fillna("")
        df_a["conf_str"] = df_a["confidence"].apply(
            lambda x: f"{float(x)*100:.0f}%"
            if str(x).replace(".", "", 1).isdigit() and float(x) <= 1.0
            else f"{x}%"
        )
        disp_a = df_a[
            ["sender_email", "subject", "extracted_project", "extracted_customer", "conf_str", "received_at"]
        ].rename(
            columns={
                "sender_email": "Người gửi",
                "subject": "Tiêu đề Email",
                "extracted_project": "Tên CT (AI bóc tách)",
                "extracted_customer": "Khách hàng (AI)",
                "conf_str": "Độ tin cậy",
                "received_at": "Thời gian nhận",
            }
        )
        ev_a = st.dataframe(
            disp_a,
            width="stretch",
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="df_ai",
        )
        if ev_a.selection.rows:
            render_action_panel(df_a.iloc[ev_a.selection.rows[0]], "ai")
    else:
        st.info("🎉 Không có bản ghi AI bóc tách nào đang tồn đọng.")

with tab_done:
    if processed_items:
        st.markdown("#### 📜 Danh sách các mục đã duyệt / đã xử lý (Click chọn dòng nếu muốn hoàn tác về Chờ duyệt)")
        df_p = pd.DataFrame(processed_items).fillna("")
        disp_p = df_p[
            ["sender_email", "subject", "extracted_project", "decision", "reason", "reviewed_at"]
        ].rename(
            columns={
                "sender_email": "Người gửi",
                "subject": "Tiêu đề Email",
                "extracted_project": "Tên Công trình",
                "decision": "Quyết định xử lý",
                "reason": "Ghi chú / Lý do",
                "reviewed_at": "Thời gian xử lý",
            }
        )
        ev_p = st.dataframe(
            disp_p,
            width="stretch",
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="df_done",
        )
        if ev_p.selection.rows:
            sel_done = df_p.iloc[ev_p.selection.rows[0]]
            st.markdown(
                f"**Mục đang chọn:** `{sel_done['subject']}` — Trạng thái hiện tại: `{sel_done['decision']}`"
            )
            if st.button("🔄 Hoàn tác mục này về hàng đợi Chờ xác nhận", type="primary"):
                re_res = reopen_processed_item(
                    queue_id=sel_done.get("queue_id"),
                    ai_id=sel_done.get("ai_id"),
                    email_id=sel_done.get("email_id"),
                )
                if re_res["success"]:
                    st.success(re_res["message"])
                    st.rerun()
                else:
                    st.error(re_res["message"])
    else:
        st.info("Chưa có lịch sử mục nào đã xử lý.")
