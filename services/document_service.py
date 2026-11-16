import streamlit as st
from supabase import create_client
from datetime import datetime

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_all_project_documents():
    try:
        docs_res = supabase.table('project_documents').select('*').execute()
        docs_data = docs_res.data if docs_res.data else []
        if not docs_data:
            return []

        try:
            proj_res = supabase.table('projects').select('id, project_code, project_name, customer_name').execute()
            proj_map = {p['id']: p for p in (proj_res.data or [])}
        except Exception:
            proj_map = {}

        try:
            att_res = supabase.table('email_attachments').select('id, file_name, mime_type, storage_path, email_id').execute()
            att_map = {a['id']: a for a in (att_res.data or [])}
        except Exception:
            att_map = {}

        enriched_docs = []
        for d in docs_data:
            p_info = proj_map.get(d.get('project_id'), {})
            a_info = att_map.get(d.get('attachment_id'), {})
            
            storage_path = d.get('storage_path') or a_info.get('storage_path') or "Chưa cập nhật đường dẫn"
            file_name = a_info.get('file_name') or (storage_path.split('/')[-1] if '/' in storage_path else storage_path)

            enriched_docs.append({
                "doc_id": d.get('id'),
                "project_id": d.get('project_id'),
                "project_code": p_info.get('project_code', 'Chưa rõ'),
                "project_name": p_info.get('project_name', 'Chưa rõ'),
                "customer_name": p_info.get('customer_name', ''),
                "document_type": d.get('document_type') or "Hồ sơ chung",
                "file_name": file_name,
                "mime_type": a_info.get('mime_type', 'Tài liệu'),
                "storage_path": storage_path,
                "attachment_id": d.get('attachment_id')
            })
        return enriched_docs
    except Exception as e:
        print(f"Lỗi tải danh sách hồ sơ: {e}")
        return []

def get_unlinked_email_attachments(project_id):
    """
    Tìm các file đính kèm (email_attachments) thuộc các email của công trình (project_emails)
    hoặc toàn hệ thống để người dùng gắn nhanh vào hồ sơ công trình.
    """
    try:
        pe_res = supabase.table('project_emails').select('email_id').eq('project_id', project_id).execute()
        email_ids = [item['email_id'] for item in (pe_res.data or []) if item.get('email_id')]

        if email_ids:
            att_res = supabase.table('email_attachments').select('*').in_('email_id', email_ids).execute()
        else:
            att_res = supabase.table('email_attachments').select('*').limit(50).execute()
            
        return att_res.data if att_res.data else []
    except Exception as e:
        print(f"Lỗi tải đính kèm email: {e}")
        return []

def add_project_document(project_id, document_type, storage_path, attachment_id=None):
    """
    Thêm bản ghi mới vào bảng project_documents.
    """
    try:
        payload = {
            "project_id": project_id,
            "document_type": document_type,
            "storage_path": storage_path,
            "attachment_id": attachment_id if attachment_id else None
        }
        res = supabase.table('project_documents').insert(payload).execute()
        if res.data:
            return {"success": True, "message": "✅ Đã lưu hồ sơ vào công trình thành công!"}
        return {"success": False, "message": "❌ Không thể lưu bản ghi hồ sơ."}
    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi hệ thống: {str(e)}"}

def delete_project_document(doc_id):
    """
    Xóa hồ sơ khỏi bảng project_documents.
    """
    try:
        supabase.table('project_documents').delete().eq('id', doc_id).execute()
        return {"success": True, "message": "🗑️ Đã xóa hồ sơ khỏi công trình!"}
    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi khi xóa hồ sơ: {str(e)}"}
