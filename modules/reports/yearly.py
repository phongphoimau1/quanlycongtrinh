import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from services.project_service import get_all_projects

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📆 Báo cáo Tổng hợp Năm")

try:
    projects_data = get_all_projects()
    prof_res = supabase.table("profiles").select("id, full_name, email").execute()
    uuid_to_name = {
        str(p["id"]): (p.get("full_name") or p.get("email") or "Chưa rõ")
        for p in (prof_res.data or [])
    }
except Exception as e:
    st.error(f"❌ Lỗi tải dữ liệu báo cáo năm: {e}")
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
    df["year"] = df["parsed_date"].dt.year.fillna(current_year).astype(int)
    df["month"] = df["parsed_date"].dt.month.fillna(1).astype(int)

    available_years = sorted(df["year"].unique().tolist(), reverse=True)
    if not available_years:
        available_years = [current_year]

    col_y1, col_y2 = st.columns([1, 3])
    with col_y1:
        sel_year = st.selectbox("Chọn Năm Báo cáo", available_years)

    df_y = df[df["year"] == sel_year].copy()

    total_y = len(df_y)
    done_y = len(df_y[df_y["status"].isin(["Hoàn thành", "Đã hoàn thành"])])
    doing_y = len(df_y[df_y["status"].isin(["Đang thực hiện", "Mới tiếp nhận"])])
    rate_y = round((done_y / total_y * 100), 1) if total_y > 0 else 0.0

    yk1, yk2, yk3, yk4 = st.columns(4)
    yk1.metric(f"🏗️ Tổng Công trình Năm {sel_year}", total_y)
    yk2.metric("✅ Đã hoàn thành", done_y)
    yk3.metric("⚡ Đang thực hiện", doing_y)
    yk4.metric("🎯 Hiệu suất Năm", f"{rate_y}%")

    st.divider()

    if not df_y.empty:
        st.markdown(f"### 📈 Biểu đồ Sản lượng Công trình qua 12 Tháng ({sel_year})")

        monthly_summary = []
        for m in range(1, 13):
            sub = df_y[df_y["month"] == m]
            tot_m = len(sub)
            dn_m = len(sub[sub["status"].isin(["Hoàn thành", "Đã hoàn thành"])])
            dg_m = len(sub[sub["status"].isin(["Đang thực hiện", "Mới tiếp nhận"])])
            monthly_summary.append(
                {
                    "Tháng": f"Tháng {m:02d}",
                    "Tổng công trình": tot_m,
                    "Đã hoàn thành": dn_m,
                    "Đang thực hiện": dg_m,
                    "Tỷ lệ hoàn thành (%)": round((dn_m / tot_m * 100), 1) if tot_m > 0 else 0.0,
                }
            )

        df_summary = pd.DataFrame(monthly_summary)
        chart_df = df_summary.set_index("Tháng")[["Đã hoàn thành", "Đang thực hiện"]]
        st.bar_chart(chart_df)

        col_t1, col_t2 = st.columns([3, 2])
        with col_t1:
            st.markdown(f"#### 📋 Bảng Tổng hợp theo Tháng ({sel_year})")
            st.dataframe(df_summary, width="stretch", hide_index=True)
        with col_t2:
            st.markdown(f"#### 🏆 Đóng góp theo Nhân sự ({sel_year})")
            st.bar_chart(df_y["staff_name"].value_counts())

        csv_year = df_summary.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label=f"📥 Xuất Báo cáo Năm {sel_year} (CSV/Excel)",
            data=csv_year,
            file_name=f"bao_cao_nam_{sel_year}.csv",
            mime="text/csv",
        )
    else:
        st.info(f"📭 Không có dữ liệu công trình trong năm {sel_year}.")
else:
    st.info("📭 Chưa có dữ liệu công trình trên hệ thống.")
