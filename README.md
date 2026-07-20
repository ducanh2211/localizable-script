# Công cụ Localization cho iOS `.xcstrings`

Bộ 4 script Python giúp tối ưu workflow dịch thuật cho file **String Catalog**
(`.xcstrings`) trong Xcode: trích xuất chuỗi ra CSV → dịch bằng AI/thủ công →
merge ngược vào file gốc → verify. Toàn bộ **giữ nguyên format file gốc**, chỉ
thay đổi phần bản dịch.

Hỗ trợ **2 chế độ CSV**, tự chọn tuỳ workflow dịch:

| Chế độ | Khi nào dùng | Đặc điểm |
| --- | --- | --- |
| **long-format** (mặc định) | Dịch tách riêng theo từng ngôn ngữ, chạy script riêng cho mỗi ngôn ngữ | 1 dòng CSV = 1 key + 1 ngôn ngữ |
| **wide-format** (`--languages`) | Dịch 1 key cho nhiều ngôn ngữ cùng lúc | 1 dòng CSV = 1 key, N cột `{lang}_target` |

CSV chỉ giữ đúng những cột AI/người dịch cần: `key`, `variant` (định vị
plural/device), `source_value`, và (các) cột `target`. Không có cột
`language`/`state` lặp lại hay chỉ để tham khảo.

`merge_csv.py` tự nhận diện long/wide theo header, không cần chọn cờ —
riêng long-format cần thêm `--lang <mã ngôn ngữ>` vì CSV không còn cột
`language`. `verify.py` chấp nhận cả 2 chế độ như cũ.

> Viết bằng Python (không phải Swift) vì chỉ Python cho phép kiểm soát chính
> xác cách serialize JSON để khớp 100% với quy ước ghi file của Xcode
> (separator `" : "`, object rỗng dạng đặc biệt, không sort lại key, không
> newline cuối file). Điều này cần thiết để git diff sạch — chỉ hiện phần dịch.

## Yêu cầu

- Python 3.7 trở lên (chỉ dùng thư viện chuẩn: `json`, `csv`, `re`, `pathlib`).
  Không cần cài thêm gì.

## Cấu trúc thư mục

```
xcstrings_common.py       # Module dùng chung (load/serialize/duyệt) — KHÔNG chạy trực tiếp
export_all.py             # Script 1: export TOÀN BỘ key-value ra CSV
export_untranslated.py    # Script 2: export chỉ những dòng CHƯA DỊCH
merge_csv.py              # Script 3: merge CSV đã dịch ngược vào .xcstrings
verify.py                 # Script 4: kiểm tra file sau merge
README.md                 # File này
```

Đặt cả 4 file `.py` **cùng một thư mục** (vì đều import `xcstrings_common`).

## Quy trình 5 bước (long-format — 1 ngôn ngữ/lần chạy)

### Bước 1 — Export chuỗi chưa dịch (để không dịch lại phần đã có)

```bash
python3 export_untranslated.py Localizable.xcstrings vi todo.csv
```

- `vi` = mã ngôn ngữ đích (đổi thành `ja`, `ko`, `fr`... tuỳ nhu cầu).
- Sinh ra `todo.csv` chỉ chứa những ô **chưa dịch**: thiếu bản dịch, hoặc
  state `new`/`needs_review`, hoặc value rỗng.

> Muốn xuất **toàn bộ** (cả đã dịch lẫn chưa) để tham khảo:
> ```bash
> python3 export_all.py Localizable.xcstrings vi all.csv
> ```

### Bước 2 — Dịch bằng AI Chatbot

Mở `todo.csv` (Excel / Google Sheets / editor). Các cột:

| Cột              | Ý nghĩa                                                        |
| ---------------- | ------------------------------------------------------------- |
| `key`            | Định danh chuỗi trong `.xcstrings` — **KHÔNG sửa**            |
| `variant`        | Rỗng / `plural.one` / `device.iphone`... — định vị path cho merge, **KHÔNG sửa** |
| `source_value`   | Chuỗi gốc (tiếng nguồn) để làm ngữ cảnh dịch — **KHÔNG sửa**  |
| `target_value`   | **CHỖ ĐIỀN BẢN DỊCH** ← chỉ sửa cột này                       |

