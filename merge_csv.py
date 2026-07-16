#!/usr/bin/env python3
r"""
merge_csv.py
============

Merge bản dịch từ file CSV (đã điền cột target) NGƯỢC vào file .xcstrings,
TẠO RA FILE MỚI có đuôi `.merged.xcstrings`.

Tự động NHẬN DIỆN định dạng CSV theo header, không cần chọn cờ:
  - LONG-FORMAT: có cột `language` + `target_value` (1 ngôn ngữ/dòng).
  - WIDE-FORMAT: có (các) cột `{lang}_target` (nhiều ngôn ngữ/dòng).

Nguyên tắc bảo toàn format (áp dụng cho cả 2 định dạng):
  - Chỉ chỉnh/thêm phần bản dịch của ngôn ngữ đích liên quan.
  - Mọi field khác (source, ngôn ngữ khác, comment, extractionState, ...)
    giữ nguyên tuyệt đối.
  - Ghi bằng serializer khớp 100% quy ước Xcode (trong xcstrings_common).
  - KHÔNG ghi đè file gốc: luôn xuất ra <tên gốc>.merged.xcstrings.

--- Quy tắc LONG-FORMAT (không đổi so với bản gốc) ---
  - Row có target_value KHÔNG rỗng -> áp dụng: value = target_value,
    state = "translated".
  - Row có target_value rỗng -> bỏ qua.

--- Quy tắc WIDE-FORMAT ---
So sánh trực tiếp với giá trị HIỆN CÓ trong chính file .xcstrings truyền vào
(existing_value), theo đúng path (variation_type, variation_key):
  - {lang}_target rỗng                       -> bỏ qua, không đổi gì.
    (KHÔNG hỗ trợ xoá bản dịch qua CSV bằng cách để trống ô.)
  - {lang}_target == existing_value,
    VÀ state hiện có KHÔNG PHẢI needs_review  -> bỏ qua (tránh ghi state lại
                                                  vô ích khi người dùng không
                                                  sửa gì).
  - {lang}_target == existing_value,
    NHƯNG state hiện có LÀ needs_review       -> vẫn áp dụng: state chuyển
                                                  thành "translated" (coi như
                                                  người dịch đã xem CSV và
                                                  xác nhận bản dịch cũ vẫn
                                                  đúng, dù không sửa chữ nào).
  - {lang}_target khác existing_value         -> áp dụng: value = target,
                                                  state = "translated".

Cột ngôn ngữ bị xoá thủ công khỏi CSV (vd. chỉ giữ vi_target, bỏ ja_target)
được xử lý graceful: ngôn ngữ đó đơn giản không được merge, không báo lỗi.

RÀNG BUỘC QUAN TRỌNG (wide-format): phải merge trên ĐÚNG file .xcstrings đã
dùng để export ra CSV đó. Nếu file gốc đã bị cập nhật bản dịch cho cùng
key/ngôn ngữ trong lúc chờ dịch (vd. người khác merge trước, hoặc sửa trực
tiếp trong Xcode), so sánh existing_value sẽ dựa trên bản MỚI hơn đó -- CSV
đang cầm giá trị CŨ từ lúc export có thể ghi đè mất bản dịch mới hơn. Dùng
`--dry-run` để xem trước danh sách thay đổi trước khi ghi file thật.

Cách dùng:
    python3 merge_csv.py <input.xcstrings> <translated.csv> [--dry-run]

Ví dụ:
    python3 merge_csv.py Localizable.xcstrings todo.csv
    -> tạo ra: Localizable.merged.xcstrings

    python3 merge_csv.py Localizable.xcstrings all_wide.csv --dry-run
    -> chỉ in ra danh sách thay đổi, KHÔNG ghi file.

Ghi chú:
  - Key trong CSV không tồn tại trong .xcstrings sẽ được CẢNH BÁO, không làm
    hỏng file.
"""

import sys
import csv
from pathlib import Path

import xcstrings_common as x


def _ensure_string_unit(entry, target_lang, var_type, var_key):
    r"""
    Trả về (và nếu cần thì TẠO) dict stringUnit tương ứng với một "path"
    (var_type, var_key) trong localization của ngôn ngữ đích.

    Tạo dần các cấp còn thiếu:
      localizations -> [target_lang] -> (stringUnit | variations.<type>.<key>.stringUnit)

    Trả về tham chiếu tới dict stringUnit để hàm gọi gán value/state.
    """
    localizations = entry.setdefault("localizations", {})
    target_loc = localizations.setdefault(target_lang, {})

    if var_type == "":
        return target_loc.setdefault("stringUnit", {})
    else:
        variations = target_loc.setdefault("variations", {})
        type_dict = variations.setdefault(var_type, {})
        leaf = type_dict.setdefault(var_key, {})
        return leaf.setdefault("stringUnit", {})


def _detect_mode(fieldnames):
    """Nhận diện long/wide dựa trên tên cột CSV. Trả về None nếu không rõ."""
    fieldnames = fieldnames or []
    if "language" in fieldnames and "target_value" in fieldnames:
        return "long"
    if any(f.endswith("_target") for f in fieldnames):
        return "wide"
    return None


def merge_long(data, rows):
    """Merge long-format -- LOGIC GIỮ NGUYÊN 100% so với bản gốc."""
    strings = data.get("strings", {})
    merged_count = 0
    skipped_empty = 0
    missing_keys = []

    for row in rows:
        target_value = (row.get("target_value") or "").strip()
        if not target_value:
            skipped_empty += 1
            continue

        key = row.get("key", "")
        target_lang = row.get("language", "")
        var_type = row.get("variation_type", "") or ""
        var_key = row.get("variation_key", "") or ""

        entry = strings.get(key)
        if entry is None:
            missing_keys.append(key)
            continue

        su = _ensure_string_unit(entry, target_lang, var_type, var_key)
        su["state"] = "translated"
        su["value"] = target_value
        merged_count += 1

    return {
        "mode": "long",
        "merged_count": merged_count,
        "skipped_empty": skipped_empty,
        "missing_keys": missing_keys,
    }


