import re
from datetime import datetime
import streamlit as st
from supabase import create_client
from services.project_service import create_project_directly_from_email

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def _safe_query(table_name, select_cols="*", order_col=None):
    """Truy vấn an toàn, cô lập lỗi phân quyền 42501 nếu có."""
    try:
        q = supabase.table(table_name).select(select_cols)
        if order_col:
            q = q.order(order_col, desc=True)
        res = q.execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Cảnh báo truy vấn bảng {table_name}: {e}")
        return []

def _smart_extract_from_subject(subject, sender_email):
    """
    Hàm AI/Heuristic trích xuất thông tin khách hàng, mã và tên công trình từ tiêu đề email.
    """
    subj = str(subject or "").strip()
    clean_subj = re.sub(r'^(Fwd:|Re:|FW:|RE:)\s*', '', subj, flags=re.IGNORECASE).strip()

    # Tách tên khách hàng nếu tiêu đề có dạng "v252-ANH HUY-HN" hoặc "Nhà anh Vinh"
    customer = sender_email or "Khách hàng"
    parts = [p.strip() for p in re.split(r'[-–|]', clean_subj) if p.strip()]
    if len(parts) >= 2:
        customer = parts[1]
    else:
        match_cust = re.search(r'(?:anh|chị|bác|cô|chú|đại lý|gđ)\s+([a-zA-ZÀ-ỹ0-9\s]{2,20})', clean_subj, re.IGNORECASE)
        if match_cust:
            customer = match_cust.group(0).strip()

    return {
        "customer_name": customer,
        "project_name": clean_subj or "Công trình mới từ Email",
        "project_code": "",
        "request_content": f"Yêu cầu từ email: {subj} (Người gửi: {sender_email})"
    }

def sync_unprocessed_emails_to_queue():
    """
    Quét toàn bộ email đang 'Chưa xử lý' nhưng chưa nằm trong confirmation_queue/ai_extractions,
    tự động bóc tách dữ liệu và đẩy vào hàng đợi để người dùng duyệt.
    """
    try:
        emails = _safe_query('emails', '*', order_col='received_at')
        queue_data = _safe_query('confirmation_queue', 'id, email_id')
        ai_data = _safe_query('ai_extractions', 'id, email_id')
        proj_emails = _safe_query('project_emails', 'email_id')

        queued_email_ids = {item.get('email_id') for item in queue_data if item.get('email_id')}
        ai_email_ids = {item.get('email_id') for item in ai_data if item.get('email_id')}
        linked_email_ids = {item.get('email_id') for item in proj_emails if item.get('email_id')}

        # Lấy danh sách công trình hiện có để gợi ý ghép nối nếu trùng tên
        projects = _safe_query('projects', 'id, project_code, project_name, customer_name')

        synced_count = 0
        now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for em in emails:
            eid = em.get('id')
            st_val = str(em.get('processing_status') or '').strip()
            if not eid or eid in linked_email_ids:
                continue
            if st_val in ['Đã giao', 'Hoàn thành', 'Từ chối', 'processed', 'rejected']:
                continue

            extracted = _smart_extract_from_subject(em.get('subject'), em.get('sender_email'))

            # Tìm công trình gợi ý nếu tiêu đề có nét tương đồng
            candidate_pid = None
            subj_lower = str(em.get('subject') or '').lower()
            for p in projects:
                p_name = str(p.get('project_name') or '').lower()
                c_name = str(p.get('customer_name') or '').lower()
                if (p_name and len(p_name) > 5 and p_name in subj_lower) or (c_name and len(c_name) > 3 and c_name in subj_lower):
                    candidate_pid = p.get('id')
                    break

            # 1. Đẩy vào bảng ai_extractions nếu chưa có
            if eid not in ai_email_ids:
                try:
                    supabase.table('ai_extractions').insert({
                        "email_id": eid,
                        "suggested_project_id": candidate_pid,
                        "extracted_data": extracted,
                        "confidence": 0.85 if candidate_pid else 0.75,
                        "decision": "pending",
                        "created_at": now_iso
                    }).execute()
                    synced_count += 1
                except Exception as e:
                    print(f"Lỗi insert ai_extractions: {e}")

            # 2. Đẩy vào bảng confirmation_queue nếu chưa có
            if eid not in queued_email_ids:
                try:
                    supabase.table('confirmation_queue').insert({
                        "email_id": eid,
                        "candidate_project_id": candidate_pid,
                        "reason": "Trùng thông tin khách hàng/công trình có sẵn" if candidate_pid else "Email mới chờ xác nhận khởi tạo CT",
                        "decision": "pending"
                    }).execute()
                    synced_count += 1
                except Exception as e:
                    print(f"Lỗi insert confirmation_queue: {e}")

        return {"success": True, "synced": synced_count, "message": f"✅ Đã đồng bộ & bóc tách {synced_count} mục mới vào hàng đợi!"}
    except Exception as e:
        return {"success": False, "synced": 0, "message": f"❌ Lỗi đồng bộ hàng đợi: {e}"}

