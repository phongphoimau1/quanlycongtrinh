import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📧 Quản lý & Tra cứu Email Hệ thống")

def safe_fetch_table(table_name, columns="*", order_col=None):
    """
    Truy vấn bảng an toàn: Nếu bảng bị chặn quyền RLS/42501, 
    tự động trả về danh sách rỗng [] thay vì làm sập toàn bộ trang.
    """
    try:
        query = supabase.table(table_name).select(columns)
        if order_col:
            query = query.order(order_col, desc=True)
        res = query.execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Cảnh báo phân quyền bảng {table_name}: {e}")
        return []

# 1. Tải dữ liệu độc lập từ từng bảng (Cô lập lỗi 42501)
emails_data = safe_fetch_table('emails', '*', order_col='received_at')
pe_data = safe_fetch_table('project_emails', '*')
proj_data = safe_fetch_table('projects', 'id, project_code, project_name')
att_data = safe_fetch_table('email_attachments', '*')

proj_map = {p['id']: p for p in proj_data if 'id' in p}

# Map email_id -> Danh sách công trình đã liên kết
email_to_projects = {}
for pe in pe_data:
    eid = pe.get('email_id')
    pid = pe.get('project_id')
    if eid and pid and pid in proj_map:
        p_code = proj_map[pid].get('project_code') or proj_map[pid].get('project_name')
        email_to_projects.setdefault(eid, []).append(p_code)

# Map email_id -> Số lượng và danh sách file đính kèm
email_to_attachments = {}
for att in att_data:
    eid = att.get('email_id')
    if eid:
        email_to_attachments.setdefault(eid, []).append(att)

# 2. Thống kê nhanh (KPIs)
total_em = len(emails_data)
unprocessed_em = sum(1 for e in emails_data if e.get('processing_status') in [None, '', 'Chưa xử lý', 'pending'])
assigned_em = sum(1 for e in emails_data if e.get('processing_status') in ['Đã giao', 'Hoàn thành', 'processed'])
rejected_em = sum(1 for e in emails_data if e.get('processing_status') in ['Từ chối', 'rejected'])

k1, k2, k3, k4 = st.columns(4)
k1.metric("📨 Tổng số Email", total_em)
k2.metric("⏳ Chưa xử lý", unprocessed_em)
k3.metric("✅ Đã giao / Xử lý", assigned_em)
k4.metric("🚫 Đã từ chối / Rác", rejected_em)

st.divider()

# 3. Thanh công cụ Tìm kiếm, Lọc & Thêm mới thủ công
c_f1, c_f2, c_f3, c_f4 = st.columns([2, 1, 1, 1])
with c_f1:
    kw_search = st.text_input("🔍 Tìm theo tiêu đề, người gửi, Message ID...", placeholder="Nhập từ khóa...")
with c_f2:
    status_filter = st.selectbox("Trạng thái xử lý", ["Tất cả", "Chưa xử lý", "Đang xử lý", "Đã giao", "Từ chối"])
with c_f3:
    type_filter = st.selectbox("Phân loại Email", ["Tất cả", "Yêu cầu mới", "Phản hồi / Bổ sung", "Khác"])
with c_f4:
    st.write("")
    st.write("")
    if st.button("🔄 Làm mới dữ liệu", width='stretch'):
        st.cache_data.clear()
        st.rerun()

with st.expander("➕ Tạo / Nhập Email thủ công vào Hệ thống (Dành cho Test hoặc Nhập bổ sung)", expanded=False):
    with st.form("form_manual_add_email"):
        cm1, cm2 = st.columns(2)
        with cm1:
            new_sender = st.text_input("Email người gửi *", placeholder="khachhang@gmail.com")
            new_subject = st.text_input("Tiêu đề Email *", placeholder="Đề nghị phối màu công trình...")
        with cm2:
            new_type = st.selectbox("Loại Email", ["Yêu cầu mới", "Phản hồi / Bổ sung", "Khác"])
            new_status = st.selectbox("Trạng thái ban đầu", ["Chưa xử lý", "Đang xử lý", "Đã giao"])

        btn_create_em = st.form_submit_button("📥 Lưu Email vào Hệ thống", type="primary", width='stretch')
        if btn_create_em:
            if not new_sender or not new_subject:
                st.warning("⚠️ Vui lòng nhập đầy đủ Người gửi và Tiêu đề email!")
            else:
                try:
                    org_res = supabase.table('organizations').select('id').limit(1).execute()
                    org_id = org_res.data[0]['id'] if org_res.data else None
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    msg_id = f"MANUAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"

                    supabase.table('emails').insert({
                        "organization_id": org_id,
                        "gmail_message_id": msg_id,
                        "email_thread_id": msg_id,
                        "sender_email": new_sender.strip(),
                        "subject": new_subject.strip(),
                        "received_at": now_str,
                        "email_type": new_type,
                        "processing_status": new_status
                    }).execute()
                    st.success("✅ Đã thêm email mới vào hệ thống thành công!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Lỗi khi thêm email: {ex}")

