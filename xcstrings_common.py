r"""
xcstrings_common.py
===================

Module dùng chung cho toàn bộ workflow localization file `.xcstrings`
(Xcode String Catalog).

Nhiệm vụ chính:
  1. Load file `.xcstrings` (là JSON) -> dict Python, GIỮ NGUYÊN thứ tự key.
  2. Serialize dict trở lại chuỗi theo ĐÚNG quy ước ghi file của Xcode,
     để khi merge chỉ có phần bản dịch thay đổi, tránh git diff nhiễu.
  3. Duyệt đệ quy mọi `stringUnit` bên trong một entry, xử lý an toàn cả
     3 dạng cấu trúc: chuỗi đơn giản, plural variations, device variations.
  4. Định nghĩa thế nào là "chưa được dịch".

Quy ước format của Xcode (đã dò trực tiếp từ file thật):
  - Indent: 2 space.
  - Separator giữa key và value: " : "  (CÓ space cả hai bên dấu hai chấm).
    (Python mặc định dùng ": " nên phải override.)
  - Object rỗng {} được Xcode ghi thành "{\n\n    }" (xuống dòng + dòng trống).
  - ensure_ascii = False (giữ nguyên ký tự Unicode, không escape \uXXXX).
  - KHÔNG có newline ở cuối file.
  - Thứ tự key: Xcode dùng sort locale-aware, KHÁC với sort theo codepoint
    của Python. => Ta KHÔNG re-sort; giữ nguyên thứ tự insertion đọc từ file
    gốc. Vì merge chỉ chỉnh giá trị của key đã tồn tại nên thứ tự được bảo toàn.
"""

import json
from pathlib import Path

# Các state của Xcode bị coi là "chưa dịch xong" (cần dịch lại / review).
# "new"          -> string vừa được trích xuất, chưa dịch.
# "needs_review" -> đã có bản dịch nhưng source thay đổi, cần xem lại.
UNTRANSLATED_STATES = {"new", "needs_review"}


def load(path):
    """
    Đọc file .xcstrings và trả về dict Python.

    Dùng json.loads (không phải json.load) để có toàn quyền kiểm soát,
    nhưng quan trọng là dict của Python 3.7+ giữ nguyên thứ tự chèn,
    nên thứ tự key gốc trong file được bảo toàn.
    """
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def _serialize(obj, indent_level=0):
    r"""
    Serialize đệ quy một object Python (dict/list/str/số/bool/None) thành
    chuỗi JSON khớp CHÍNH XÁC quy ước ghi file của Xcode.

    Đây là hàm cốt lõi đảm bảo yêu cầu "giữ nguyên format file gốc".
    Không dùng json.dumps trực tiếp vì json.dumps không tạo được:
      - separator " : "
      - object rỗng dạng "{\n\n    }"

    Tham số:
      obj          : object cần serialize.
      indent_level : độ sâu thụt lề hiện tại (mỗi cấp = 2 space).

    Trả về: chuỗi JSON của obj (không kèm indent của chính dòng mở đầu;
             phần indent mở đầu do hàm gọi cha chịu trách nhiệm).
    """
    pad = "  " * indent_level          # indent cho các phần tử con
    pad_close = "  " * (indent_level - 1) if indent_level > 0 else ""

    # --- dict ---
    if isinstance(obj, dict):
        # Object rỗng: Xcode ghi thành "{\n\n    }" -- một dòng trống rồi
        # đóng ngoặc thụt vào bằng (indent_level) * 2 space.
        if not obj:
            # closing brace của object rỗng thụt vào bằng indent_level hiện tại
            return "{\n\n" + ("  " * indent_level) + "}"

        parts = []
        for key, value in obj.items():                 # giữ nguyên thứ tự
            key_str = json.dumps(key, ensure_ascii=False)   # escape key đúng chuẩn
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
    # json.dumps xử lý escape chuỗi và literal true/false/null đúng chuẩn.
    return json.dumps(obj, ensure_ascii=False)


def dumps(data):
    """
    Chuyển dict .xcstrings thành chuỗi theo đúng format Xcode.
    KHÔNG kèm newline ở cuối (Xcode không ghi newline cuối file).
    """
    return _serialize(data, 0)


def dump(data, path):
    """Ghi dict .xcstrings ra file theo đúng format Xcode."""
    Path(path).write_text(dumps(data), encoding="utf-8")


