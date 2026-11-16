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

def _resolve_display_staff_name(assigned_val):
    """
    Hàm phụ trợ dịch ngược từ UUID hoặc mã giả lập sang tên hiển thị nhân viên cho trang detail.py.
    """
    if not assigned_val:
        return "Chưa phân công"
    val_str = str(assigned_val).strip()
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

    try:
        res = supabase.table('profiles').select('id, full_name, email').eq('id', val_str).limit(1).execute()
        if res.data:
            p = res.data[0]
            return p.get('full_name') or p.get('email') or val_str
    except Exception:
        pass

    return val_str


# ==============================================================================
# 2. CÁC HÀM TRUY VẤN & CẬP NHẬT CÔNG TRÌNH (DÙNG CHO VIEW.PY, DETAIL.PY, CREATE.PY)
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
            # Bổ sung thêm trường staff_name đã ánh xạ sẵn để detail.py hiển thị thuận tiện
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
    Hỗ trợ truyền vào project_code (VD: 'PRJ-2611-0014') hoặc UUID id của project,
    đồng thời ghi vết vào bảng project_status_history.
    """
    try:
        now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Xác định tìm theo id (UUID) hay project_code
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

        # Cho phép cập nhật linh hoạt các trường khác nếu detail.py truyền qua kwargs
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

        # Tự động ghi nhận lịch sử vào bảng project_status_history
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

def update_project(project_code_or_id, update_data: dict):
    """
    Hàm cập nhật tổng quát thông tin công trình (dự phòng nếu detail.py gọi update_project).
    """
    try:
        if 'assigned_to' in update_data:
            update_data['assigned_to'] = resolve_staff_assignment(supabase, update_data['assigned_to'])
        if 'received_date' in update_data:
            update_data['received_date'] = format_to_iso_date(update_data['received_date'])
        if 'due_date' in update_data:
            update_data['due_date'] = format_to_iso_date(update_data['due_date'])
        if 'completed_date' in update_data:
            update_data['completed_date'] = format_to_iso_date(update_data['completed_date'])

        update_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        val_str = str(project_code_or_id).strip()
        uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        if uuid_regex.match(val_str):
            res = supabase.table('projects').update(update_data).eq('id', val_str).execute()
        else:
            res = supabase.table('projects').update(update_data).eq('project_code', val_str).execute()
        return True if res.data else False
    except Exception as e:
        print(f"Lỗi update_project: {e}")
        return False

def create_project(project_data: dict):
    """
    Hàm tạo mới công trình (dự phòng cho trang modules/projects/create.py).
    """
    try:
        if not project_data.get('organization_id'):
            org_res = supabase.table('organizations').select('id').limit(1).execute()
            if org_res.data:
                project_data['organization_id'] = org_res.data[0]['id']

        if 'assigned_to' in project_data:
            project_data['assigned_to'] = resolve_staff_assignment(supabase, project_data['assigned_to'])
        if 'received_date' in project_data:
            project_data['received_date'] = format_to_iso_date(project_data['received_date'])
        if 'due_date' in project_data:
            project_data['due_date'] = format_to_iso_date(project_data['due_date'])

        res = supabase.table('projects').insert(project_data).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Lỗi create_project: {e}")
        return None


# ==============================================================================
# 3. HÀM KHỞI TẠO CÔNG TRÌNH TRỰC TIẾP TỪ EMAIL (DÙNG CHO EMAILS & CONFIRMATION)
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

        project_payload = {
            "organization_id": org_id,
            "project_code": project_code if project_code else None,
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
