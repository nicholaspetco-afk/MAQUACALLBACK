# MAQUA 回訪系統

這個資料夾整理了部署到 GitHub / Render 所需的最小專案內容：

- `index.html`, `report.html`, `records.html`, `style.css`, `assets/`：前端頁面與靜態資源
- `server/`：Flask 後端（`app.py` 為入口），內含 `requirements.txt`

### 本地啟動
```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app
```

### 部署到 Render（範例設定）
- Build Command: `pip install -r server/requirements.txt`
- Start Command: `gunicorn server.app:app --workers 2 --bind 0.0.0.0:$PORT`
- Python 版本：3.11 以上

環境變數（如 API token）請在 Render 儀表板設定。
