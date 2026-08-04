"""
생성된 초안을 카카오톡 '나에게 보내기'로 발송한다.
"""

import os
import json
import requests
from datetime import datetime

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


def _get_access_token() -> str:
    rest_api_key = os.environ["KAKAO_REST_API_KEY"]
    client_secret = os.environ.get("KAKAO_CLIENT_SECRET", "")
    refresh_token = os.environ["KAKAO_REFRESH_TOKEN"]

    data = {
        "grant_type": "refresh_token",
        "client_id": rest_api_key,
        "refresh_token": refresh_token,
    }
    if client_secret:
        data["client_secret"] = client_secret

    resp = requests.post(
        TOKEN_URL,
        data=data,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def send_draft_kakao(daily_post: str, hook_post: str, product_name: str, deeplink: str):
    access_token = _get_access_token()

    today = datetime.now().strftime("%Y-%m-%d")
    text = f"""[스레드 초안] {today} - {product_name}

[일상글 - 위장용/필러]
{daily_post}

[후킹글 + 추천글]
{hook_post}

[딥링크]
{deeplink}"""

    text = text[:1000]

    template_object = {
        "object_type": "text",
        "text": text,
        "link": {
            "web_url": deeplink,
            "mobile_web_url": deeplink,
        },
    }

    resp = requests.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template_object, ensure_ascii=False)},
        timeout=15,
    )
    resp.raise_for_status()

    print("카카오톡 '나에게 보내기' 발송 완료")
