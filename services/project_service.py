from datetime import datetime
import re
import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================================================================
# 1. CÁC HÀM TIỆN ÍCH CHUẨN HÓA NGÀY THÁNG & ÁNH XẠ NHÂN SỰ
# ==============================================================================

def format_to_iso_date(date_input):
    """
    Chuẩn hóa định dạng ngày tháng về chuẩn ISO (YYYY-MM-DD hoặc YYYY-MM-DD HH:MM:SS).
    """
    if not date_input:
        return None
    if isinstance(date_input, datetime):
        return date_input.strftime('%Y-%m-%d %H:%M:%S')
        
    date_str = str(date_input).strip()
    if not date_str or date_str.lower() in ["none", "nan", "null", "chưa cập nhật"]:
        return None

    formats_to_try = [
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d'
    ]
    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d %H:%M:%S') if '%H' in fmt else dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def resolve_staff_assignment(supabase_client, staff_input):
    """
    Phân giải thông tin nhân viên phụ trách:
    - Nếu đầu vào là UUID hợp lệ: giữ nguyên.
    - Dò tìm trong bảng profiles để lấy UUID nếu trùng tên/email.
    - Nếu không có trong profiles (hoặc cột assigned_to là kiểu TEXT): trả về chuỗi tên.
    """
    if not staff_input or str(staff_input).strip() in ["", "Chưa phân nhân sự", "Chưa phân công", "None", "nan"]:
        return None
        
    val_str = str(staff_input).strip()
    uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    if uuid_regex.match(val_str):
        return val_str

    try:
        res = supabase_client.table('profiles').select('id, full_name, email').execute()
        profiles = res.data if res.data else []
        target = val_str.lower()
        for p in profiles:
            full_name = str(p.get('full_name') or '').lower()
            email = str(p.get('email') or '').lower()
            if target in full_name or target in email or (full_name and full_name in target):
                return p['id']
    except Exception as e:
        print(f"Lỗi tra cứu profiles: {e}")

    return val_str

def _resolve_display_staff_name(assigned_val, uuid_map=None):
    """
    Dịch ngược từ UUID hoặc mã giả lập sang tên hiển thị nhân viên.
    """
    if not assigned_val:
        return "Chưa phân công"
    val_str = str(assigned_val).strip()
    if not val_str or val_str.lower() in ["none", "nan", "null", "chưa phân nhân sự"]:
        return "Chưa phân công"

    val_lower = val_str.lower()
    if "11111111" in val_str or "hân" in val_lower:
        return "Ms Hân"
    elif "22222222" in val_str or "thái" in val_lower:
        return "Mr Thái"
    elif "33333333" in val_str or "thịnh" in val_lower:
        return "Mr Thịnh"
    elif "44444444" in val_str or "hương" in val_lower:
        return "Ms Hương"
    elif "55555555" in val_str or "hiếu" in val_lower:
        return "Ms Hiếu"

    if uuid_map and val_str in uuid_map:
        return uuid_map[val_str]

    try:
        res = supabase.table('profiles').select('id, full_name, email').eq('id', val_str).limit(1).execute()
        if res.data:
            p = res.data[0]
            return p.get('full_name') or p.get('email') or val_str
    except Exception:
        pass

    return val_str


# ==============================================================================
# 2. HÀM THỐNG KÊ DASHBOARD (DÙNG CHO MODULES/DASHBOARD/VIEW.PY)
# ==============================================================================

class SafeStatsDict(dict):
    """
    Dictionary thông minh cho Dashboard: nếu giao diện truy cập một key bất kỳ 
    bằng stats['ten_key'] mà chưa được khai báo, tự động trả về 0 thay vì báo lỗi KeyError.
    """
    def __missing__(self, key):
        return 0