def get_confirmation_dashboard_data():
    """
    Trả về trọn bộ 3 danh sách:
    1. pending_matching: Chờ ghép nối vào CT có sẵn (confirmation_queue)
    2. pending_ai: AI bóc tách chờ duyệt tạo mới (ai_extractions + email chưa xử lý)
    3. processed_items: Các mục đã xử lý (để hiển thị rõ '2 mục' trên giao diện)
    """
    emails = _safe_query('emails', '*')
    emails_map = {e['id']: e for e in emails if 'id' in e}

    projects = _safe_query('projects', 'id, project_code, project_name, customer_name')
    proj_map = {p['id']: p for p in projects if 'id' in p}

    queue_data = _safe_query('confirmation_queue', '*')
    ai_data = _safe_query('ai_extractions', '*')

    ai_by_email = {a.get('email_id'): a for a in ai_data if a.get('email_id')}
    queue_by_email = {q.get('email_id'): q for q in queue_data if q.get('email_id')}

    pending_Decisions = {None, "", "pending", "chờ xác nhận", "chưa xử lý", "waiting"}

    pending_matching = []
    pending_ai = []
    processed_items = []

    # 1. Phân loại từ bảng confirmation_queue
    for q in queue_data:
        eid = q.get('email_id')
        em = emails_map.get(eid, {})
        ai_info = ai_by_email.get(eid, {})
        extracted = ai_info.get('extracted_data') if isinstance(ai_info.get('extracted_data'), dict) else _smart_extract_from_subject(em.get('subject'), em.get('sender_email'))
        
        cand_pid = q.get('candidate_project_id') or ai_info.get('suggested_project_id')
        cand_proj = proj_map.get(cand_pid, {})

        dec = str(q.get('decision') or '').strip().lower()
        item_obj = {
            "source_table": "confirmation_queue",
            "record_id": q.get('id'),
            "queue_id": q.get('id'),
            "ai_id": ai_info.get('id'),
            "email_id": eid,
            "sender_email": em.get('sender_email', 'Chưa rõ'),
            "subject": em.get('subject', 'Không có tiêu đề'),
            "received_at": str(em.get('received_at') or '')[:19].replace('T', ' '),
            "candidate_project_id": cand_pid,
            "candidate_project_display": f"{cand_proj.get('project_code', '')} - {cand_proj.get('project_name', '')}".strip(" -") or "Chưa có CT gợi ý",
            "reason": q.get('reason') or "Chờ xác nhận điều phối",
            "confidence": ai_info.get('confidence') or 0.8,
            "decision": q.get('decision') or "pending",
            "reviewed_at": str(q.get('reviewed_at') or '')[:19].replace('T', ' '),
            "extracted_customer": extracted.get('customer_name') or em.get('sender_email', ''),
            "extracted_project": extracted.get('project_name') or em.get('subject', ''),
            "extracted_code": extracted.get('project_code', ''),
            "extracted_requirements": extracted.get('request_content') or em.get('subject', ''),
            "raw_extracted": extracted
        }

        if dec in pending_Decisions:
            pending_matching.append(item_obj)
        else:
            processed_items.append(item_obj)

    # 2. Phân loại từ bảng ai_extractions
    for a in ai_data:
        eid = a.get('email_id')
        em = emails_map.get(eid, {})
        q_info = queue_by_email.get(eid, {})
        extracted = a.get('extracted_data') if isinstance(a.get('extracted_data'), dict) else _smart_extract_from_subject(em.get('subject'), em.get('sender_email'))
        
        cand_pid = a.get('suggested_project_id') or q_info.get('candidate_project_id')
        cand_proj = proj_map.get(cand_pid, {})

        dec = str(a.get('decision') or '').strip().lower()
        item_obj = {
            "source_table": "ai_extractions",
            "record_id": a.get('id'),
            "queue_id": q_info.get('id'),
            "ai_id": a.get('id'),
            "email_id": eid,
            "sender_email": em.get('sender_email', 'Chưa rõ'),
            "subject": em.get('subject', 'Không có tiêu đề'),
            "received_at": str(em.get('received_at') or a.get('created_at') or '')[:19].replace('T', ' '),
            "candidate_project_id": cand_pid,
            "candidate_project_display": f"{cand_proj.get('project_code', '')} - {cand_proj.get('project_name', '')}".strip(" -") or "Tạo công trình mới",
            "reason": q_info.get('reason') or "AI bóc tách chờ duyệt khởi tạo",
            "confidence": a.get('confidence') or 0.85,
            "decision": a.get('decision') or "pending",
            "reviewed_at": str(q_info.get('reviewed_at') or a.get('created_at') or '')[:19].replace('T', ' '),
            "extracted_customer": extracted.get('customer_name') or em.get('sender_email', ''),
            "extracted_project": extracted.get('project_name') or em.get('subject', ''),
            "extracted_code": extracted.get('project_code', ''),
            "extracted_requirements": extracted.get('request_content') or em.get('subject', ''),
            "raw_extracted": extracted
        }

        if dec in pending_Decisions:
            pending_ai.append(item_obj)
        elif eid not in {p['email_id'] for p in processed_items}:
            processed_items.append(item_obj)

    # 3. Fallback thông minh: Nếu cả 2 bảng đang trống mục pending nhưng bảng emails có email 'Chưa xử lý',
    # tự động hiển thị các email đó vào tab Duyệt bóc tách AI để người dùng xử lý ngay!
    existing_pending_eids = {x['email_id'] for x in pending_matching} | {x['email_id'] for x in pending_ai}
    for em in emails:
        eid = em.get('id')
        st_val = str(em.get('processing_status') or '').strip()
        if eid not in existing_pending_eids and st_val in ['', 'Chưa xử lý', 'Đang xử lý', 'pending']:
            extracted = _smart_extract_from_subject(em.get('subject'), em.get('sender_email'))
            pending_ai.append({
                "source_table": "emails",
                "record_id": eid,
                "queue_id": None,
                "ai_id": None,
                "email_id": eid,
                "sender_email": em.get('sender_email', 'Chưa rõ'),
                "subject": em.get('subject', 'Không có tiêu đề'),
                "received_at": str(em.get('received_at') or '')[:19].replace('T', ' '),
                "candidate_project_id": None,
                "candidate_project_display": "Đề xuất tạo CT mới",
                "reason": "Email mới chưa xử lý",
                "confidence": 0.80,
                "decision": "pending",
                "reviewed_at": "",
                "extracted_customer": extracted['customer_name'],
                "extracted_project": extracted['project_name'],
                "extracted_code": "",
                "extracted_requirements": extracted['request_content'],
                "raw_extracted": extracted
            })

    return {
        "pending_matching": pending_matching,
        "pending_ai": pending_ai,
        "processed_items": processed_items
    }

