"""Service to merge translated CSV into .xcstrings data."""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from ..core import dump, get_existing_unit, load, parse_variant


def _ensure_string_unit(
    entry: Dict[str, Any], target_lang: str, var_type: str, var_key: str
) -> Dict[str, Any]:
    """Trả về (và nếu chưa có thì tạo) dict stringUnit tương ứng với path."""
    localizations = entry.setdefault("localizations", {})
    target_loc = localizations.setdefault(target_lang, {})

    if var_type == "":
        return target_loc.setdefault("stringUnit", {})
    else:
        variations = target_loc.setdefault("variations", {})
        type_dict = variations.setdefault(var_type, {})
        leaf = type_dict.setdefault(var_key, {})
        return leaf.setdefault("stringUnit", {})


def _detect_mode(fieldnames: Optional[Sequence[str]]) -> Optional[str]:
    """Tự động nhận diện định dạng CSV long/wide từ fieldnames."""
    fieldnames = fieldnames or []
    if "target_value" in fieldnames:
        return "long"
    if any(f.endswith("_target") for f in fieldnames):
        return "wide"
    return None


def merge_long(
    data: Dict[str, Any], rows: Sequence[Dict[str, Any]], target_lang: str
) -> Dict[str, Any]:
    """Merge danh sách row theo định dạng long-format."""
    strings = data.get("strings", {})
    merged_count = 0
    skipped_empty = 0
    missing_keys: List[str] = []

    for row in rows:
        target_value = (row.get("target_value") or "").strip()
        if not target_value:
            skipped_empty += 1
            continue

        key = row.get("key", "")
        var_type, var_key = parse_variant(row.get("variant", ""))

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
        "target_langs": [target_lang],
        "merged_count": {target_lang: merged_count},
        "skipped_empty": {target_lang: skipped_empty},
        "skipped_unchanged": {target_lang: 0},
        "missing_keys": missing_keys,
        "changes": [],
    }


def merge_wide(
    data: Dict[str, Any], rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]
) -> Dict[str, Any]:
    """Merge danh sách row theo định dạng wide-format."""
    strings = data.get("strings", {})
    target_langs = sorted({f[:-len("_target")] for f in fieldnames if f.endswith("_target")})

    merged_count = {lang: 0 for lang in target_langs}
    skipped_empty = {lang: 0 for lang in target_langs}
    skipped_unchanged = {lang: 0 for lang in target_langs}
    missing_keys: List[str] = []
    changes: List[Dict[str, Any]] = []

    for row in rows:
        key = row.get("key", "")
        var_type, var_key = parse_variant(row.get("variant", ""))

        entry = strings.get(key)
        if entry is None:
            missing_keys.append(key)
            continue

        for lang in target_langs:
            col = f"{lang}_target"
            if col not in row:
                continue

            csv_value = (row.get(col) or "").strip()
            if not csv_value:
                skipped_empty[lang] += 1
                continue

            existing_value, existing_state = get_existing_unit(entry, lang, var_type, var_key)
            existing_value_norm = (existing_value or "").strip()

            unchanged = csv_value == existing_value_norm
            if unchanged and existing_state != "needs_review":
                skipped_unchanged[lang] += 1
                continue

            su = _ensure_string_unit(entry, lang, var_type, var_key)
            su["state"] = "translated"
            su["value"] = csv_value
            merged_count[lang] += 1
            changes.append({
                "key": key,
                "var_type": var_type,
                "var_key": var_key,
                "lang": lang,
                "old": existing_value,
                "new": csv_value,
            })

    return {
        "mode": "wide",
        "target_langs": target_langs,
        "merged_count": merged_count,
        "skipped_empty": skipped_empty,
        "skipped_unchanged": skipped_unchanged,
        "missing_keys": missing_keys,
        "changes": changes,
    }


def merge_translations(
    input_xcstrings: Union[str, Path],
    csv_source: Union[str, Path, Sequence[Dict[str, Any]]],
    target_lang: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
    in_place: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Hàm merge cấp cao hỗ trợ cả file path và in-memory rows."""
    data = load(input_xcstrings)

    if isinstance(csv_source, (str, Path)):
        with open(csv_source, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    else:
        rows = list(csv_source)
        fieldnames = list(rows[0].keys()) if rows else []

    mode = _detect_mode(fieldnames)
    if not mode:
        raise ValueError(f"Không nhận diện được định dạng CSV từ header: {fieldnames}")

    if mode == "long":
        if not target_lang:
            raise ValueError("Chế độ Long-format cần cung cấp target_lang.")
        report = merge_long(data, rows, target_lang)
    else:
        report = merge_wide(data, rows, fieldnames)

    # Xác định output path
    src = Path(input_xcstrings)
    if in_place:
        # Tạo bản sao lưu backup .bak nếu ghi đè
        backup_path = src.with_suffix(src.suffix + ".bak")
        if not dry_run:
            backup_path.write_bytes(src.read_bytes())
        out_file = src
    elif output_path:
        out_file = Path(output_path)
    else:
        out_file = src.with_name(f"{src.stem}.merged{src.suffix}")

    if not dry_run:
        dump(data, out_file)

    report["output_path"] = str(out_file)
    report["dry_run"] = dry_run
    report["data"] = data
    return report