(Ngôn ngữ đích không còn là 1 cột trong CSV — nó cố định cho cả file, truyền
qua tham số dòng lệnh khi merge, xem Bước 3.)

**Điền bản dịch vào cột `target_value`.** Lưu ý khi dịch:
- Giữ nguyên mọi **placeholder**: `%@`, `%lld`, `%d`, `%1$@`, `%2$@`... phải
  xuất hiện đủ và đúng loại trong bản dịch (verify sẽ kiểm tra việc này).
- `%%` là dấu phần trăm literal, giữ nguyên.

Mẹo dùng AI: dán nội dung CSV và yêu cầu *"dịch cột source_value sang tiếng
Việt, điền vào target_value, giữ nguyên tất cả placeholder dạng %@ %lld %1$@,
không đổi các cột khác, trả về đúng định dạng CSV"*.

> Mẹo tiết kiệm token: `source_value` chỉ cần thiết để AI có ngữ cảnh khi
> dịch — `merge_csv.py` không đọc lại cột này. Nên yêu cầu AI **trả về CSV
> không có cột `source_value`** (chỉ `key, variant, target_value`), tránh
> việc AI phải echo lại nguyên văn cột đó trên mọi dòng output một cách vô
> ích. Xem 2 prompt mẫu ở cuối file — đã có sẵn quy tắc này.

Lưu lại thành file CSV (giữ encoding UTF-8), ví dụ `todo_translated.csv`.

### Bước 3 — Merge bản dịch ngược vào `.xcstrings`

```bash
python3 merge_csv.py Localizable.xcstrings todo_translated.csv --lang vi
```

- `--lang vi` **bắt buộc** với long-format vì CSV không còn cột `language` —
  phải nói rõ ngôn ngữ đích qua CLI (đúng ngôn ngữ đã dùng lúc export).
- Tạo ra file mới **`Localizable.merged.xcstrings`** (KHÔNG ghi đè file gốc).
- Chỉ những dòng có `target_value` khác rỗng mới được merge; đánh dấu
  state = `translated`.
- Dòng có `target_value` rỗng bị bỏ qua. Key lạ (không có trong file gốc)
  được cảnh báo chứ không làm hỏng file.

### Bước 4 — Verify file kết quả

```bash
python3 verify.py Localizable.xcstrings Localizable.merged.xcstrings vi
```

Kiểm tra 3 việc:
1. File vẫn là JSON hợp lệ.
2. **Format được bảo toàn** — khác biệt duy nhất so với file gốc chỉ nằm ở
   bản dịch ngôn ngữ đích, không đụng gì khác.
3. Chất lượng: còn ô chưa dịch không, value rỗng không, và **placeholder có
   khớp** giữa nguồn và bản dịch không.

Exit code `0` = ổn; khác `0` = có lỗi nghiêm trọng (format hỏng hoặc
placeholder lệch) — xem cảnh báo, sửa CSV rồi merge lại.

### Bước 5 — Đưa vào Xcode

Nếu verify báo OK, đổi tên `Localizable.merged.xcstrings` thành
`Localizable.xcstrings` (nên backup file cũ trước) và mở lại trong Xcode.

## Quy trình wide-format (nhiều ngôn ngữ/lần chạy)

Dùng khi bạn muốn dịch **1 key cho nhiều ngôn ngữ cùng lúc** (thay vì tách
riêng theo từng ngôn ngữ) — ví dụ đưa cả dòng key + tất cả ngôn ngữ vào 1 lần
hỏi AI Chatbot để có đủ ngữ cảnh.

### Bước 1 — Export bằng `--languages`

```bash
python3 export_untranslated.py Localizable.xcstrings todo_wide.csv --languages vi,ja,ko
```

- Không còn tham số `target_lang` ở giữa — thay bằng cờ `--languages` (danh
  sách ngôn ngữ, phân cách bởi dấu phẩy).
- `--languages` được **validate tự động**: ngôn ngữ trùng `sourceLanguage`
  hoặc bị lặp sẽ bị bỏ qua kèm cảnh báo, không làm hỏng lệnh.
