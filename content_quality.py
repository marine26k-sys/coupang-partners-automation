"""Conservative local checks; these checks do not establish factual truth."""
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

SPEC = re.compile(r'\d+(?:\.\d+)?\s*(?:mm|cm|kg|ml|mah|리터|킬로그램|센티미터|밀리미터|개입|매입|롤|팩|겹|개|매|세트|인치|[mglwv])', re.I)


def validate_copy(copy, evidence):
    sentences = [re.sub(r'\W+', '', s).lower() for s in re.split(r'[.!?。！？\n]+', copy)]
    sentences = [s for s in sentences if len(s) >= 12]
    if len(sentences) != len(set(sentences)):
        raise ValueError('본문에 같은 문장이 반복되어 발행을 보류합니다.')
    if re.search(r'내돈내산|써보니|사용해보니|직접\s*(?:써|사용해)|최저가|100%\s*만족', copy):
        raise ValueError('확인되지 않은 경험 또는 과장 표현입니다.')
    corpus = re.sub(r'\s+', '', evidence).lower()
    for match in SPEC.finditer(copy):
        claim = re.sub(r'\s+', '', match.group()).lower()
        if claim not in corpus:
            raise ValueError('근거에서 확인되지 않은 수치·사양이 포함되어 발행을 보류합니다.')
    if re.search(r'\d[\d,]*\s*원', copy):
        raise ValueError('생성 본문의 가격 주장은 발행 전에 별도 확인이 필요합니다.')


def validate_threads_ready(draft, disclosure, now=None):
    text = draft.get('threadsPost', '')
    link = draft.get('deeplink', '')
    parsed = urlparse(link)
    if parsed.scheme != 'https' or parsed.hostname != 'link.coupang.com' or not parsed.path.strip('/'):
        raise ValueError('유효한 쿠팡 제휴 링크가 필요합니다.')
    if not text or len(text) > 500 or disclosure not in text or link not in text:
        raise ValueError('발행 본문·광고 고지·링크를 확인하세요.')
    if not draft.get('productName') or draft['productName'] not in text:
        raise ValueError('선정 상품과 게시 본문이 일치하지 않습니다.')
    image = urlparse(draft.get('productImage', ''))
    if image.scheme != 'https' or not image.hostname or not (image.hostname.endswith('.coupangcdn.com') or image.hostname == 'ads-partners.coupang.com'):
        raise ValueError('상품 이미지 정보를 확인하지 못해 발행을 보류합니다.')
    try:
        captured = datetime.fromisoformat(draft['priceCapturedAt'])
        if captured.tzinfo is None:
            raise ValueError()
        age = ((now or datetime.now(timezone.utc)) - captured).total_seconds()
        if not 0 <= age <= 6 * 3600:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise ValueError('상품 조회 후 6시간이 지나거나 조회 시각이 없어 발행을 보류합니다.') from None
