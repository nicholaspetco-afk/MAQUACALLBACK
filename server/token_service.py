"""Utilities for retrieving and caching YonBIP access tokens."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

import requests

try:
    import server.config as config  # type: ignore
except ImportError:  # pragma: no cover
    import server.config_example as config  # fallback for development


@dataclass
class CachedToken:
    token: str
    expires_at: float


class TokenService:
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._cache: Optional[CachedToken] = None

    def get_token(self, *, force_refresh: bool = False) -> str:
        with self._lock:
            if not force_refresh and self._cache and self._cache.expires_at > time.time():
                return self._cache.token

            token = self._fetch_token()
            # The API returns expire seconds (e.g., 7200); subtract a buffer.
            expire_seconds = getattr(self, "_last_expire", 7200)
            expires_at = time.time() + max(expire_seconds - 60, 60)
            self._cache = CachedToken(token=token, expires_at=expires_at)
            return token

    def _fetch_token(self) -> str:
        timestamp = str(int(time.time() * 1000))
        params = {"appKey": config.APP_KEY, "timestamp": timestamp}
        signature = self._build_signature(params, config.APP_SECRET)
        params["signature"] = signature

        url = config.TOKEN_URL.rstrip("/") + config.SELF_APP_TOKEN_PATH
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "00000":
            raise RuntimeError(f"Failed to fetch token: {data}")
        token_data = data.get("data", {})
        token = token_data.get("access_token")
        if not token:
            raise RuntimeError("Token missing in response")
        self._last_expire = int(token_data.get("expire", 7200))  # type: ignore[attr-defined]
        return token

    @staticmethod
    def _build_signature(params: dict[str, str], secret: str) -> str:
        # 根據用友官方示例：params = "appKey{}timestamp{}".format(app_key,ts)
        app_key = params.get("appKey", "")
        timestamp = params.get("timestamp", "")
        to_sign = f"appKey{app_key}timestamp{timestamp}"
        digest = TokenService._hmac_sha256(secret, to_sign)
        return digest

    @staticmethod
    def _hmac_sha256(secret: str, message: str) -> str:
        import base64
        import hashlib
        import hmac

        digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")


TOKEN_SERVICE = TokenService()