- Xuất dòng theo **OR-rule**: 1 dòng được xuất ra nếu **còn thiếu dịch ở ÍT
  NHẤT 1 ngôn ngữ** trong danh sách — không cần thiếu toàn bộ. Ngôn ngữ đã
  dịch xong trong dòng đó vẫn hiện giá trị cũ để làm ngữ cảnh.

> Muốn xuất **toàn bộ** (cả đã dịch lẫn chưa) để tham khảo:
> ```bash
> python3 export_all.py Localizable.xcstrings all_wide.csv --languages vi,ja,ko
> ```

### Bước 2 — Schema CSV wide-format

```
key,variant,source_value,vi_target,ja_target
welcome,,Welcome,Chào mừng,
items,plural.one,%d item,,
items,plural.other,%d items,,
```

- 1 dòng = 1 `(key, variant)` — **không lặp theo ngôn ngữ** như long-format.
- `variant` gộp `(variation_type, variation_key)` thành 1 cột, vd.
  `plural.one`, `device.iphone`; rỗng = string đơn giản.
- Mỗi ngôn ngữ đích có đúng 1 cột `{lang}_target` (**chỗ điền dịch**). Không
  còn cột `{lang}_state` — thông tin đó merge không đọc lại nên đã bỏ để CSV
  gọn hơn.
- `{lang}_target` được pre-fill giá trị hiện có (kể cả rỗng) để vừa làm ngữ
  cảnh vừa dùng so sánh lúc merge.
- Muốn dịch xong 1 key cho hết các ngôn ngữ, chỉ cần điền các cột `_target`
  còn thiếu trên cùng 1 dòng — không cần dò nhiều dòng như long-format.
- **Không hỗ trợ xoá bản dịch qua CSV**: để trống 1 ô `{lang}_target` nghĩa
  là "chưa dịch/không đổi", KHÔNG bị hiểu là "xoá dịch cũ". Muốn xoá bản dịch
  đã có, sửa trực tiếp trong Xcode.

### Bước 3 — Merge

```bash
python3 merge_csv.py Localizable.xcstrings todo_wide_translated.csv
```

`merge_csv.py` **tự nhận diện** CSV là long hay wide format dựa trên header,
không cần chọn cờ. Với wide-format, quy tắc so sánh mỗi ô `{lang}_target` với
giá trị **hiện có trong chính file `.xcstrings` truyền vào**:

| So sánh | Hành động |
| --- | --- |
| `{lang}_target` rỗng | Bỏ qua, không đổi gì |
| Bằng giá trị hiện có, state hiện có **không phải** `needs_review` | Bỏ qua (tránh ghi state lại vô ích) |
| Bằng giá trị hiện có, state hiện có **là** `needs_review` | Vẫn áp dụng: state → `translated` (coi như người dịch đã xem CSV và xác nhận bản dịch cũ vẫn đúng) |
| Khác giá trị hiện có | Áp dụng: value = giá trị mới, state = `translated` |

Cột ngôn ngữ bị xoá thủ công khỏi CSV (vd. chỉ giữ `vi_target`, bỏ hẳn cột
`ja_target`) được xử lý graceful — ngôn ngữ đó đơn giản không được merge,
không báo lỗi.

**Xem trước thay đổi trước khi ghi file** bằng `--dry-run`:

```bash
python3 merge_csv.py Localizable.xcstrings todo_wide_translated.csv --dry-run
```

> ⚠️ **Ràng buộc quan trọng:** phải merge trên **đúng file `.xcstrings`** đã
> dùng để export ra CSV đó — không phải bản mới hơn/đã bị sửa. Vì merge so
> sánh với giá trị hiện có đọc từ chính file truyền vào lúc merge: nếu file
> đó đã được người khác cập nhật bản dịch cho cùng key/ngôn ngữ trong lúc
> chờ dịch (vd. sửa trực tiếp trong Xcode, hoặc đã merge 1 lần trước đó),
> CSV đang cầm giá trị cũ có thể **ghi đè mất bản dịch mới hơn**. Luôn chạy
> `--dry-run` trước nếu không chắc file gốc còn nguyên như lúc export.

### Bước 4 — Verify nhiều ngôn ngữ cùng lúc