def iter_units(localization):
    """
    Duyệt mọi `stringUnit` bên trong một localization (dữ liệu của MỘT ngôn ngữ).

    Một localization có thể có 3 dạng:
      (A) stringUnit trực tiếp:
            { "stringUnit": { "state": ..., "value": ... } }
      (B) plural variations:
            { "variations": { "plural": { "one": {"stringUnit": ...},
                                          "other": {"stringUnit": ...} } } }
      (C) device variations:
            { "variations": { "device": { "iphone": {"stringUnit": ...}, ... } } }

    Sinh ra (yield) tuple: (variation_type, variation_key, string_unit_dict)
      - variation_type = ""      , variation_key = ""       cho dạng (A).
      - variation_type = "plural", variation_key = "one"/"other"/... cho (B).
      - variation_type = "device", variation_key = "iphone"/... cho (C).

    string_unit_dict là tham chiếu TRỰC TIẾP tới dict con trong data, nên
    chỉnh sửa nó sẽ chỉnh trực tiếp vào cây dữ liệu (dùng khi merge).
    """
    # Dạng (A): stringUnit trực tiếp
    if "stringUnit" in localization:
        yield ("", "", localization["stringUnit"])

    # Dạng (B) & (C): variations
    variations = localization.get("variations", {})
    for var_type, var_dict in variations.items():          # "plural" hoặc "device"
        for var_key, leaf in var_dict.items():             # "one"/"other"/"iphone"...
            if isinstance(leaf, dict) and "stringUnit" in leaf:
                yield (var_type, var_key, leaf["stringUnit"])


def is_untranslated_unit(string_unit):
    """
    Một stringUnit được coi là chưa dịch nếu state của nó nằm trong
    UNTRANSLATED_STATES ("new" / "needs_review").
    """
    return string_unit.get("state") in UNTRANSLATED_STATES


def get_source_value(entry, source_lang):
    """
    Lấy giá trị nguồn (source) của một entry để làm ngữ cảnh khi dịch.
    Trả về value của stringUnit đơn giản ở ngôn ngữ nguồn, hoặc "" nếu không có.
    (Với plural/device thì source value được lấy riêng theo từng variation
     trong hàm iter_rows_for_key.)
    """
    loc = entry.get("localizations", {}).get(source_lang, {})
    su = loc.get("stringUnit")
    if su:
        return su.get("value", "")
    return ""


def iter_rows_for_key(key, entry, source_lang, target_lang):
    """
    Sinh ra các "row" (dict) mô tả từng ô dịch của một entry, dùng cho CSV.

    Với mỗi stringUnit ở NGÔN NGỮ ĐÍCH (hoặc nếu chưa có ngôn ngữ đích thì
    dựa trên cấu trúc của ngôn ngữ nguồn), tạo một row gồm:
      key            : key gốc trong .xcstrings (định danh entry).
      language       : ngôn ngữ đích.
      variation_type : ""/"plural"/"device" -- để merge định vị chính xác.
      variation_key  : ""/"one"/"iphone"... -- kết hợp với type thành "path".
      source_value   : giá trị nguồn tương ứng (giúp người/AI dịch có ngữ cảnh).
      target_value   : giá trị đích hiện tại (rỗng nếu chưa dịch) -- chỗ điền.
      state          : state hiện tại của bản dịch đích ("" nếu chưa có).

    Logic chọn "khung" variation:
      - Ưu tiên cấu trúc của ngôn ngữ nguồn (source) làm chuẩn, vì source
        luôn tồn tại và định nghĩa các variation cần dịch.
      - Nếu source không có localization (một số entry rỗng), thử lấy từ đích.
    """
    localizations = entry.get("localizations", {})
    source_loc = localizations.get(source_lang, {})
    target_loc = localizations.get(target_lang, {})

    # Lập map cấu trúc từ source: {(var_type, var_key): source_value}
    source_units = {}
    for var_type, var_key, su in iter_units(source_loc):
        source_units[(var_type, var_key)] = su.get("value", "")
    # Fallback: nếu entry không lưu localization nguồn (key trùng chuỗi nguồn),
    # dùng chính key làm source value cho ô chuỗi đơn giản, để CSV có ngữ cảnh.
    if ("", "") not in source_units:
        source_units[("", "")] = key

    # Lập map cấu trúc từ target hiện có: {(var_type, var_key): (value, state)}
    target_units = {}
    for var_type, var_key, su in iter_units(target_loc):
        target_units[(var_type, var_key)] = (su.get("value", ""), su.get("state", ""))

    # Tập các "path" cần xuất: hợp của source và target.
    # Nếu entry hoàn toàn rỗng (không source không target), vẫn xuất 1 row
    # đơn giản để người dùng biết key này tồn tại.
    all_paths = set(source_units.keys()) | set(target_units.keys())
    if not all_paths:
        all_paths = {("", "")}

    rows = []
    # Sắp path theo thứ tự ổn định để CSV nhất quán giữa các lần chạy.
    for (var_type, var_key) in sorted(all_paths):
        src_val = source_units.get((var_type, var_key), "")
        tgt_val, tgt_state = target_units.get((var_type, var_key), ("", ""))
        rows.append({
            "key": key,
            "language": target_lang,
            "variation_type": var_type,
            "variation_key": var_key,
            "source_value": src_val,
            "target_value": tgt_val,
            "state": tgt_state,
        })
    return rows


