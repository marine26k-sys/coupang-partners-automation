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
