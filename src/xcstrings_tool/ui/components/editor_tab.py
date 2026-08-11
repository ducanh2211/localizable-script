"""Spreadsheet Editor component for interactive table editing."""

import streamlit as st


def render_editor_tab() -> None:
    """Render Tab Bảng Dịch Tương Tác."""
    rows = st.session_state.table_rows
    target_langs = st.session_state.target_langs

    if not rows:
        st.info("Chưa có dữ liệu để hiển thị. Vui lòng nạp file .xcstrings.")
        return

    # Thanh công cụ lọc & tìm kiếm
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        filter_mode = st.selectbox(
            "Bộ lọc hiển thị:",
            ["Tất cả", "Chỉ dòng thiếu dịch (ít nhất 1 ngôn ngữ)", "Chỉ dòng có state needs_review"],
            index=0,
        )
    with c2:
        search_query = st.text_input("🔍 Tìm kiếm (key hoặc source):", placeholder="Gõ từ khóa...")

    # Lọc danh sách rows
    filtered_rows = []
    for r in rows:
        # Kiểm tra search
        if search_query:
            q = search_query.lower()
            if q not in r.get("key", "").lower() and q not in r.get("source_value", "").lower():
                continue

        # Kiểm tra filter
        if filter_mode == "Chỉ dòng thiếu dịch (ít nhất 1 ngôn ngữ)":
            missing = any(not (r.get(f"{lang}_target") or "").strip() for lang in target_langs)
            if not missing:
                continue
        elif filter_mode == "Chỉ dòng có state needs_review":
            review = any(r.get(f"{lang}_state") == "needs_review" for lang in target_langs)
            if not review:
                continue

        filtered_rows.append(r)

    st.caption(f"Đang hiển thị **{len(filtered_rows)}** / {len(rows)} dòng.")

    # Cấu hình các cột hiển thị trên st.data_editor
    column_config = {
        "key": st.column_config.TextColumn("Key", disabled=True, width="medium"),
        "variant": st.column_config.TextColumn("Variant", disabled=True, width="small"),
        "source_value": st.column_config.TextColumn("Source (Nguồn)", disabled=True, width="large"),
    }
    for lang in target_langs:
        column_config[f"{lang}_target"] = st.column_config.TextColumn(f"🌐 {lang} (Bản dịch)", width="large")
        column_config[f"{lang}_state"] = st.column_config.TextColumn(f"Trạng thái {lang}", disabled=True, width="small")

    # Hiển thị data editor
    edited_data = st.data_editor(
        filtered_rows,
        column_config=column_config,
        disabled=["key", "variant", "source_value", "variation_type", "variation_key"] + [f"{l}_state" for l in target_langs],
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="localization_data_editor",
    )

    # Đồng bộ thay đổi từ edited_data vào table_rows chính
    if edited_data:
        lookup = {(r["key"], r.get("variant", "")): r for r in edited_data}
        for orig in st.session_state.table_rows:
            k = (orig["key"], orig.get("variant", ""))
            if k in lookup:
                updated = lookup[k]
                for lang in target_langs:
                    col = f"{lang}_target"
                    if col in updated:
                        orig[col] = updated[col]