def get_pending_confirmations():
    """Giữ hàm tương thích ngược."""
    data = get_confirmation_dashboard_data()
    return data["pending_matching"] + data["pending_ai"]

def reopen_processed_item(queue_id=None, ai_id=None, email_id=None):
    """Đưa một mục đã xử lý quay trở lại trạng thái chờ xác nhận (pending)."""
    try:
        if queue_id:
            supabase.table('confirmation_queue').update({"decision": "pending", "reviewed_at": None}).eq("id", queue_id).execute()
        if ai_id:
            supabase.table('ai_extractions').update({"decision": "pending"}).eq("id", ai_id).execute()
        if email_id:
            supabase.table('confirmation_queue').update({"decision": "pending"}).eq("email_id", email_id).execute()
            supabase.table('ai_extractions').update({"decision": "pending"}).eq("email_id", email_id).execute()
            supabase.table('emails').update({"processing_status": "Chưa xử lý"}).eq("id", email_id).execute()
        return {"success": True, "message": "🔄 Đã hoàn tác bản ghi về trạng thái Chờ xác nhận!"}
    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi hoàn tác: {e}"}

def approve_and_create_project(
    queue_id,
    email_id,
    customer_name,
    project_name,
    project_code,
    category_id,
    assigned_to,
    received_date,
    due_date,
    request_content,
    status
):
    try:
        res = create_project_directly_from_email(
            email_id=email_id,
            customer_name=customer_name,
            project_name=project_name,
            project_code=project_code,
            category_id=category_id,
            assigned_to_uuid=assigned_to,
            received_date=received_date,
            due_date=due_date,
            request_content=request_content,
            status=status
        )
        if not res.get("success"):
            return res

        now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if queue_id:
            try:
                supabase.table('confirmation_queue').update({"decision": "approved", "reviewed_at": now_iso}).eq("id", queue_id).execute()
            except Exception:
                pass
        if email_id:
            try:
                supabase.table('confirmation_queue').update({"decision": "approved", "reviewed_at": now_iso}).eq("email_id", email_id).execute()
            except Exception:
                pass
            try:
                supabase.table('ai_extractions').update({"decision": "approved", "suggested_project_id": res.get("project
