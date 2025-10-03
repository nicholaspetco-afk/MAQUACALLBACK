"""Flask application exposing simplified endpoints for CRM follow-up assets."""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from flask import Flask, jsonify, request, send_from_directory, send_file

try:
    import server.config as config  # type: ignore
except ImportError:  # pragma: no cover
    import server.config_example as config  # type: ignore

from server.crm_client import CRM_CLIENT
from server.token_service import TOKEN_SERVICE

ROOT_DIR = Path(__file__).resolve().parent.parent

app = Flask(__name__)
app.logger.setLevel("DEBUG")


@app.route("/")
def index_page() -> Any:  # pragma: no cover - static file helper
    return send_from_directory(ROOT_DIR, "index.html")


@app.route("/report.html")
def report_page() -> Any:  # pragma: no cover - static file helper
    return send_from_directory(ROOT_DIR, "report.html")


@app.route("/records.html")
def records_page() -> Any:  # pragma: no cover - static file helper
    return send_from_directory(ROOT_DIR, "records.html")


@app.route("/members.html")
def members_page() -> Any:  # pragma: no cover - static file helper
    return send_file(ROOT_DIR / "MAQUA會員制" / "index.html")


@app.route("/members.css")
def members_style() -> Any:  # pragma: no cover - static file helper
    return send_from_directory(str(ROOT_DIR / "MAQUA會員制"), "members.css")


@app.route("/style.css")
def style_file() -> Any:  # pragma: no cover - static file helper
    return send_from_directory(ROOT_DIR, "style.css")


@app.route("/assets/<path:filename>")
def assets_file(filename: str) -> Any:  # pragma: no cover - static file helper
    return send_from_directory(ROOT_DIR / "assets", filename)


@app.route("/api/token")
def api_token() -> Any:  # pragma: no cover - debug endpoint
    token = TOKEN_SERVICE.get_token(force_refresh=request.args.get("refresh") == "1")
    return jsonify({"access_token": token})


@app.route("/api/followups", methods=["POST"])
def api_save_followup() -> Any:
    """保存跟進記錄"""
    try:
        # 獲取請求數據
        request_data = request.get_json()
        if not request_data:
            return jsonify({"code": 400, "message": "請求數據不能為空"}), 400
        
        # 驗證必填字段
        required_fields = ["followContext", "code", "followTime", "org", "_status"]
        for field in required_fields:
            if field not in request_data:
                return jsonify({"code": 400, "message": f"缺少必填字段: {field}"}), 400
        
        # 調用CRM客戶端保存跟進記錄
        result = CRM_CLIENT.save_followup(request_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"code": 500, "message": f"保存失敗: {str(e)}"}), 500


