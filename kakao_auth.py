"""
카카오톡 '나에게 보내기' 최초 1회 인증용 스크립트.
실행 후 안내에 따라 로그인하면 REFRESH_TOKEN을 발급해준다.
발급된 값을 .env의 KAKAO_REFRESH_TOKEN에 넣으면 이후에는 이 스크립트를 다시 실행할 필요 없다.
"""

import os
import sys
import webbrowser
import requests
from dotenv import load_dotenv

load_dotenv()

REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]
CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "")
REDIRECT_URI = os.environ["KAKAO_REDIRECT_URI"]

AUTH_URL = (
    "https://kauth.kakao.com/oauth/authorize"
    f"?client_id={REST_API_KEY}&redirect_uri={REDIRECT_URI}"
    "&response_type=code&scope=talk_message"
)


def main():
    if len(sys.argv) > 1:
        redirected = sys.argv[1].strip()
    else:
        print("아래 URL을 브라우저에서 열어 카카오 로그인 후 동의해주세요.")
        print(AUTH_URL)
        webbrowser.open(AUTH_URL)
        redirected = input("\n로그인 후 이동된 페이지의 주소창 URL 전체를 붙여넣으세요: ").strip()

    code = redirected.split("code=")[1].split("&")[0]

    data = {
        "grant_type": "authorization_code",
        "client_id": REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    if CLIENT_SECRET:
        data["client_secret"] = CLIENT_SECRET

    resp = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data=data,
        timeout=15,
    )
    resp.raise_for_status()
    tokens = resp.json()

    print("\n발급 완료! 아래 값을 .env의 KAKAO_REFRESH_TOKEN에 넣으세요:")
    print(tokens["refresh_token"])


if __name__ == "__main__":
    main()
