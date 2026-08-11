#!/bin/bash
cd "$(dirname "$0")"

echo "=================================================="
echo "🚀 Khởi động Xcode String Catalog Studio (Streamlit)"
echo "=================================================="

# Kiểm tra python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Lỗi: Không tìm thấy Python 3 trên máy của bạn."
    exit 1
fi

# Kiểm tra streamlit
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "📦 Đang cài đặt thư viện cần thiết (streamlit)..."
    python3 -m pip install -r requirements.txt
fi

echo "🌐 Đang mở giao diện Web Dashboard..."
python3 -m streamlit run app.py
