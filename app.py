"""Root launcher for Streamlit Dashboard."""

import sys
from pathlib import Path

# Đưa thư mục src vào sys.path
src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from xcstrings_tool.ui.app import main

if __name__ == "__main__":
    main()
