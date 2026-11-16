import streamlit as st
import pandas as pd
from services.document_service import (
    get_all_project_documents,
    get_unlinked_email_attachments,
    add_project_document,
    delete_project_document
)
from services.project_service import get_all_projects

st.title("📂 Quản lý Hồ sơ & Tài liệu Công trình")

# 1. Bộ lọc và Tìm kiếm
projects_list = get_all_projects()
proj_dict = {
    f"{p.get('project_code', 'N/A')} - {p.get('project_name', 'Chưa đặt tên')}": p['id']
    for p in (projects_list or [])
}

col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
with col_f1:
    search_doc = st.text_input("🔍 Tìm tên file, mã công trình hoặc khách hàng...", placeholder="Nhập từ khóa...")
with col_f2:
    doc_type_filter = st.selectbox(
        "Phân loại hồ sơ", 
        ["Tất cả", "Bản vẽ kỹ thuật", "Phương án phối màu", "Hợp đồng / Báo giá", "Hình ảnh hiện trạng", "Hồ sơ chung"]
    )
with col_f3:
    st.write("")
    st.write("")
    if st.button("🔄 Làm mới", width='stretch'):
        st.cache_data.clear()
        st.rerun()

# 2. Khu vực Thêm mới / Đồng bộ Hồ sơ từ Email
with st.expander("➕ Thêm mới Hồ sơ hoặc Đồng bộ File đính kèm từ Email", expanded=False):
    if not proj_dict:
        st.warning("⚠️ Chưa có công trình nào trên hệ thống. Vui lòng tạo công trình trước.")
    else:
        tab_upload, tab_from_email = st.tabs(["📤 Khai báo Hồ sơ / Đường dẫn Lưu trữ", "📎 Lấy từ Đính kèm Email (email_attachments)"])
        
        with tab_upload:
            with st.form("form_add_manual_doc"):
                c1, c2 = st.columns(2)
                with c1:
                    sel_proj_label = st.selectbox("Chọn công trình", list(proj_dict.keys()))
                    doc_type = st.selectbox(
                        "Loại tài liệu", 
                        ["Bản vẽ kỹ thuật", "Phương án phối màu", "Hợp đồng / Báo giá", "Hình ảnh hiện trạng", "Hồ sơ chung"]
                    )
                with c2:
                    storage_path = st.text_input("Đường dẫn file / Link lưu trữ (Supabase Storage / Drive URL)", placeholder="projects/PRJ-2611/ban-ve.pdf")
                    uploaded_file = st.file_uploader("Hoặc chọn file từ máy tính (Tự động lấy tên đường dẫn)", type=['pdf', 'png', 'jpg', 'jpeg', 'dwg', 'docx', 'xlsx', 'zip'])

                btn_save_doc = st.form_submit_button("💾 Lưu vào Hồ sơ Công trình", type="primary", width='stretch')
                if btn_save_doc:
                    target_proj_id = proj_dict[sel_proj_label]
                    final_path = storage_path.strip()
                    if uploaded_file and not final_path:
                        final_path = f"uploads/{target_proj_id}/{uploaded_file.name}"
                    
                    if not final_path:
                        st.warning("⚠️ Vui lòng nhập đường dẫn lưu trữ hoặc chọn 1 file!")
                    else:
                        res = add_project_document(
                            project_id=target_proj_id,
                            document_type=doc_type,
                            storage_path=final_path
                        )
                        if res["success"]:
                            st.success(res["message"])
                            st.rerun()
                        else:
                            st.error(res["message"])

        with tab_from_email:
            sel_proj_email_label = st.selectbox("Chọn công trình cần gắn file từ Email", list(proj_dict.keys()), key="sel_proj_att")
            target_proj_id_att = proj_dict[sel_proj_email_label]
            attachments = get_unlinked_email_attachments(target_proj_id_att)
            
            if attachments:
                att_options = {
                    f"{a.get('file_name', 'File không tên')} ({a.get('mime_type', 'N/A')})": a
                    for a in attachments
                }
                c_a1, c_a2 = st.columns(2)
                with c_a1:
                    sel_att_label = st.selectbox("Chọn file đính kèm từ Email", list(att_options.keys()))
                with c_a2:
                    att_doc_type = st.selectbox(
                        "Phân loại khi lưu vào hồ sơ",
                        ["Bản vẽ kỹ thuật", "Phương án phối màu", "Hình ảnh hiện trạng", "Hợp đồng / Báo giá", "Hồ sơ chung"],
                        key="att_doc_type"
                    )
                if st.button("🔗 Gắn File đính kèm này vào Hồ sơ Công trình", type="primary", width='stretch'):
                    chosen_att = att_options[sel_att_label]
                    res = add_project_document(
                        project_id=target_proj_id_att,
                        document_type=att_doc_type,
                        storage_path=chosen_att.get('storage_path') or chosen_att.get('file_name', ''),
                        attachment_id=chosen_att.get('id')
                    )
                    if res["success"]:
                        st.success(res["message"])
                        st.rerun()
                    else:
                        st.error(res["message"])
            else:
                st.info("📭 Không tìm thấy file đính kèm nào trong bảng `email_attachments` cho công trình này.")

# 3. Hiển thị Danh sách Hồ sơ
docs_data = get_all_project_documents()

if docs_data:
    df_docs = pd.DataFrame(docs_data).fillna("")

    if doc_type_filter != "Tất cả":
        df_docs = df_docs[df_docs['document_type'] == doc_type_filter]

    if search_doc:
        kw = search_doc.lower()
        df_docs = df_docs[
            df_docs['file_name'].astype(str).str.lower().str.contains(kw, na=False) |
            df_docs['project_code'].astype(str).str.lower().str.contains(kw, na=False) |
            df_docs['project_name'].astype(str).str.lower().str.contains(kw, na=False) |
            df_docs['customer_name'].astype(str).str.lower().str.contains(kw, na=False)
        ]

    st.markdown(f"### 📋 Danh sách Hồ sơ Lưu trữ ({len(df_docs)} tài liệu) - Click vào dòng để xem / thao tác")

    display_docs_df = df_docs[[
        "project_code",
        "project_name",
        "document_type",
        "file_name",
        "mime_type",
        "storage_path"
    ]].rename(columns={
        "project_code": "Mã CT",
        "project_name": "Tên công trình",
        "document_type": "Loại hồ sơ",
        "file_name": "Tên File",
        "mime_type": "Định dạng",
        "storage_path": "Đường dẫn lưu trữ"
    }).replace("", "Chưa cập nhật")

    event = st.dataframe(
        display_docs_df,
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    selected_rows = event.selection.rows
    if selected_rows:
        sel_idx = selected_rows[0]
        sel_doc = df_docs.iloc[sel_idx]
        
        st.divider()
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            st.markdown(f"**📄 Tài liệu đang chọn:** `{sel_doc['file_name']}` | **Công trình:** `{sel_doc['project_code']} - {sel_doc['project_name']}`")
            st.code(sel_doc['storage_path'], language="text")
        with col_d2:
            if st.button("🗑️ Xóa hồ sơ này", type="secondary", width='stretch'):
                del_res = delete_project_document(sel_doc['doc_id'])
                if del_res["success"]:
                    st.toast(del_res["message"], icon="🗑️")
                    st.rerun()
                else:
                    st.error(del_res["message"])
else:
    st.info("📭 Chưa có hồ sơ tài liệu nào được lưu trong hệ thống.")
