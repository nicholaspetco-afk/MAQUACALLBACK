"""Configuration template for CRM integration."""

# YonBIP OpenAPI credentials
APP_KEY = "5eb18c62078542728cf3c63f34906775"
APP_SECRET = "aee93787cf51f588766183987331fe6d11bfd234"
TENANT_ID = "i65qty77"  # optional for self app; used for data center lookup
TOKEN_URL = "https://c2.yonyoucloud.com/iuap-api-auth"
GATEWAY_URL = "https://c2.yonyoucloud.com/iuap-api-gateway"

# Field mapping for follow-up records
FOLLOWUP_SERVICE_DATE_FIELD = "followUpTime"  # adjust to actual field name
FOLLOWUP_NEXT_SERVICE_DATE_FIELD = "nextFollowUpTime"
FOLLOWUP_ID_FIELD = "id"
FOLLOWUP_CUSTOMER_FIELD = "customer.name"  # API要求使用xxx.name或xxx.code查詢
FOLLOWUP_CUSTOMER_OPERATOR = "like"  # 以客戶編碼部分匹配

# Task (任務) 列表 API，用於推算下次保養日期
TASK_LIST_PATH = "/yonbip/crm/task/list"
TASK_CUSTOMER_FIELD = "customer.name"
TASK_CUSTOMER_OPERATOR = "like"

# API relative paths
DATA_CENTER_PATH = "/open-auth/dataCenter/getGatewayAddress"
SELF_APP_TOKEN_PATH = "/open-auth/selfAppAuth/base/v1/getAccessToken"
FOLLOWUP_LIST_PATH = "/yonbip/crm/followup/list"
FOLLOWUP_FILES_PATH = "/yonbip/crm/rest/v1/openapi/queryBusinessFiles_followrecord"
FOLLOWUP_SAVE_PATH = "/yonbip/crm/bill/followupsave"  # 跟進記錄保存API
FOLLOWUP_QUERY_FILES_PATH = "/yonbip/crm/rest/v1/openapi/queryBusinessFiles_followrecord"  # 跟進記錄附件查詢API
# Customer detail & address APIs
CUSTOMER_DETAIL_PATH = "/yonbip/crm/customer/getbyid"
CUSTOMER_ADDRESS_LIST_PATH = "/yonbip/digitalModel/merchant/listaddressbycodelist"
# FILE_DOWNLOAD_PATH 保留以便必要時額外調用
FILE_DOWNLOAD_PATH = None

# Default pagination when querying follow-up records
DEFAULT_PAGE_SIZE = 20
DEFAULT_TASK_PAGE_SIZE = 50
