"""Publish a credential-free product catalog for the public profile site."""
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from urllib.parse import urlparse,parse_qs,urlencode
from dotenv import load_dotenv
from coupang_api import CoupangPartnersClient

ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT.parent/'sallim-select-catalog'

def collect():
    load_dotenv(ROOT/'.env')
    client=CoupangPartnersClient()
    now=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    products=[]; errors=[]
    previous_catalog={}
    try:previous_catalog=json.loads((PUBLIC/'catalog.json').read_text())
    except (OSError,ValueError):pass
    failed_categories=[]
    for category,keyword,endpoint in [('수납','팬트리 정리함',None),('주방','주방용품','/products/bestcategories/1013'),('생활','생활용품','/products/bestcategories/1014'),('골드박스','골드박스','/products/goldbox')]:
        try:
            found=(client._request('GET','/v2/providers/affiliate_open_api/apis/openapi/v1'+endpoint,query='limit=8' if 'bestcategories' in endpoint else '').get('data',[])[:8] if endpoint else client.search_products(keyword,limit=8))
            if not found:raise RuntimeError('빈 목록')
            for p in found:
                pid=str(p.get('productId',''))
                if not pid.isdigit() or not p.get('productName'): continue
                query=parse_qs(urlparse(p.get('productUrl','')).query)
                options={k:query[k][0] for k in ('itemId','vendorItemId') if query.get(k) and query[k][0].isdigit()}
                plain='https://www.coupang.com/vp/products/'+pid+('?' + urlencode(options) if options else '')
                products.append({'id':pid,'option':options.get('vendorItemId'),'name':p['productName'],
                    'price':p.get('productPrice'),'image':p.get('productImage',''),'category':category,
                    'rocket':p.get('isRocket',False),'source':('골드박스' if category=='골드박스' else '카테고리 베스트' if endpoint else '검색'),'rank':p.get('rank') if endpoint else None,'plain':plain})
        except Exception as exc:
            errors.append(category+':'+type(exc).__name__)
            failed_categories.append(category)
    from catalog_guard import check_count, price_anomaly
    previous_count=len([p for p in previous_catalog.get('products',[]) if p.get('category') not in failed_categories])
    check_count(len(products),previous_count)
    if not products: raise RuntimeError('상품 수집 실패: 기존 공개 자료 유지')
    links=[]
    for start in range(0,len(products),5):
        links.extend(client.create_deeplinks([p['plain'] for p in products[start:start+5]],sub_id='sallim_select'))
    by_url={x.get('originalUrl'):x.get('shortenUrl') for x in links}
    valid=[]
    folder=ROOT/'artifacts';folder.mkdir(exist_ok=True)
    with closing(sqlite3.connect(folder/'catalog-prices.sqlite3')) as db:
        db.execute('CREATE TABLE IF NOT EXISTS ranks(category TEXT,id TEXT,day TEXT,rank INTEGER,PRIMARY KEY(category,id,day))')
        db.execute('CREATE TABLE IF NOT EXISTS prices(id TEXT,option TEXT,day TEXT,price REAL,PRIMARY KEY(id,option,day))')
        for p in products:
            link=by_url.get(p.pop('plain'))
            if not link or not link.startswith('https://link.coupang.com/'): continue
            p['url']=link;p['priceChange']=None;p['previousPrice']=None;p['previousDate']=None
            price=p['price']; option=p['option']
            p['optionKey']=option
            p['reviewReason']=price_anomaly(price,None)
            if option and isinstance(price,(int,float)) and price>0:
                previous=db.execute('SELECT price,day FROM prices WHERE id=? AND option=? AND day<? ORDER BY day DESC LIMIT 1',(p['id'],option,now[:10])).fetchone()
                p['reviewReason']=price_anomaly(price,previous[0] if previous else None)
                if previous and not p['reviewReason']:
                    p['priceChange']=price-previous[0]
                    p['previousPrice']=previous[0]
                    p['previousDate']=previous[1]
                if not p['reviewReason']:
                    db.execute('INSERT OR REPLACE INTO prices VALUES(?,?,?,?)',(p['id'],option,now[:10],price))
            image=p['image']
            if image.startswith('//'):p['image']='https:'+image
            if not urlparse(p['image']).hostname or not (urlparse(p['image']).hostname.endswith('.coupangcdn.com') or urlparse(p['image']).hostname=='ads-partners.coupang.com'):p['image']=''
            from catalog_signals import enrich
            p['observedAt']=now
            p['stale']=False
            p['recommendScore']=enrich(db,p,option,now[:10])
            p.pop('option');valid.append(p)
        db.commit()
    check_count(len(valid),previous_count)
    if not valid:raise RuntimeError('본인 제휴 링크 생성 실패: 공개 자료 유지')
    for old in previous_catalog.get('products',[]):
        if old.get('category') in failed_categories:
            valid.append({**old,'stale':True,'observedAt':old.get('observedAt',previous_catalog.get('updatedAt'))})
    PUBLIC.mkdir(exist_ok=True)
    from catalog_signals import recommendations
    from catalog_navigation import enrich_navigation
    from featured_products import featured_records
    from publication_history import History
    numbers=enrich_navigation(valid,previous_catalog,featured_records(History()))
    from marketplace_compare import load_comparisons
    comparisons=load_comparisons(folder/'comparison-offers.json')
    result={'comparisons':comparisons,'productNumbers':numbers,'updatedAt':now,'products':valid,'recommendations':recommendations(valid),'partial':bool(errors)}
    temporary=PUBLIC/'catalog.json.tmp'
    temporary.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    temporary.replace(PUBLIC/'catalog.json')
    os.chmod(folder/'catalog-prices.sqlite3',0o600)
    return len(valid)

def publish():
    if not (PUBLIC/'.git').exists():raise RuntimeError('공개 상품 데이터 저장소 설정 필요')
    subprocess.run(['git','add','catalog.json'],cwd=PUBLIC,check=True,capture_output=True)
    changed=subprocess.run(['git','diff','--cached','--quiet'],cwd=PUBLIC).returncode
    if changed:
        subprocess.run(['git','commit','-m','Refresh public product catalog'],cwd=PUBLIC,check=True,capture_output=True)
    subprocess.run(['git','push','origin','main'],cwd=PUBLIC,check=True,capture_output=True,timeout=60)
    if os.environ.get('CATALOG_CLOUDFLARE_ENABLED','').lower()=='true':
        from cloudflare_publish import deploy
        deploy()

if __name__=='__main__':
    import sys
    try:
        n=collect()
        if '--publish' in sys.argv:publish()
        print(f'공개 상품 목록 {n}개 갱신 완료')
    except Exception as exc:
        print('상품 목록 갱신 실패: '+type(exc).__name__)
        raise SystemExit(1) from None
