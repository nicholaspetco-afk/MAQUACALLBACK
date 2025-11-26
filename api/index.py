import sys
from pathlib import Path

# 將項目根目錄與 Flask 專案路徑加入 sys.path
ROOT = Path(__file__).resolve().parent.parent
MAQUA_DIR = ROOT / "maqua-members"
if str(MAQUA_DIR) not in sys.path:
    sys.path.insert(0, str(MAQUA_DIR))

# 匯出 Flask app 給 Vercel Python 函數使用
from app import app as application  # noqa: E402

# Vercel 會尋找名為 "app" 或 "application" 的 WSGI 對象
# 這裡直接使用 maqua-members/app.py 中的 app
