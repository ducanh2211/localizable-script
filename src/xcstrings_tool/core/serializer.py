"""Custom JSON Serializer for Xcode String Catalog (.xcstrings).

Matches Xcode's formatting conventions:
- Indent: 2 spaces.
- Key-value separator: " : " (spaces on both sides of colon).
- Empty dict / list formatting with newline and indent.
- ensure_ascii = False (Unicode unescaped).
- No trailing newline at EOF.
- Preserves key order from dict (no re-sorting).
"""

import json
from pathlib import Path
from typing import Any, Union


def _serialize(obj: Any, indent_level: int = 0) -> str:
    r"""Serialize Python objects to JSON string following Xcode conventions."""
    pad = "  " * indent_level
    pad_close = "  " * (indent_level - 1) if indent_level > 0 else ""

    # --- dict ---
    if isinstance(obj, dict):
        if not obj:
            return "{\n\n" + ("  " * indent_level) + "}"

        parts = []
        for key, value in obj.items():
            key_str = json.dumps(key, ensure_ascii=False)
            val_str = _serialize(value, indent_level + 1)
            parts.append(f"{pad}  {key_str} : {val_str}")
        inner = ",\n".join(parts)
        return "{\n" + inner + "\n" + pad + "}"

    # --- list ---
    if isinstance(obj, list):
        if not obj:
            return "[\n\n" + ("  " * indent_level) + "]"
        parts = []
        for item in obj:
            parts.append(f"{pad}  " + _serialize(item, indent_level + 1))
        inner = ",\n".join(parts)
        return "[\n" + inner + "\n" + pad + "]"

    # --- scalar (str, int, float, bool, None) ---
    return json.dumps(obj, ensure_ascii=False)


def dumps(data: Any) -> str:
    """Convert dict data into a JSON string formatted according to Xcode conventions."""
    return _serialize(data, 0)


def dump(data: Any, path: Union[str, Path]) -> None:
    """Write dict data to a file formatted according to Xcode conventions."""
    Path(path).write_text(dumps(data), encoding="utf-8")
