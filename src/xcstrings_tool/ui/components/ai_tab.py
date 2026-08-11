"""AI Auto-Translate tab component."""

import streamlit as st

from ...services.ai_translator import AIProvider, AITranslator


def render_ai_tab() -> None:
    """Render Tab Dịch Tự Động Bằng AI."""
    st.subheader("🤖 Dịch Tự Động Bằng AI")

    rows = st.session_state.table_rows
    target_langs = st.session_state.target_langs

    if not rows:
        st.info("Chưa có dữ liệu để dịch. Vui lòng nạp file .xcstrings.")
        return

    provider = st.session_state.get("ai_provider", "gemini")
    api_key = st.session_state.get(f"api_key_{provider}", "")

    if not api_key:
        st.warning(f"⚠️ Chưa có API Key cho nhà cung cấp **{provider.upper()}**. Vui lòng nhập API Key ở thanh Sidebar bên trái.")
        return

    c1, c2 = st.columns(2)
    with c1:
        translate_langs = st.multiselect(
            "Chọn ngôn ngữ muốn dịch:",
            options=target_langs,
            default=target_langs,
            help="Chỉ những ngôn ngữ được chọn mới được AI dịch.",
        )
    with c2:
        scope = st.radio(
            "Phạm vi dịch:",
            ["Chỉ dịch các ô đang trống", "Dịch ô trống + ô needs_review", "Dịch lại toàn bộ"],
            index=0,
        )

    # Đếm số ô cần dịch
    items_to_translate_count = 0
    for r in rows:
        for lang in translate_langs:
            val = (r.get(f"{lang}_target") or "").strip()
            state = r.get(f"{lang}_state", "")
            if scope == "Chỉ dịch các ô đang trống" and not val:
                items_to_translate_count += 1
                break
            elif scope == "Dịch ô trống + ô needs_review" and (not val or state == "needs_review"):
                items_to_translate_count += 1
                break
            elif scope == "Dịch lại toàn bộ":
                items_to_translate_count += 1
                break

    st.write(f"Số dòng cần xử lý dịch: **{items_to_translate_count}** dòng.")

    if st.button("🚀 Bắt đầu dịch tự động", type="primary", disabled=(items_to_translate_count == 0)):
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def on_progress(completed: int, total: int):
            frac = completed / total if total > 0 else 1.0
            progress_bar.progress(frac)
            status_text.text(f"Đang dịch: {completed}/{total} dòng...")

        try:
            translator = AITranslator(provider=provider, api_key=api_key)
            status_text.text("Đang kết nối tới AI API...")

            # Lọc các dòng thực sự cần dịch
            rows_to_process = []
            for r in rows:
                need = False
                for lang in translate_langs:
                    val = (r.get(f"{lang}_target") or "").strip()
                    state = r.get(f"{lang}_state", "")
                    if scope == "Chỉ dịch các ô đang trống" and not val:
                        need = True
                    elif scope == "Dịch ô trống + ô needs_review" and (not val or state == "needs_review"):
                        need = True
                    elif scope == "Dịch lại toàn bộ":
                        need = True
                if need:
                    rows_to_process.append(r)

            translator.translate_rows(
                rows=rows_to_process,
                target_langs=translate_langs,
                batch_size=20,
                progress_callback=on_progress,
            )

            progress_bar.progress(1.0)
            status_text.empty()
            st.success("🎉 Đã dịch tự động hoàn tất! Chuyển sang Tab 1 (Bảng Dịch) hoặc Tab 4 (Lưu) để kiểm tra kết quả.")
            st.rerun()

        except Exception as e:
            st.error(f"Lỗi trong quá trình dịch AI: {e}")
