"""xcstrings_tool: Python toolkit for Xcode String Catalog (.xcstrings) localization."""

__version__ = "1.0.0"

from .core import (
    load,
    dump,
    dumps,
    UNTRANSLATED_STATES,
    CSV_FIELDS,
    format_variant,
    parse_variant,
    validate_languages,
    wide_csv_fields,
)
from .services import (
    export_all_rows,
    export_untranslated_rows,
    export_to_csv,
    merge_translations,
    verify_files,
    AITranslator,
    AIProvider,
)

__all__ = [
    "__version__",
    "load",
    "dump",
    "dumps",
    "UNTRANSLATED_STATES",
    "CSV_FIELDS",
    "format_variant",
    "parse_variant",
    "validate_languages",
    "wide_csv_fields",
    "export_all_rows",
    "export_untranslated_rows",
    "export_to_csv",
    "merge_translations",
    "verify_files",
    "AITranslator",
    "AIProvider",
]
