"""Save and Verify tab component."""

import copy
from pathlib import Path
import streamlit as st

from ...core import dump, dumps
from ...services.merger import merge_wide
from ...services.verifier import check_format_preserved, check_translations


def render_save_tab() -> None:
    """Render Tab Verify & Lưu Bản Dịch."""
    st.subheader("💾 Kiểm Tra (Verify) & Lưu Bản Dịch")

    rows = st.session_state.table_rows
    target_langs = st.session_state.target_langs
    raw_data = st.session_state.raw_data
    file_path = st.session_state.file_path

    if not rows or not raw_data:
        st.info("Chưa có dữ liệu. Vui lòng nạp file .xcstrings.")
        return

    # Chuẩn bị dữ liệu merge
    merged_data = copy.deepcopy(raw_data)
    fieldnames = ["key", "variant", "source_value"] + [f"{l}_target" for l in target_langs]
    report = merge_wide(merged_data, rows, fieldnames)

    # Chạy verify
    format_problems = check_format_preserved(raw_data, merged_data, target_langs)
    format_ok = len(format_problems) == 0

    stats_by_lang = {}
    warnings_by_lang = {}
    for lang in target_langs:
        w, s = check_translations(merged_data, lang)
        stats_by_lang[lang] = s
        warnings_by_lang[lang] = w

    total_placeholder_mismatch = sum(s["placeholder_mismatch"] for s in stats_by_lang.values())

    # 1. Báo cáo kiểm tra
    st.write("#### 1. Kết quả kiểm tra tính toàn vẹn:")
    c1, c2 = st.columns(2)
    with c1:
        if format_ok:
            st.success("✅ **Format:** Được bảo toàn 100% (chuẩn xác format Xcode).")
        else:
            st.error("❌ **Format:** Phát hiện thay đổi ngoài phạm vi dịch!")

    with c2:
        if total_placeholder_mismatch == 0:
            st.success("✅ **Placeholders:** Tất cả placeholder (%@, %d, ...) đều khớp chính xác.")
        else:
            st.error(f"❌ **Placeholders:** Có {total_placeholder_mismatch} chỗ bị lệch placeholder!")

    # Cảnh báo chi tiết nếu có
    has_warnings = False
    for lang, w_list in warnings_by_lang.items():
        if w_list:
            has_warnings = True
            with st.expander(f"⚠️ Cảnh báo chi tiết ngôn ngữ [{lang}] ({len(w_list)} mục)"):
                for item in w_list[:30]:
                    st.text(item)

    st.divider()

    # 2. Hành động Lưu
    st.write("#### 2. Áp dụng bản dịch:")
    if file_path and Path(file_path).exists():
        st.info(f"Đường dẫn file Xcode đích: `{file_path}`")
        c_save, c_dl = st.columns(2)
        with c_save:
            if st.button("🔥 Lưu trực tiếp vào Xcode Project (In-Place Update)", type="primary"):
                try:
                    p = Path(file_path)
                    # Tạo file backup .bak
                    bak_path = p.with_suffix(p.suffix + ".bak")
                    bak_path.write_bytes(p.read_bytes())

                    # Ghi đè file
                    dump(merged_data, p)

                    st.session_state.raw_data = merged_data
                    st.success(f"🎉 Đã lưu thành công vào file Xcode! (Đã tạo backup an toàn tại `{bak_path.name}`)")
                except Exception as e:
                    st.error(f"Lỗi khi ghi file: {e}")

        with c_dl:
            json_str = dumps(merged_data)
            st.download_button(
                label="📥 Tải về file .xcstrings",
                data=json_str.encode("utf-8"),
                file_name=Path(file_path).name,
                mime="application/json",
            )
    else:
        st.info("Đang ở chế độ Upload file. Bạn có thể tải file kết quả về máy:")
        json_str = dumps(merged_data)
        st.download_button(
            label="📥 Tải về Localizable.xcstrings đã cập nhật",
            data=json_str.encode("utf-8"),
            file_name="Localizable.xcstrings",
            mime="application/json",
            type="primary",
        )
