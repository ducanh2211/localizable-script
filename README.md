# Xcode String Catalog Studio (`xcstrings-tool`)

Bộ công cụ toàn diện và hiện đại giúp tối ưu hóa 100% quy trình dịch thuật & bản địa hóa (**Localization**) cho file **String Catalog (`.xcstrings`)** trong **Xcode / iOS Development**:
- 🌐 **Web Dashboard trực quan** (Streamlit): Quản lý tiến độ, sửa bảng tương tác như Excel, dịch tự động 1-Click.
- 🤖 **Dịch tự động AI**: Tích hợp Google Gemini, OpenAI, DeepSeek, Claude với khả năng bảo toàn tuyệt đối placeholder (`%@`, `%d`, `%lld`, plural variations).
- 💾 **Lưu trực tiếp vào Xcode (In-Place Update)**: Tự động tạo backup `.bak` và ghi đè thẳng vào Xcode Project mà không cần copy/paste JSON thủ công.
- ⚡ **Bảo toàn chuẩn format Xcode**: Khớp 100% quy ước serialize của Xcode (git diff sạch, chỉ thay đổi bản dịch).
- 🛠 **CLI thống nhất**: Cung cấp lệnh `xcstrings` với đầy đủ subcommands (`export`, `merge`, `verify`, `dashboard`).

---

## 🚀 1. Khởi động nhanh Web Dashboard

### Cách 1: Click đúp trên macOS (Khuyên dùng)
Double-click vào file **`start_dashboard.command`** trong thư mục dự án. Hệ thống sẽ tự động mở trình duyệt web tại `http://localhost:8501`.

### Cách 2: Chạy qua Terminal
```bash
# Cài đặt thư viện phụ thuộc (lần đầu tiên)
python3 -m pip install -r requirements.txt

# Khởi chạy Dashboard
python3 -m streamlit run app.py
```

---

## 🖥 2. Các tính năng nổi bật trên Web Dashboard

1. **Thống kê tổng quan (Metrics):**
   - Theo dõi % hoàn thành, số lượng chuỗi đã dịch / chưa dịch / cần review (`needs_review`) theo từng ngôn ngữ đích.
2. **Tab 1 - Bảng dịch tương tác (Spreadsheet Editor):**
   - Xem và chỉnh sửa trực tiếp các ô dịch trên bảng dữ liệu.
   - Hỗ trợ bộ lọc thông minh: *Chỉ hiện chuỗi thiếu dịch*, *Chỉ hiện chuỗi needs_review*, tìm kiếm theo từ khóa.
3. **Tab 2 - Dịch tự động 1-Click bằng AI (AI API):**
   - Hỗ trợ Google Gemini, OpenAI GPT-4o, DeepSeek, Claude.
   - Tự động chia lô (batching) và dịch các ô còn thiếu trong tích tắc kèm Progress Bar.
4. **Tab 3 - Dịch qua Chatbot Web (Prompt & CSV):**
   - Nút **`📋 Copy Prompt + CSV vào Clipboard`**: 1 bấm là copy toàn bộ dữ liệu kèm prompt tối ưu vào bộ nhớ tạm máy Mac (`Cmd + V` dán vào ChatGPT / Claude Web).
   - Kéo thả file CSV kết quả từ Chatbot để tự động merge vào bảng.
5. **Tab 4 - Verify & Lưu trực tiếp vào Xcode:**
   - Kiểm tra tính toàn vẹn format và rà soát lệch placeholder (`%@` vs `%d`).
   - Nút **`🔥 Lưu trực tiếp vào Xcode Project (In-Place)`**: Tự động tạo file sao lưu an toàn `.bak` và cập nhật thẳng vào file trong Xcode Project.

---

## ⌨️ 3. Sử dụng qua Command Line Interface (CLI)

Cài đặt package ở chế độ editable (tùy chọn):
```bash
python3 -m pip install -e .
```

### Các lệnh thường dùng:

#### 1. Trích xuất (Export)
```bash
# Xuất chuỗi chưa dịch dạng Wide-format (nhiều ngôn ngữ)
xcstrings export path/to/Localizable.xcstrings todo_wide.csv --untranslated --languages vi,ja,ko

# Xuất toàn bộ chuỗi dạng Long-format (1 ngôn ngữ)
xcstrings export path/to/Localizable.xcstrings all_vi.csv --lang vi
```

#### 2. Tích hợp bản dịch (Merge)
```bash
# Xem trước thay đổi (dry-run)
xcstrings merge path/to/Localizable.xcstrings todo_translated.csv --dry-run

# Ghi đè trực tiếp vào file Xcode (tự động tạo backup .bak)
xcstrings merge path/to/Localizable.xcstrings todo_translated.csv --in-place
```

#### 3. Kiểm tra (Verify)
```bash
xcstrings verify path/to/Localizable.xcstrings path/to/Localizable.merged.xcstrings vi,ja,ko
```

#### 4. Mở Dashboard UI
```bash
xcstrings dashboard
```

---

## 📁 4. Cấu trúc thư mục dự án

```
localizable-script/
├── src/
│   └── xcstrings_tool/             # Package mã nguồn chính
│       ├── core/                   # Serializer Xcode, Models, File I/O
│       ├── services/               # Exporter, Merger, Verifier, AI Translator
│       ├── cli/                    # Unified CLI Commands
│       └── ui/                     # Streamlit Web App & Components
├── tests/                          # Bộ Unit Tests tự động
├── legacy/                         # Chứa các script nguyên bản ban đầu
├── localizble/                     # Dữ liệu mẫu thực tế
├── app.py                          # Shortcut chạy Web Dashboard
├── pyproject.toml                  # Cấu hình chuẩn Python Package
├── requirements.txt                # Thư viện phụ thuộc (streamlit)
├── start_dashboard.command         # Shortcut 1-Click mở app trên macOS
└── README.md                       # Tài liệu hướng dẫn
```

---

## 🧪 5. Chạy Unit Tests

```bash
python3 -m unittest discover -s tests
```

---

## 📜 6. Tài liệu Legacy Scripts & 2 Prompt Mẫu AI

Nếu bạn muốn:
- Xem lại tài liệu hướng dẫn chi tiết từng bước ban đầu cho 5 file script Python độc lập.
- Sao chép **2 Prompt mẫu chuyên dụng cho AI Chatbot** (ChatGPT, Claude, Gemini Web) cho chế độ Long-format và Wide-format.
- Xem chi tiết về quy tắc CLDR Plural Variations và Device Variations.

👉 Vui lòng xem tài liệu chi tiết tại: **[`legacy/README.md`](file:///Users/ducanh/Desktop/Amobear_Workspace/localizable-script/legacy/README.md)**.

