"""Constants, data models, and format helpers for xcstrings."""

from typing import List, Tuple, Sequence

# Trạng thái trong Xcode được coi là chưa hoàn thành dịch (cần dịch lại/review)
UNTRANSLATED_STATES = {"new", "needs_review"}

# Thứ tự cột chuẩn cho CSV Long-format
CSV_FIELDS = [
    "key",
    "variant",
    "source_value",
    "target_value",
]


def format_variant(var_type: str, var_key: str) -> str:
    """Gộp (variation_type, variation_key) thành cột 'variant' (vd: plural.one, device.iphone)."""
    if not var_type:
        return ""
    return f"{var_type}.{var_key}"


def parse_variant(variant: str) -> Tuple[str, str]:
    """Tách cột 'variant' thành tuple (variation_type, variation_key)."""
    variant = (variant or "").strip()
    if not variant:
        return "", ""
    var_type, _, var_key = variant.partition(".")
    return var_type, var_key


def validate_languages(languages: Sequence[str], source_lang: str) -> Tuple[List[str], List[str]]:
    """Chuẩn hóa và validate danh sách ngôn ngữ đích.

    - Loại bỏ chuỗi rỗng.
    - Loại bỏ ngôn ngữ trùng với source_lang.
    - Loại bỏ ngôn ngữ lặp lại, giữ nguyên thứ tự xuất hiện đầu tiên.
    """
    warnings: List[str] = []
    seen = set()
    clean: List[str] = []
    for raw in languages:
        lang = raw.strip()
        if not lang:
            continue
        if lang == source_lang:
            warnings.append(f"Bỏ qua '{lang}': trùng ngôn ngữ nguồn ({source_lang}).")
            continue
        if lang in seen:
            warnings.append(f"Bỏ qua '{lang}': bị lặp trong danh sách ngôn ngữ.")
            continue
        seen.add(lang)
        clean.append(lang)
    return clean, warnings


def wide_csv_fields(target_langs: Sequence[str]) -> List[str]:
    """Tạo danh sách cột CSV cho wide-format: [key, variant, source_value, {lang}_target, ...]."""
    fields = ["key", "variant", "source_value"]
    for lang in target_langs:
        fields.append(f"{lang}_target")
    return fields