```bash
python3 verify.py Localizable.xcstrings Localizable.merged.xcstrings vi,ja,ko
```

- Tham số cuối nhận **danh sách ngôn ngữ cách nhau bởi dấu phẩy** (truyền 1
  ngôn ngữ vẫn hoạt động như long-format, xem Bước 4 ở trên).
- Kiểm tra format 1 lần cho tất cả ngôn ngữ, nhưng báo cáo chất lượng dịch
  (đã dịch / chưa dịch / rỗng / placeholder lệch) theo **bảng riêng từng
  ngôn ngữ**.

### Bước 5 — Đưa vào Xcode

Giống long-format: đổi tên `Localizable.merged.xcstrings` thành
`Localizable.xcstrings` (backup file cũ trước) rồi mở lại trong Xcode.

## Xử lý plural & device variations

Bộ script tự động nhận diện và xử lý cả 3 dạng cấu trúc trong `.xcstrings`:
- Chuỗi đơn giản (`stringUnit`).
- Số nhiều (`variations.plural`: `one`, `other`, `few`, `many`, `zero`).
- Theo thiết bị (`variations.device`: `iphone`, `ipad`, `mac`...).

Mỗi ô dịch được định danh bằng cột `variant` (gộp `variation_type` +
`variation_key`, vd. `plural.one`, `device.iphone`) trong CSV, nên merge
luôn đặt bản dịch vào đúng vị trí. **Không tự sửa cột này.**

## Ghi chú kỹ thuật

- File `.xcstrings` mà key trùng với chuỗi nguồn thì Xcode thường không lưu
  localization nguồn riêng — khi đó chính `key` được dùng làm `source_value`.
- CSV xuất ra dùng UTF-8 kèm BOM (`utf-8-sig`) để Excel/Sheets hiển thị đúng
  tiếng Việt và Unicode. Khi đọc lại, script cũng dùng `utf-8-sig` nên BOM
  được xử lý tự động.
- Serializer được kiểm chứng tái tạo file gốc **byte-for-byte** trước khi
  dùng, đảm bảo git diff chỉ hiện đúng phần thay đổi.
- Các ngôn ngữ có thể có **tập plural category khác nhau** (CLDR) — vd. tiếng
  Nga có thêm `few`/`many` mà tiếng Anh không có. Wide-format union path theo
  TẤT CẢ ngôn ngữ đích, nên 1 dòng có thể hiện cột trống cho ngôn ngữ không
  cần category đó; để trống là đúng, không cần điền.

## Prompt mẫu để nhờ AI Chatbot dịch

Copy nguyên khối prompt tương ứng, dán vào đầu tin nhắn, rồi dán tiếp nội
dung file CSV (todo.csv / todo_wide.csv) ngay phía dưới trong cùng tin nhắn.

### Case 1 — long-format (1 ngôn ngữ/dòng)

```
Bạn là biên dịch viên phần mềm. Tôi sẽ dán một file CSV xuất ra từ Xcode
String Catalog (.xcstrings), có các cột: key, variant, source_value,
target_value. Toàn bộ file này chỉ dịch sang MỘT ngôn ngữ đích: <NGÔN NGỮ
ĐÍCH> (mã ISO, ví dụ "vi" = Tiếng Việt).

Nhiệm vụ: dịch cột `source_value` sang ngôn ngữ trên, rồi điền kết quả vào
cột `target_value`.

Quy tắc bắt buộc:
1. CHỈ điền/sửa cột `target_value`. Không đổi bất kỳ cột nào khác (key,
   variant, source_value).
2. Giữ NGUYÊN VẸN mọi placeholder xuất hiện trong source_value: %@, %d,
   %lld, %f, %1$@, %2$lld... phải xuất hiện đủ số lượng, đúng thứ tự đánh
   số (nếu có $), và đúng loại trong bản dịch. %% là dấu % literal, giữ
   nguyên, không dịch.
3. Nếu cột `variant` bắt đầu bằng "plural.": các dòng cùng key là các dạng
   số nhiều (plural.one/plural.other/plural.few/...) của CÙNG một câu — dịch
   tự nhiên theo ngữ pháp số nhiều của ngôn ngữ đích, không cần dịch y hệt
   cấu trúc tiếng Anh.
4. Nếu cột `variant` bắt đầu bằng "device.": các dòng cùng key là biến thể
   theo thiết bị (device.iphone/device.ipad/...) — thường nội dung gần
   giống nhau, dịch nhất quán.
5. Nếu source_value rỗng, để target_value rỗng (không tự bịa nội dung).
6. Giữ nguyên số lượng dòng, thứ tự dòng. KHÔNG thêm/xoá/gộp dòng.
7. CSV trả về CHỈ cần 3 cột: key, variant, target_value — BỎ HẲN cột
   source_value (không cần echo lại, đỡ tốn token output). Vẫn giữ đủ 3 cột
   trên, đúng header, không thêm giải thích hay text nào khác ngoài CSV.

Dữ liệu CSV:
```

