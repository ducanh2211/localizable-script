#!/usr/bin/env python3
r"""
export_all.py
=============

Export TOÀN BỘ key-value của một file .xcstrings ra file CSV.

Có 2 chế độ:

  1) LONG-FORMAT (mặc định, 1 ngôn ngữ / lần chạy) -- dịch tách riêng theo
     từng ngôn ngữ. Cột CSV: key, variant, source_value, target_value.
       python3 export_all.py <input.xcstrings> <target_lang> <output.csv>
     Ví dụ:
       python3 export_all.py Localizable.xcstrings vi all_vi.csv
     Khi merge, truyền lại đúng ngôn ngữ qua --lang (xem merge_csv.py).

  2) WIDE-FORMAT (nhiều ngôn ngữ / 1 file CSV) -- dịch 1 key cho nhiều ngôn
     ngữ cùng lúc, mỗi ngôn ngữ có 1 cột {lang}_target:
       python3 export_all.py <input.xcstrings> <output.csv> --languages vi,ja,ko
     Ví dụ:
       python3 export_all.py Localizable.xcstrings all_wide.csv --languages vi,ja,ko

Cột "variant" gộp (variation_type, variation_key) làm 1, vd. "plural.one",
"device.iphone"; rỗng ("") nghĩa là string đơn giản (không có variation).
Đây là thông tin merge cần để ghi đúng path -- KHÔNG sửa cột này.

Dùng để có cái nhìn tổng thể tất cả chuỗi (đã dịch + chưa dịch). CSV sinh ra
có (các) cột target để (nếu muốn) dịch/ghi đè.

CSV xuất ra dùng encoding UTF-8 kèm BOM (utf-8-sig) để Excel / Google Sheets
mở lên hiển thị đúng tiếng Việt và các ký tự Unicode khác.
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

    # --- Sinh các row cho mọi entry, mọi variation ---
    all_rows = []
    for key, entry in strings.items():
        rows = x.iter_rows_for_key(key, entry, source_lang, target_lang)
        all_rows.extend(rows)

    # --- Ghi ra CSV ---
    # newline="" theo khuyến nghị của module csv để không sinh dòng trống thừa.
    # extrasaction="ignore": row nội bộ còn giữ variation_type/variation_key/
    # language/state để dùng nội bộ, nhưng CSV chỉ ghi đúng x.CSV_FIELDS.
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=x.CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Đã export {len(all_rows)} dòng (toàn bộ) ra: {output_csv}")
    print(f"  Ngôn ngữ nguồn: {source_lang}  |  Ngôn ngữ đích: {target_lang}")
    print(f"  -> Khi merge, nhớ truyền --lang {target_lang}.")
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

    # --- Sinh các row wide cho mọi entry, mọi variation ---
    all_rows = []
    for key, entry in strings.items():
        rows = x.iter_rows_for_key_wide(key, entry, source_lang, target_langs)
        all_rows.extend(rows)

    # --- Ghi ra CSV ---
    fieldnames = x.wide_csv_fields(target_langs)
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Đã export {len(all_rows)} dòng (toàn bộ) ra: {output_csv}")
    print(f"  Ngôn ngữ nguồn: {source_lang}  |  Ngôn ngữ đích: {', '.join(target_langs)}")
    return 0


def main(argv):
    if "--languages" in argv:
        return main_wide(argv)
    return main_long(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
