"""
쿠팡파트너스 Open API 래퍼
- 상품 검색 (키워드 기반)
- 딥링크(제휴링크) 생성
인증 방식: HMAC-SHA256 서명 (CEA algorithm)
"""

import os
import hmac
import hashlib
import requests
from datetime import datetime, timezone
from urllib.parse import urlencode

DOMAIN = "https://api-gateway.coupang.com"


def _generate_hmac(method: str, path: str, query: str, secret_key: str, access_key: str) -> str:
    datetime_gmt = datetime.now(timezone.utc).strftime("%y%m%d") + "T" + \
        datetime.now(timezone.utc).strftime("%H%M%S") + "Z"
    message = datetime_gmt + method + path + query
    signature = hmac.new(
        bytes(secret_key, "utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return (
        f"CEA algorithm=HmacSHA256, access-key={access_key}, "
        f"signed-date={datetime_gmt}, signature={signature}"
    )


class CoupangPartnersClient:
    def __init__(self, access_key: str = None, secret_key: str = None, vendor_id: str = None):
        self.access_key = access_key or os.environ["COUPANG_ACCESS_KEY"]
        self.secret_key = secret_key or os.environ["COUPANG_SECRET_KEY"]
        self.vendor_id = vendor_id or os.environ.get("COUPANG_VENDOR_ID", "")

    def _request(self, method: str, path: str, query: str = "", body: dict = None):
        auth_header = _generate_hmac(method, path, query, self.secret_key, self.access_key)
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json;charset=UTF-8",
        }
        full_url = DOMAIN + path + (("?" + query) if query else "")
        resp = requests.request(method, full_url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def search_products(self, keyword: str, limit: int = 10) -> list:
        path = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
        query = urlencode({"keyword": keyword, "limit": limit})
        result = self._request("GET", path, query=query)
        return result.get("data", {}).get("productData", [])

    def create_deeplinks(self, coupang_urls: list, sub_id: str = "") -> list:
        path = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
        body = {"coupangUrls": coupang_urls}
        if sub_id:
            body["subId"] = sub_id
        result = self._request("POST", path, body=body)
        return result.get("data", [])
