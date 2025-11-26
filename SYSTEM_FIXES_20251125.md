# 系統小問題修復報告

## 📅 修復日期: 2025-11-25

---

## 修復的問題

### 1. ✅ 付費方式總是顯示最後一個選項

**問題描述**:
- 輸入: `目前付費方式：信用卡分期/一次性全繳/季度收費`
- 預期: 顯示 "信用卡分期"（第一個）
- 實際: 顯示 "季度收費"（最後一個）或隨機顯示

**根本原因**:
`_normalize_payment_code` 函數使用 `re.search(r"\d{2}")` 會匹配到任意一個兩位數字，對於包含多個選項的輸入，可能會匹配到錯誤的代碼。

**修復方案**:
修改 `/新增商機/opportunity_builder.py` 中的 `_normalize_payment_code` 函數：

1. 如果輸入包含多個選項（用 `/` 或 `、` 分隔），先分割取第一個選項
2. 添加關鍵詞映射，優先匹配常見付費方式名稱
3. 再嘗試提取數字代碼

```python
def _normalize_payment_code(text: Optional[str]) -> Optional[str]:
    """提取付款方式代碼。如果有多個選項，優先取第一個。"""
    if not text:
        return None
    clean = _normalize_placeholder(text)
    if not clean:
        return None
    
    # 如果有多個選項（用斜杠或中文頓號分隔），取第一個
    if "/" in clean or "、" in clean:
        parts = re.split(r"[/、]", clean)
        if parts:
            first_option = next((p.strip() for p in parts if p.strip()), None)
            if first_option:
                clean = first_option
    
    # 嘗試提取兩位數字代碼
    digits = re.search(r"\d{2}", clean)
    if digits:
        return digits.group(0)
    
    # 根據關鍵詞映射
    payment_keywords = {
        "信用卡分期": "02",
        "一次性全繳": "01",
        "季度收費": "04",
        "年度收費": "05",
        # ... 更多映射
    }
    
    for keyword, code in payment_keywords.items():
        if keyword in clean:
            return code
    
    return clean
```

**測試結果**:
- ✅ `信用卡分期/一次性全繳/季度收費` → `02` (信用卡分期)
- ✅ `一次性全繳` → `01`
- ✅ `季度收費` → `04`

---

### 2. ✅ 自動創建任務（應該手動控制）

**問題描述**:
新增商機後，系統自動創建了「新增項目」任務，用戶沒有按「新增任務」按鈕。

**根本原因**:
在修復之前的任務創建問題時，我們在 `_create_opportunity_for_customer` 函數中添加了自動創建任務的邏輯（第 2526 行），但用戶希望手動控制任務創建。

**修復方案**:
註釋掉自動創建任務的代碼：

```python
# 在 customer_submission.py 第 2523-2529 行
if result["success"]:
    # 註釋掉自動創建任務，改為手動創建（通過前端"新增任務"按鈕觸發）
    # try:
    #     _auto_create_tasks_for_opportunity(context, create_response, settings, client)
    # except Exception as exc:
    #     print(f"[task] auto-create error: {exc}", flush=True)
    pass
```

**現在的行為**:
- 新增商機：✅ 成功（不自動創建任務）
- 新增任務：⏳ 需要用戶手動點擊「新增任務」按鈕

---

### 3. ⚠️ 重複創建商機

**問題描述**:
點擊「新增商機」按鈕一次，創建了兩個商機。

**可能原因**:
1. 前端按鈕重複提交（用戶連點或網絡延遲）
2. 後端沒有防重複提交機制失效

**已有機制**:
後端有商機查重功能（`check_opportunity_repeat`），但可能因為：
- 查重規則未設置
- 查重條件不匹配
- 兩次提交之間時間太短，CRM 還未索引第一個商機

**建議的前端修復**:
在前端添加防抖或禁用按鈕：

```javascript
// 在 index.html 或相關 JavaScript 文件中
let isSubmitting = false;

function onCreateOpportunity() {
    if (isSubmitting) {
        return; // 防止重複提交
    }
    
    isSubmitting = true;
    // 禁用按鈕
    const button = document.getElementById('createOpportunityButton');
    button.disabled = true;
    button.textContent = '提交中...';
    
    // 發送請求
    fetch('/api/opportunities/create', {...})
        .then(response => {
            // 處理響應
        })
        .finally(() => {
            // 重新啟用按鈕
            isSubmitting = false;
            button.disabled = false;
            button.textContent = '新增商機';
        });
}
```

**臨時解決方案**:
提醒用戶只點擊一次「新增商機」按鈕，等待響應完成。

---

## 修改的文件

### ✅ 已修改
1. `/新增商機/opportunity_builder.py` - 修復付費方式解析邏輯
2. `/maqua-members/services/customer_submission.py` - 禁用自動創建任務

### ⏳ 待修改（可選）
3. `/maqua-members/templates/index.html` - 添加前端防重複提交

---

## 重啟服務

修改完成後，需要重啟服務以應用更新：

```bash
# 端口 6025（有密碼的系統）
cd "/Users/pureenergy/Documents/Codex/CRM系統程序/V8 查詢用戶指定資料 /一鍵新增客戶0501/maqua-members"
lsof -ti:6025 | xargs kill -9
nohup python3 app.py > ../server_app.log 2>&1 &
```

---

## 測試建議

### 測試 1: 付費方式解析
輸入：
```
目前付費方式：信用卡分期/一次性全繳/季度收費
```

預期結果：
- 新增客戶：顯示「信用卡分期」或 `02`
- 新增商機：顯示「信用卡分期」或 `02`

### 測試 2: 手動創建任務
1. 新增客戶 + 商機
2. 確認沒有自動創建任務
3. 點擊「新增任務」按鈕
4. 確認任務創建成功

### 測試 3: 防重複提交
1. 點擊「新增商機」按鈕
2. 在前一個請求完成前，不要再次點擊
3. 檢查 CRM 中只有一個商機

---

## 優先級

1. 🔴 **高** - 付費方式解析錯誤（已修復）
2. 🟡 **中** - 自動創建任務（已修復）
3. 🟢 **低** - 重複創建商機（需前端配合）

---

**修復完成時間**: 2025-11-25 11:10  
**狀態**: ✅ 後端修復完成，等待重啟服務測試
