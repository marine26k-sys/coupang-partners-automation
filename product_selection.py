"""Choose fresh candidates from official Goldbox/category lists in API order."""
SOURCES = {
    '골드박스': '/products/goldbox',
    '주방용품 베스트': '/products/bestcategories/1013',
    '생활용품 베스트': '/products/bestcategories/1014',
}
BASE='/v2/providers/affiliate_open_api/apis/openapi/v1'

# 골드박스에는 식품·패션·건강용품 등 계정 주제와 무관한 상품이 함께 섞인다.
# 상품명으로 확인 가능한 범위만 사용하고, 애매한 상품은 게시 후보에서 제외한다.
HOUSEHOLD_TERMS = (
    '주방', '키친', '냄비', '팬', '용기', '밀폐', '랩', '종이호일', '키친타월',
    '수납', '정리', '리빙', '생활', '청소', '세제', '휴지', '화장지', '물티슈',
    '쓰레기봉투', '기저귀봉투', '마스크', '장갑', '저울', '수건', '바구니',
    '보관', '걸이', '행주', '위생', '주방용품', '생활용품', '매직캔'
)
NON_HOUSEHOLD_TERMS = (
    '사과', '과일', '콜라', '비타민', '프로틴', '립밤', '폼클렌징', '클렌징',
    '소파', '가구', '포켓몬', '완구', '장난감', '향수', '샴푸', '화장품'
)


def editorial_candidates(products):
    """Return only products that can support the household editorial promise.

    Official lists are authoritative for availability and price, but a list
    membership alone is not evidence that a Goldbox item belongs on this
    account. Ambiguous titles are held back instead of being guessed into the
    kitchen/storage/household category.
    """
    ready = []
    for product in products:
        source = product.get('selectionSource', '')
        title = str(product.get('productName', '')).strip()
        if source in ('주방용품 베스트', '생활용품 베스트'):
            ready.append(product)
            continue
        if source == '골드박스':
            has_household = any(term in title for term in HOUSEHOLD_TERMS)
            has_excluded = any(term in title for term in NON_HOUSEHOLD_TERMS)
            if has_household and not has_excluded:
                ready.append(product)
    return ready


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
