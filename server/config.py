from .config_example import *  # noqa: F401,F403

# Prefer exact lookups on the official customer code field; fall back to
# alternate field names only when必要.
FOLLOWUP_CUSTOMER_FIELD = "customer.code"
FOLLOWUP_CUSTOMER_OPERATOR = "eq"
FOLLOWUP_CUSTOMER_FIELD_FALLBACKS = [
    "customer.code",
    "customer.customerCode",
    "customer_code",
]

# Tasks use the same strict code matching to避免交叉客戶。
TASK_CUSTOMER_FIELD = "customer.code"
TASK_CUSTOMER_OPERATOR = "eq"

# Maintenance settings
MAINTENANCE_NEXT_DATE_OFFSET_DAYS = 14
MAINTENANCE_TASK_OWNER_KEYWORD = "客服003"
# Optional constraint on how far future tasks can be. None means no limit.
MAINTENANCE_TASK_MAX_GAP_DAYS = None
