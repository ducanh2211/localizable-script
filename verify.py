#!/usr/bin/env python3
r"""
verify.py
=========

Kiểm tra (verify) file .xcstrings sau khi merge để chắc chắn:
  1. File vẫn là JSON hợp lệ.
  2. FORMAT được bảo toàn: khi so sánh với file gốc, khác biệt DUY NHẤT chỉ
     nằm ở phần bản dịch của (các) ngôn ngữ đích (value/state), không đụng
     chỗ khác.
  3. Chất lượng bản dịch cơ bản, cho TỪNG ngôn ngữ:
       - còn ô nào state new/needs_review hoặc value rỗng không,
       - placeholder có khớp giữa source và bản dịch không
         (ví dụ số lượng %@, %lld, %1$@ ... phải bằng nhau).

Hỗ trợ verify NHIỀU ngôn ngữ cùng lúc (dùng cho cả long-format lẫn
wide-format ở merge_csv.py, vì verify chỉ cần biết ngôn ngữ nào cần kiểm tra,
không quan tâm CSV gốc là long hay wide) -- truyền danh sách ngôn ngữ cách
nhau bởi dấu phẩy:

Cách dùng:
    python3 verify.py <original.xcstrings> <merged.xcstrings> <lang1[,lang2,...]>

Ví dụ (1 ngôn ngữ, như bản gốc):
    python3 verify.py Localizable.xcstrings Localizable.merged.xcstrings vi

Ví dụ (nhiều ngôn ngữ, wide-format):
    python3 verify.py Localizable.xcstrings Localizable.merged.xcstrings vi,ja,ko

Thoát với mã 0 nếu không có lỗi nghiêm trọng, khác 0 nếu có.
"""

import sys
import re

import xcstrings_common as x

# Regex bắt các placeholder định dạng chuỗi kiểu C/Cocoa mà iOS dùng:
#   %@  %d  %lld  %f  %1$@  %2$lld  %%  ...
# Dùng để đối chiếu source vs bản dịch, tránh dịch làm mất/thêm placeholder.
PLACEHOLDER_RE = re.compile(r"%(?:\d+\$)?[-+ 0#]?\d*(?:\.\d+)?(?:ll|l|h|hh|q|z|t|j|L)?[@diouxXeEfgGaAcsSp%]")


def _placeholder_multiset(text):
    """
    Trả về danh sách đã sắp xếp các placeholder trong một chuỗi, để so sánh
    'multiset' (số lượng + loại) giữa source và target.
    %% (dấu phần trăm literal) được bỏ qua vì không phải tham số thật.
    """
    found = [p for p in PLACEHOLDER_RE.findall(text) if p != "%%"]
    return sorted(found)


def check_json_valid(path):
    """Bước 1: parse thử; trả về (data, error_message)."""
    try:
        return x.load(path), None
    except Exception as e:
        return None, f"File không phải JSON hợp lệ: {e}"


def check_format_preserved(original, merged, target_langs):
    r"""
    Bước 2: xác nhận format/nội dung ngoài phần dịch được giữ nguyên.

    Cách làm: tạo bản sao 'chuẩn hoá' của cả hai file trong đó XOÁ toàn bộ
    localization của TẤT CẢ ngôn ngữ đích (target_langs), rồi serialize bằng
    cùng serializer. Nếu hai bản chuẩn hoá GIỐNG HỆT nhau -> mọi thay đổi chỉ
    nằm ở các ngôn ngữ đích, tức format và các ngôn ngữ khác được bảo toàn.

    target_langs là list (kể cả khi chỉ verify 1 ngôn ngữ, caller truyền [lang]).

    Trả về danh sách thông báo lỗi (rỗng nếu ổn).
    """
    import copy

    def strip_targets(data):
        d = copy.deepcopy(data)
        for entry in d.get("strings", {}).values():
            loc = entry.get("localizations")
            if loc:
                for lang in target_langs:
                    if lang in loc:
                        del loc[lang]
            # Nếu sau khi bỏ các ngôn ngữ đích mà localizations rỗng, xoá
            # luôn nhánh này để entry trở về đúng dạng ban đầu (object rỗng),
            # tránh báo nhầm khác biệt format ở những entry mới được thêm dịch.
            if "localizations" in entry and not entry["localizations"]:
                del entry["localizations"]
        return d

    problems = []
    a = x.dumps(strip_targets(original))
    b = x.dumps(strip_targets(merged))
    if a != b:
        problems.append(
            "Khác biệt NGOÀI phần dịch ngôn ngữ đích được phát hiện "
            "(format hoặc nội dung khác đã bị thay đổi)."
        )
        # Chỉ ra điểm khác đầu tiên để debug.
        for i, (ca, cb) in enumerate(zip(a, b)):
            if ca != cb:
                problems.append(f"  Khác đầu tiên tại vị trí {i}:")
                problems.append(f"    gốc  : {a[max(0,i-30):i+30]!r}")
                problems.append(f"    merge: {b[max(0,i-30):i+30]!r}")
                break
    return problems