def get_dashboard_stats():
    """
    Tổng hợp toàn bộ số liệu thống kê cho trang Dashboard tổng quan.
    Cung cấp đầy đủ các biến phổ biến để tương thích với modules/dashboard/view.py.
    """
    try:
        projects = get_all_projects()
        
        try:
            prof_res = supabase.table('profiles').select('id, full_name, email').execute()
            uuid_map = {str(p['id']): (p.get('full_name') or p.get('email') or "Chưa rõ") for p in (prof_res.data or [])}
        except Exception:
            uuid_map = {}

        for p in projects:
            p['staff_name'] = _resolve_display_staff_name(p.get('assigned_to'), uuid_map)

        total = len(projects)
        completed = sum(1 for p in projects if p.get('status') in ['Hoàn thành', 'Đã hoàn thành', 'Completed', 'Done'])
        in_progress = sum(1 for p in projects if p.get('status') in ['Đang thực hiện', 'Đang xử lý', 'In Progress'])
        new_proj = sum(1 for p in projects if p.get('status') in ['Mới tiếp nhận', 'Chưa xử lý', 'Mới', 'New'])
        paused = sum(1 for p in projects if p.get('status') in ['Tạm dừng', 'Pending', 'On Hold'])
        unassigned = sum(1 for p in projects if p.get('staff_name') == 'Chưa phân công')

        # Thống kê số lượng email & hàng đợi chờ xác nhận
        total_emails = 0
        unprocessed_emails = 0
        pending_confirmations = 0
        try:
            em_res = supabase.table('emails').select('id, processing_status').execute()
            emails_data = em_res.data or []
            total_emails = len(emails_data)
            unprocessed_emails = sum(1 for e in emails_data if e.get('processing_status') in [None, '', 'Chưa xử lý', 'pending'])
        except Exception:
            pass

        try:
            cq_res = supabase.table('confirmation_queue').select('id, decision').execute()
            cq_data = cq_res.data or []
            pending_confirmations = sum(1 for c in cq_data if not c.get('decision') or c.get('decision') in ['pending', 'Chờ xác nhận'])
        except Exception:
            pass

        # Gom nhóm theo trạng thái và nhân viên
        by_status = {}
        by_staff = {}
        for p in projects:
            st_val = p.get('status') or 'Đang thực hiện'
            by_status[st_val] = by_status.get(st_val, 0) + 1
            sf_val = p.get('staff_name') or 'Chưa phân công'
            by_staff[sf_val] = by_staff.get(sf_val, 0) + 1

        completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

        return SafeStatsDict({
            "total": total,
            "total_projects": total,
            "completed": completed,
            "completed_projects": completed,
            "done": completed,
            "in_progress": in_progress,
            "processing": in_progress,
            "active_projects": in_progress,
            "doing": in_progress,
            "new": new_proj,
            "new_projects": new_proj,
            "pending": paused + new_proj,
            "pending_projects": paused + new_proj,
            "paused": paused,
            "overdue": 0,
            "overdue_projects": 0,
            "unassigned": unassigned,
            "unassigned_projects": unassigned,
            "total_emails": total_emails,
            "unprocessed_emails": unprocessed_emails,
            "pending_emails": unprocessed_emails,
            "pending_confirmations": pending_confirmations,
            "completion_rate": completion_rate,
            "by_status": by_status,
            "status_counts": by_status,
            "by_staff": by_staff,
            "staff_counts": by_staff,
            "recent_projects": projects[:10],
            "projects": projects
        })
    except Exception as e:
        print(f"Lỗi get_dashboard_stats: {e}")
        return SafeStatsDict({
            "total": 0, "total_projects": 0, "completed": 0, "completed_projects": 0,
            "in_progress": 0, "active_projects": 0, "new_projects": 0, "pending": 0,
            "unassigned": 0, "total_emails": 0, "unprocessed_emails": 0,
            "pending_confirmations": 0, "completion_rate": 0.0,
            "by_status": {}, "by_staff": {}, "recent_projects": [], "projects": []
        })


# ==============================================================================
# 3. CÁC HÀM TRUY VẤN & CẬP NHẬT CÔNG TRÌNH (VIEW.PY, DETAIL.PY, CREATE.PY)
# ==============================================================================

def get_all_projects():
    """
    Lấy toàn bộ danh sách công trình từ bảng projects, sắp xếp mới nhất lên đầu.
    """
    try:
        res = supabase.table('projects').select('*').order('created_at', desc=True).execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Lỗi get_all_projects: {e}")
        return []

def get_project_by_code(project_code):
    """
    Lấy thông tin chi tiết của 1 công trình dựa theo mã project_code (dùng trong modules/projects/detail.py).
    """
    if not project_code:
        return None
    try:
        res = supabase.table('projects').select('*').eq('project_code', project_code).limit(1).execute()
        if res.data:
            project = res.data[0]
            project['staff_name'] = _resolve_display_staff_name(project.get('assigned_to'))
            return project
        return None
    except Exception as e:
        print(f"Lỗi get_project_by_code ({project_code}): {e}")
        return None

