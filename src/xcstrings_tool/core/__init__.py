"""Core engine and models for Xcode String Catalog (.xcstrings) processing."""

from .serializer import dumps, dump
from .models import (
    UNTRANSLATED_STATES,
    CSV_FIELDS,
    format_variant,
    parse_variant,
    validate_languages,
    wide_csv_fields,
)
from .file_io import (
    load,
    iter_units,
    is_untranslated_unit,
    get_source_value,
    get_existing_unit,
    iter_rows_for_key,
    iter_rows_for_key_wide,
    row_is_untranslated,
    path_is_untranslated,
)

__all__ = [
    "dumps",
    "dump",
    "UNTRANSLATED_STATES",
    "CSV_FIELDS",
    "format_variant",
    "parse_variant",
    "validate_languages",
    "wide_csv_fields",
    "load",
    "iter_units",
    "is_untranslated_unit",
    "get_source_value",
    "get_existing_unit",
    "iter_rows_for_key",
    "iter_rows_for_key_wide",
    "row_is_untranslated",
    "path_is_untranslated",
]
