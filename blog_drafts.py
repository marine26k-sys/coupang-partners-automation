"""Private, provider-aware blog drafts. Never publishes or invents affiliate links."""
import argparse
import html
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from content_generator import DISCLOSURE_TEXT

TOSS_DISCLOSURE='이 포스팅은 토스쇼핑 쉐어링크 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.'


def compose(product, provider):
    name=str(product.get('name','')).strip()
    url=str(product.get('affiliateUrl','')).strip()
    parsed=urlparse(url)
    allowed={'coupang':{'link.coupang.com'},'toss':{'toss.shopping','toss.im'}}
    if provider not in allowed or parsed.scheme!='https' or parsed.hostname not in allowed[provider] or not name:
        raise ValueError('상품명과 해당 서비스에서 발급한 본인 제휴 링크가 필요합니다.')
    if provider=='toss' and product.get('linkVerifiedByOwner') is not True:
        raise ValueError('본인 계정에서 발급한 토스 쉐어링크인지 확인이 필요합니다.')
    disclosure=DISCLOSURE_TEXT if provider=='coupang' else TOSS_DISCLOSURE
    price=product.get('price');stamp=product.get('checkedAt')
    title=name+' | 구매 전 확인할 점'
    paragraphs=[disclosure,name,'상품의 크기·구성과 사용할 공간을 먼저 비교해보세요.']
    if isinstance(price,(int,float)) and price>0 and stamp:
        paragraphs.append(f'확인 가격: {price:,.0f}원 · 확인 시각: {stamp}')
    paragraphs+=['선택 옵션·쿠폰·배송비에 따라 최종 금액이 달라질 수 있으니 구매 페이지에서 확인해주세요.',url]
    return {'provider':provider,'status':'draft_only','title':title,'text':'\n\n'.join(paragraphs),
            'html':'<h1>'+html.escape(title)+'</h1>'+''.join('<p>'+html.escape(p)+'</p>' for p in paragraphs)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider',choices=['toss','coupang'],required=True)
    parser.add_argument('--input',required=True)
    args=parser.parse_args()
    try:
        draft=compose(json.loads(Path(args.input).read_text()),args.provider)
        target=Path(__file__).parent/'artifacts/blog-drafts';target.mkdir(parents=True,exist_ok=True)
        for suffix,key in [('html','html'),('txt','text')]:
            p=target/('latest.'+suffix);p.write_text(draft[key]);p.chmod(0o600)
        print('비공개 블로그 초안 저장 완료 · 외부 게시 없음')
    except Exception as exc:
        print('초안 생성 실패: '+type(exc).__name__)
        raise SystemExit(1) from None
