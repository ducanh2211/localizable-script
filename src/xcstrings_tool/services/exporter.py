"""Service to export localization rows to CSV files."""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ..core import (
    CSV_FIELDS,
    iter_rows_for_key,
    iter_rows_for_key_wide,
    load,
    path_is_untranslated,
    row_is_untranslated,
    validate_languages,
    wide_csv_fields,
)


def export_all_rows(
    data: Dict[str, Any], target_langs: Sequence[str], mode: str = "long"
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Xuất toàn bộ rows (đã dịch + chưa dịch).

    Trả về (rows, fieldnames).
    """
    source_lang = data.get("sourceLanguage", "en")
    strings = data.get("strings", {})
    all_rows: List[Dict[str, Any]] = []

    if mode == "wide":
        clean_langs, _ = validate_languages(target_langs, source_lang)
        for key, entry in strings.items():
            rows = iter_rows_for_key_wide(key, entry, source_lang, clean_langs)
            all_rows.extend(rows)
        fieldnames = wide_csv_fields(clean_langs)
    else:
        target_lang = target_langs[0] if target_langs else "vi"
        for key, entry in strings.items():
            rows = iter_rows_for_key(key, entry, source_lang, target_lang)
            all_rows.extend(rows)
        fieldnames = CSV_FIELDS

    return all_rows, fieldnames


def export_untranslated_rows(
    data: Dict[str, Any], target_langs: Sequence[str], mode: str = "long"
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Xuất chỉ những rows chưa dịch (hoặc needs_review).

    Với wide-format, áp dụng OR-rule: thiếu ở ít nhất 1 ngôn ngữ đích.
    Trả về (rows, fieldnames).
    """
    source_lang = data.get("sourceLanguage", "en")
    strings = data.get("strings", {})
    untranslated_rows: List[Dict[str, Any]] = []

    if mode == "wide":
        clean_langs, _ = validate_languages(target_langs, source_lang)
        for key, entry in strings.items():
            for row in iter_rows_for_key_wide(key, entry, source_lang, clean_langs):
                include = any(
                    path_is_untranslated(entry, lang, row["variation_type"], row["variation_key"])
                    for lang in clean_langs
                )
                if include:
                    untranslated_rows.append(row)
        fieldnames = wide_csv_fields(clean_langs)
    else:
        target_lang = target_langs[0] if target_langs else "vi"
        for key, entry in strings.items():
            for row in iter_rows_for_key(key, entry, source_lang, target_lang):
                if row_is_untranslated(row, entry, target_lang):
                    untranslated_rows.append(row)
        fieldnames = CSV_FIELDS

    return untranslated_rows, fieldnames


def export_to_csv(
    input_xcstrings: Union[str, Path],
    output_csv: Union[str, Path],
    target_langs: Sequence[str],
    untranslated_only: bool = False,
    mode: str = "long",
) -> Dict[str, Any]:
    """Hàm tổng hợp đọc .xcstrings và ghi ra file CSV."""
    data = load(input_xcstrings)
    source_lang = data.get("sourceLanguage", "en")

    if untranslated_only:
        rows, fieldnames = export_untranslated_rows(data, target_langs, mode=mode)
    else:
        rows, fieldnames = export_all_rows(data, target_langs, mode=mode)

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return {
        "count": len(rows),
        "source_lang": source_lang,
        "target_langs": target_langs,
        "mode": mode,
        "output_csv": str(output_csv),
    }
