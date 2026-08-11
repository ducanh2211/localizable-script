"""Metrics component displaying translation progress statistics."""

import streamlit as st


def render_metrics() -> None:
    """Hiển thị các chỉ số thống kê tiến độ localization."""
    rows = st.session_state.table_rows
    target_langs = st.session_state.target_langs
    source_lang = st.session_state.source_lang

    if not rows:
        st.info("👋 Hãy chọn file .xcstrings trong Sidebar để bắt đầu.")
        return

    total_keys = len({r["key"] for r in rows})
    total_items = len(rows)

    st.write(f"**Tổng số Key:** `{total_keys}` | **Tổng số dòng biến thể (variants):** `{total_items}` | **Ngôn ngữ nguồn:** `{source_lang}`")

    cols = st.columns(min(len(target_langs), 4) if target_langs else 1)
    for idx, lang in enumerate(target_langs):
        col = cols[idx % len(cols)]
        col_target = f"{lang}_target"
        col_state = f"{lang}_state"

        translated_count = 0
        needs_review_count = 0
        empty_count = 0

        for r in rows:
            val = (r.get(col_target) or "").strip()
            state = r.get(col_state, "")
            if not val:
                empty_count += 1
            elif state == "needs_review":
                needs_review_count += 1
            else:
                translated_count += 1

        percent = (translated_count / total_items * 100) if total_items > 0 else 0
        with col:
            st.metric(
                label=f"🌐 {lang}",
                value=f"{percent:.1f}%",
                delta=f"{translated_count}/{total_items} chuỗi",
            )
            st.caption(f"Thiếu: **{empty_count}** | Review: **{needs_review_count}**")
            st.progress(min(percent / 100.0, 1.0))