@app.route("/api/customers/<customer_code>/followups")
def api_customer_followups(customer_code: str) -> Any:
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", config.DEFAULT_PAGE_SIZE))
    identifier = str(customer_code or "").strip()

    def _looks_like_phone(text: str) -> bool:
        digits = [ch for ch in text if ch.isdigit()]
        if len(digits) < 6:
            return False
        non_digits = [ch for ch in text if not (ch.isdigit() or ch in {"+", "-", " ", "#"})]
        return len(non_digits) <= 3

    search_kwargs: Dict[str, Any] = {}
    search_mode = "code"
    search_field_used: Optional[str] = None
    if _looks_like_phone(identifier):
        search_kwargs = {"search_field": "customer.name", "search_operator": "like"}
        search_mode = "phone"

    followup_data = CRM_CLIENT.get_followups(
        identifier,
        page=page,
        page_size=page_size,
        **search_kwargs,
    )
    search_field_used = search_kwargs.get("search_field") or config.FOLLOWUP_CUSTOMER_FIELD
    meta = followup_data.get("_meta") if isinstance(followup_data, dict) else None
    if isinstance(meta, dict) and meta.get("searchField"):
        search_field_used = meta.get("searchField")
    filter_info: Dict[str, Any] = {
        "expected": identifier,
        "searchMode": search_mode,
        "searchField": search_field_used,
    }

    # Guardrail: If backend uses fuzzy matching (e.g., LIKE), restrict to exact code here
    resolved_code: Optional[str] = None
    suggestions: List[str] = []
    try:
        raw_list = (
            followup_data.get("data", {}).get("recordList", []) or []
        )
        if search_mode == "phone" and not raw_list:
            fallback_field = "customer.name"
            followup_data = CRM_CLIENT.get_followups(
                identifier,
                page=page,
                page_size=page_size,
                search_field=fallback_field,
                search_operator="like",
            )
            raw_list = (
                followup_data.get("data", {}).get("recordList", []) or []
            )
            if raw_list:
                search_field_used = fallback_field
                filter_info["searchField"] = fallback_field
                filter_info["searchFallback"] = fallback_field
        else:
            filter_info["searchField"] = search_field_used
        expected = str(identifier or "").strip().upper()
        detail_cache: Dict[Tuple[str, str], str] = {}
        detail_hits = 0

        def _is_code_like(text: str) -> bool:
            return any(ch.isalpha() for ch in text)

        def _matches_code(item: Dict[str, Any], expected_code: str) -> bool:
            # Common flat fields
            for key in ("customer_code", "customerCode"):
                val = str(item.get(key) or "").strip().upper()
                if val and val == expected_code:
                    return True
            # Some payloads put the code in 'customer' (while IDs are usually numeric)
            cust = item.get("customer")
            if isinstance(cust, str):
                val = cust.strip().upper()
                if val and _is_code_like(val) and val == expected_code:
                    return True
            # Nested structure fallback (rare)
            nested = _extract_nested(item, "customer.code")
            if isinstance(nested, str) and nested.strip().upper() == expected_code:
                return True
            # Sometimes code is embedded in name like "C4021偉業行貿易公司..."
            for key in ("customer_name", "customer.name", "customerName"):
                name_val = item.get(key) if "." not in key else _extract_nested(item, key)
                if isinstance(name_val, str) and name_val:
                    m = CODE_TOKEN_RE.search(name_val.upper())
                    if m and m.group(0) == expected_code:
                        return True
            # Fallback: query customer detail to retrieve authoritative code
            cust_id = item.get("customer")
            org_id = item.get("org")
            if cust_id:
                key = (str(cust_id), str(org_id or ""))
                if key not in detail_cache:
                    try:
                        if not org_id:
                            raise ValueError("missing org id for customer detail lookup")
                        detail_resp = CRM_CLIENT.get_customer_detail(str(cust_id), str(org_id))
                        detail_data = detail_resp.get("data") or {}
                        detail_code = str(detail_data.get("code") or "").strip().upper()
                        detail_cache[key] = detail_code
                    except Exception as exc:  # pragma: no cover - runtime diagnostics
                        app.logger.debug(
                            "[Filter] detail lookup failed for %s/%s: %s",
                            cust_id,
                            org_id,
                            exc,
                        )
                        detail_cache[key] = ""
                detail_code = detail_cache.get(key, "")
                if detail_code and detail_code == expected_code:
                    nonlocal detail_hits
                    detail_hits += 1
                    return True
            return False

        raw_codes: Set[str] = set()
        raw_examples: List[Dict[str, Any]] = []
        for item in raw_list:
            candidate = ""
            for key in ("customer_code", "customerCode"):
                value = item.get(key)
                if value:
                    candidate = str(value).strip().upper()
                    break
            if not candidate:
                nested_code = _extract_nested(item, "customer.code")
                if isinstance(nested_code, str):
                    candidate = nested_code.strip().upper()
            if not candidate and isinstance(item.get("customer"), str):
                candidate = str(item.get("customer")).strip().upper()
            if candidate:
                raw_codes.add(candidate)

            if len(raw_examples) < 10:
                raw_examples.append({
                    "customer_code": candidate,
                    "customer": item.get("customer"),
                    "customer_name": item.get("customer_name"),
                    "ower_name": item.get("ower_name"),
                    "followTime": item.get("followTime") or item.get("followUpTime"),
                })

        detail_unique = sorted({code for code in detail_cache.values() if code})

        if expected and raw_list:
            exact_list = [it for it in raw_list if _matches_code(it, expected)]

            def _detail_code(item: Dict[str, Any]) -> str:
                cust_id = item.get("customer")
                org_id = item.get("org")
                if not cust_id:
                    return ""
                key = (str(cust_id), str(org_id or ""))
                return detail_cache.get(key, "")

            if not exact_list:
                prefix_candidates = [code for code in detail_unique if code.startswith(expected)]
                if search_mode == "phone" and detail_unique:
                    resolved_code = detail_unique[0]
                    suggestions = detail_unique
                    exact_list = [
                        item for item in raw_list if _detail_code(item) == resolved_code
                    ]
                elif prefix_candidates:
                    resolved_code = prefix_candidates[0]
                    suggestions = prefix_candidates
                    exact_list = [
                        item for item in raw_list if _detail_code(item) == resolved_code
                    ]
                else:
                    suggestions = detail_unique

            if exact_list:
                resolved_code = resolved_code or expected

            data_obj = dict(followup_data.get("data") or {})
            data_obj["recordList"] = exact_list  # 即使為空也覆蓋，避免混入近似代碼
            followup_data = dict(followup_data)
            followup_data["data"] = data_obj
            app.logger.debug(
                "[Filter] exact match kept %s of %s records for %s",
                len(exact_list), len(raw_list), expected,
            )
            detail_examples = [
                {
                    "customer": key[0],
                    "org": key[1],
                    "code": detail_cache.get(key, ""),
                }
                for key in list(detail_cache)[:10]
            ]
            filter_info.update({
                "rawCount": len(raw_list),
                "kept": len(exact_list),
                "rawUniqueCodes": sorted(raw_codes),
                "rawExamples": raw_examples,
                "detailLookupCount": len(detail_cache),
                "detailMatches": detail_hits,
                "detailUniqueCodes": detail_unique,
                "detailExamples": detail_examples,
                "resolvedCode": resolved_code,
                "suggestedCodes": suggestions,
            })
        else:
            detail_examples = [
                {
                    "customer": key[0],
                    "org": key[1],
                    "code": detail_cache.get(key, ""),
                }
                for key in list(detail_cache)[:10]
            ]
            filter_info.update({
                "rawCount": len(raw_list),
                "kept": 0,
                "rawUniqueCodes": sorted(raw_codes),
                "rawExamples": raw_examples,
                "detailLookupCount": len(detail_cache),
                "detailMatches": detail_hits,
                "detailUniqueCodes": detail_unique,
                "detailExamples": detail_examples,
                "resolvedCode": resolved_code,
                "suggestedCodes": suggestions,
            })
    except Exception as _exc:  # pragma: no cover - defensive
        app.logger.debug("[Filter] skip exact filter due to: %s", _exc)
        filter_info["error"] = str(_exc)

    target_customer_code = resolved_code or customer_code

    task_records: List[Dict[str, Any]] = []
    task_page_size = getattr(config, "DEFAULT_TASK_PAGE_SIZE", config.DEFAULT_PAGE_SIZE)
    if getattr(config, "TASK_LIST_PATH", ""):
        try:
            tasks_response = CRM_CLIENT.get_tasks(target_customer_code, page=1, page_size=task_page_size)
            task_records = (
                tasks_response.get("data", {}).get("recordList", []) or []
            )
        except Exception as exc:  # pragma: no cover - runtime debug only
            app.logger.warning("[Task] lookup failed for %s: %s", customer_code, exc)

    offset_days = getattr(config, "MAINTENANCE_NEXT_DATE_OFFSET_DAYS", 0)
    records: List[Dict[str, Any]] = []
    for item in followup_data.get("data", {}).get("recordList", []):
        owner = str(item.get("ower_name") or "")
        if "維修幫" not in owner:
            continue

        followup_id = str(item.get(config.FOLLOWUP_ID_FIELD, ""))
        service_date = _extract_nested(item, getattr(config, "FOLLOWUP_SERVICE_DATE_FIELD", ""))
        next_date = _extract_nested(item, getattr(config, "FOLLOWUP_NEXT_SERVICE_DATE_FIELD", ""))
        if not service_date:
            service_date = item.get("followTime") or item.get("followUpTime")
        if not next_date:
            next_date = item.get("nextFollowUpTime") or None

        service_date_obj = _parse_follow_date(service_date)
        if not service_date_obj:
            service_date_obj = _parse_follow_date(item.get("followTime") or item.get("followUpTime"))
        next_date_obj = _parse_follow_date(next_date)
        if offset_days and next_date_obj:
            next_date_obj = next_date_obj + timedelta(days=offset_days)

        photo_ids = _collect_photo_ids(item)
        app.logger.debug("[Followup] %s photo candidates: %s", followup_id, photo_ids)
        files: List[Dict[str, Any]] = []
        if photo_ids:
            try:
                files_response = CRM_CLIENT.query_followup_files(photo_ids)
            except RuntimeError as exc:
                app.logger.warning(
                    "[Followup] %s photo lookup failed: %s", followup_id, exc
                )
                files_response = {"data": {}}
            files = _extract_query_files(files_response, photo_ids)
            app.logger.debug("[Followup] %s fetched %s files", followup_id, len(files))

        photos, documents = _split_files(files)
        if not photos:
            continue

        records.append({
            "followupId": followup_id,
            "serviceDate": _date_to_iso(service_date_obj) or service_date,
            "nextServiceDate": _date_to_iso(next_date_obj) or next_date,
            "raw": item,
            "files": files,
            "photos": photos,
            "documents": documents,
        })

    records_with_photos = [rec for rec in records if rec["photos"]]
    if records_with_photos:
        records = [records_with_photos[0]]

    summary = _extract_maintenance_summary(target_customer_code, followup_data, task_records)
    if summary:
        if resolved_code and summary.get("customerCode") != resolved_code:
            summary["customerCode"] = resolved_code
        if offset_days:
            shifted_summary_next = _shift_date_string(summary.get("nextServiceDate"), offset_days)
            if shifted_summary_next:
                summary["nextServiceDate"] = shifted_summary_next

    upcoming_date = summary.get("nextServiceDate") if summary else None
    if upcoming_date:
        for record in records:
            if not record.get("nextServiceDate"):
                record["nextServiceDate"] = upcoming_date
            elif offset_days:
                shifted_record_next = _shift_date_string(record.get("nextServiceDate"), offset_days)
                if shifted_record_next:
                    record["nextServiceDate"] = shifted_record_next

    return jsonify({
        "code": "OK",
        "customerCode": customer_code,
        "resolvedCustomerCode": resolved_code,
        "suggestedCodes": suggestions,
        "records": records,
        "raw": followup_data,
        "tasks": task_records,
        "summary": summary,
        "filterInfo": filter_info,
    })


