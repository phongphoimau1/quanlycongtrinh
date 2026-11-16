import streamlit as st
import pandas as pd
from services.admin_service import get_system_audit_logs

st.title("📜 Nhật ký Hoạt động Hệ thống (Audit Logs)")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    kw_log = st.text_input("🔍 Tìm theo hành động, đối tượng, người thực hiện...", placeholder="Nhập từ khóa...")
with col2:
    entity_filter = st.selectbox("Lọc theo Bảng dữ liệu", ["Tất cả", "projects", "profiles", "categories", "emails"])
with col3:
    st.write("")
    st.write("")
    if st.button("🔄 Tải lại Nhật ký", width="stretch"):
        st.rerun()

logs_data = get_system_audit_logs(limit=300)

if logs_data:
    df_l = pd.DataFrame(logs_data).fillna("")
    df_l["time_str"] = df_l["created_at"].astype(str).str[:19].str.replace("T", " ")
    df_l["details_str"] = df_l["details"].apply(lambda d: str(d) if d else "")

    if entity_filter != "Tất cả":
        df_l = df_l[df_l["entity_type"] == entity_filter]
    if kw_log:
        k = kw_log.lower()
        df_l = df_l[
            df_l["action"].astype(str).str.lower().str.contains(k, na=False)
            | df_l["actor_name"].astype(str).str.lower().str.contains(k, na=False)
            | df_l["details_str"].astype(str).str.lower().str.contains(k, na=False)
        ]

    st.markdown(f"### 📋 Lịch sử Truy vết ({len(df_l)} bản ghi gần nhất)")

    disp_l = df_l[["time_str", "actor_name", "action", "entity_type", "entity_id", "details_str"]].rename(
        columns={
            "time_str": "Thời gian",
            "actor_name": "Người thực hiện",
            "action": "Hành động",
            "entity_type": "Bảng tác động",
            "entity_id": "ID Bản ghi",
            "details_str": "Chi tiết thay đổi (JSON)",
        }
    )

    ev_l = st.dataframe(disp_l, width="stretch", hide_index=True, selection_mode="single-row", on_select="rerun")
    if ev_l.selection.rows:
        sel_log = df_l.iloc[ev_l.selection.rows[0]]
        st.subheader("🔍 Chi tiết Payload JSON của Nhật ký")
        st.json(sel_log.get("details") or {})
else:
    st.info("📭 Chưa có bản ghi nhật ký hệ thống nào trong bảng `audit_logs`.")