def get_project_by_id(project_id):
    """
    Lấy thông tin chi tiết của 1 công trình dựa theo ID (UUID).
    """
    if not project_id:
        return None
    try:
        res = supabase.table('projects').select('*').eq('id', project_id).limit(1).execute()
        if res.data:
            project = res.data[0]
            project['staff_name'] = _resolve_display_staff_name(project.get('assigned_to'))
            return project
        return None
    except Exception as e:
        print(f"Lỗi get_project_by_id ({project_id}): {e}")
        return None

def get_all_categories():
    """
    Lấy danh sách danh mục từ bảng categories (hỗ trợ form tạo/sửa công trình).
    """
    try:
        res = supabase.table('categories').select('*').execute()
        return res.data if res.data else []
    except Exception:
        return []

def get_all_staff():
    """
    Lấy danh sách nhân sự từ bảng profiles (hỗ trợ form chọn nhân viên).
    """
    try:
        res = supabase.table('profiles').select('*').execute()
        return res.data if res.data else []
    except Exception:
        return []

def generate_project_code():
    """
    Sinh mã công trình tự động theo định dạng PRJ-YYMM-XXXX.
    """
    now = datetime.now()
    prefix = f"PRJ-{now.strftime('%y%m')}-"
    try:
        res = supabase.table('projects').select('project_code').ilike('project_code', f"{prefix}%").execute()
        count = len(res.data) + 1 if res.data else 1
        return f"{prefix}{count:04d}"
    except Exception:
        return f"{prefix}{now.strftime('%H%M')}"

def update_project_status(
    project_code_or_id,
    new_status,
    note="",
    assigned_to=None,
    due_date=None,
    completed_date=None,
    **kwargs
):
    """
    Cập nhật trạng thái (và nhân sự / thông tin bổ sung) của công trình từ trang detail.py.
    """
    try:
        now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        val_str = str(project_code_or_id).strip()
        uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        is_uuid = bool(uuid_regex.match(val_str))

        if is_uuid:
            curr_res = supabase.table('projects').select('*').eq('id', val_str).limit(1).execute()
        else:
            curr_res = supabase.table('projects').select('*').eq('project_code', val_str).limit(1).execute()

        curr_proj = curr_res.data[0] if curr_res.data else {}
        project_id = curr_proj.get('id')
        old_status = curr_proj.get('status') or "Đang thực hiện"

        update_payload = {
            "status": new_status,
            "updated_at": now_iso
        }

        if assigned_to is not None:
            update_payload["assigned_to"] = resolve_staff_assignment(supabase, assigned_to)
        if due_date is not None:
            update_payload["due_date"] = format_to_iso_date(due_date)
        if completed_date is not None:
            update_payload["completed_date"] = format_to_iso_date(completed_date)
        elif new_status in ["Hoàn thành", "Đã hoàn thành"] and not curr_proj.get("completed_date"):
            update_payload["completed_date"] = datetime.now().strftime('%Y-%m-%d')

        allowed_extra_fields = [
            "project_name", "customer_name", "customer_phone", "project_address",
            "project_type", "brand", "category_id", "request_content", "detailed_requirements"
        ]
        for k, v in kwargs.items():
            if k in allowed_extra_fields and v is not None:
                update_payload[k] = v

        if is_uuid:
            res = supabase.table('projects').update(update_payload).eq('id', val_str).execute()
        else:
            res = supabase.table('projects').update(update_payload).eq('project_code', val_str).execute()

        if project_id:
            try:
                prof_res = supabase.table('profiles').select('id').limit(1).execute()
                actor_id = prof_res.data[0]['id'] if prof_res.data else None
                supabase.table('project_status_history').insert({
                    "project_id": project_id,
                    "changed_by": actor_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "note": note or f"Cập nhật trạng thái sang {new_status}",
                    "changed_at": now_iso
                }).execute()
            except Exception as his_err:
                print(f"Lỗi ghi project_status_history: {his_err}")

        return True if res.data else False
    except Exception as e:
        print(f"Lỗi update_project_status: {e}")
        return False

