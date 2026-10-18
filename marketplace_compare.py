"""Only human-verified exact product configurations can be compared across services."""
from datetime import datetime, timezone
from pathlib import Path
import json
from urllib.parse import urlparse

FIELDS=('brand','model','variant','quantity','unit')


def verified_offer(offer, now=None):
    if offer.get('verified') is not True or not all(str(offer.get(k,'')).strip() for k in FIELDS):
        raise ValueError('브랜드·모델·색상/규격·수량·단위를 실제 확인해야 합니다.')
    service=offer.get('service');u=urlparse(offer.get('url',''))
    hosts={'coupang':{'link.coupang.com'},'toss':{'toss.shopping','toss.im'}}
    if service not in hosts or u.scheme!='https' or u.hostname not in hosts[service] or not offer.get('ownerLinkVerified'):
        raise ValueError('본인 계정에서 발급한 제휴 링크가 필요합니다.')
    price=offer.get('price');shipping=offer.get('shipping')
    if not isinstance(price,(int,float)) or isinstance(price,bool) or price<=0:raise ValueError('확인 가격이 필요합니다.')
    if shipping is not None and (not isinstance(shipping,(int,float)) or isinstance(shipping,bool) or shipping<0):raise ValueError('배송비를 확인하세요.')
    stamp=datetime.fromisoformat(offer['checkedAt'])
    if stamp.tzinfo is None or not 0<=((now or datetime.now(timezone.utc))-stamp).total_seconds()<=21600:raise ValueError('6시간 이내 자료가 필요합니다.')
    return {k:offer.get(k) for k in (*FIELDS,'service','url','price','shipping','checkedAt','name')}


def compare(offers, now=None):
    valid=[verified_offer(x,now) for x in offers]
    groups={}
    for offer in valid:
        key=tuple(str(offer[k]).strip().casefold() for k in FIELDS)
        groups.setdefault(key,[]).append(offer)
    result=[]
    for entries in groups.values():
        if len({x['service'] for x in entries})<2:continue
        for entry in entries:entry['total']=entry['price']+entry['shipping'] if entry['shipping'] is not None else None
        result.append({'name':entries[0].get('name') or entries[0]['model'],'configuration':' · '.join(str(entries[0][k]) for k in FIELDS),'offers':entries,'totalComparable':all(x['total'] is not None for x in entries),'note':'조회 시점·배송 조건 기준. 쿠폰과 회원 혜택은 결제 화면에서 확인하세요.'})
    return result


def load_comparisons(path):
    try:return compare(json.loads(Path(path).read_text()))
    except (OSError,ValueError,KeyError,TypeError):return []
