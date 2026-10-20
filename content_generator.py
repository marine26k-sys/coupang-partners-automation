"""
Gemini API로 일상글/후킹글을 생성한다.
"""

import os
from google import genai
from google.genai import types

FACTUAL_RULES = """
최우선 사실성 규칙:
실제 사용·구매·추천받은 경험, 친구·가족의 일화, 인용 후기, 체험담을 만들지 마.
가상 상황극이나 1인칭 경험담도 금지한다. 일반적인 구매 전 고민이나 확인 질문으로 쓴다.
입력된 상품명에 직접 있는 구성·규격 외에는 장점, 품질, 사용감, 효과를 추정하지 마.
예: 잇몸이 안 아프다, 개운하다, 튼튼하다, 편하다 등 확인되지 않은 주장은 금지한다.
의학·건강 권고나 출처 없는 수치 기준도 만들지 마.
정보가 부족하면 확인할 항목으로 제안하고, 직접 쓰거나 효능을 확인한 것처럼 말하지 마.
"""


class TextModel:
    def __init__(self, instruction):
        self.instruction = instruction

    def generate_content(self, text, generation_config):
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
            contents=text,
            config=types.GenerateContentConfig(system_instruction=self.instruction + FACTUAL_RULES,
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
- 글 타입은 다음 중 매번 무작위로 하나를 골라서 써: 공감형 하소연, 소소한 발견/꿀팁 공유, 자문자답형 혼잣말, 구매 전 확인 질문.
- 관점(1인칭 화자의 상황/기분)도 매번 무작위로 다르게 설정해.
- 문체는 짧고 반말인 커뮤니티체로 써. 문장은 짧게 끊어 쓰고, 과한 격식체·설명체 금지.
- 광고 느낌이 나면 안 돼. 상품이나 브랜드명, 링크는 절대 본문에 넣지 마.
- 결과는 글 본문만 출력해. 설명이나 따옴표는 붙이지 마."""

HOOK_POST_SYSTEM_PROMPT = """너는 쿠팡파트너스 제휴 마케팅용 스레드(Threads) 글을 쓰는 작가야. 아래 규칙을 반드시 지켜.

입력으로 상품명, 상품 특징, 가격 정보가 주어진다. 두 부분을 순서대로 작성해.

[1차 글 - 후킹용]
- 밈/드립 스타일로 짧고 임팩트 있게 써서 시선을 끄는 게 목적이야.
- 상품을 대놓고 광고하지 말고, 일반적인 고민이나 질문으로 궁금증을 유발해. 실제 경험담 형식은 쓰지 마.
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


def generate_threads_post(product_name: str, deeplink: str, observed_fact: str = '') -> str:
    from pathlib import Path
    voice = (Path(__file__).resolve().parent / 'config/sallim_voice.txt').read_text(encoding='utf-8')
    model = TextModel(voice + '\n이번 요청은 댓글 없이 본문 한 개로 완결해. '
        '생활 속 구체적 상황 훅 → 확인된 상품 특징 → 필요한 이유 순서의 담백한 반말 3~4줄, 180자 이내. '
        '상품명은 프로그램이 별도 추가하므로 반복하지 마. 댓글 안내·링크 안내·가짜 경험·후기·효능·가격·할인 추정은 금지. '
        '첫 줄은 한 문장 훅만 쓰고 설명을 붙이지 마. 문단 끝 마침표와 글머리 점을 쓰지 마. 빈 줄로 구분해. 이모지는 필요할 때만 최대 1개. 확인된 구성을 생활의 편의와 연결해. 억지 반전·가짜 후회·일률적인 질문형 끝맺음은 금지. 상품명·가격·링크·고지를 제외한 핵심 문장만 작성해.')
    prompt='확인된 상품명: '+product_name
    for attempt in range(3):
        response = model.generate_content(prompt, {'temperature':0.4 if attempt==0 else 0.2})
        try:
            return build_threads_post(response.text.strip(), product_name, deeplink, observed_fact)
        except ValueError:
            if attempt==2:
                raise
            prompt=('확인된 상품명: '+product_name+'\n이전 초안은 로컬 검수에서 탈락했어. '
                    '상품명에 없는 숫자·단위·치수·효능과 사용 경험을 모두 빼고 새로 작성해. '
                    '숫자를 쓰지 않고 확인된 상품 종류와 구매할 이유만 짧게 연결해. '
                    '가격·링크·상품명·광고 고지는 프로그램이 추가하므로 쓰지 마.')


def build_threads_post(copy: str, product_name: str, deeplink: str, observed_fact: str = '') -> str:
    forbidden = ['여러분','해봐라','하시길 바랍니다','진짜','너무','완전','대박','무조건','필수템','인생템','강추','역대급','갓성비','라는 점에서','할 수 있습니다','댓글']
    if not copy or 'http' in copy or any(x in copy for x in forbidden) or '!' in copy:
        raise ValueError('본문 문구 또는 말투 규칙을 확인하세요.')
    if not deeplink.startswith('https://link.coupang.com/'):
        raise ValueError('본인 제휴 링크가 필요합니다.')
    from content_quality import validate_copy
    from content_layout import threads_layout
    validate_copy(copy, product_name)
    copy = threads_layout(copy)
    text = copy+'\n\n'+product_name+(('\n'+observed_fact) if observed_fact else '')+'\n'+deeplink+'\n\n※ '+DISCLOSURE_TEXT
    if len(text)>500:
        raise ValueError('Threads 본문이 500자를 초과했습니다.')
    return text


SHORT_DISCLOSURE = '[제휴광고] 링크 구매 시 수수료를 받습니다.'


def generate_threads_pair(product_name: str, deeplink: str) -> dict:
    import json
    import secrets
    from pathlib import Path
    voice = (Path(__file__).resolve().parent / 'config/sallim_voice.txt').read_text(encoding='utf-8')
    angle = secrets.choice(['공간 치수 하나', '구성 선택 하나', '정리 전에 분류할 물건', '구매 전 놓치기 쉬운 조건'])
    model = TextModel(voice + '\n이번 글의 관점: ' + angle + '\nThreads 본문과 첫 댓글을 JSON으로 작성해. '
        '형식: {"hook":"본문", "reply":"댓글"}. '
        'hook은 상품 카테고리의 구매 전 고민이나 질문으로 호기심을 끄는 반말 2~3문장, 180자 이내. '
        '상품명·링크·고지·가짜 경험담 없이 써. 댓글 안내는 필요할 때만 짧게, 매번 다르게 써. '
        'reply는 입력된 상품명과 명시된 구성만 담은 담백한 반말 200자 이내. '
        '후기·효능·할인·판매량·최고 등의 주장을 만들지 마. 코드블록 없이 JSON만 출력해.')
    response = model.generate_content('확인된 상품명: '+product_name, {'temperature': 0.4})
    raw = response.text.strip()
    if raw.startswith('```'):
        raw = raw.removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    parsed = json.loads(raw)
    hook, reply = parsed['hook'].strip(), parsed['reply'].strip()
    if not hook or not reply or 'http' in hook or 'http' in reply:
        raise ValueError('Threads 본문·댓글 형식이 올바르지 않습니다.')
    forbidden = ['여러분', '해봐라', '하시길 바랍니다', '진짜', '너무', '완전', '대박', '무조건', '필수템', '인생템', '강추', '역대급', '갓성비', '라는 점에서', '할 수 있습니다']
    if any(word in hook or word in reply for word in forbidden) or '!' in hook + reply:
        raise ValueError('살림셀렉트 말투 규칙 위반: 자동발행을 중단합니다.')
    pair = {'body': SHORT_DISCLOSURE+'\n\n'+hook,
            'reply': DISCLOSURE_TEXT+'\n\n'+reply+'\n\n'+deeplink}
    if any(len(value)>500 for value in pair.values()):
        raise ValueError('Threads 본문 또는 댓글이 500자를 초과했습니다.')
    return pair
