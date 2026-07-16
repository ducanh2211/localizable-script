#!/usr/bin/env python3
r"""
export_untranslated.py
======================

Chỉ export những key-value CHƯA ĐƯỢC DỊCH của một file .xcstrings ra CSV,
để không phải dịch lại phần đã dịch.

Định nghĩa "chưa dịch" (đã chốt), áp dụng cho MỖI ô/path/ngôn ngữ:
  - THIẾU HẲN localization cho ngôn ngữ đích, HOẶC
  - state của ô đó là "new" / "needs_review", HOẶC
  - value đích rỗng.

Có 2 chế độ:

  1) LONG-FORMAT (mặc định, 1 ngôn ngữ / lần chạy):
       python3 export_untranslated.py <input.xcstrings> <target_lang> <output.csv>
     Ví dụ:
       python3 export_untranslated.py Localizable.xcstrings vi todo.csv
     Chỉ xuất dòng chưa dịch của CHÍNH ngôn ngữ đó.

  2) WIDE-FORMAT (nhiều ngôn ngữ / 1 file CSV), áp dụng OR-rule: xuất dòng
     nếu CÒN THIẾU Ở ÍT NHẤT 1 NGÔN NGỮ ĐÍCH bất kỳ trong danh sách (không
     cần thiếu toàn bộ). Ngôn ngữ đã dịch xong trong dòng đó vẫn hiện giá
     trị cũ để tiện ngữ cảnh khi dịch nốt phần còn thiếu:
       python3 export_untranslated.py <input.xcstrings> <output.csv> --languages vi,ja,ko
     Ví dụ:
       python3 export_untranslated.py Localizable.xcstrings todo_wide.csv --languages vi,ja,ko

CSV xuất ra dùng encoding utf-8-sig để Excel / Google Sheets mở đúng Unicode.
(Các) cột target để trống -> đây là chỗ bạn (hoặc AI Chatbot) điền bản dịch.
"""

import sys
import csv

import xcstrings_common as x


def main_long(argv):
    if len(argv) != 4:
        print(__doc__)
        print("LỖI: long-format cần đúng 3 tham số (input, target_lang, output.csv).",
              file=sys.stderr)
        return 1

    input_path, target_lang, output_csv = argv[1], argv[2], argv[3]

    # --- Load file .xcstrings ---
    data = x.load(input_path)
    source_lang = data.get("sourceLanguage", "en")
    strings = data.get("strings", {})

    # --- Sinh row rồi LỌC chỉ giữ những ô chưa dịch ---
    untranslated_rows = []
    for key, entry in strings.items():
        for row in x.iter_rows_for_key(key, entry, source_lang, target_lang):
            if x.row_is_untranslated(row, entry, target_lang):
                untranslated_rows.append(row)

    # --- Ghi ra CSV ---
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=x.CSV_FIELDS)
        writer.writeheader()
        writer.writerows(untranslated_rows)

    print(f"Đã export {len(untranslated_rows)} dòng CHƯA DỊCH ra: {output_csv}")
    print(f"  Ngôn ngữ nguồn: {source_lang}  |  Ngôn ngữ đích: {target_lang}")
    print("  -> Điền bản dịch vào cột 'target_value' rồi dùng merge_csv.py.")
    return 0


def main_wide(argv):
    args = argv[1:]
    idx = args.index("--languages")
    if idx + 1 >= len(args):
        print(__doc__)
        print("LỖI: --languages cần giá trị, ví dụ --languages vi,ja,ko", file=sys.stderr)
        return 1

    langs_raw = args[idx + 1]
    positional = args[:idx] + args[idx + 2:]
    if len(positional) != 2:
        print(__doc__)
        print("LỖI: wide-format cần đúng 2 tham số (input.xcstrings, output.csv).",
              file=sys.stderr)
        return 1
    input_path, output_csv = positional

    # --- Load file .xcstrings ---
    data = x.load(input_path)
    source_lang = data.get("sourceLanguage", "en")
    strings = data.get("strings", {})

    # --- Validate danh sách ngôn ngữ đích ---
    target_langs, warnings = x.validate_languages(langs_raw.split(","), source_lang)
    for w in warnings:
        print(f"CẢNH BÁO: {w}", file=sys.stderr)
    if not target_langs:
        print("LỖI: không còn ngôn ngữ đích hợp lệ nào sau khi validate.", file=sys.stderr)
        return 1

    # --- Sinh row rồi lọc theo OR-rule: thiếu ở BẤT KỲ ngôn ngữ nào thì giữ ---
    untranslated_rows = []
    for key, entry in strings.items():
        for row in x.iter_rows_for_key_wide(key, entry, source_lang, target_langs):
            include = any(
                x.path_is_untranslated(entry, lang, row["variation_type"], row["variation_key"])
                for lang in target_langs
            )
            if include:
                untranslated_rows.append(row)

    # --- Ghi ra CSV ---
    fieldnames = x.wide_csv_fields(target_langs)
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(untranslated_rows)

    print(f"Đã export {len(untranslated_rows)} dòng CHƯA DỊCH (ít nhất 1 ngôn ngữ) ra: {output_csv}")
    print(f"  Ngôn ngữ nguồn: {source_lang}  |  Ngôn ngữ đích: {', '.join(target_langs)}")
    print("  -> Điền bản dịch vào các cột '{lang}_target' rồi dùng merge_csv.py.")
    return 0


def main(argv):
    if "--languages" in argv:
        return main_wide(argv)
    return main_long(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