def row_is_untranslated(row, entry, target_lang):
    """
    Xác định một row (từ iter_rows_for_key) có "chưa dịch" hay không, theo
    ĐỊNH NGHĨA đã chốt: chưa dịch nếu THIẾU HẲN localization đích cho ô đó,
    HOẶC state của ô đó là new/needs_review.

    Tham số entry dùng để tra cứu stringUnit đích thực tế (nếu có).
    """
    localizations = entry.get("localizations", {})
    target_loc = localizations.get(target_lang)

    # Trường hợp 1: hoàn toàn chưa có localization cho ngôn ngữ đích -> chưa dịch.
    if not target_loc:
        return True

    # Tìm stringUnit đích tương ứng với path của row.
    want = (row["variation_type"], row["variation_key"])
    for var_type, var_key, su in iter_units(target_loc):
        if (var_type, var_key) == want:
            # Trường hợp 2: có ô nhưng state là new/needs_review, hoặc value rỗng.
            if is_untranslated_unit(su) or not su.get("value"):
                return True
            return False  # đã dịch và state ổn

    # Không tìm thấy ô tương ứng ở đích -> thiếu -> chưa dịch.
    return True


# Thứ tự cột chuẩn của file CSV, dùng chung cho export và merge (LONG-format).
CSV_FIELDS = [
    "key",
    "language",
    "variation_type",
    "variation_key",
    "source_value",
    "target_value",
    "state",
]


# =====================================================================
# WIDE-FORMAT (multi-language): 1 dòng CSV = 1 (key, variation_type,
# variation_key), có 2 cột {lang}_target / {lang}_state cho MỖI ngôn ngữ
# đích. Dùng khi dịch 1 key cho nhiều ngôn ngữ cùng lúc.
# Các hàm long-format ở trên giữ nguyên, không đổi hành vi.
# =====================================================================


def validate_languages(languages, source_lang):
    """
    Chuẩn hoá + validate danh sách ngôn ngữ đích cho wide-mode.

    - Loại bỏ chuỗi rỗng (do trailing comma, khoảng trắng thừa...).
    - Loại bỏ ngôn ngữ trùng source_lang (dịch nguồn sang chính nó vô nghĩa).
    - Loại bỏ ngôn ngữ bị lặp lại, chỉ giữ lần xuất hiện đầu tiên.
    - Giữ nguyên thứ tự xuất hiện đầu tiên (quyết định thứ tự cột CSV).

    Trả về (clean_list, warnings) -- warnings là list chuỗi để caller in ra;
    không tự in để giữ hàm này thuần (dễ test).
    """
    warnings = []
    seen = set()
    clean = []
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


def wide_csv_fields(target_langs):
    """Danh sách cột CSV wide-mode: 4 cột cố định + 2 cột/ngôn ngữ đích."""
    fields = ["key", "variation_type", "variation_key", "source_value"]
    for lang in target_langs:
        fields.append(f"{lang}_target")
        fields.append(f"{lang}_state")
    return fields


def iter_rows_for_key_wide(key, entry, source_lang, target_langs):
    """
    Sinh ra các row wide-format cho một entry: mỗi row ứng với một
    (variation_type, variation_key), chứa cột dịch của TẤT CẢ ngôn ngữ trong
    target_langs cùng lúc (khác iter_rows_for_key vốn xử lý 1 ngôn ngữ/row).

    "Path" cần xuất là hợp của source VÀ TẤT CẢ target_langs (không chỉ 1
    ngôn ngữ), vì các ngôn ngữ có thể có tập variation_key khác nhau (vd.
    plural rule tiếng Nga có "few"/"many" mà tiếng Anh không có) -- nếu chỉ
    lấy path theo 1 ngôn ngữ sẽ bỏ sót ô cần dịch của ngôn ngữ khác.
    """
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
            "source_value": source_units.get((var_type, var_key), ""),
        }
        for lang in target_langs:
            value, state = units_by_lang[lang].get((var_type, var_key), ("", ""))
            row[f"{lang}_target"] = value
            row[f"{lang}_state"] = state
        rows.append(row)
    return rows


def path_is_untranslated(entry, target_lang, var_type, var_key):
    """
    Giống row_is_untranslated nhưng tra thẳng theo (var_type, var_key) thay vì
    nhận cả row long-format -- dùng cho wide-mode vì 1 row phục vụ nhiều ngôn
    ngữ cùng lúc, không có "row" ứng riêng 1 ngôn ngữ để tái dùng hàm cũ.
    """
    localizations = entry.get("localizations", {})
    target_loc = localizations.get(target_lang)
    if not target_loc:
        return True
    for vt, vk, su in iter_units(target_loc):
        if (vt, vk) == (var_type, var_key):
            return is_untranslated_unit(su) or not su.get("value")
    return True


def get_existing_unit(entry, lang, var_type, var_key):
    """
    Tra (KHÔNG mutate cây dữ liệu) giá trị + state hiện có tại đúng path
    (var_type, var_key) của một ngôn ngữ -- dùng để so sánh lúc merge
    wide-mode trước khi quyết định có ghi đè hay không.

    Trả về (value, state), hoặc (None, None) nếu path đó chưa tồn tại.
    """
    loc = entry.get("localizations", {}).get(lang)
    if not loc:
        return None, None
    for vt, vk, su in iter_units(loc):
        if (vt, vk) == (var_type, var_key):
            return su.get("value", ""), su.get("state", "")
    return None, None
