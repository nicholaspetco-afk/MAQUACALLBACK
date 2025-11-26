# 一鍵新增客戶套件

此資料夾整合了「一鍵新增客戶」所需的程式碼與設定：

- `maqua-members/`：Flask 服務，提供查詢與匯入客戶的前端頁面。
- `新增優化/`：銷售文案解析與送件腳本 (`customer_builder.py` 等)。
- `新增商機/`：商機欄位解析與 payload 組裝輔助工具。
- `.env`：預設的 CRM 欄位設定（`CFG_FIELD_PAYMENT` 已維持 `merchantAppliedDetail!payway`）。
- 自 2025/07/xx 起，「一鍵新增」會先建立客戶，待成功後可按下「新增商機」按鈕，使用相同文案資料再送出商機。

## 安裝與啟動
1. 切換到本資料夾：
   ```bash
   cd "/Users/pureenergy/Documents/Codex/CRM系統程序/V8 查詢用戶指定資料/一鍵新增客戶"
   ```
2. 建議使用虛擬環境並安裝需求：
   ```bash
   pip install -r maqua-members/requirements.txt
   ```
3. 啟動服務（以 2034 埠為例）：
   ```bash
   PORT=2034 HOST=0.0.0.0 CFG_FIELD_PAYMENT='merchantAppliedDetail!payway' python3 maqua-members/app.py
   ```
4. 瀏覽 `http://localhost:2034/` 進行查詢或使用「一鍵新增客戶」匯入流程。

## 其他腳本
- 透過 `新增優化/customer_builder.py` 可以離線解析文案並輸出 CRM payload：
  ```bash
  cd 新增優化
  python3 customer_builder.py sample_input.txt --pretty
  ```

若需更新設定，請同步調整本資料夾下的 `.env` 與 `新增優化/.env`，並重新啟動服務。
