# Vercel 部署指引（摘要）

## 1) 準備專案
- 這個資料夾可直接推到 GitHub，名稱可用 `一鍵新增客戶github`。
- 確保不要提交 `.env`（已在 `.gitignore`），機密環境變數請改用 Vercel 的 Environment Variables。
- 根目錄 `requirements.txt` 會引用 `maqua-members/requirements.txt`，Vercel 會自動安裝。

## 2) Vercel 設定
- 需要 Vercel CLI：`npm i -g vercel`
- 在專案根目錄，有 `vercel.json` 與 `api/index.py`，Vercel 會當成 Python Serverless 函數，內部導向 `maqua-members/app.py` 的 Flask `app`。
- 常用指令：
  ```bash
  vercel login
  vercel   # 首次部署時選擇專案
  vercel --prod
  ```

## 3) 環境變數
- 將原本 `.env` 中的所有鍵，逐一在 Vercel 後台「Environment Variables」設定（Production + Preview）。
- 任何敏感金鑰、CRM gateway URL、APP_KEY/APP_SECRET 都放在 Vercel，不要放在 repo。

## 4) 結構說明
- `api/index.py`：Vercel 入口，匯出 `application` 指向 Flask app。
- `vercel.json`：指定 Python 3.11，所有路由導向 `/api/index.py`。
- `requirements.txt`：引用子目錄依賴，避免重複。
- 主程式仍在 `maqua-members/app.py`，未更動路由。

## 5) 本地測試
```bash
pip install -r requirements.txt
python3 maqua-members/app.py  # 本地 127.0.0.1:6025
vercel dev                    # 使用 Vercel 模擬（需安裝 vercel CLI）
```

## 6) 注意
- Vercel Serverless 有超時與記憶體限制，長時間任務/背景排程不適合。若需常駐服務，請考慮 Render/Railway。
- 如果路徑含空白，上傳到 GitHub 前建議將資料夾重新命名為無空白路徑（如 `yijian-add-customer`）。  