@app.route("/api/members/profile", methods=["POST"])
def api_members_profile() -> Any:
    payload = request.get_json(silent=True) or {}
    identifier = str(payload.get("identifier", "")).strip()
    if not identifier:
        return jsonify({"message": "請輸入客戶編碼或電話"}), 400

    try:
        profile = _build_member_profile(identifier)
    except LookupError as exc:
        return jsonify({"message": str(exc)}), 404
    except Exception as exc:  # pragma: no cover - runtime logging
        app.logger.exception("Failed to build member profile")
        return jsonify({"message": "查詢時發生錯誤，請稍後再試。"}), 500

    return jsonify({"code": "OK", "profile": profile})


def _extract_files(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    data = response.get("data")
    items: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        if "list" in data:
            items = data.get("list", [])
        elif "bussinessId" in data:
            items = data.get("bussinessId", [])
    elif isinstance(data, list):
        items = data

    for entry in items:
        file_url = (
            entry.get("filePath")
            or entry.get("url")
            or entry.get("fileUrl")
            or entry.get("previewUrl")
        )
        file_id = entry.get("fileId") or entry.get("id")
        if not file_url and file_id:
            if config.FILE_DOWNLOAD_PATH:
                try:
                    file_url = CRM_CLIENT.get_file_download_url(str(file_id))
                except Exception:  # pragma: no cover - optional fallback
                    file_url = None
        files.append({
            "fileId": file_id,
            "fileName": entry.get("fileName") or entry.get("name"),
            "fileUrl": file_url,
            "raw": entry,
        })
    return files


def _extract_query_files(
    response: Dict[str, Any], requested_ids: List[str] | None = None
) -> List[Dict[str, Any]]:
    """從 query_followup_files API 響應中提取文件信息"""
    files: List[Dict[str, Any]] = []
    data = response.get("data", [])

    items: List[Dict[str, Any]] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        keys = requested_ids or list(data.keys())
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                items.extend(value)
    elif isinstance(data, (tuple, set)):
        items = [entry for entry in data if isinstance(entry, dict)]

    for entry in items:
        file_url = (
            entry.get("signedUrl")
            or entry.get("fileUrl")
            or entry.get("url")
            or entry.get("filePath")
        )

        files.append({
            "fileId": entry.get("fileId") or entry.get("id"),
            "fileName": entry.get("fileName") or entry.get("name"),
            "fileUrl": file_url,
            "fileSize": entry.get("fileSize"),
            "uploadTime": entry.get("uploadTime"),
            "fileType": entry.get("fileType"),
            "fileExtension": _guess_extension(entry),
            "raw": entry,
        })
    return files


def _collect_photo_ids(record: Dict[str, Any]) -> List[str]:
    """從跟進紀錄中提取照片欄位（picture1~picture5）的附件 ID。"""
    candidates: List[str] = []
    seen: set[str] = set()

    def _push(value: Any) -> None:
        if value in (None, ""):
            return
        if isinstance(value, (list, tuple, dict)):
            return
        text = str(value).strip()
        if not text or text.lower() in {"none", "null"}:
            return
        if not _looks_like_attachment_id(text):
            return
        if text in seen:
            return
        seen.add(text)
        candidates.append(text)

    for picture_key in ("picture1", "picture2", "picture3", "picture4", "picture5"):
        _push(record.get(picture_key))

    return candidates


def _looks_like_attachment_id(text: str) -> bool:
    if len(text) < 8:
        return False
    allowed = set("0123456789abcdefABCDEF-")
    return all(ch in allowed for ch in text)


def _split_files(files: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    photos: List[Dict[str, Any]] = []
    documents: List[Dict[str, Any]] = []

    for file in files:
        if _is_image_file(file):
            photos.append(file)
        else:
            documents.append(file)

    return photos, documents


def _is_image_file(file_entry: Dict[str, Any]) -> bool:
    extension = (file_entry.get("fileExtension") or "").lower()
    name = (file_entry.get("fileName") or file_entry.get("name") or "").lower()

    for candidate in (extension, name):
        if candidate.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic")):
            return True
    return False


def _guess_extension(entry: Dict[str, Any]) -> str:
    for key in ("fileExtension", "extension"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value

    name = entry.get("fileName") or entry.get("name")
    if isinstance(name, str) and '.' in name:
        return name[name.rfind('.'):]
    return ""


def _extract_nested(source: Dict[str, Any], path: str) -> Any:
    if not path:
        return None
    current: Any = source
    for part in path.split('.'):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


DATE_PATTERN = re.compile(
    r"(?P<year>19\d{2}|20\d{2})[年\-/.](?P<month>\d{1,2})[月\-/.](?P<day>\d{1,2})"
)

# 標準化用友客戶代碼的偵測（本專案中常見如 C3770、C402 等）
CODE_TOKEN_RE = re.compile(r"\bC\d{2,}\b", re.IGNORECASE)


def _shift_date_string(value: Optional[str], days: int) -> Optional[str]:
    if not value or not days:
        return value
    text = str(value).strip()
    if not text:
        return value
    base_part = text.split('T')[0].split(' ')[0].replace('/', '-').strip()
    try:
        parsed = date.fromisoformat(base_part)
    except ValueError:
        return value
    shifted = parsed + timedelta(days=days)
    return shifted.isoformat()


def _parse_follow_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    base_part = text.split('T')[0].split(' ')[0].replace('/', '-').strip()
    try:
        return date.fromisoformat(base_part)
    except ValueError:
        return None


def _date_to_iso(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if isinstance(value, date) else None


def _select_task_base_date(
    task_records: List[Dict[str, Any]],
    owner_keyword: Optional[str],
    latest_date: Optional[date],
    previous_date: Optional[date],
) -> Optional[date]:
    if not task_records:
        return None

    today = date.today()
    owner_future_today: List[date] = []
    owner_future_latest: List[date] = []
    owner_past: List[date] = []
    general_future_today: List[date] = []
    general_future_latest: List[date] = []
    general_past: List[date] = []

    for task in task_records:
        start = _parse_follow_date(task.get("startDate")) or _parse_follow_date(task.get("planDate"))
        if not start:
            start = _parse_follow_date(task.get("endDate"))
        if not start:
            continue

        bucket_future_today = owner_future_today if owner_keyword and owner_keyword in str(task.get("ower_name") or "") else general_future_today
        bucket_future_latest = owner_future_latest if owner_keyword and owner_keyword in str(task.get("ower_name") or "") else general_future_latest
        bucket_past = owner_past if owner_keyword and owner_keyword in str(task.get("ower_name") or "") else general_past

        if start > today:
            bucket_future_today.append(start)
        elif latest_date and start > latest_date:
            bucket_future_latest.append(start)
        else:
            bucket_past.append(start)

    if owner_future_today:
        return min(owner_future_today)
    if general_future_today:
        return min(general_future_today)
    if owner_future_latest:
        return min(owner_future_latest)
    if general_future_latest:
        return min(general_future_latest)
    if owner_past:
        owner_past.sort(reverse=True)
        return owner_past[0]
    if general_past:
        general_past.sort(reverse=True)
        return general_past[0]
    return previous_date


def _extract_maintenance_summary(
    customer_code: str,
    followup_data: Dict[str, Any],
    task_records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Optional[str]]:
    record_list: List[Dict[str, Any]] = (
        followup_data.get("data", {}).get("recordList", []) or []
    )

    maintenance = [
        item for item in record_list if "維修幫" in str(item.get("ower_name") or "")
    ]

    owner_keyword = getattr(config, "MAINTENANCE_TASK_OWNER_KEYWORD", None)

    parsed_records: List[tuple[Dict[str, Any], date]] = []
    for item in maintenance:
        parsed = _parse_follow_date(item.get("followTime"))
        if parsed:
            parsed_records.append((item, parsed))

    task_records = task_records or []

    if not parsed_records:
        task_date_iso = _extract_upcoming_task_date(
            task_records,
            reference_date=date.today(),
            owner_keyword=owner_keyword,
            max_gap_days=getattr(config, "MAINTENANCE_TASK_MAX_GAP_DAYS", None),
        )
        task_date = _parse_follow_date(task_date_iso)
        return {
            "customerCode": customer_code,
            "customerName": None,
            "latestServiceDate": None,
            "previousServiceDate": None,
            "nextServiceDate": _date_to_iso(task_date),
        }

    parsed_records.sort(key=lambda entry: entry[1], reverse=True)
    today = date.today()

    latest_index = 0
    for idx, (_, record_date) in enumerate(parsed_records):
        if record_date <= today:
            latest_index = idx
            break

    latest_item, latest_date = parsed_records[latest_index]
    previous_item, previous_date = (None, None)
    if latest_index + 1 < len(parsed_records):
        previous_item, previous_date = parsed_records[latest_index + 1]

    task_date = _select_task_base_date(
        task_records,
        owner_keyword,
        latest_date,
        previous_date,
    )

    next_base_date: Optional[date] = task_date or previous_date or latest_date

    customer_name = str(latest_item.get("customer_name") or "") or None

    previous_norm = _date_to_iso(previous_date)
    return {
        "customerCode": customer_code,
        "customerName": customer_name,
        "latestServiceDate": _date_to_iso(latest_date),
        "previousServiceDate": previous_norm,
        "nextServiceDate": _date_to_iso(next_base_date),
    }


def _build_member_profile(identifier: str) -> Dict[str, Any]:
    followup_resp = CRM_CLIENT.get_followups(identifier, page=1, page_size=config.DEFAULT_PAGE_SIZE)
    record_list: List[Dict[str, Any]] = (
        followup_resp.get("data", {}).get("recordList", []) or []
    )

    maintenance_records = [
        item for item in record_list
        if "維修幫" in str(item.get("ower_name") or "")
    ]

    candidate_records = maintenance_records if maintenance_records else record_list

    if not candidate_records:
        return {
            "customerCode": customer_code,
            "customerName": None,
            "latestServiceDate": None,
            "previousServiceDate": None,
        }

    candidate_records.sort(
        key=lambda item: (item.get("followTime") or ""), reverse=True
    )

    latest = candidate_records[0]
    previous = candidate_records[1] if len(candidate_records) > 1 else None

    def _format_date(item: Optional[Dict[str, Any]]) -> Optional[str]:
        if not item:
            return None
        value = item.get("followTime") or ""
        return value.split(" ")[0] if value else None

    customer_id = str(latest.get("customer") or "")
    org_id = str(latest.get("org") or "")

    detail_data: Dict[str, Any] = {}
    addresses: List[Dict[str, Any]] = []

    if customer_id and org_id:
        detail_resp = CRM_CLIENT.get_customer_detail(customer_id, org_id)
        detail_data = detail_resp.get("data") or {}
        addresses = detail_data.get("merchantAddressInfos") or []

        if (not addresses) and detail_data.get("code"):
            addr_resp = CRM_CLIENT.get_addresses_by_codes([detail_data["code"]])
            addresses = addr_resp.get("data") or []

    selected_address = None
    if isinstance(addresses, list) and addresses:
        for item in addresses:
            if item.get("isDefault"):
                selected_address = item
                break
        if not selected_address:
            selected_address = addresses[0]

    address_text = None
    contact_name = None
    contact_phone = None
    if isinstance(selected_address, dict):
        address_text = (
            selected_address.get("mergerName")
            or selected_address.get("address")
            or selected_address.get("addressInfo")
        )
        contact_name = selected_address.get("receiver")
        contact_phone = selected_address.get("mobile") or selected_address.get("telePhone")

    profile = {
        "keyword": identifier,
        "customerCode": detail_data.get("code"),
        "customerName": (
            (detail_data.get("name") or {}).get("zh_CN")
            or detail_data.get("enterpriseName")
            or (latest.get("customer_name") if isinstance(latest, dict) else None)
        ),
        "latestServiceDate": _format_date(latest),
        "previousServiceDate": _format_date(previous),
        "address": address_text,
        "contact": {
            "name": contact_name,
            "phone": contact_phone,
        },
        "points": None,
    }

    return profile


if __name__ == "__main__":  # pragma: no cover
    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", "5000"))
    except ValueError:
        port = 5000
    debug = os.getenv("FLASK_DEBUG", "1") not in {"0", "false", "False"}
    app.run(host=host, port=port, debug=debug)