def merge_wide(data, rows, fieldnames):
    """Merge wide-format: so sánh existing_value trước khi ghi đè (xem docstring)."""
    strings = data.get("strings", {})
    target_langs = sorted({f[: -len("_target")] for f in fieldnames if f.endswith("_target")})

    merged_count = {lang: 0 for lang in target_langs}
    skipped_empty = {lang: 0 for lang in target_langs}
    skipped_unchanged = {lang: 0 for lang in target_langs}
    missing_keys = []
    changes = []  # (key, var_type, var_key, lang, existing_value, csv_value) -- cho --dry-run

    for row in rows:
        key = row.get("key", "")
        var_type = row.get("variation_type", "") or ""
        var_key = row.get("variation_key", "") or ""

        entry = strings.get(key)
        if entry is None:
            missing_keys.append(key)
            continue

        for lang in target_langs:
            col = f"{lang}_target"
            if col not in row:
                # Cột ngôn ngữ này bị xoá thủ công khỏi CSV -> bỏ qua graceful.
                continue

            csv_value = (row.get(col) or "").strip()
            if not csv_value:
                skipped_empty[lang] += 1
                continue

            existing_value, existing_state = x.get_existing_unit(entry, lang, var_type, var_key)
            existing_value_norm = (existing_value or "").strip()

            unchanged = csv_value == existing_value_norm
            if unchanged and existing_state != "needs_review":
                skipped_unchanged[lang] += 1
                continue

            su = _ensure_string_unit(entry, lang, var_type, var_key)
            su["state"] = "translated"
            su["value"] = csv_value
            merged_count[lang] += 1
            changes.append((key, var_type, var_key, lang, existing_value, csv_value))

    return {
        "mode": "wide",
        "target_langs": target_langs,
        "merged_count": merged_count,
        "skipped_empty": skipped_empty,
        "skipped_unchanged": skipped_unchanged,
        "missing_keys": missing_keys,
        "changes": changes,
    }


def _print_report(report, out_path, dry_run):
    verb = "Sẽ merge" if dry_run else "Đã merge"

    if report["mode"] == "long":
        suffix = "" if dry_run else f" vào: {out_path}"
        print(f"{verb} {report['merged_count']} bản dịch{suffix}")
        print(f"  Bỏ qua {report['skipped_empty']} dòng (target_value rỗng).")
    else:
        suffix = "" if dry_run else f" vào: {out_path}"
        print(f"{verb} bản dịch (wide-format){suffix}")
        for lang in report["target_langs"]:
            print(
                f"  [{lang}] cập nhật: {report['merged_count'][lang]}"
                f"  | bỏ qua (rỗng): {report['skipped_empty'][lang]}"
                f"  | bỏ qua (không đổi): {report['skipped_unchanged'][lang]}"
            )

    if report["missing_keys"]:
        mk = report["missing_keys"]
        print(f"  CẢNH BÁO: {len(mk)} key trong CSV không có trong file gốc:")
        for k in mk[:20]:
            print(f"    - {k!r}")
        if len(mk) > 20:
            print(f"    ... và {len(mk) - 20} key khác.")

    if dry_run and report["mode"] == "wide" and report["changes"]:
        print(f"\n  --- Chi tiết thay đổi (dry-run, tối đa 30/{len(report['changes'])} dòng) ---")
        for key, var_type, var_key, lang, old, new in report["changes"][:30]:
            print(f"    [{lang}] key={key!r} path=({var_type!r},{var_key!r})")
            print(f"        cũ : {old!r}")
            print(f"        mới: {new!r}")
        if len(report["changes"]) > 30:
            print(f"    ... và {len(report['changes']) - 30} thay đổi khác.")


def main(argv):
    args = argv[1:]
    dry_run = "--dry-run" in args
    positional = [a for a in args if a != "--dry-run"]

    if len(positional) != 2:
        print(__doc__)
        print("LỖI: cần đúng 2 tham số (input.xcstrings, translated.csv).", file=sys.stderr)
        return 1

    input_path, csv_path = positional

    # --- Load file gốc ---
    data = x.load(input_path)

    # --- Đọc CSV các bản dịch ---
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # --- Nhận diện định dạng CSV ---
    mode = _detect_mode(fieldnames)
    if mode is None:
        print(f"LỖI: không nhận diện được định dạng CSV từ header: {fieldnames}", file=sys.stderr)
        print(
            "  Cần có cột 'language' + 'target_value' (long-format) "
            "hoặc '{lang}_target' (wide-format).",
            file=sys.stderr,
        )
        return 1

    # --- Áp bản dịch vào cây dữ liệu ---
    if mode == "long":
        report = merge_long(data, rows)
    else:
        report = merge_wide(data, rows, fieldnames)

    # --- Ghi ra file .merged.xcstrings (KHÔNG ghi đè file gốc) ---
    src = Path(input_path)
    out_path = src.with_suffix("")  # bỏ đuôi .xcstrings
    out_path = Path(str(out_path) + ".merged.xcstrings")

    if not dry_run:
        x.dump(data, out_path)

    # --- Báo cáo kết quả ---
    _print_report(report, out_path, dry_run)
    if dry_run:
        print("\n  (dry-run: CHƯA ghi file nào, chỉ xem trước thay đổi.)")
    else:
        print("  -> Chạy verify.py để kiểm tra file kết quả.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
