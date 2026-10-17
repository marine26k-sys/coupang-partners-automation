"""
Gemini API로 일상글/후킹글을 생성한다.
"""

import os
from google import genai
from google.genai import types

class TextModel:
    def __init__(self, instruction):
        self.instruction = instruction

    def generate_content(self, text, generation_config):
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=text,
            config=types.GenerateContentConfig(system_instruction=self.instruction,
                                               **generation_config),
        )
        if not response.text:
            raise RuntimeError("Gemini가 빈 응답을 반환했습니다.")
        return response

DISCLOSURE_TEXT = "이 게시물은 쿠팡파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."


def _comment_block(deeplink: str) -> str:
    return f"\n\n[댓글]\n{DISCLOSURE_TEXT}\n{deeplink}"


DAILY_POST_SYSTEM_PROMPT = """너는 스레드(Threads)용 '일상글'을 쓰는 작가야. 아래 규칙을 반드시 지켜.

- 입력으로 주어진 주제에서 연상되는 키워드를 먼저 떠올리고, 그걸 바탕으로 일반적인 상황을 소개해. 실제 사용 경험을 꾸며내지 마.
- 글 타입은 다음 중 매번 무작위로 하나를 골라서 써: 공감형 하소연, 소소한 발견/꿀팁 공유, 자문자답형 혼잣말, 짧은 에피소드 회고.
- 관점(1인칭 화자의 상황/기분)도 매번 무작위로 다르게 설정해.
- 문체는 짧고 반말인 커뮤니티체로 써. 문장은 짧게 끊어 쓰고, 과한 격식체·설명체 금지.
- 광고 느낌이 나면 안 돼. 상품이나 브랜드명, 링크는 절대 본문에 넣지 마.
- 결과는 글 본문만 출력해. 설명이나 따옴표는 붙이지 마."""

HOOK_POST_SYSTEM_PROMPT = """너는 쿠팡파트너스 제휴 마케팅용 스레드(Threads) 글을 쓰는 작가야. 아래 규칙을 반드시 지켜.

입력으로 상품명, 상품 특징, 가격 정보가 주어진다. 두 부분을 순서대로 작성해.

[1차 글 - 후킹용]
- 밈/드립 스타일로 짧고 임팩트 있게 써서 시선을 끄는 게 목적이야.
- 상품을 대놓고 광고하지 말고, 상황극이나 드립으로 궁금증을 유발해.
- 반말 커뮤니티체, 이모지는 절제해서 1~2개만.

[2차 글 - 추천형]
- 1차 글에서 이어지는 자연스러운 추천 글로, 입력으로 확인되는 상품 정보만 소개해. 정보가 없으면 특징이나 장점을 만들어내지 마.
- 과장광고나 실제 상품과 다른 효능·효과를 단정적으로 말하지 마 (표시광고법 위반 소지 있음).
- 친구한테 추천하듯 편하게, 하지만 정보는 정확하게.
- 가격 정보는 입력으로 주어지더라도 이 글에서 구체적인 가격/숫자는 절대 언급하지 마.
- 링크는 절대 본문에 넣지 마.

출력 형식은 아래처럼 정확히 맞춰:
[1차글]
(내용)

[2차글]
(내용)"""

DASHBOARD_POST_SYSTEM_PROMPT = """너는 쿠팡파트너스 상품 추천 글을 쓰는 작가야. 아래 규칙을 반드시 지켜.

입력으로 상품명, 특징이 주어진다. 입력으로 확인되는 정보만 사용해 짧고 담백한 소개 글을 써. 사용 경험, 리뷰, 효능, 할인, 상품 특징을 만들어내지 마.

- 가격/숫자는 절대 언급하지 마.
- 과장광고나 실제와 다른 효능·효과를 단정적으로 말하지 마 (표시광고법 위반 소지 있음).
- 반말 커뮤니티체, 3~5줄 이내로 짧게.
- 결과는 글 본문만 출력해. 설명이나 따옴표, 링크는 붙이지 마."""

_daily_model = TextModel(DAILY_POST_SYSTEM_PROMPT)
_hook_model = TextModel(HOOK_POST_SYSTEM_PROMPT)
_dashboard_model = TextModel(DASHBOARD_POST_SYSTEM_PROMPT)


def generate_daily_post(topic: str = "랜덤", deeplink: str = "") -> str:
    resp = _daily_model.generate_content(
        f"주제: {topic}",
        generation_config={"temperature": 0.9},
    )
    content = DISCLOSURE_TEXT + "\n\n" + resp.text.strip()
    if deeplink:
        content += _comment_block(deeplink)
    return content


def generate_hook_and_recommend(product_name: str, product_features: str,
                                 price: str, deeplink: str) -> str:
    user_msg = (
        f"상품명: {product_name}\n"
        f"특징: {product_features}\n"
        f"가격: {price}\n"
        f"구매링크: {deeplink}"
    )
    resp = _hook_model.generate_content(
        user_msg,
        generation_config={"temperature": 0.8},
    )
    content = DISCLOSURE_TEXT + "\n\n" + resp.text.strip()
    content += _comment_block(deeplink)
    return content


def generate_dashboard_post(product_name: str, product_features: str) -> str:
    user_msg = f"상품명: {product_name}\n특징: {product_features}"
    resp = _dashboard_model.generate_content(
        user_msg,
        generation_config={"temperature": 0.8},
    )
    return DISCLOSURE_TEXT + "\n\n" + resp.text.strip()


def build_comment(deeplink: str) -> str:
    return f"{DISCLOSURE_TEXT}\n{deeplink}"
