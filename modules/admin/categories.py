import streamlit as st
import pandas as pd
from services.admin_service import (
    get_all_categories_admin,
    create_category,
    update_category,
    delete_category,
)

st.title("🗂️ Quản lý Danh mục Hệ thống (Categories)")

CATEGORY_TYPES = [
    "Loại công trình",
    "Nhãn hiệu / Brand",
    "Khu vực / Tỉnh thành",
    "Mức độ ưu tiên",
    "Phân loại hồ sơ",
]

cats_data = get_all_categories_admin()

c_left, c_right = st.columns([2, 1])

with c_right:
    st.subheader("➕ Thêm Danh mục mới")
    with st.form("add_category_form"):
        cat_name = st.text_input("Tên danh mục *", placeholder="VD: Biệt thự tân cổ điển, Nhà phố 3 tầng...")
        cat_type = st.selectbox("Nhóm phân loại *", CATEGORY_TYPES)
        cat_active = st.checkbox("Đang sử dụng", value=True)

        if st.form_submit_button("💾 Lưu Danh mục", type="primary", width="stretch"):
            if not cat_name:
                st.warning("⚠️ Vui lòng nhập Tên danh mục!")
            else:
                res = create_category(cat_name, cat_type, cat_active)
                if res["success"]:
                    st.success(res["message"])
                    st.rerun()
                else:
                    st.error(res["message"])

with c_left:
    st.subheader(f"📋 Danh sách Danh mục hiện có ({len(cats_data)})")
    if cats_data:
        df_c = pd.DataFrame(cats_data).fillna("")
        if "category_type" not in df_c.columns:
            df_c["category_type"] = "Loại công trình"
        if "is_active" not in df_c.columns:
            df_c["is_active"] = True

        df_c["status_str"] = df_c["is_active"].apply(lambda x: "🟢 Hoạt động" if x else "🔴 Ngưng dùng")

        disp_c = df_c[["category_name", "category_type", "status_str"]].rename(
            columns={
                "category_name": "Tên Danh mục",
                "category_type": "Nhóm Phân loại",
                "status_str": "Trạng thái",
            }
        )

        ev_c = st.dataframe(
            disp_c,
            width="stretch",
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
        )

        if ev_c.selection.rows:
            sel_cat = df_c.iloc[ev_c.selection.rows[0]]
            cid = sel_cat["id"]
            st.divider()
            st.markdown(f"#### ✏️ Chỉnh sửa Danh mục: `{sel_cat['category_name']}`")
            with st.form(f"edit_cat_{cid}"):
                up_name = st.text_input("Tên danh mục", value=sel_cat["category_name"])
                curr_t = sel_cat["category_type"] if sel_cat["category_type"] in CATEGORY_TYPES else CATEGORY_TYPES[0]
                up_type = st.selectbox("Nhóm phân loại", CATEGORY_TYPES, index=CATEGORY_TYPES.index(curr_t))
                up_act = st.checkbox("Đang hoạt động", value=bool(sel_cat["is_active"]))

                if st.form_submit_button("💾 Cập nhật", type="primary", width="stretch"):
                    u_res = update_category(cid, up_name, up_type, up_act)
                    if u_res["success"]:
                        st.success(u_res["message"])
                        st.rerun()
                    else:
                        st.error(u_res["message"])

            if st.button("🗑️ Xóa danh mục này", type="secondary"):
                d_res = delete_category(cid)
                if d_res["success"]:
                    st.toast(d_res["message"], icon="🗑️")
                    st.rerun()
                else:
                    st.error(d_res["message"])
    else:
        st.info("📭 Chưa có danh mục nào. Hãy thêm danh mục đầu tiên ở khung bên phải.")
