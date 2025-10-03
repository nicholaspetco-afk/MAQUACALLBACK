"""Client for calling YonBIP CRM APIs."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

import requests

try:
    import server.config as config  # type: ignore
except ImportError:  # pragma: no cover
    import server.config_example as config

from server.token_service import TOKEN_SERVICE

# 導入模擬數據模塊
try:
    from . import mock_data
except ImportError:
    import mock_data


class CRMClient:
    def __init__(self) -> None:
        self.gateway_url = config.GATEWAY_URL.rstrip("/")

    def _request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None,
                 json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self.gateway_url + path
        token = TOKEN_SERVICE.get_token()
        req_params = {"access_token": token}
        if params:
            req_params.update(params)
        resp = requests.request(method, url, params=req_params, json=json_body, timeout=15)
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            details: Any
            try:
                details = resp.json()
            except ValueError:  # pragma: no cover
                details = resp.text
            raise RuntimeError(
                f"HTTP {resp.status_code} calling {path}: {json.dumps(details, ensure_ascii=False)}"
            ) from exc

        data = resp.json()
        if data.get("code") not in {"00000", "200", 200, "200000"}:
            raise RuntimeError(f"CRM API error: {json.dumps(data, ensure_ascii=False)}")
        return data

    def get_followups(
        self,
        customer_code: str = "",
        page: int = 1,
        page_size: int = 10,
        *,
        search_field: Optional[str] = None,
        search_operator: Optional[str] = None,
    ) -> Dict[str, Any]:
        """獲取跟進記錄列表"""
        
        # 檢查是否使用模擬數據
        if getattr(mock_data, "USE_MOCK_DATA", False):
            print("使用模擬數據返回跟進記錄")
            return mock_data.generate_mock_followup_data(customer_code, page, page_size)
        
        # 原有的真實API調用邏輯
        payload = {
            "pageIndex": page,
            "pageSize": page_size,
        }
        
        # 如果指定了客戶代碼，添加查詢條件
        if customer_code:
            primary_field = search_field or config.FOLLOWUP_CUSTOMER_FIELD
            operator = search_operator or config.FOLLOWUP_CUSTOMER_OPERATOR
            field_candidates = [primary_field]
            fallback_fields = getattr(config, "FOLLOWUP_CUSTOMER_FIELD_FALLBACKS", [])
            for candidate in fallback_fields:
                if candidate not in field_candidates:
                    field_candidates.append(candidate)

            last_response: Dict[str, Any] = {}
            for candidate_field in field_candidates:
                payload_attempt = dict(payload)
                payload_attempt["simpleVOs"] = [
                    {
                        "field": candidate_field,
                        "op": operator,
                        "value1": customer_code,
                    }
                ]

                response = self._request("POST", config.FOLLOWUP_LIST_PATH, json_body=payload_attempt)
                last_response = response
                record_list = response.get("data", {}).get("recordList", [])
                if record_list:
                    response.setdefault("_meta", {})["searchField"] = candidate_field
                    return response

            if last_response:
                last_response.setdefault("_meta", {})["searchField"] = field_candidates[-1]
                return last_response
            return self._request("POST", config.FOLLOWUP_LIST_PATH, json_body=payload)

        return self._request("POST", config.FOLLOWUP_LIST_PATH, json_body=payload)

    def get_followup_files(self, followup_id: str) -> Dict[str, Any]:
        """獲取跟進記錄的附件信息"""
        
        # 檢查是否使用模擬數據
        if getattr(mock_data, "USE_MOCK_DATA", False):
            print("使用模擬數據返回跟進記錄附件")
            return mock_data.generate_mock_followup_files(followup_id)
        
        # 原有的真實API調用邏輯
        payload = {"businessIds": [followup_id]}
        return self._request("POST", config.FOLLOWUP_FILES_PATH, json_body=payload)

    def query_followup_files(self, business_ids: Iterable[str]) -> Dict[str, Any]:
        """批次查詢跟進記錄附件信息"""

        # 檢查是否使用模擬數據
        if getattr(mock_data, "USE_MOCK_DATA", False):
            print("使用模擬數據返回跟進記錄附件查詢結果")
            first_id = next(iter(business_ids), "")
            return mock_data.generate_mock_query_files_response(first_id)

        # 根據用戶提供的API文檔格式
        payload = {"businessIds": list(business_ids)}
        return self._request("POST", config.FOLLOWUP_QUERY_FILES_PATH, json_body=payload)

    def get_tasks(
        self, customer_code: str = "", page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """查詢任務（排程），用於推算下次保養日期。"""

        task_path = getattr(config, "TASK_LIST_PATH", "").strip()
        if not task_path:
            raise RuntimeError("TASK_LIST_PATH is not configured")

        payload: Dict[str, Any] = {
            "pageIndex": page,
            "pageSize": page_size,
        }

        if customer_code:
            field = getattr(config, "TASK_CUSTOMER_FIELD", "customer.name")
            operator = getattr(config, "TASK_CUSTOMER_OPERATOR", "like")
            filter_payload: Dict[str, Any] = {
                "field": field,
                "op": operator,
                "value1": customer_code,
            }
            if operator == "between":
                filter_payload.setdefault("value2", customer_code)
            payload["simpleVOs"] = [filter_payload]

        return self._request("POST", task_path, json_body=payload)

    def save_followup(self, followup_data: Dict[str, Any]) -> Dict[str, Any]:
        """保存跟進記錄"""

        # 檢查是否使用模擬數據
        if getattr(mock_data, "USE_MOCK_DATA", False):
            print("使用模擬數據保存跟進記錄")
            return mock_data.generate_mock_save_response(followup_data)

        # 構建請求體，根據API文檔格式
        payload = {
            "data": followup_data,
            "systemSource": "followupOpenAPIAdd"
        }

        return self._request("POST", config.FOLLOWUP_SAVE_PATH, payload)

    def get_customer_detail(self, customer_id: str, org_id: str) -> Dict[str, Any]:
        params = {"id": customer_id, "orgId": org_id}
        return self._request("GET", config.CUSTOMER_DETAIL_PATH, params=params)

    def get_addresses_by_codes(self, codes: Iterable[str]) -> Dict[str, Any]:
        codes_list = list(codes)
        payload = {
            "codeList": codes_list,
            "pageIndex": 1,
            "pageSize": max(len(codes_list), 1),
        }
        return self._request("POST", config.CUSTOMER_ADDRESS_LIST_PATH, json_body=payload)

    def get_file_download_url(self, file_id: str) -> str:
        # Some APIs return preview URL directly. If not, use this endpoint.
        if not config.FILE_DOWNLOAD_PATH:
            raise RuntimeError("FILE_DOWNLOAD_PATH is not configured")
        params = {"fileId": file_id}
        data = self._request("GET", config.FILE_DOWNLOAD_PATH, params=params)
        file_url = data.get("data")
        if isinstance(file_url, dict):
            file_url = file_url.get("url") or file_url.get("downloadUrl")
        if not file_url:
            raise RuntimeError("Download URL not found in response")
        return file_url


CRM_CLIENT = CRMClient()
