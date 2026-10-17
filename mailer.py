"""
생성된 초안을 카카오톡 '나에게 보내기'로 발송한다.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import set_key
from datetime import datetime, timezone, timedelta

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
    tokens = resp.json()
    rotated = tokens.get("refresh_token")
    if rotated and rotated != refresh_token:
        # Local scheduled runs must retain Kakao's replacement refresh token.
        env_file = Path(__file__).resolve().parent / ".env"
        if env_file.exists() and not os.environ.get("GITHUB_ACTIONS"):
            os.chmod(env_file, 0o600)
            set_key(str(env_file), "KAKAO_REFRESH_TOKEN", rotated)
            os.environ["KAKAO_REFRESH_TOKEN"] = rotated
    return tokens["access_token"]


def send_draft_kakao(daily_post: str, hook_post: str, product_name: str, deeplink: str):
    access_token = _get_access_token()

    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
    text = f"""[스레드 초안] {today} - {product_name}
{deeplink}

[주제 소개 초안]
{daily_post}

[후킹글 + 추천글]
{hook_post}"""

    # Preserve complete drafts across Kakao text messages (1000 characters each).
    parts = [text[i:i + 1000] for i in range(0, len(text), 1000)]

    for part in parts:
        template_object = {
            "object_type": "text",
            "text": part,
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
        if resp.json().get("result_code") != 0:
            raise RuntimeError("카카오 메시지 전송 실패")

    print("카카오톡 '나에게 보내기' 발송 완료")
