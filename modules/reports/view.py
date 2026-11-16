import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from services.project_service import get_all_projects

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📊 Hệ thống Báo cáo & Đánh giá Hiệu suất")

try:
    projects_data = get_all_projects()
    prof_res = supabase.table('profiles').select('id, full_name, email').execute()
    uuid_to_name = {
        str(p['id']): (p.get('full_name') or p.get('email') or "Chưa rõ")
        for p in (prof_res.data or [])
    }
except Exception as e:
    st.error(f"❌ Lỗi tải dữ liệu báo cáo: {e}")
    projects_data = []
    uuid_to_name = {}

def map_staff(val):
    if not val or pd.isna(val):
        return "Chưa phân công"
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["none", "nan", "null", "chưa phân nhân sự"]:
        return "Chưa phân công"
    return uuid_to_name.get(val_str, val_str)

if projects_data:
    df = pd.DataFrame(projects_data)
    df['staff_name'] = df['assigned_to'].apply(map_staff) if 'assigned_to' in df.columns else "Chưa phân công"
    df['status'] = df.get('status', 'Mới tiếp nhận').fillna("Mới tiếp nhận").replace("", "Mới tiếp nhận")

    # Chuẩn hóa cột thời gian để lọc theo Tháng và Năm
    date_col = 'received_date' if 'received_date' in df.columns else 'created_at'
    df['parsed_date'] = pd.to_datetime(df[date_col], errors='coerce')
    # Nếu ngày nhận bị trống, fallback sang created_at
    if 'created_at' in df.columns:
        df['parsed_date'] = df['parsed_date'].fillna(pd.to_datetime(df['created_at'], errors='coerce'))

    df['year'] = df['parsed_date'].dt.year.fillna(datetime.now().year).astype(int)
    df['month'] = df['parsed_date'].dt.month.fillna(datetime.now().month).astype(int)

    tab_month, tab_year, tab_staff = st.tabs([
        "📅 Báo cáo Tháng",
        "📆 Báo cáo Năm",
        "🏆 Hiệu suất Nhân viên"
    ])

    # --- TAB 1: BÁO CÁO THÁNG ---
    with tab_month:
        c1, c2 = st.columns(2)
        with c1:
            available_years = sorted(df['year'].unique().tolist(), reverse=True)
            sel_year = st.selectbox("Chọn Năm", available_years, key="m_year")
        with c2:
            sel_month = st.selectbox("Chọn Tháng", list(range(1, 13)), index=datetime.now().month - 1, key="m_month")

        df_m = df[(df['year'] == sel_year) & (df['month'] == sel_month)]

        total_m = len(df_m)
        done_m = len(df_m[df_m['status'].isin(['Hoàn thành', 'Đã hoàn thành'])])
        doing_m = len(df_m[df_m['status'].isin(['Đang thực hiện', 'Mới tiếp nhận'])])
        rate_m = round((done_m / total_m * 100), 1) if total_m > 0 else 0.0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric(f"Tổng CT Tháng {sel_month}/{sel_year}", total_m)
        k2.metric("Đã hoàn thành", done_m)
        k3.metric("Đang thực hiện", doing_m)
        k4.metric("Tỷ lệ hoàn thành", f"{rate_m}%")

        if not df_m.empty:
            st.markdown("#### Phân bổ theo Trạng thái & Nhân sự trong tháng")
            ch1, ch2 = st.columns(2)
            with ch1:
                st.bar_chart(df_m['status'].value_counts())
            with ch2:
                st.bar_chart(df_m['staff_name'].value_counts())

            st.dataframe(
                df_m[["project_code", "project_name", "customer_name", "staff_name", "status", "received_date"]].rename(columns={
                    "project_code": "Mã CT",
                    "project_name": "Tên công trình",
                    "customer_name": "Khách hàng",
                    "staff_name": "Nhân viên phụ trách",
                    "status": "Trạng thái",
                    "received_date": "Ngày nhận"
                }).fillna("Chưa cập nhật"),
                width='stretch',
                hide_index=True
            )
        else:
            st.info(f"Không có công trình nào ghi nhận trong Tháng {sel_month}/{sel_year}.")

    # --- TAB 2: BÁO CÁO NĂM ---
    with tab_year:
        sel_y = st.selectbox("Chọn Năm Báo cáo", available_years, key="y_year")
        df_y = df[df['year'] == sel_y]

        total_y = len(df_y)
        done_y = len(df_y[df_y['status'].isin(['Hoàn thành', 'Đã hoàn thành'])])
        rate_y = round((done_y / total_y * 100), 1) if total_y > 0 else 0.0

        yk1, yk2, yk3 = st.columns(3)
        yk1.metric(f"Tổng Công trình Năm {sel_y}", total_y)
        yk2.metric("Tổng Hoàn thành", done_y)
        yk3.metric("Hiệu suất Năm", f"{rate_y}%")

        if not df_y.empty:
            st.markdown(f"#### Biểu đồ Sản lượng Công trình qua 12 tháng ({sel_y})")
            monthly_counts = df_y.groupby('month').size().reindex(range(1, 13), fill_value=0)
            monthly_df = pd.DataFrame({"Tháng": [f"T{m}" for m in range(1, 13)], "Số lượng CT": monthly_counts.values}).set_index("Tháng")
            st.bar_chart(monthly_df)

    # --- TAB 3: HIỆU SUẤT NHÂN VIÊN ---
    with tab_staff:
        st.markdown("### 🏆 Bảng Xếp hạng & Đánh giá Hiệu suất Nhân sự")
        staff_summary = []
        for s_name, group in df.groupby('staff_name'):
            tot = len(group)
            done = len(group[group['status'].isin(['Hoàn thành', 'Đã hoàn thành'])])
            doing = len(group[group['status'].isin(['Đang thực hiện', 'Mới tiếp nhận'])])
            paused = tot - done - doing
            comp_rate = round((done / tot * 100), 1) if tot > 0 else 0.0

            staff_summary.append({
                "Nhân sự": s_name,
                "Tổng CT đảm nhận": tot,
                "Đã hoàn thành": done,
                "Đang thực hiện": doing,
                "Tạm dừng / Khác": max(0, paused),
                "Tỷ lệ hoàn thành (%)": comp_rate
            })

        df_perf = pd.DataFrame(staff_summary).sort_values(by="Tổng CT đảm nhận", ascending=False)
        st.dataframe(df_perf, width='stretch', hide_index=True)

        st.markdown("#### So sánh Khối lượng Công việc giữa các Nhân sự")
        chart_perf = df_perf.set_index("Nhân sự")[["Đã hoàn thành", "Đang thực hiện"]]
        st.bar_chart(chart_perf)
else:
    st.info("📭 Chưa có dữ liệu công trình để tổng hợp báo cáo.")
