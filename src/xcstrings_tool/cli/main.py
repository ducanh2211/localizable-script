"""Unified Command Line Interface for xcstrings_tool."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Đảm bảo import được package khi chạy trực tiếp file main.py
src_dir = Path(__file__).resolve().parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from xcstrings_tool.services.exporter import export_to_csv
from xcstrings_tool.services.merger import merge_translations
from xcstrings_tool.services.verifier import verify_files
from xcstrings_tool.services.ai_translator import AITranslator, AIProvider


def cmd_export(args: argparse.Namespace) -> int:
    """Xử lý lệnh export."""
    input_path = args.input
    output_path = args.output

    if args.languages:
        target_langs = [l.strip() for l in args.languages.split(",") if l.strip()]
        mode = "wide"
    elif args.lang:
        target_langs = [args.lang.strip()]
        mode = "long"
    else:
        print("LỖI: Cần cung cấp --lang <mã> (long-format) hoặc --languages <ds,ngôn,ngữ> (wide-format).", file=sys.stderr)
        return 1

    res = export_to_csv(
        input_xcstrings=input_path,
        output_csv=output_path,
        target_langs=target_langs,
        untranslated_only=args.untranslated,
        mode=mode,
    )
    status_str = "CHƯA DỊCH" if args.untranslated else "TOÀN BỘ"
    print(f"Đã export {res['count']} dòng ({status_str}) ra: {res['output_csv']}")
    print(f"  Ngôn ngữ nguồn: {res['source_lang']} | Ngôn ngữ đích: {', '.join(target_langs)}")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    """Xử lý lệnh merge."""
    try:
        res = merge_translations(
            input_xcstrings=args.input,
            csv_source=args.csv,
            target_lang=args.lang,
            output_path=args.output,
            in_place=args.in_place,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"LỖI khi merge: {e}", file=sys.stderr)
        return 1

    verb = "Sẽ merge (dry-run)" if args.dry_run else "Đã merge"
    print(f"{verb} vào: {res['output_path']}")

    if res["mode"] == "long":
        lang = res["target_langs"][0]
        print(f"  [{lang}] cập nhật: {res['merged_count'][lang]} | bỏ qua (rỗng): {res['skipped_empty'][lang]}")
    else:
        for lang in res["target_langs"]:
            print(
                f"  [{lang}] cập nhật: {res['merged_count'][lang]} "
                f"| bỏ qua (rỗng): {res['skipped_empty'][lang]} "
                f"| không đổi: {res['skipped_unchanged'][lang]}"
            )

    if res["missing_keys"]:
        print(f"  CẢNH BÁO: {len(res['missing_keys'])} key trong CSV không có trong file gốc.")

    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Xử lý lệnh verify."""
    target_langs = [l.strip() for l in args.languages.split(",") if l.strip()]
    res = verify_files(args.original, args.merged, target_langs)

    if "error" in res:
        print(f"[FAIL] {res['error']}", file=sys.stderr)
        return 2

    print("[OK] Cả hai file đều là JSON hợp lệ.")
    if res["format_ok"]:
        print("[OK] Format được bảo toàn: chỉ phần dịch ngôn ngữ đích thay đổi.")
    else:
        print("[FAIL] Format KHÔNG được bảo toàn:")
        for p in res["format_problems"]:
            print(f"  {p}")

    print("\n--- Thống kê bản dịch theo ngôn ngữ ---")
    header = f"  {'lang':<8}{'translated':>12}{'new/review':>12}{'empty':>8}{'placeholder lệch':>18}"
    print(header)
    for lang in res["clean_langs"]:
        s = res["stats_by_lang"][lang]
        print(
            f"  {lang:<8}{s['translated']:>12}{s['untranslated']:>12}"
            f"{s['empty']:>8}{s['placeholder_mismatch']:>18}"
        )

    for lang in res["clean_langs"]:
        w = res["warnings_by_lang"][lang]
        if w:
            print(f"\n--- Cảnh báo chi tiết [{lang}] (tối đa 20 dòng) ---")
            for line in w[:20]:
                print(f"  {line}")

    if not res["valid"]:
        print("\n[KẾT LUẬN] Có lỗi NGHIÊM TRỌNG cần xử lý trước khi dùng file.")
        return 1
    print("\n[KẾT LUẬN] File hợp lệ. Có thể đưa vào Xcode.")
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Khởi chạy Streamlit Dashboard UI."""
    app_path = Path(__file__).parent.parent / "ui" / "app.py"
    port = args.port or 8501
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)]
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="xcstrings",
        description="Bộ công cụ tối ưu quy trình Localization cho file .xcstrings trong Xcode",
    )
    subparsers = parser.add_subparsers(dest="command", help="Lệnh cần thực thi")

    # export
    p_export = subparsers.add_parser("export", help="Trích xuất chuỗi ra CSV")
    p_export.add_argument("input", help="Đường dẫn file .xcstrings")
    p_export.add_argument("output", help="Đường dẫn file CSV kết quả")
    p_export.add_argument("--untranslated", action="store_true", help="Chỉ xuất các chuỗi chưa dịch / needs_review")
    p_export.add_argument("--lang", help="Ngôn ngữ đích (chế độ long-format, vd: vi)")
    p_export.add_argument("--languages", help="Danh sách ngôn ngữ đích (chế độ wide-format, vd: vi,ja,ko)")
    p_export.set_defaults(func=cmd_export)

    # merge
    p_merge = subparsers.add_parser("merge", help="Merge bản dịch từ CSV vào .xcstrings")
    p_merge.add_argument("input", help="Đường dẫn file .xcstrings gốc")
    p_merge.add_argument("csv", help="Đường dẫn file CSV đã dịch")
    p_merge.add_argument("--lang", help="Ngôn ngữ đích (bắt buộc với long-format)")
    p_merge.add_argument("--output", help="Đường dẫn file kết quả (mặc định: *.merged.xcstrings)")
    p_merge.add_argument("--in-place", action="store_true", help="Ghi đè trực tiếp vào file gốc (tự động backup .bak)")
    p_merge.add_argument("--dry-run", action="store_true", help="Chỉ xem trước thay đổi, không ghi file")
    p_merge.set_defaults(func=cmd_merge)

    # verify
    p_verify = subparsers.add_parser("verify", help="Kiểm tra tính hợp lệ và chất lượng bản dịch sau khi merge")
    p_verify.add_argument("original", help="File .xcstrings gốc")
    p_verify.add_argument("merged", help="File .xcstrings sau khi merge")
    p_verify.add_argument("languages", help="Danh sách ngôn ngữ cần kiểm tra (vd: vi hoặc vi,ja,ko)")
    p_verify.set_defaults(func=cmd_verify)

    # dashboard
    p_dashboard = subparsers.add_parser("dashboard", help="Mở giao diện Web Dashboard Streamlit")
    p_dashboard.add_argument("--port", type=int, default=8501, help="Port cho Streamlit server (mặc định: 8501)")
    p_dashboard.set_defaults(func=cmd_dashboard)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