def update_project(project_code_or_id, update_data: dict = None, **kwargs):
    """
    Hàm cập nhật tổng quát thông tin công trình.
    """
    try:
        payload = dict(update_data) if isinstance(update_data, dict) else {}
        payload.update(kwargs)

        if 'assigned_to' in payload:
            payload['assigned_to'] = resolve_staff_assignment(supabase, payload['assigned_to'])
        if 'received_date' in payload:
            payload['received_date'] = format_to_iso_date(payload['received_date'])
        if 'due_date' in payload:
            payload['due_date'] = format_to_iso_date(payload['due_date'])
        if 'completed_date' in payload:
            payload['completed_date'] = format_to_iso_date(payload['completed_date'])

        payload['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        val_str = str(project_code_or_id).strip()
        uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        if uuid_regex.match(val_str):
            res = supabase.table('projects').update(payload).eq('id', val_str).execute()
        else:
            res = supabase.table('projects').update(payload).eq('project_code', val_str).execute()
        return True if res.data else False
    except Exception as e:
        print(f"Lỗi update_project: {e}")
        return False

def create_project(project_data: dict = None, **kwargs):
    """
    Hàm tạo mới công trình (hỗ trợ cả truyền dictionary hoặc truyền keyword arguments).
    """
    try:
        payload = dict(project_data) if isinstance(project_data, dict) else {}
        payload.update(kwargs)

        if not payload.get('organization_id'):
            org_res = supabase.table('organizations').select('id').limit(1).execute()
            if org_res.data:
                payload['organization_id'] = org_res.data[0]['id']

        if not payload.get('project_code'):
            payload['project_code'] = generate_project_code()

        if 'assigned_to' in payload:
            payload['assigned_to'] = resolve_staff_assignment(supabase, payload['assigned_to'])
        if 'received_date' in payload:
            payload['received_date'] = format_to_iso_date(payload['received_date'])
        if 'due_date' in payload:
            payload['due_date'] = format_to_iso_date(payload['due_date'])

        res = supabase.table('projects').insert(payload).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Lỗi create_project: {e}")
        return None

def delete_project(project_code_or_id):
    """
    Xóa công trình theo ID hoặc mã công trình.
    """
    try:
        val_str = str(project_code_or_id).strip()
        uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        if uuid_regex.match(val_str):
            supabase.table('projects').delete().eq('id', val_str).execute()
        else:
            supabase.table('projects').delete().eq('project_code', val_str).execute()
        return True
    except Exception as e:
        print(f"Lỗi delete_project: {e}")
        return False


# ==============================================================================
# 4. HÀM KHỞI TẠO CÔNG TRÌNH TRỰC TIẾP TỪ EMAIL
# ==============================================================================

def create_project_directly_from_email(
    email_id, 
    customer_name, 
    project_name, 
    project_code, 
    category_id, 
    assigned_to_uuid, 
    received_date, 
    due_date, 
    request_content, 
    status="Mới tiếp nhận"
):
    """
    Khởi tạo công trình từ email và đồng bộ trạng thái bảng project_emails, emails.
    """
    try:
        org_res = supabase.table('organizations').select('id').limit(1).execute()
        org_id = org_res.data[0]['id'] if org_res.data else None

        final_assigned_to = resolve_staff_assignment(supabase, assigned_to_uuid)
        final_code = project_code if project_code else generate_project_code()

        project_payload = {
            "organization_id": org_id,
            "project_code": final_code,
            "project_name": project_name,
            "customer_name": customer_name,
            "category_id": category_id if category_id else None,
            "assigned_to": final_assigned_to,
            "received_date": format_to_iso_date(received_date),
            "due_date": format_to_iso_date(due_date),
            "status": status,
            "request_content": request_content
        }
        
        try:
            proj_res = supabase.table('projects').insert(project_payload).execute()
        except Exception as insert_err:
            if "22P02" in str(insert_err) or "23503" in str(insert_err):
                project_payload["assigned_to"] = None
                proj_res = supabase.table('projects').insert(project_payload).execute()
            else:
                raise insert_err

        if not proj_res.data:
            return {"success": False, "message": "❌ Lỗi: Không thể tạo bản ghi dự án trong CSDL."}
        
        new_project_id = proj_res.data[0]['id']

        if email_id:
            try:
                supabase.table('project_emails').upsert({
                    "project_id": new_project_id,
                    "email_id": email_id,
                    "relation_type": "source",
                    "is_confirmed": True
                }, on_conflict="project_id,email_id").execute()
            except Exception as e:
                print(f"Lỗi ghi project_emails: {e}")

            try:
                supabase.table('emails').update({
                    "processing_status": "Đã giao"
                }).eq("id", email_id).execute()
            except Exception as e:
                print(f"Lỗi update status email: {e}")

        return {
            "success": True, 
            "message": "🎉 Khởi tạo công trình và đồng bộ trạng thái email thành công!",
            "project_id": new_project_id
        }

    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi hệ thống: {str(e)}"}
