from datetime import datetime
import streamlit as st
from supabase import create_client
from services.project_service import create_project_directly_from_email

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_pending_confirmations():
    """
    Lấy danh sách các yêu cầu trong hàng đợi confirmation_queue và ai_extractions
    đang ở trạng thái chờ duyệt (decision IS NULL hoặc 'pending').
    """
    try:
        # 1. Lấy dữ liệu từ bảng confirmation_queue
        q_res = supabase.table('confirmation_queue').select('*').order('id', desc=True).execute()
        queue_items = q_res.data if q_res.data else []

        # 2. Lấy dữ liệu từ bảng ai_extractions
        ai_res = supabase.table('ai_extractions').select('*').order('created_at', desc=True).execute()
        ai_items = ai_res.data if ai_res.data else []

        # 3. Lấy danh sách emails, projects, profiles để map thông tin hiển thị
        emails_res = supabase.table('emails').select('id, sender_email, subject, received_at, processing_status').execute()
        emails_map = {e['id']: e for e in (emails_res.data or [])}

        proj_res = supabase.table('projects').select('id, project_code, project_name, customer_name, assigned_to').execute()
        proj_map = {p['id']: p for p in (proj_res.data or [])}

        return {
            "queue": queue_items,
            "ai_extractions": ai_items,
            "emails_map": emails_map,
            "proj_map": proj_map
        }
    except Exception as e:
        print(f"Lỗi truy vấn hàng đợi xác nhận: {e}")
        return {"queue": [], "ai_extractions": [], "emails_map": {}, "proj_map": {}}

def approve_link_to_existing_project(queue_id, email_id, project_id, reason_note=""):
    """
    Xác nhận ghép email vào một công trình đã tồn tại (từ bảng confirmation_queue).
    """
    try:
        now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 1. Cập nhật quyết định trong confirmation_queue
        supabase.table('confirmation_queue').update({
            "decision": "approved",
            "reason": reason_note,
            "reviewed_at": now_iso
        }).eq("id", queue_id).execute()

        # 2. Ghi nhận liên kết vào bảng trung gian project_emails
        if project_id and email_id:
            supabase.table('project_emails').upsert({
                "project_id": project_id,
                "email_id": email_id,
                "relation_type": "update",
                "is_confirmed": True
            }, on_conflict="project_id,email_id").execute()

        # 3. Đổi trạng thái email sang 'Đã giao'
        if email_id:
            supabase.table('emails').update({
                "processing_status": "Đã giao"
            }).eq("id", email_id).execute()

        return {"success": True, "message": "✅ Đã xác nhận ghép email vào công trình thành công!"}
    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi hệ thống: {str(e)}"}

def reject_queue_item(table_name, item_id, email_id=None, reason_note=""):
    """
    Từ chối gợi ý của hệ thống/AI.
    """
    try:
        update_payload = {"decision": "rejected"}
        if table_name == "confirmation_queue":
            update_payload["reason"] = reason_note
            update_payload["reviewed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        supabase.table(table_name).update(update_payload).eq("id", item_id).execute()

        if email_id:
            supabase.table('emails').update({
                "processing_status": "Chưa xử lý"
            }).eq("id", email_id).execute()

        return {"success": True, "message": "🚫 Đã từ chối gợi ý và trả email về danh sách chờ xử lý."}
    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi khi từ chối: {str(e)}"}

def approve_ai_extraction_to_new_project(
    extraction_id, email_id, customer_name, project_name, 
    project_code, category_id, staff_name, received_date, 
    due_date, request_content, status
):
    """
    Duyệt dữ liệu bóc tách từ bảng ai_extractions và khởi tạo công trình mới.
    """
    res = create_project_directly_from_email(
        email_id=email_id,
        customer_name=customer_name,
        project_name=project_name,
        project_code=project_code,
        category_id=category_id,
        assigned_to_uuid=staff_name if staff_name != "Chưa phân nhân sự" else None,
        received_date=received_date,
        due_date=str(due_date),
        request_content=request_content,
        status=status
    )

    if res.get("success"):
        try:
            supabase.table('ai_extractions').update({
                "decision": "approved",
                "suggested_project_id": res.get("project_id")
            }).eq("id", extraction_id).execute()
        except Exception as e:
            print(f"Lỗi cập nhật ai_extractions: {e}")

    return res