# 4. Hiển thị Bảng Quản lý Email
if emails_data:
    df_em = pd.DataFrame(emails_data).fillna("")

    df_em['linked_projects'] = df_em['id'].apply(
        lambda x: ", ".join(email_to_projects.get(x, [])) if x in email_to_projects else "Chưa gắn CT"
    )
    df_em['attachment_count'] = df_em['id'].apply(
        lambda x: f"📎 {len(email_to_attachments.get(x, []))} file" if x in email_to_attachments else "Không có"
    )
    df_em['processing_status'] = df_em['processing_status'].replace("", "Chưa xử lý")
    df_em['email_type'] = df_em.get('email_type', pd.Series([""] * len(df_em))).replace("", "Yêu cầu mới")

    if status_filter != "Tất cả":
        df_em = df_em[df_em['processing_status'] == status_filter]
    if type_filter != "Tất cả":
        df_em = df_em[df_em['email_type'] == type_filter]
    if kw_search:
        kw = kw_search.lower()
        df_em = df_em[
            df_em['subject'].astype(str).str.lower().str.contains(kw, na=False) |
            df_em['sender_email'].astype(str).str.lower().str.contains(kw, na=False) |
            df_em['linked_projects'].astype(str).str.lower().str.contains(kw, na=False)
        ]

    st.markdown(f"### 📋 Danh sách Quản lý Email ({len(df_em)} bản ghi) - Click chọn để cập nhật / xem đính kèm")

    display_df = df_em[[
        "sender_email",
        "subject",
        "linked_projects",
        "attachment_count",
        "email_type",
        "processing_status",
        "received_at"
    ]].rename(columns={
        "sender_email": "Người gửi",
        "subject": "Tiêu đề Email",
        "linked_projects": "Công trình liên kết",
        "attachment_count": "Đính kèm",
        "email_type": "Phân loại",
        "processing_status": "Trạng thái",
        "received_at": "Thời gian nhận"
    })

    event = st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # 5. Chi tiết & Thao tác quản trị trên Email đang chọn
    selected_rows = event.selection.rows
    if selected_rows:
        sel_idx = selected_rows[0]
        sel_email = df_em.iloc[sel_idx]
        eid = sel_email['id']

        st.divider()
        col_detail, col_action = st.columns([3, 2])

        with col_detail:
            st.subheader("🔍 Thông tin Chi tiết Email")
            st.markdown(f"**Tiêu đề:** {sel_email['subject']}")
            st.markdown(f"**Người gửi:** `{sel_email['sender_email']}` | **Ngày nhận:** `{sel_email['received_at']}`")
            st.markdown(f"**Message ID:** `{sel_email.get('gmail_message_id', 'N/A')}` | **Thread ID:** `{sel_email.get('email_thread_id', 'N/A')}`")
            st.markdown(f"**Công trình đã gắn:** `{sel_email['linked_projects']}`")

            atts = email_to_attachments.get(eid, [])
            if atts:
                st.markdown("**📎 Danh sách File đính kèm (`email_attachments`):**")
                df_att = pd.DataFrame(atts)[["file_name", "mime_type", "storage_path"]].rename(columns={
                    "file_name": "Tên file",
                    "mime_type": "Định dạng",
                    "storage_path": "Đường dẫn lưu trữ"
                })
                st.dataframe(df_att, width='stretch', hide_index=True)
            else:
                st.caption("📭 Email này không có file đính kèm.")

        with col_action:
            st.subheader("⚙️ Cập nhật / Xử lý")
            with st.form(f"form_edit_email_{eid}"):
                st_options = ["Chưa xử lý", "Đang xử lý", "Đã giao", "Từ chối"]
                curr_st = sel_email['processing_status'] if sel_email['processing_status'] in st_options else "Chưa xử lý"
                up_status = st.selectbox("Đổi trạng thái xử lý", st_options, index=st_options.index(curr_st))

                tp_options = ["Yêu cầu mới", "Phản hồi / Bổ sung", "Khác"]
                curr_tp = sel_email['email_type'] if sel_email['email_type'] in tp_options else "Yêu cầu mới"
                up_type = st.selectbox("Phân loại email", tp_options, index=tp_options.index(curr_tp))

                btn_up = st.form_submit_button("💾 Lưu thay đổi", type="primary", width='stretch')
                if btn_up:
                    try:
                        supabase.table('emails').update({
                            "processing_status": up_status,
                            "email_type": up_type
                        }).eq('id', eid).execute()
                        st.success("✅ Đã cập nhật trạng thái email!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"❌ Lỗi cập nhật: {ex}")

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("🚀 Chuyển sang Khởi tạo CT", width='stretch'):
                    st.switch_page("modules/emails/view.py")
            with c_btn2:
                if st.button("🗑️ Xóa Email này", type="secondary", width='stretch'):
                    try:
                        try:
                            supabase.table('project_emails').delete().eq('email_id', eid).execute()
                        except Exception:
                            pass
                        try:
                            supabase.table('email_attachments').delete().eq('email_id', eid).execute()
                        except Exception:
                            pass
                        supabase.table('emails').delete().eq('id', eid).execute()
                        st.toast("🗑️ Đã xóa email khỏi hệ thống!", icon="🗑️")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"❌ Không thể xóa: {ex}")
else:
    st.info("📭 Chưa có dữ liệu email nào trong hệ thống.")