### Case 2 — wide-format (nhiều ngôn ngữ/dòng)

Sửa danh sách ngôn ngữ trong đoạn `{lang}_target` cho khớp với các cột thực
tế trong file CSV của bạn (vd. nếu export với `--languages vi,ja,ko` thì có
`vi_target`, `ja_target`, `ko_target`).

```
Bạn là biên dịch viên phần mềm, thành thạo nhiều ngôn ngữ. Tôi sẽ dán một
file CSV xuất ra từ Xcode String Catalog (.xcstrings), có các cột: key,
variant, source_value, rồi đến từng cột {mã_ngôn_ngữ}_target cho mỗi ngôn
ngữ đích (vd. vi_target, ja_target, ko_target...).

Nhiệm vụ: với MỖI dòng, dịch `source_value` sang TẤT CẢ ngôn ngữ đích có mặt
trong header (suy ra ngôn ngữ từ tiền tố cột, vd cột "vi_target" ứng với
Tiếng Việt, "ja_target" ứng với Tiếng Nhật...), điền kết quả vào đúng cột
`{lang}_target` tương ứng.

Quy tắc bắt buộc:
1. CHỈ điền/sửa các cột `{lang}_target`. Không đổi key, variant, source_value.
2. Nếu một ô `{lang}_target` ĐÃ CÓ SẴN giá trị (không rỗng) — đó là bản dịch
   cũ, hiện ra để bạn tham khảo ngữ cảnh. GIỮ NGUYÊN, không sửa, trừ khi tôi
   nói rõ là cần dịch lại.
3. Chỉ cần điền vào những ô `{lang}_target` đang RỖNG.
4. Giữ NGUYÊN VẸN mọi placeholder trong source_value: %@, %d, %lld, %f,
   %1$@, %2$lld... phải xuất hiện đủ số lượng, đúng thứ tự đánh số (nếu có
   $), đúng loại, trong TẤT CẢ ngôn ngữ dịch. %% là dấu % literal, giữ
   nguyên, không dịch.
5. Nếu cột `variant` bắt đầu bằng "plural.": các dòng cùng key là các dạng
   số nhiều (plural.one/plural.other/...) của CÙNG một câu — dịch tự nhiên
   theo ngữ pháp số nhiều của TỪNG ngôn ngữ đích (số lượng category có thể
   khác nhau giữa các ngôn ngữ, không sao).
6. Nếu cột `variant` bắt đầu bằng "device.": các dòng cùng key là biến thể
   theo thiết bị (device.iphone/device.ipad/...) — thường nội dung gần
   giống nhau, dịch nhất quán.
7. Nếu source_value rỗng, để tất cả target rỗng (không tự bịa nội dung).
8. Giữ nguyên số lượng dòng, thứ tự dòng. KHÔNG thêm/xoá/gộp dòng.
9. CSV trả về CHỈ cần key, variant, và các cột {lang}_target — BỎ HẲN cột
   source_value (không cần echo lại, đỡ tốn token output). Vẫn giữ đúng
   header, không thêm giải thích hay text nào khác ngoài CSV.

Dữ liệu CSV:
```

> Với cả 2 case: nếu file CSV quá dài (nhiều dòng/nhiều ngôn ngữ) khiến
> chatbot cắt bớt output, chia nhỏ CSV thành nhiều batch (vd. 50-100 dòng),
> lặp lại prompt cho từng batch rồi ghép kết quả lại trước khi merge.
