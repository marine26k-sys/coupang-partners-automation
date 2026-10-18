"""Situation-led comparison drafts using only observed names, options and prices."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, ROUND_HALF_UP
import html
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from content_packages import fresh
from growth_analytics import private_json
from publication_history import ROOT


def quantity(name):
    match=re.search(r',\s*([1-9]\d*)개\s*$',name)
    return int(match[1]) if match else None


def build(products, now=None):
    selected=[];seen=set()
    for p in products:
        if p.get('category')!='수납' or p['id'] in seen or not fresh(p,now):continue
        u=urlparse(p.get('url',''))
        if u.scheme!='https' or u.hostname!='link.coupang.com' or not p.get('optionKey'):continue
        count=quantity(p['name'])
        if count is None:continue
        seen.add(p['id'])
        selected.append({**p,'quantity':count,'unitPrice':int((Decimal(str(p['price']))/count).quantize(Decimal('1'),rounding=ROUND_HALF_UP))})
        if len(selected)==3:break
    if len(selected)<2:raise ValueError('구성과 판매 옵션이 확인된 비교 후보가 부족합니다.')
    title='팬트리 정리함, 우리 집에 맞는 구성 고르는 법'
    intro=['정리함은 많이 사는 것보다 놓을 자리에 맞게 고르는 게 먼저예요.','아래 상품은 구성과 조회 가격을 정리한 후보예요. 직접 사용한 후기나 수납 성능 순위는 아닙니다.']
    situations=[('정리할 곳이 한 구역이라면','선반 하나에 놓을 물건부터 나눠보세요. 묶음 수량을 다 쓰지 못하면 남는 정리함도 보관할 자리가 필요해요.'),('여러 선반을 정리한다면','각 선반의 가로·깊이·높이를 따로 재보세요. 모양을 통일하기 전에 실제로 필요한 수량을 먼저 적어두면 좋아요.'),('포장 크기가 제각각이라면','담을 물건 중 가장 큰 포장을 기준으로 내부 치수를 확인해요. 외부 크기만으로 실제로 들어가는지 판단하지 않아요.')]
    checks=['선반의 가로·깊이·높이와 손을 넣을 여유','상품의 내부·외부 치수, 선택 옵션과 수량','배송비·쿠폰을 반영한 최종 결제금액']
    lines=['※ 이 게시물은 쿠팡파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.','',title,'']+intro+['','🧺 공간과 사용 목적부터 정해요','']
    for heading,body in situations:lines += [heading,body,'']
    lines += ['📌 확인된 구성과 가격','']
    for p in selected:
        stamp=datetime.fromisoformat(p['observedAt']).astimezone(ZoneInfo('Asia/Seoul')).strftime('%m/%d %H:%M')
        lines += [p['name'],f"· 구성 {p['quantity']}개 / 조회 가격 {p['price']:,.0f}원",f"· 1개당 약 {p['unitPrice']:,}원 (상품 표시가격 ÷ 수량, 원 단위 반올림)",f'· 가격 확인 {stamp} 한국시간',p['url'],'']
    lines += ['상품마다 크기·형태가 달라 1개당 가격만으로 가성비 순위를 정하지 않았어요. 같은 이름의 상품도 판매 옵션이 다르면 가격이 달라질 수 있어요.','', '🔎 이런 경우에는 구매를 잠깐 미뤄요','', '선반 치수를 아직 모르거나, 묶음 수량을 어디에 쓸지 정하지 못했다면 먼저 자리를 정리해보세요. 이미 가진 바구니로 해결되는지도 살펴보면 좋아요.','']
    lines += ['· '+x for x in checks]+['','배송비와 쿠폰은 위 단가에 포함하지 않았어요. 실제 치수·재질·적층 가능 여부는 각 상품의 정확한 옵션에서 확인해주세요.','직접 사용한 후기는 수집하지 않았으므로 실제 사용감이나 내구성에 대한 평가를 덧붙이지 않았습니다.']
    text='\n'.join(lines)
    markup='<h1>'+html.escape(title)+'</h1>'+''.join('<p>'+html.escape(x)+'</p>' for x in lines[:1]+intro)
    markup+='<h2>🧺 공간과 사용 목적부터 정해요</h2>'
    for heading,body in situations:markup+='<h3>'+html.escape(heading)+'</h3><p>'+html.escape(body)+'</p>'
    markup+='<h2>📌 확인된 구성과 가격</h2>'
    for p in selected:
        markup+='<h3>'+html.escape(p['name'])+'</h3><p>구성 '+str(p['quantity'])+'개 · 조회 가격 '+f"{p['price']:,.0f}"+'원</p><p>1개당 약 '+f"{p['unitPrice']:,}"+'원 · 상품 표시가격 기준</p><p>확인 '+html.escape(p['observedAt'])+'</p><p><a href="'+html.escape(p['url'])+'" rel="sponsored noopener">상품 구성 확인</a></p>'
    markup+='<p>서로 다른 크기·형태의 상품이므로 단가만으로 순위를 정하지 않습니다.</p><h2>🔎 구매를 미뤄도 좋은 경우</h2><p>선반 치수나 필요한 수량이 정해지지 않았다면 먼저 놓을 자리를 확인해요.</p><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in checks)+'</ul><p>배송비·쿠폰은 단가에 미포함. 직접 사용한 후기와 성능 평가는 포함하지 않았습니다.</p>'
    return {'kind':'comparison','status':'draft_only','title':title,'text':text,'html':markup,'createdAt':datetime.now(timezone.utc).isoformat(),'products':[{'id':p['id'],'optionKey':p['optionKey'],'name':p['name'],'url':p['url'],'quantity':p['quantity'],'price':p['price'],'unitPrice':p['unitPrice'],'observedAt':p['observedAt'],'image':p.get('image','')} for p in selected],'requiresReview':['각 상품의 정확한 사진 확인 후 모든 본문 아래 배치','가격이 6시간을 넘었으면 재조회','기존 단일상품 대기열과 분리하여 다상품 검수 후 발행'],'noPerformanceRanking':True}


def run():
    catalog=json.loads((ROOT.parent/'sallim-select-catalog/catalog.json').read_text())
    result=build(catalog['products'])
    folder=ROOT/'artifacts/content-packages';folder.mkdir(exist_ok=True)
    private_json(folder/'pantry-bundle.json',result)
    for suffix,key in [('md','text'),('html','html')]:
        p=folder/('pantry-comparison.'+suffix);p.write_text(result[key]);p.chmod(0o600)
    return result

if __name__=='__main__':
    try:run();print('팬트리 비교 초안 생성 완료 · 외부 발행 없음')
    except Exception as exc:print('비교 초안 생성 보류: '+type(exc).__name__);raise SystemExit(1) from None