def check_translations(merged, target_lang):
    """
    Bước 3: rà soát chất lượng bản dịch ở ngôn ngữ đích.
    Trả về (warnings, stats) — warning là cảnh báo (không nhất thiết fail).
    """
    warnings = []
    source_lang = merged.get("sourceLanguage", "en")
    strings = merged.get("strings", {})

    n_untranslated = 0       # còn new/needs_review
    n_empty = 0              # value rỗng
    n_placeholder_mismatch = 0
    n_translated = 0

    for key, entry in strings.items():
        loc = entry.get("localizations", {})
        target_loc = loc.get(target_lang)
        source_loc = loc.get(source_lang, {})
        if not target_loc:
            continue  # entry này không có bản dịch đích (có thể cố ý), bỏ qua

        # Map source theo path để đối chiếu placeholder.
        source_units = {(t, k): su.get("value", "")
                        for t, k, su in x.iter_units(source_loc)}
        # Fallback quan trọng: trong .xcstrings, nếu key TRÙNG với chuỗi nguồn
        # thì Xcode thường KHÔNG lưu localization nguồn riêng -- chính `key` là
        # source value. Khi đó dùng key làm source cho ô chuỗi đơn giản ("","").
        if ("", "") not in source_units:
            source_units[("", "")] = key

        for var_type, var_key, su in x.iter_units(target_loc):
            state = su.get("state", "")
            value = su.get("value", "")

            if state in x.UNTRANSLATED_STATES:
                n_untranslated += 1
                warnings.append(f"[{state}] key={key!r} path=({var_type},{var_key})")
            elif state == "translated":
                n_translated += 1

            if not value:
                n_empty += 1
                warnings.append(f"[value rỗng] key={key!r} path=({var_type},{var_key})")

            # Đối chiếu placeholder với source (nếu source có ô tương ứng).
            src_val = source_units.get((var_type, var_key))
            if src_val is not None and value:
                if _placeholder_multiset(src_val) != _placeholder_multiset(value):
                    n_placeholder_mismatch += 1
                    warnings.append(
                        f"[placeholder lệch] key={key!r} path=({var_type},{var_key})\n"
                        f"    source: {src_val!r}\n"
                        f"    dịch  : {value!r}"
                    )

    stats = {
        "translated": n_translated,
        "untranslated": n_untranslated,
        "empty": n_empty,
        "placeholder_mismatch": n_placeholder_mismatch,
    }
    return warnings, stats


def main(argv):
    # --- Kiểm tra tham số ---
    if len(argv) != 4:
        print(__doc__)
        print("LỖI: cần đúng 3 tham số.", file=sys.stderr)
        return 2

    original_path, merged_path, langs_raw = argv[1], argv[2], argv[3]

    # --- Bước 1: JSON hợp lệ ---
    original, err1 = check_json_valid(original_path)
    if err1:
        print(f"[FAIL] File gốc: {err1}")
        return 2
    merged, err2 = check_json_valid(merged_path)
    if err2:
        print(f"[FAIL] File merge: {err2}")
        return 2
    print("[OK] Cả hai file đều là JSON hợp lệ.")

    # --- Validate danh sách ngôn ngữ cần verify ---
    source_lang = original.get("sourceLanguage", "en")
    target_langs, warnings_lang = x.validate_languages(langs_raw.split(","), source_lang)
    for w in warnings_lang:
        print(f"CẢNH BÁO: {w}")
    if not target_langs:
        print("LỖI: không còn ngôn ngữ hợp lệ nào để verify.", file=sys.stderr)
        return 2

    # --- Bước 2: format được bảo toàn (kiểm tra chung 1 lần cho mọi ngôn ngữ) ---
    fmt_problems = check_format_preserved(original, merged, target_langs)
    if fmt_problems:
        print("[FAIL] Format KHÔNG được bảo toàn:")
        for p in fmt_problems:
            print("  " + p)
        format_ok = False
    else:
        print("[OK] Format được bảo toàn: chỉ phần dịch (các) ngôn ngữ đích thay đổi.")
        format_ok = True

    # --- Bước 3: chất lượng bản dịch, RIÊNG cho từng ngôn ngữ ---
    stats_by_lang = {}
    warnings_by_lang = {}
    for lang in target_langs:
        warnings, stats = check_translations(merged, lang)
        stats_by_lang[lang] = stats
        warnings_by_lang[lang] = warnings

    print("\n--- Thống kê bản dịch theo ngôn ngữ ---")
    header = f"  {'lang':<8}{'translated':>12}{'new/review':>12}{'empty':>8}{'placeholder lệch':>18}"
    print(header)
    for lang in target_langs:
        s = stats_by_lang[lang]
        print(
            f"  {lang:<8}{s['translated']:>12}{s['untranslated']:>12}"
            f"{s['empty']:>8}{s['placeholder_mismatch']:>18}"
        )

    for lang in target_langs:
        w = warnings_by_lang[lang]
        if w:
            print(f"\n--- Cảnh báo chi tiết [{lang}] (tối đa 30 dòng) ---")
            for line in w[:30]:
                print("  " + line)
            if len(w) > 30:
                print(f"  ... và {len(w) - 30} cảnh báo khác.")

    # --- Kết luận: fail nếu format hỏng hoặc có placeholder lệch ở BẤT KỲ ngôn ngữ nào ---
    total_placeholder_mismatch = sum(s["placeholder_mismatch"] for s in stats_by_lang.values())
    critical = (not format_ok) or (total_placeholder_mismatch > 0)
    if critical:
        print("\n[KẾT LUẬN] Có lỗi NGHIÊM TRỌNG cần xử lý trước khi dùng file.")
        return 1
    print("\n[KẾT LUẬN] File hợp lệ. Có thể đưa vào Xcode.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
