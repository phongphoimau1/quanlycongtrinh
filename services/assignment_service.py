import streamlit as st
from supabase import create_client
from datetime import datetime
from services.project_service import format_to_iso_date, resolve_staff_assignment

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def assign_projects_bulk(project_ids, staff_name, due_date=None, note=""):
    """
    Phân công hoặc điều chuyển nhân sự cho một hoặc nhiều công trình cùng lúc.
    Đồng bộ tự động vào bảng projects, project_status_history và audit_logs.
    """
    if not project_ids:
        return {"success": False, "message": "⚠️ Vui lòng chọn ít nhất 1 công trình để phân công."}

    try:
        now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        final_assigned = resolve_staff_assignment(supabase, staff_name)

        # Lấy organization_id và actor_id mặc định cho audit_logs
        org_res = supabase.table('organizations').select('id').limit(1).execute()
        org_id = org_res.data[0]['id'] if org_res.data else None

        prof_res = supabase.table('profiles').select('id').limit(1).execute()
        actor_id = prof_res.data[0]['id'] if prof_res.data else None

        update_payload = {
            "assigned_to": final_assigned,
            "updated_at": now_iso
        }
        if due_date:
            update_payload["due_date"] = format_to_iso_date(due_date)

        for pid in project_ids:
            # 1. Cập nhật bảng projects
            supabase.table('projects').update(update_payload).eq('id', pid).execute()

            # 2. Ghi vết vào project_status_history
            try:
                supabase.table('project_status_history').insert({
                    "project_id": pid,
                    "changed_by": actor_id,
                    "old_status": "Chưa phân công",
                    "new_status": "Đang thực hiện",
                    "note": f"Phân công phụ trách cho: {staff_name}. {note}".strip(),
                    "changed_at": now_iso
                }).execute()
            except Exception as e:
                print(f"Lỗi ghi history khi phân công: {e}")

            # 3. Ghi vết vào bảng audit_logs theo chuẩn Schema
            try:
                supabase.table('audit_logs').insert({
                    "organization_id": org_id,
                    "action": "ASSIGN_STAFF",
                    "entity_type": "projects",
                    "entity_id": pid,
                    "details": {
                        "assigned_to": staff_name,
                        "resolved_value": str(final_assigned),
                        "due_date": str(due_date) if due_date else None,
                        "note": note
                    },
                    "actor_id": actor_id,
                    "created_at": now_iso
                }).execute()
            except Exception as e:
                print(f"Lỗi ghi audit_logs: {e}")

        return {
            "success": True,
            "message": f"✅ Đã phân công {len(project_ids)} công trình cho **{staff_name}**!"
        }
    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi hệ thống khi phân công: {str(e)}"}
