"""Service to verify and validate .xcstrings files."""

import copy
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ..core import UNTRANSLATED_STATES, dumps, iter_units, load, validate_languages

# Regex khớp các placeholder định dạng chuỗi Cocoa/iOS (%@, %d, %lld, %1$@, %2$lld, %% ...)
PLACEHOLDER_RE = re.compile(
    r"%(?:\d+\$)?[-+ 0#]?\d*(?:\.\d+)?(?:ll|l|h|hh|q|z|t|j|L)?[@diouxXeEfgGaAcsSp%]"
)


def _placeholder_multiset(text: str) -> List[str]:
    """Trả về danh sách placeholder đã sắp xếp trong một chuỗi (bỏ qua %% literal)."""
    found = [p for p in PLACEHOLDER_RE.findall(text) if p != "%%"]
    return sorted(found)


def check_json_valid(path: Union[str, Path]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Kiểm tra file có parse được JSON không."""
    try:
        data = load(path)
        return data, None
    except Exception as e:
        return None, f"File không phải JSON hợp lệ: {e}"


def check_format_preserved(
    original_data: Dict[str, Any], merged_data: Dict[str, Any], target_langs: Sequence[str]
) -> List[str]:
    """Kiểm tra format và dữ liệu ngoài các target_langs có được giữ nguyên 100% không."""
    def strip_targets(data: Dict[str, Any]) -> Dict[str, Any]:
        d = copy.deepcopy(data)
        for entry in d.get("strings", {}).values():
            loc = entry.get("localizations")
            if loc:
                for lang in target_langs:
                    if lang in loc:
                        del loc[lang]
                if not loc:
                    del entry["localizations"]
        return d

    problems: List[str] = []
    a = dumps(strip_targets(original_data))
    b = dumps(strip_targets(merged_data))

    if a != b:
        problems.append(
            "Khác biệt NGOÀI phần dịch ngôn ngữ đích được phát hiện "
            "(format hoặc nội dung khác đã bị thay đổi)."
        )
        for i, (ca, cb) in enumerate(zip(a, b)):
            if ca != cb:
                problems.append(f"  Khác đầu tiên tại ký tự thứ {i}:")
                problems.append(f"    gốc  : {a[max(0, i-30):i+30]!r}")
                problems.append(f"    merge: {b[max(0, i-30):i+30]!r}")
                break
    return problems


def check_translations(
    merged_data: Dict[str, Any], target_lang: str
) -> Tuple[List[str], Dict[str, int]]:
    """Kiểm tra chất lượng bản dịch (chuỗi rỗng, needs_review, lệch placeholder) của 1 ngôn ngữ."""
    warnings: List[str] = []
    source_lang = merged_data.get("sourceLanguage", "en")
    strings = merged_data.get("strings", {})

    n_untranslated = 0
    n_empty = 0
    n_placeholder_mismatch = 0
    n_translated = 0

    for key, entry in strings.items():
        loc = entry.get("localizations", {})
        target_loc = loc.get(target_lang)
        source_loc = loc.get(source_lang, {})
        if not target_loc:
            continue

        source_units = {(t, k): su.get("value", "") for t, k, su in iter_units(source_loc)}
        if ("", "") not in source_units:
            source_units[("", "")] = key

        for var_type, var_key, su in iter_units(target_loc):
            state = su.get("state", "")
            value = su.get("value", "")

            if state in UNTRANSLATED_STATES:
                n_untranslated += 1
                warnings.append(f"[{state}] key={key!r} path=({var_type},{var_key})")
            elif state == "translated":
                n_translated += 1

            if not value:
                n_empty += 1
                warnings.append(f"[value rỗng] key={key!r} path=({var_type},{var_key})")

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


def verify_files(
    original_path: Union[str, Path],
    merged_path: Union[str, Path],
    target_langs: Sequence[str],
) -> Dict[str, Any]:
    """Hàm tổng hợp kiểm tra 2 file .xcstrings."""
    original_data, err1 = check_json_valid(original_path)
    if err1:
        return {"valid": False, "error": f"File gốc không hợp lệ: {err1}"}

    merged_data, err2 = check_json_valid(merged_path)
    if err2:
        return {"valid": False, "error": f"File merge không hợp lệ: {err2}"}

    source_lang = original_data.get("sourceLanguage", "en")
    clean_langs, warnings_lang = validate_languages(target_langs, source_lang)

    format_problems = check_format_preserved(original_data, merged_data, clean_langs)
    format_ok = len(format_problems) == 0

    stats_by_lang = {}
    warnings_by_lang = {}
    for lang in clean_langs:
        warnings, stats = check_translations(merged_data, lang)
        stats_by_lang[lang] = stats
        warnings_by_lang[lang] = warnings

    total_placeholder_mismatch = sum(s["placeholder_mismatch"] for s in stats_by_lang.values())
    critical_error = (not format_ok) or (total_placeholder_mismatch > 0)

    return {
        "valid": not critical_error,
        "format_ok": format_ok,
        "format_problems": format_problems,
        "stats_by_lang": stats_by_lang,
        "warnings_by_lang": warnings_by_lang,
        "clean_langs": clean_langs,
    }
