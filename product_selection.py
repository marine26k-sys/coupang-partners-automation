"""Choose fresh candidates from official Goldbox/category lists in API order."""
SOURCES = {
    '골드박스': '/products/goldbox',
    '주방용품 베스트': '/products/bestcategories/1013',
    '생활용품 베스트': '/products/bestcategories/1014',
}
BASE='/v2/providers/affiliate_open_api/apis/openapi/v1'


def ranked_candidates(client, history):
    preferred=history.next_keyword(list(SOURCES))
    ordered=[preferred]+[name for name in SOURCES if name!=preferred]
    products=[]; seen=set()
    for source in ordered:
        try:
            query='' if source=='골드박스' else 'limit=10'
            found=client._request('GET',BASE+SOURCES[source],query=query).get('data',[])
            if not isinstance(found,list):continue
            for index,product in enumerate(found[:10],1):
                pid=str(product.get('productId',''))
                if not pid.isdigit() or pid in seen or not product.get('productName'):continue
                seen.add(pid)
                products.append({**product,'selectionSource':source,'selectionRank':index})
        except Exception:
            # Another official list can still supply candidates. Never substitute random search.
            continue
    if not products:
        raise RuntimeError('골드박스·베스트 목록을 가져오지 못해 이번 발행을 중단합니다.')
    return products,preferred


def apply_observed_signals(products, database):
    """Re-rank within each source using only matching vendor-option observations."""
    import sqlite3
    from contextlib import closing
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from urllib.parse import urlparse,parse_qs
    from pathlib import Path
    if not Path(database).exists():return products
    today=datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    try:
        with closing(sqlite3.connect(database)) as db:
            for p in products:
                p['observedScore']=0;p['observedFact']=''
                option=parse_qs(urlparse(p.get('productUrl','')).query).get('vendorItemId',[None])[0]
                if not option:continue
                previous=db.execute('SELECT day,price FROM prices WHERE id=? AND option=? AND day<? ORDER BY day DESC LIMIT 1',(str(p['productId']),option,today)).fetchone()
                price=p.get('productPrice')
                from catalog_guard import price_anomaly
                p['reviewReason']=price_anomaly(price,previous[1] if previous else None)
                if p['reviewReason']:continue
                if previous and isinstance(price,(int,float)) and previous[1]>price>0:
                    drop=previous[1]-price
                    p['observedScore']=min(40,drop/previous[1]*200)
                    p['observedFact']=f"{previous[0]} 같은 판매 옵션 관측 {previous[1]:,.0f}원 → 이번 조회 {price:,.0f}원. 쿠폰·배송비·선택 옵션에 따라 최종 가격은 달라질 수 있어."
                rows=db.execute('SELECT day,price FROM prices WHERE id=? AND option=? AND day>=date(?,\'-29 days\') AND day<?',(str(p['productId']),option,today,today)).fetchall()
                if len(rows)>=2 and isinstance(price,(int,float)) and 0<price<=min(r[1] for r in rows):p['observedScore']+=20
                category={'주방용품 베스트':'주방','생활용품 베스트':'생활'}.get(p['selectionSource'])
                if category:
                    rank=db.execute('SELECT rank FROM ranks WHERE category=? AND id=? AND day<? ORDER BY day DESC LIMIT 1',(category,str(p['productId']),today)).fetchone()
                    if rank:p['observedScore']+=max(0,min(15,(rank[0]-p['selectionRank'])*3))
    except sqlite3.Error:
        return products
    sources=list(dict.fromkeys(p['selectionSource'] for p in products))
    return sorted([p for p in products if not p.get('reviewReason')],key=lambda p:(sources.index(p['selectionSource']),-p.get('observedScore',0),p['selectionRank']))


def prefer_budget(products, hour=None):
    """Rotate affordable editorial themes, preserving evidence order within groups."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    hour = datetime.now(ZoneInfo('Asia/Seoul')).hour if hour is None else hour
    limit = 10000 if hour < 12 else 30000 if hour < 17 else None
    if limit is None:
        return products
    def fits(product):
        price = product.get('productPrice')
        return isinstance(price, (int, float)) and not isinstance(price, bool) and 0 < price <= limit
    # Fall back to other fresh official-list products when this budget has no eligible stock.
    return sorted(products, key=lambda product: not fits(product))
