"""Detect collection anomalies without inventing prices or hiding uncertainty."""

def check_count(current, previous):
    if previous >= 10 and current < previous * .6:
        raise ValueError('상품 수가 이전의 60% 미만이라 기존 공개 자료를 유지합니다.')


def price_anomaly(current, previous):
    if not isinstance(current,(int,float)) or isinstance(current,bool) or current<=0:
        return '가격 확인 필요'
    if isinstance(previous,(int,float)) and previous>0:
        ratio=current/previous
        if ratio < .5 or ratio > 2:
            return '가격 급변 · 구성과 판매 옵션 재확인 필요'
    return None
