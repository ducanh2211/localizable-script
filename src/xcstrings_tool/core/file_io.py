"""File I/O and tree traversing operations for .xcstrings files."""

import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence, Tuple, Union

from .models import UNTRANSLATED_STATES, format_variant


def load(path: Union[str, Path]) -> Dict[str, Any]:
    """Đọc file .xcstrings và trả về dict Python giữ nguyên thứ tự insertion."""
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def iter_units(localization: Dict[str, Any]) -> Generator[Tuple[str, str, Dict[str, Any]], None, None]:
    """Duyệt mọi `stringUnit` bên trong một localization (dữ liệu của MỘT ngôn ngữ).

    Sinh ra tuple: (variation_type, variation_key, string_unit_dict)
    - variation_type = "", variation_key = "" cho chuỗi đơn giản
    - variation_type = "plural", variation_key = "one"/"other"/... cho plural
    - variation_type = "device", variation_key = "iphone"/... cho device
    """
    # Dạng chuỗi đơn giản
    if "stringUnit" in localization:
        yield ("", "", localization["stringUnit"])

    # Dạng variations
    variations = localization.get("variations", {})
    for var_type, var_dict in variations.items():
        for var_key, leaf in var_dict.items():
            if isinstance(leaf, dict) and "stringUnit" in leaf:
                yield (var_type, var_key, leaf["stringUnit"])


def is_untranslated_unit(string_unit: Dict[str, Any]) -> bool:
    """Kiểm tra một stringUnit có thuộc trạng thái chưa dịch (new/needs_review) hay không."""
    return string_unit.get("state") in UNTRANSLATED_STATES


def get_source_value(entry: Dict[str, Any], source_lang: str) -> str:
    """Lấy giá trị nguồn của một entry để làm ngữ cảnh."""
    loc = entry.get("localizations", {}).get(source_lang, {})
    su = loc.get("stringUnit")
    if su:
        return su.get("value", "")
    return ""


def get_existing_unit(
    entry: Dict[str, Any], lang: str, var_type: str, var_key: str
) -> Tuple[Optional[str], Optional[str]]:
    """Tra cứu (không mutate) giá trị và state hiện có tại đúng path (var_type, var_key)."""
    loc = entry.get("localizations", {}).get(lang)
    if not loc:
        return None, None
    for vt, vk, su in iter_units(loc):
        if (vt, vk) == (var_type, var_key):
            return su.get("value", ""), su.get("state", "")
    return None, None


def iter_rows_for_key(
    key: str, entry: Dict[str, Any], source_lang: str, target_lang: str
) -> List[Dict[str, Any]]:
    """Sinh ra danh sách các row (dict) mô tả từng ô dịch của entry theo Long-format."""
    localizations = entry.get("localizations", {})
    source_loc = localizations.get(source_lang, {})
    target_loc = localizations.get(target_lang, {})

    source_units = {}
    for var_type, var_key, su in iter_units(source_loc):
        source_units[(var_type, var_key)] = su.get("value", "")
    if ("", "") not in source_units:
        source_units[("", "")] = key

    target_units = {}
    for var_type, var_key, su in iter_units(target_loc):
        target_units[(var_type, var_key)] = (su.get("value", ""), su.get("state", ""))

    all_paths = set(source_units.keys()) | set(target_units.keys())
    if not all_paths:
        all_paths = {("", "")}

    rows = []
    for (var_type, var_key) in sorted(all_paths):
        src_val = source_units.get((var_type, var_key), "")
        tgt_val, tgt_state = target_units.get((var_type, var_key), ("", ""))
        rows.append({
            "key": key,
            "language": target_lang,
            "variation_type": var_type,
            "variation_key": var_key,
            "variant": format_variant(var_type, var_key),
            "source_value": src_val,
            "target_value": tgt_val,
            "state": tgt_state,
        })
    return rows


def iter_rows_for_key_wide(
    key: str, entry: Dict[str, Any], source_lang: str, target_langs: Sequence[str]
) -> List[Dict[str, Any]]:
    """Sinh ra danh sách các row (dict) mô tả từng ô dịch của entry theo Wide-format."""
    localizations = entry.get("localizations", {})
    source_loc = localizations.get(source_lang, {})

    source_units = {}
    for var_type, var_key, su in iter_units(source_loc):
        source_units[(var_type, var_key)] = su.get("value", "")
    if ("", "") not in source_units:
        source_units[("", "")] = key

    units_by_lang = {}
    for lang in target_langs:
        loc = localizations.get(lang, {})
        units = {}
        for var_type, var_key, su in iter_units(loc):
            units[(var_type, var_key)] = (su.get("value", ""), su.get("state", ""))
        units_by_lang[lang] = units

    all_paths = set(source_units.keys())
    for units in units_by_lang.values():
        all_paths |= set(units.keys())
    if not all_paths:
        all_paths = {("", "")}

    rows = []
    for (var_type, var_key) in sorted(all_paths):
        row = {
            "key": key,
            "variation_type": var_type,
            "variation_key": var_key,
            "variant": format_variant(var_type, var_key),
            "source_value": source_units.get((var_type, var_key), ""),
        }
        for lang in target_langs:
            value, state = units_by_lang[lang].get((var_type, var_key), ("", ""))
            row[f"{lang}_target"] = value
            row[f"{lang}_state"] = state
        rows.append(row)
    return rows


def row_is_untranslated(row: Dict[str, Any], entry: Dict[str, Any], target_lang: str) -> bool:
    """Kiểm tra row long-format có chưa dịch hoặc needs_review hay không."""
    localizations = entry.get("localizations", {})
    target_loc = localizations.get(target_lang)
    if not target_loc:
        return True

    want = (row["variation_type"], row["variation_key"])
    for var_type, var_key, su in iter_units(target_loc):
        if (var_type, var_key) == want:
            if is_untranslated_unit(su) or not su.get("value"):
                return True
            return False
    return True


def path_is_untranslated(entry: Dict[str, Any], target_lang: str, var_type: str, var_key: str) -> bool:
    """Kiểm tra path cụ thể (var_type, var_key) của ngôn ngữ đích có chưa dịch hay không."""
    localizations = entry.get("localizations", {})
    target_loc = localizations.get(target_lang)
    if not target_loc:
        return True
    for vt, vk, su in iter_units(target_loc):
        if (vt, vk) == (var_type, var_key):
            return is_untranslated_unit(su) or not su.get("value")
    return True
