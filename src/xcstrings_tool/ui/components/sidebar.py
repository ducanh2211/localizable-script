"""Sidebar component for file selection, languages, and API settings."""

import os
from pathlib import Path
import streamlit as st

from ..state import load_file_into_state, reload_table_rows

COMMON_LANGUAGES = [
    "vi", "ja", "ko", "zh-Hans", "zh-Hant", "fr", "de", "es", "it",
    "pt-BR", "ru", "th", "id", "ms", "hi", "ar", "tr", "pl", "nl"
]


def render_sidebar() -> None:
    """Render Sidebar giao diện."""
    st.sidebar.title("🛠 Cấu hình & Dữ liệu")

    # 1. Chọn nguồn file
    st.sidebar.subheader("1. File .xcstrings")
    file_mode = st.sidebar.radio("Nguồn file:", ["Đường dẫn trực tiếp (Xcode)", "Upload file"], horizontal=True)

    if file_mode == "Đường dẫn trực tiếp (Xcode)":
        default_path = st.session_state.file_path or ""
        input_path = st.sidebar.text_input(
            "Đường dẫn file .xcstrings:",
            value=default_path,
            placeholder="/Users/.../Localizable.xcstrings",
            help="Nhập đường dẫn tuyệt đối hoặc tương đối tới file .xcstrings trong Xcode project",
        )
        if st.sidebar.button("📂 Đọc / Tải lại file", use_container_width=True):
            if input_path:
                if load_file_into_state(input_path, is_upload=False):
                    st.sidebar.success("Đã nạp file thành công!")
            else:
                st.sidebar.warning("Vui lòng nhập đường dẫn file.")
    else:
        uploaded_file = st.sidebar.file_uploader("Kéo thả file .xcstrings:", type=["xcstrings", "json"])
        if uploaded_file is not None:
            if st.sidebar.button("📂 Nạp file upload", use_container_width=True):
                if load_file_into_state(uploaded_file, is_upload=True):
                    st.sidebar.success("Đã nạp file upload thành công!")

    st.sidebar.divider()

    # 2. Quản lý ngôn ngữ đích
    st.sidebar.subheader("2. Ngôn ngữ đích")
    current_targets = list(st.session_state.target_langs)
    selected_targets = st.sidebar.multiselect(
        "Danh sách ngôn ngữ:",
        options=sorted(list(set(COMMON_LANGUAGES + current_targets))),
        default=current_targets,
        help="Chọn các ngôn ngữ bạn muốn dịch hoặc quản lý.",
    )

    new_lang = st.sidebar.text_input("Thêm mã ngôn ngữ khác:", placeholder="vd: sv, no, da")
    if st.sidebar.button("➕ Thêm ngôn ngữ"):
        if new_lang and new_lang.strip() not in selected_targets:
            selected_targets.append(new_lang.strip())

    if selected_targets != st.session_state.target_langs:
        st.session_state.target_langs = selected_targets
        reload_table_rows()

    st.sidebar.divider()

    # 3. Cài đặt AI API
    st.sidebar.subheader("3. Cài đặt AI API")
    ai_provider = st.sidebar.selectbox(
        "Nhà cung cấp AI:",
        options=["gemini", "openai", "deepseek", "claude"],
        index=0,
        help="Chọn AI provider để dịch tự động.",
    )
    st.session_state.ai_provider = ai_provider

    # Lấy API Key từ session hoặc biến môi trường
    env_key_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
    }
    env_default_key = os.environ.get(env_key_map.get(ai_provider, ""), "")

    api_key_input = st.sidebar.text_input(
        f"API Key ({ai_provider}):",
        value=st.session_state.get(f"api_key_{ai_provider}", env_default_key),
        type="password",
        help="API key của bạn (không lưu vào disk, chỉ giữ trong phiên làm việc).",
    )
    st.session_state[f"api_key_{ai_provider}"] = api_key_input
