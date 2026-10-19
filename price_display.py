"""Render prices from verified source fields, never generated prose."""
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def price_line(amount, captured_at, now=None):
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount <= 0:
        raise ValueError('확인한 판매가격이 필요합니다.')
    captured = datetime.fromisoformat(captured_at)
    if captured.tzinfo is None or not 0 <= ((now or datetime.now(timezone.utc))-captured).total_seconds() <= 21600:
        raise ValueError('6시간 이내 가격 확인이 필요합니다.')
    stamp=captured.astimezone(ZoneInfo('Asia/Seoul')).strftime('%m/%d %H:%M')
    return f'표시가격 {amount:,.0f}원 · {stamp} 기준'


def add_threads_price(text, link, amount, captured_at):
    marker='\n'+link
    if text.count(marker)!=1:
        raise ValueError('가격을 넣을 상품 링크를 확인하세요.')
    result=text.replace(marker,'\n'+price_line(amount,captured_at)+'\n가격·옵션은 구매 화면에서 확인\n'+link,1)
    if len(result)>500:
        raise ValueError('가격 포함 본문이 500자를 초과합니다.')
    return result
