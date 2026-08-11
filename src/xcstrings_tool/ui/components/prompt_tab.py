"""Prompt and CSV export/import tab component."""

import csv
import io
import subprocess
import streamlit as st

from ...core import wide_csv_fields


def _copy_to_mac_clipboard(text: str) -> bool:
    """Copy text vào clipboard macOS bằng pbcopy."""
    try:
        process = subprocess.Popen("pbcopy", env={"LANG": "en_US.UTF-8"}, stdin=subprocess.PIPE)
        process.communicate(text.encode("utf-8"))
        return process.returncode == 0
    except Exception:
        return False


def render_prompt_tab() -> None:
    """Render Tab Prompt & CSV Generator."""
    st.subheader("📋 Dịch Qua AI Chatbot Web (ChatGPT / Claude Web)")

    rows = st.session_state.table_rows
    target_langs = st.session_state.target_langs

    if not rows:
        st.info("Chưa có dữ liệu. Vui lòng nạp file .xcstrings.")
        return

    st.write(
        "Nếu bạn muốn tự dán vào ChatGPT hoặc Claude trên trình duyệt: "
        "Bấm nút **Copy Prompt + CSV** rồi nhấn `Cmd + V` dán vào Chatbot."
    )

    # Lọc các dòng còn thiếu
    untranslated_rows = [
        r for r in rows if any(not (r.get(f"{lang}_target") or "").strip() for lang in target_langs)
    ]

    # Tạo CSV in-memory
    fieldnames = wide_csv_fields(target_langs)
    csv_buf = io.StringIO()
    writer = csv.DictWriter(csv_buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(untranslated_rows if untranslated_rows else rows)
    csv_content = csv_buf.getvalue()

    target_cols_str = ", ".join([f"{l}_target" for l in target_langs])
    prompt_text = (
        f"Bạn là biên dịch viên phần mềm, thành thạo nhiều ngôn ngữ. Tôi sẽ dán một file CSV xuất ra từ "
        f"Xcode String Catalog (.xcstrings), có các cột: key, variant, source_value, rồi đến các cột: {target_cols_str}.\n\n"
        f"Nhiệm vụ: Với MỖI dòng, dịch `source_value` sang TẤT CẢ ngôn ngữ đích tương ứng với từng cột {target_cols_str}.\n\n"
        f"Quy tắc bắt buộc:\n"
        f"1. CHỈ điền/sửa các cột `_target`. Không đổi key, variant, source_value.\n"
        f"2. Nếu ô đã có sẵn giá trị, giữ nguyên không đổi.\n"
        f"3. Giữ NGUYÊN VẸN mọi placeholder trong source_value: %@, %d, %lld, %f, %1$@, %2$lld... (%% là dấu % literal, giữ nguyên).\n"
        f"4. Nếu variant bắt đầu bằng 'plural.', dịch tự nhiên theo ngữ pháp số nhiều của ngôn ngữ đích.\n"
        f"5. CSV trả về CHỈ cần các cột: key, variant, {target_cols_str} (bỏ hẳn cột source_value để tiết kiệm token).\n"
        f"6. Giữ đúng header và cấu trúc CSV, không thêm giải thích hay text nào ngoài CSV.\n\n"
        f"Dữ liệu CSV:\n```csv\n{csv_content}\n```"
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋 Copy Prompt + CSV vào Clipboard (macOS)", type="primary"):
            if _copy_to_mac_clipboard(prompt_text):
                st.success("✅ Đã copy vào Clipboard! Hãy mở ChatGPT/Claude và nhấn Cmd + V.")
            else:
                st.info("Không gọi được pbcopy. Vui lòng copy thủ công từ ô bên dưới.")

    with c2:
        st.download_button(
            label="📥 Tải về file todo.csv",
            data=csv_content.encode("utf-8-sig"),
            file_name="todo_wide.csv",
            mime="text/csv",
        )

    with st.expander("👁 Xem trước Prompt & CSV"):
        st.code(prompt_text, language="markdown")

    st.divider()

    # Nhận lại file CSV đã dịch từ Chatbot
    st.subheader("📥 Nạp lại file CSV đã dịch từ Chatbot")
    csv_upload = st.file_uploader("Kéo thả file CSV đã dịch:", type=["csv"])
    if csv_upload is not None:
        if st.button("🔄 Cập nhật bản dịch từ CSV vào bảng"):
            try:
                content = csv_upload.getvalue().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(content))
                translated_data = list(reader)

                lookup = {(r.get("key", ""), r.get("variant", "")): r for r in translated_data}
                updated_count = 0

                for orig in st.session_state.table_rows:
                    k = (orig["key"], orig.get("variant", ""))
                    if k in lookup:
                        csv_row = lookup[k]
                        for lang in target_langs:
                            col = f"{lang}_target"
                            if col in csv_row and csv_row[col].strip():
                                orig[col] = csv_row[col].strip()
                                updated_count += 1

                st.success(f"🎉 Đã cập nhật thành công {updated_count} ô bản dịch từ CSV!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi đọc file CSV: {e}")
