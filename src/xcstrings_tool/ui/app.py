"""Main Streamlit Application for Xcode String Catalog Localization."""

import streamlit as st

from .components.ai_tab import render_ai_tab
from .components.editor_tab import render_editor_tab
from .components.metrics_view import render_metrics
from .components.prompt_tab import render_prompt_tab
from .components.save_tab import render_save_tab
from .components.sidebar import render_sidebar
from .state import init_session_state, load_file_into_state


def main():
    st.set_page_config(
        page_title="Xcode String Catalog Studio",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    # Tự động nạp file gần nhất nếu chưa nạp
    if st.session_state.raw_data is None and st.session_state.file_path:
        load_file_into_state(st.session_state.file_path, is_upload=False)

    # 1. Sidebar
    render_sidebar()

    # 2. Header & Metrics
    st.title("🌐 Xcode String Catalog Localization Studio")
    st.caption("Quản lý, chỉnh sửa, tự động dịch bằng AI và đồng bộ trực tiếp vào Xcode Project (.xcstrings)")
    st.divider()

    render_metrics()
    st.divider()

    # 3. Các Tabs chức năng
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Bảng Dịch (Editor)",
        "🤖 Dịch Tự Động (AI API)",
        "📋 Dịch Chatbot Web (Prompt & CSV)",
        "💾 Lưu & Verify (Xcode In-Place)",
    ])

    with tab1:
        render_editor_tab()

    with tab2:
        render_ai_tab()

    with tab3:
        render_prompt_tab()

    with tab4:
        render_save_tab()


if __name__ == "__main__":
    main()
