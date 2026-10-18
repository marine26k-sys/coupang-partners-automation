"""Observed facts only: same-option price history and category rank history."""
from datetime import datetime,timedelta


def enrich(db,p,option,day):
    cutoff=(datetime.fromisoformat(day)-timedelta(days=29)).date().isoformat()
    history=db.execute('SELECT day,price FROM prices WHERE id=? AND option=? AND day>=? AND day<=? ORDER BY day',(p['id'],option,cutoff,day)).fetchall() if option else []
    p['priceHistory']=[{'date':d,'price':price} for d,price in history]
    p['observationDays']=len(history)
    p['observedLow']=min(x[1] for x in history) if len(history)>=2 else None
    p['atObservedLow']=p['observedLow'] is not None and p['price']<=p['observedLow']
    p['rankChange']=None
    if p.get('source')=='카테고리 베스트' and isinstance(p.get('rank'),int):
        prev=db.execute('SELECT day,rank FROM ranks WHERE category=? AND id=? AND day<? ORDER BY day DESC LIMIT 1',(p['category'],p['id'],day)).fetchone()
        if prev:
            p['rankChange']=prev[1]-p['rank'];p['previousRankDate']=prev[0]
        db.execute('INSERT OR REPLACE INTO ranks VALUES(?,?,?,?)',(p['category'],p['id'],day,p['rank']))
    reasons=[];score=0
    if isinstance(p.get('priceChange'),(int,float)) and p['priceChange']<0:
        reasons.append(f"이전 관측보다 {abs(p['priceChange']):,.0f}원 하락")
        score+=min(40,abs(p['priceChange'])/max(p['previousPrice'],1)*200)
    if p['atObservedLow']:
        reasons.append(f"관측 {len(history)}일 중 최저가와 같음");score+=20
    if (p.get('rankChange') or 0)>0:
        reasons.append(f"카테고리 목록 {p['rankChange']}계단 상승");score+=min(15,p['rankChange']*3)
    p['recommendReasons']=reasons
    return score


def recommendations(products):
    fresh=[p for p in products if not p.get('stale') and not p.get('reviewReason')]
    ordered=sorted(fresh,key=lambda p:p.get('recommendScore',0),reverse=True)
    seen=set();picks=[]
    for p in ordered:
        if p['id'] in seen:continue
        if not p.get('recommendReasons'):
            p['recommendReasons']=['가격·순위 변화 근거 부족 · 현재 목록에서 선정']
        seen.add(p['id']);picks.append({'id':p['id'],'category':p['category'],'reasons':p['recommendReasons']})
        if len(picks)==3:break
    return picks
