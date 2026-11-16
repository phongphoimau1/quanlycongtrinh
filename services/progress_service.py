import streamlit as st
from supabase import create_client
from datetime import datetime
from services.project_service import format_to_iso_date, resolve_staff_assignment

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_project_status_logs(project_id=None):
    """
    Lấy lịch sử thay đổi trạng thái từ bảng project_status_history,
    ánh xạ tên người thực hiện từ bảng profiles và tên công trình từ bảng projects.
    """
    try:
        query = supabase.table('project_status_history').select('*').order('changed_at', desc=True)
        if project_id:
            query = query.eq('project_id', project_id)
        res = query.execute()
        logs = res.data if res.data else []
        if not logs:
            return []

        proj_res = supabase.table('projects').select('id, project_code, project_name').execute()
        proj_map = {p['id']: p for p in (proj_res.data or [])}

        prof_res = supabase.table('profiles').select('id, full_name, email').execute()
        prof_map = {str(p['id']): (p.get('full_name') or p.get('email') or "Nhân sự") for p in (prof_res.data or [])}

        enriched_logs = []
        for log in logs:
            p_info = proj_map.get(log.get('project_id'), {})
            changer_id = str(log.get('changed_by') or '')
            changer_name = prof_map.get(changer_id, changer_id if changer_id and changer_id != 'None' else "Hệ thống / Quản trị viên")

            enriched_logs.append({
                "id": log.get('id'),
                "project_code": p_info.get('project_code', 'N/A'),
                "project_name": p_info.get('project_name', 'Chưa rõ'),
                "old_status": log.get('old_status') or "Khởi tạo",
                "new_status": log.get('new_status') or "Đang thực hiện",
                "changed_by_name": changer_name,
                "note": log.get('note') or "",
                "changed_at": str(log.get('changed_at', ''))[:19].replace('T', ' ')
            })
        return enriched_logs
    except Exception as e:
        print(f"Lỗi truy vấn lịch sử tiến độ: {e}")
        return []

def update_project_progress(project_id, old_status, new_status, assigned_to_name, due_date, completed_date, note, actor_name=None):
    """
    Cập nhật trạng thái, hạn hoàn thành của công trình trong bảng projects
    và tự động ghi vết vào bảng project_status_history.
    """
    try:
        now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        final_assigned = resolve_staff_assignment(supabase, assigned_to_name)

        update_payload = {
            "status": new_status,
            "assigned_to": final_assigned,
            "updated_at": now_iso
        }
        if due_date:
            update_payload["due_date"] = format_to_iso_date(due_date)
        if completed_date:
            update_payload["completed_date"] = format_to_iso_date(completed_date)
        elif new_status == "Hoàn thành":
            update_payload["completed_date"] = datetime.now().strftime('%Y-%m-%d')

        supabase.table('projects').update(update_payload).eq('id', project_id).execute()

        # Tìm UUID hợp lệ cho cột changed_by (khóa ngoại trỏ tới profiles.id)
        actor_uuid = None
        try:
            prof_res = supabase.table('profiles').select('id, full_name, email').execute()
            profiles = prof_res.data if prof_res.data else []
            if actor_name and profiles:
                target = str(actor_name).lower().strip()
                for p in profiles:
                    if target in str(p.get('full_name', '')).lower() or target in str(p.get('email', '')).lower():
                        actor_uuid = p['id']
                        break
            if not actor_uuid and profiles:
                actor_uuid = profiles[0]['id']
        except Exception:
            actor_uuid = None

        history_payload = {
            "project_id": project_id,
            "changed_by": actor_uuid,
            "old_status": old_status,
            "new_status": new_status,
            "note": f"[{actor_name}] {note}".strip() if actor_name else note,
            "changed_at": now_iso
        }
        supabase.table('project_status_history').insert(history_payload).execute()

        return {"success": True, "message": "🚀 Cập nhật tiến độ và ghi nhận lịch sử thành công!"}
    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi cập nhật tiến độ: {str(e)}"}
