import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from services.project_service import get_all_projects

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📅 Báo cáo Công trình Theo Tháng")

try:
    projects_data = get_all_projects()
    prof_res = supabase.table("profiles").select("id, full_name, email").execute()
    uuid_to_name = {
        str(p["id"]): (p.get("full_name") or p.get("email") or "Chưa rõ")
        for p in (prof_res.data or [])
    }
except Exception as e:
    st.error(f"❌ Lỗi tải dữ liệu báo cáo tháng: {e}")
    projects_data = []
    uuid_to_name = {}


def map_staff_name(val):
    if not val or pd.isna(val):
        return "Chưa phân công"
    val_str = str(val).strip()
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
    return uuid_to_name.get(val_str, val_str)


if projects_data:
    df = pd.DataFrame(projects_data)
    df["staff_name"] = (
        df["assigned_to"].apply(map_staff_name)
        if "assigned_to" in df.columns
        else "Chưa phân công"
    )
    df["status"] = (
        df.get("status", "Mới tiếp nhận")
        .fillna("Mới tiếp nhận")
        .replace("", "Mới tiếp nhận")
    )

    rec_series = (
        pd.to_datetime(df["received_date"], errors="coerce", utc=True)
        if "received_date" in df.columns
        else pd.Series([pd.NaT] * len(df), dtype="datetime64[ns, UTC]")
    )
    cre_series = (
        pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        if "created_at" in df.columns
        else pd.Series([pd.NaT] * len(df), dtype="datetime64[ns, UTC]")
    )
    df["parsed_date"] = pd.to_datetime(
        rec_series.fillna(cre_series), errors="coerce", utc=True
    )

    current_year = datetime.now().year
    current_month = datetime.now().month

    df["year"] = df["parsed_date"].dt.year.fillna(current_year).astype(int)
    df["month"] = df["parsed_date"].dt.month.fillna(current_month).astype(int)

    # Bộ lọc chọn Năm, Tháng và Nhân sự
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        available_years = sorted(df["year"].unique().tolist(), reverse=True)
        if not available_years:
            available_years = [current_year]
        sel_year = st.selectbox("Chọn Năm", available_years)
    with c2:
        sel_month = st.selectbox(
            "Chọn Tháng", list(range(1, 13)), index=current_month - 1
        )
    with c3:
        staff_list = ["Tất cả"] + sorted(df["staff_name"].unique().tolist())
        sel_staff = st.selectbox("Lọc theo Nhân viên phụ trách", staff_list)

    df_m = df[(df["year"] == sel_year) & (df["month"] == sel_month)].copy()
    if sel_staff != "Tất cả":
        df_m = df_m[df_m["staff_name"] == sel_staff]

    # Chỉ số KPI Tháng
    total_m = len(df_m)
    done_m = len(df_m[df_m["status"].isin(["Hoàn thành", "Đã hoàn thành"])])
    doing_m = len(df_m[df_m["status"].isin(["Đang thực hiện", "Mới tiếp nhận"])])
    unassigned_m = len(df_m[df_m["staff_name"] == "Chưa phân công"])
    rate_m = round((done_m / total_m * 100), 1) if total_m > 0 else 0.0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(f"🏗️ Tổng CT T{sel_month}/{sel_year}", total_m)
    k2.metric("✅ Đã hoàn thành", done_m)
    k3.metric("⚡ Đang thực hiện", doing_m)
    k4.metric("🚨 Chưa phân công", unassigned_m)
    k5.metric("🎯 Tỷ lệ hoàn thành", f"{rate_m}%")

    st.divider()

    if not df_m.empty:
        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown("#### 📊 Thống kê theo Trạng thái")
            st.bar_chart(df_m["status"].value_counts())
        with ch2:
            st.markdown("#### 👤 Khối lượng theo Nhân sự trong tháng")
            st.bar_chart(df_m["staff_name"].value_counts())

        st.markdown(f"### 📋 Danh sách Chi tiết Công trình Tháng {sel_month}/{sel_year}")

        for col_req in [
            "project_code",
            "project_name",
            "customer_name",
            "staff_name",
            "status",
            "received_date",
            "completed_date",
        ]:
            if col_req not in df_m.columns:
                df_m[col_req] = ""

        disp_m = (
            df_m[
                [
                    "project_code",
                    "project_name",
                    "customer_name",
                    "staff_name",
                    "status",
                    "received_date",
                    "completed_date",
                ]
            ]
            .rename(
                columns={
                    "project_code": "Mã CT",
                    "project_name": "Tên công trình",
                    "customer_name": "Khách hàng",
                    "staff_name": "Nhân viên phụ trách",
                    "status": "Trạng thái",
                    "received_date": "Ngày nhận",
                    "completed_date": "Ngày hoàn thành",
                }
            )
            .fillna("Chưa cập nhật")
            .replace("", "Chưa cập nhật")
        )

        st.dataframe(disp_m, width="stretch", hide_index=True)

        csv_bytes = disp_m.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label=f"📥 Xuất Báo cáo Tháng {sel_month}/{sel_year} (CSV/Excel)",
            data=csv_bytes,
            file_name=f"bao_cao_thang_{sel_month}_{sel_year}.csv",
            mime="text/csv",
        )
    else:
        st.info(f"📭 Không có công trình nào ghi nhận trong Tháng {sel_month}/{sel_year}.")
else:
    st.info("📭 Chưa có dữ liệu công trình trên hệ thống.")
