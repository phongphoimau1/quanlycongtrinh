import streamlit as st
import pandas as pd
from supabase import create_client
from services.confirmation_service import (
    get_pending_confirmations,
    approve_link_to_existing_project,
    reject_queue_item,
    approve_ai_extraction_to_new_project
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("⏳ Chờ xác nhận (AI & Điều phối Công trình)")

# Tải dữ liệu tổng hợp
data_bundle = get_pending_confirmations()
queue_list = data_bundle["queue"]
ai_list = data_bundle["ai_extractions"]
emails_map = data_bundle["emails_map"]
proj_map = data_bundle["proj_map"]

# Lọc các bản ghi đang chờ xử lý (decision trống hoặc 'pending')
pending_queue = [
    q for q in queue_list 
    if not q.get("decision") or str(q.get("decision")).lower() in ["pending", "chờ xác nhận", "none"]
]
pending_ai = [
    a for a in ai_list 
    if not a.get("decision") or str(a.get("decision")).lower() in ["pending", "chờ xác nhận", "none"]
]

# Thống kê nhanh trên đầu trang
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("🔗 Chờ ghép vào CT có sẵn", f"{len(pending_queue)} yêu cầu")
col_m2.metric("🤖 AI bóc tách chờ duyệt mới", f"{len(pending_ai)} bản ghi")
col_m3.metric("✅ Tổng đã xử lý", f"{(len(queue_list) - len(pending_queue)) + (len(ai_list) - len(pending_ai))} mục")

st.divider()

tab1, tab2 = st.tabs([
    f"🔗 Ghép nối Công trình ({len(pending_queue)})", 
    f"🤖 Duyệt bóc tách AI ({len(pending_ai)})"
])

# ==============================================================================
# TAB 1: HÀNG ĐỢI GHÉP NỐI CÔNG TRÌNH (Bảng confirmation_queue)
# ==============================================================================
with tab1:
    if pending_queue:
        rows = []
        for q in pending_queue:
            e_info = emails_map.get(q.get("email_id"), {})
            p_info = proj_map.get(q.get("candidate_project_id"), {})
            rows.append({
                "queue_id": q.get("id"),
                "email_id": q.get("email_id"),
                "project_id": q.get("candidate_project_id"),
                "Tiêu đề Email": e_info.get("subject", "Không rõ tiêu đề"),
                "Người gửi": e_info.get("sender_email", "Chưa rõ"),
                "Mã CT gợi ý": p_info.get("project_code", "Chưa có mã"),
                "Tên CT gợi ý": p_info.get("project_name", "Không rõ"),
                "Lý do ghép": q.get("reason") or "Trùng khớp thông tin luồng email"
            })
        
        df_q = pd.DataFrame(rows)
        st.markdown("#### 📋 Danh sách đề xuất ghép Email vào Công trình hiện hữu")
        
        event_q = st.dataframe(
            df_q[["Tiêu đề Email", "Người gửi", "Mã CT gợi ý", "Tên CT gợi ý", "Lý do ghép"]],
            width='stretch',
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="table_confirm_queue"
        )

        sel_q = event_q.selection.rows
        if sel_q:
            selected_item = df_q.iloc[sel_q[0]]
            st.markdown(f"##### 🔍 Xử lý đề xuất: `{selected_item['Tiêu đề Email']}` ➡️ `{selected_item['Mã CT gợi ý']}`")
            
            # Cho phép chọn lại công trình khác nếu AI gợi ý lệch
            proj_options = {
                f"{p.get('project_code', 'N/A')} - {p.get('project_name', 'Chưa đặt tên')}": p_id 
                for p_id, p in proj_map.items()
            }
            default_label = next(
                (k for k, v in proj_options.items() if v == selected_item["project_id"]), 
                list(proj_options.keys())[0] if proj_options else ""
            )

            col_act1, col_act2 = st.columns(2)
            with col_act1:
                chosen_proj_label = st.selectbox(
                    "Công trình đích (Có thể đổi nếu cần):", 
                    options=list(proj_options.keys()) if proj_options else ["Chưa có công trình"],
                    index=list(proj_options.keys()).index(default_label) if default_label in proj_options else 0
                )
            with col_act2:
                review_note = st.text_input("Ghi chú xác nhận:", value=selected_item["Lý do ghép"])

            col_btn1, col_btn2, _ = st.columns([1, 1, 3])
            with col_btn1:
                if st.button("✅ Xác nhận Ghép", type="primary", width='stretch', key="btn_approve_q"):
                    target_proj_id = proj_options.get(chosen_proj_label)
                    res = approve_link_to_existing_project(
                        queue_id=selected_item["queue_id"],
                        email_id=selected_item["email_id"],
                        project_id=target_proj_id,
                        reason_note=review_note
                    )
                    if res["success"]:
                        st.success(res["message"])
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(res["message"])
            with col_btn2:
                if st.button("🚫 Từ chối", width='stretch', key="btn_reject_q"):
                    res = reject_queue_item(
                        table_name="confirmation_queue",
                        item_id=selected_item["queue_id"],
                        email_id=selected_item["email_id"],
                        reason_note=review_note
                    )
                    if res["success"]:
                        st.warning(res["message"])
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(res["message"])
    else:
        st.info("🎉 Không có yêu cầu ghép nối công trình nào đang chờ xác nhận.")

# ==============================================================================
# TAB 2: DUYỆT BÓC TÁCH AI TẠO CÔNG TRÌNH MỚI (Bảng ai_extractions)
# ==============================================================================
with tab2:
    if pending_ai:
        ai_rows = []
        for a in pending_ai:
            e_info = emails_map.get(a.get("email_id"), {})
            ext_json = a.get("extracted_data") or {}
            if not isinstance(ext_json, dict):
                ext_json = {}
            
            conf_val = a.get("confidence")
            conf_str = f"{float(conf_val)*100:.0f}%" if conf_val is not None else "N/A"

            ai_rows.append({
                "extraction_id": a.get("id"),
                "email_id": a.get("email_id"),
                "Tiêu đề Email": e_info.get("subject", "Không rõ tiêu đề"),
                "Khách hàng (AI)": ext_json.get("customer_name") or e_info.get("sender_email", "Chưa rõ"),
                "Tên CT (AI)": ext_json.get("project_name") or e_info.get("subject", ""),
                "Độ tin cậy": conf_str,
                "raw_json": ext_json,
                "received_at": str(e_info.get("received_at", ""))[:10]
            })

        df_ai = pd.DataFrame(ai_rows)
        st.markdown("#### 🤖 Danh sách dữ liệu AI đã bóc tách từ Email (Click vào dòng để duyệt & khởi tạo)")

        event_ai = st.dataframe(
            df_ai[["Tiêu đề Email", "Khách hàng (AI)", "Tên CT (AI)", "Độ tin cậy", "received_at"]].rename(
                columns={"received_at": "Ngày nhận"}
            ),
            width='stretch',
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="table_ai_extractions"
        )

        sel_ai = event_ai.selection.rows
        if sel_ai:
            sel_item = df_ai.iloc[sel_ai[0]]
            ext_data = sel_item["raw_json"]

            st.divider()
            st.markdown(f"##### 🚀 Duyệt & Khởi tạo Công trình từ bản ghi AI (Độ tin cậy: `{sel_item['Độ tin cậy']}`)")

            try:
                cat_res = supabase.table('categories').select('id, category_name').execute()
                cat_dict = {c['category_name']: c['id'] for c in (cat_res.data or [])}
            except Exception:
                cat_dict = {}

            with st.form(f"form_confirm_ai_{sel_item['extraction_id']}"):
                c1, c2 = st.columns(2)
                with c1:
                    customer_name = st.text_input("Tên khách hàng", value=sel_item["Khách hàng (AI)"])
                    project_name = st.text_input("Tên công trình", value=sel_item["Tên CT (AI)"])
                with c2:
                    project_code = st.text_input("Mã công trình (Để trống nếu tự sinh)", value=ext_data.get("project_code", ""))
                    category_name = st.selectbox("Danh mục dự án", list(cat_dict.keys()) if cat_dict else ["Mặc định"])
                    category_id = cat_dict.get(category_name)

                c3, c4 = st.columns(2)
                with c3:
                    received_date = st.text_input("Ngày nhận", value=sel_item["received_at"])
                with c4:
                    due_date = st.date_input("Ngày hạn hoàn thành")

                staff_options = ["Chưa phân nhân sự", "Ms Hân", "Mr Thái", "Mr Thịnh", "Ms Hương", "Ms Hiếu"]
                suggested_staff = ext_data.get("assigned_to", "Chưa phân nhân sự")
                default_staff_idx = staff_options.index(suggested_staff) if suggested_staff in staff_options else 0
                staff_name = st.selectbox("Giao cho nhân viên phụ trách", staff_options, index=default_staff_idx)

                status = st.selectbox("Trạng thái khởi tạo", ["Mới tiếp nhận", "Đang thực hiện", "Hoàn thành"], index=1)
                request_content = st.text_area(
                    "Nội dung yêu cầu bóc tách", 
                    value=ext_data.get("request_content") or sel_item["Tiêu đề Email"]
                )

                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    btn_approve = st.form_submit_button("✅ Duyệt & Tạo Công trình", type="primary", width='stretch')
                with b_col2:
                    btn_reject = st.form_submit_button("🚫 Từ chối bản ghi AI", width='stretch')

                if btn_approve:
                    if not customer_name:
                        st.warning("⚠️ Vui lòng nhập Tên khách hàng!")
                    else:
                        res = approve_ai_extraction_to_new_project(
                            extraction_id=sel_item["extraction_id"],
                            email_id=sel_item["email_id"],
                            customer_name=customer_name,
                            project_name=project_name,
                            project_code=project_code,
                            category_id=category_id,
                            staff_name=staff_name,
                            received_date=received_date,
                            due_date=due_date,
                            request_content=request_content,
                            status=status
                        )
                        if res["success"]:
                            st.success(res["message"])
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(res["message"])

                if btn_reject:
                    res = reject_queue_item(
                        table_name="ai_extractions",
                        item_id=sel_item["extraction_id"],
                        email_id=sel_item["email_id"]
                    )
                    if res["success"]:
                        st.warning(res["message"])
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(res["message"])
    else:
        st.info("🎉 Không có bản ghi bóc tách AI nào đang chờ duyệt.")
