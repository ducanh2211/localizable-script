"""State management and helper functions for Streamlit UI."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import streamlit as st

from ..core import iter_rows_for_key_wide, load, validate_languages

RECENT_PATH_FILE = Path.home() / ".xcstrings_recent_path"


def get_recent_file_path() -> str:
    """Lấy đường dẫn file gần nhất đã mở."""
    if RECENT_PATH_FILE.exists():
        try:
            return RECENT_PATH_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    return ""


def save_recent_file_path(path: str) -> None:
    """Lưu đường dẫn file gần nhất."""
    try:
        RECENT_PATH_FILE.write_text(str(path).strip(), encoding="utf-8")
    except Exception:
        pass


def init_session_state() -> None:
    """Khởi tạo các biến session state cần thiết."""
    if "file_path" not in st.session_state:
        st.session_state.file_path = get_recent_file_path()
    if "raw_data" not in st.session_state:
        st.session_state.raw_data = None
    if "source_lang" not in st.session_state:
        st.session_state.source_lang = "en"
    if "target_langs" not in st.session_state:
        st.session_state.target_langs = ["vi"]
    if "table_rows" not in st.session_state:
        st.session_state.table_rows = []
    if "filter_mode" not in st.session_state:
        st.session_state.filter_mode = "Tất cả"
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""


def load_file_into_state(path_or_content: Any, is_upload: bool = False) -> bool:
    """Load nội dung file .xcstrings vào session state."""
    try:
        if is_upload:
            content = path_or_content.getvalue().decode("utf-8")
            data = json.loads(content)
            st.session_state.file_path = ""
        else:
            p = Path(path_or_content)
            if not p.exists() or not p.is_file():
                st.error(f"File không tồn tại: {path_or_content}")
                return False
            data = load(p)
            st.session_state.file_path = str(p)
            save_recent_file_path(str(p))

        st.session_state.raw_data = data
        st.session_state.source_lang = data.get("sourceLanguage", "en")

        # Quét các ngôn ngữ đích đã có trong file
        found_langs = set()
        for entry in data.get("strings", {}).values():
            locs = entry.get("localizations", {})
            for lang in locs.keys():
                if lang != st.session_state.source_lang:
                    found_langs.add(lang)

        # Merge với target_langs hiện tại nếu có
        existing_targets = list(st.session_state.target_langs)
        for fl in sorted(found_langs):
            if fl not in existing_targets:
                existing_targets.append(fl)

        st.session_state.target_langs = existing_targets if existing_targets else ["vi"]
        reload_table_rows()
        return True
    except Exception as e:
        st.error(f"Lỗi khi đọc file .xcstrings: {e}")
        return False


def reload_table_rows() -> None:
    """Tạo lại danh sách rows từ raw_data và target_langs hiện tại."""
    if not st.session_state.raw_data:
        st.session_state.table_rows = []
        return

    data = st.session_state.raw_data
    source_lang = st.session_state.source_lang
    target_langs, _ = validate_languages(st.session_state.target_langs, source_lang)

    strings = data.get("strings", {})
    all_rows = []
    for key, entry in strings.items():
        rows = iter_rows_for_key_wide(key, entry, source_lang, target_langs)
        all_rows.extend(rows)

    st.session_state.table_rows = all_rows
