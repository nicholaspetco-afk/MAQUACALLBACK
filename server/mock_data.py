"""
模擬CRM數據，用於在API授權問題解決前提供測試數據
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
import random

def generate_mock_followup_data(customer_code: str = "", page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """生成模擬的跟進記錄數據"""
    
    # 模擬客戶列表
    customers = [
        {"code": "C3770", "name": "北京小米智能科技有限公司-測試"},
        {"code": "C3771", "name": "上海華為技術有限公司"},
        {"code": "C3772", "name": "深圳騰訊計算機系統有限公司"},
        {"code": "C3773", "name": "杭州阿里巴巴網絡技術有限公司"},
        {"code": "C3774", "name": "北京百度網訊科技有限公司"},
        {"code": "MOCK001", "name": "模擬測試客戶001"},
        {"code": "TEST001", "name": "測試客戶001"},
    ]
    
    # 跟進方式
    follow_methods = [
        {"code": "phone", "name": "電話跟進"},
        {"code": "visit", "name": "實地拜訪"},
        {"code": "email", "name": "郵件溝通"},
        {"code": "wechat", "name": "微信聯繫"},
        {"code": "meeting", "name": "會議討論"},
    ]
    
    # 生成模擬記錄
    records = []
    total_records = 50  # 總記錄數
    
    # 如果指定了客戶代碼，只返回該客戶的記錄
    if customer_code:
        filtered_customers = [c for c in customers if c["code"] == customer_code]
        if not filtered_customers:
            # 如果找不到客戶，返回空結果
            return {
                "code": 200,
                "message": "操作成功",
                "data": {
                    "recordList": []
                }
            }
        customers = filtered_customers
        total_records = 10  # 單個客戶的記錄數較少
    
    # 計算分頁
    start_index = (page - 1) * page_size
    end_index = min(start_index + page_size, total_records)
    
    for i in range(start_index, end_index):
        customer = random.choice(customers)
        method = random.choice(follow_methods)
        
        # 生成隨機日期（最近30天內）
        follow_date = datetime.now() - timedelta(days=random.randint(0, 30))
        create_date = follow_date + timedelta(hours=random.randint(1, 24))
        
        record = {
            "id": f"207{6169693366321156 + i}",
            "code": f"2024{(8 + i % 4):02d}{(29 + i % 28):02d}{(1748 + i):06d}",
            "followContext": f"模擬跟進內容 - 第{i+1}次跟進，討論了產品需求和合作意向",
            "followTime": follow_date.strftime("%Y-%m-%d %H:%M:%S"),
            "createTime": create_date.strftime("%Y-%m-%d %H:%M:%S"),
            "customer": customer["code"],
            "customer_name": customer["name"],
            "customer_code": customer["code"],
            "followMethodDoc": method["code"],
            "followMethodDoc_name": method["name"],
            "followMethodDoc_code": method["code"],
            "ower": f"188470261112425678{i % 10}",
            "ower_name": f"銷售代表{chr(65 + i % 26)}",
            "ower_code": f"SALE{(i % 100):03d}",
            "creator": f"創建人{chr(65 + i % 26)}",
            "org": "1884698324742176769",
            "org_name": "集團",
            "org_code": "GROUP001",
            "dept": "1884699295404785664",
            "dept_name": "銷管二部",
            "dept_code": f"DEPT{(i % 10):02d}",
            "saleArea": "1884703933956882438",
            "saleArea_name": "華北大區",
            "saleArea_code": f"AREA{(i % 5):02d}",
            "bustype": "1884699295404785664",
            "bustype_code": "zy001",
            "bustype_name": "測試交易類型",
            "verifystate": 0,
            "isWfControlled": False,
            "followUpTime": (follow_date + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
            "followUpContext": f"下次跟進計劃：繼續跟進產品演示和報價事宜",
            "oppt": f"207491127653590631{i % 10}",
            "oppt_name": f"商機-{customer['name'][:10]}",
            "oppt_code": f"OPP{(20240827 + i):08d}",
            "contact": f"203181198410671718{i % 10}",
            "contact_name": f"聯繫人{chr(65 + i % 26)}",
            "location": f"北京市海淀區中關村大街{100 + i}號",
            "longitude": 116.241113 + (i % 100) * 0.001,
            "latitude": 40.073291 + (i % 100) * 0.001,
            "pubts": create_date.strftime("%Y-%m-%d %H:%M:%S"),
        }
        records.append(record)
    
    return {
        "code": 200,
        "message": "操作成功",
        "data": {
            "recordList": records
        }
    }

def generate_mock_followup_files(followup_id: str) -> Dict[str, Any]:
    """生成模擬的跟進記錄附件數據"""
    
    # 模擬文件列表
    files = [
        {
            "fileId": f"6565cf9f1xxa4b52490a995{i}",
            "filePath": f"https://mock-oss.example.com/files/followup_{followup_id}_{i}.png",
            "fileSize": random.randint(100000, 2000000),
            "name": f"跟進記錄附件_{i+1}.png",
            "fileName": f"attachment_{i+1}",
            "fileExtension": random.choice([".png", ".jpg", ".pdf", ".doc", ".xlsx"]),
            "yhtUserId": "30950820-8b32-b7a60c037680",
            "tenantId": "0000KN5XXXX43JE9SF0000",
            "ctime": int((datetime.now() - timedelta(days=random.randint(1, 30))).timestamp() * 1000),
            "utime": int(datetime.now().timestamp() * 1000),
            "objectId": f"206088047738014924{i}",
            "objectName": "yonbip-mkt-crm"
        }
        for i in range(random.randint(1, 5))  # 隨機1-5個文件
    ]
    
    return {
        "code": "200",
        "data": {
            followup_id: files
        }
    }

def generate_mock_save_response(followup_data: Dict[str, Any]) -> Dict[str, Any]:
    """生成模擬的跟進記錄保存響應"""
    from datetime import datetime
    import random
    
    # 生成一個新的ID
    new_id = f"207{random.randint(6169693366321156, 9999999999999999)}"
    
    # 基於輸入數據構建響應
    response_data = {
        "id": new_id,
        "code": followup_data.get("code", f"2024{datetime.now().strftime('%m%d%H%M%S')}"),
        "followContext": followup_data.get("followContext", ""),
        "followTime": followup_data.get("followTime", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "createTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "creator": followup_data.get("creator", "測試用戶"),
        "customer": followup_data.get("customer", ""),
        "customer_code": followup_data.get("customer_code", ""),
        "customer_name": followup_data.get("customer_name", "測試客戶"),
        "org": followup_data.get("org", "1884698324742176769"),
        "org_code": followup_data.get("org_code", "GROUP001"),
        "org_name": "集團",
        "dept": followup_data.get("dept", "1884699295404785664"),
        "dept_code": followup_data.get("dept_code", "DEPT01"),
        "dept_name": "銷管二部",
        "ower": followup_data.get("ower", "1884702611124256789"),
        "ower_code": followup_data.get("ower_code", "SALE001"),
        "ower_name": "銷售代表A",
        "bustype": followup_data.get("bustype", "1981914333946314761"),
        "bustype_code": followup_data.get("bustype_code", "11"),
        "bustype_name": "投標測算審批",
        "followMethodDoc": followup_data.get("followMethodDoc", "1869243606466822260"),
        "followMethodDoc_code": followup_data.get("followMethodDoc_code", "other"),
        "followMethodDoc_name": "其他",
        "verifystate": 0,
        "isWfControlled": False,
        "pubts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "_status": followup_data.get("_status", "Insert")
    }
    
    # 如果有富文本內容，添加富文本格式
    if followup_data.get("followContext"):
        response_data["followContextRichText"] = f'<div class="mdf_rich_text" forprinttag="true"><div>{followup_data["followContext"]}</div></div>'
    
    return {
        "code": 200,
        "message": "操作成功",
        "data": response_data
    }

def generate_mock_query_files_response(business_id: str) -> Dict[str, Any]:
    """生成模擬的跟進記錄附件查詢響應 - 新API格式"""
    
    # 模擬附件文件列表，返回已簽名的URL
    files = []
    num_files = random.randint(2, 6)  # 隨機2-6個文件
    
    for i in range(num_files):
        file_data = {
            "fileId": f"file_{business_id}_{i+1}_{random.randint(1000, 9999)}",
            "fileName": f"保養照片_{i+1}.jpg",
            "fileUrl": f"https://mock-signed-url.example.com/images/maintenance_{business_id}_{i+1}.jpg?signature=mock_signature_{random.randint(100000, 999999)}",
            "fileSize": random.randint(500000, 3000000),
            "uploadTime": (datetime.now() - timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d %H:%M:%S"),
            "fileType": "image/jpeg",
            "businessId": business_id
        }
        files.append(file_data)
    
    return {
        "code": 200,
        "message": "查詢成功",
        "data": files
    }

# 模擬數據開關
USE_MOCK_DATA = False  # 設置為True使用模擬數據，False使用真實API
