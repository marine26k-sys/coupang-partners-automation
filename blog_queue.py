"""Validated private blog queue. Browser publishing remains a separate step."""
from contextlib import contextmanager
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse
from blog_drafts import compose
from content_quality import validate_copy
from content_layout import blog_section, validate_emoji, mobile_blog_html

ROOT = Path(__file__).resolve().parent
DEFAULT = ROOT/'artifacts/blog-drafts/queue.sqlite3'


def prepare(data, now=None):
    product = data['product']
    provider = data['provider']
    base = compose(product, provider)  # validates service and owner verification for Toss
    title = str(data.get('title', '')).strip()
    validate_emoji(title,0)
    sections = data.get('sections', [])
    if not 8 <= len(title) <= 100 or len(sections) != 3:
        raise ValueError('간결한 제목과 소제목 3개가 필요합니다.')
    evidence = product['name'] + '\n' + str(product.get('verifiedEvidence', ''))
    if not product.get('option') or not product.get('imageVerifiedByOwner'):
        raise ValueError('상품 옵션과 공식 이미지 확인이 필요합니다.')
    image = urlparse(product.get('image', ''))
    if image.scheme != 'https' or not image.hostname:
        raise ValueError('공식 상품 이미지 주소가 필요합니다.')
    captured = datetime.fromisoformat(product.get('checkedAt', ''))
    if captured.tzinfo is None or not 0 <= ((now or datetime.now(timezone.utc))-captured).total_seconds() <= 21600:
        raise ValueError('6시간 이내에 상품 정보를 확인해야 합니다.')
    paragraphs = []
    formatted=[]
    for index, section in enumerate(sections):
        heading = str(section.get('heading', '')).strip()
        body = str(section.get('body', '')).strip()
        if not heading or len(body) < 30:
            raise ValueError('각 소제목과 충분한 설명이 필요합니다.')
        heading, blocks=blog_section(heading,body,index)
        formatted.append({'heading':heading,'blocks':blocks})
        paragraphs.extend([heading, '\n\n'.join(blocks)])
    copy = title+'\n'+'\n'.join(paragraphs)
    validate_copy(copy, evidence)
    if len(copy) < 250 or len(copy) > 2500:
        raise ValueError('본문 길이는 250~2500자여야 합니다.')
    disclosure = base['text'].split('\n\n')[0]
    url = product['affiliateUrl']
    price_blocks=[]
    if product.get('priceVerifiedByOwner') is True:
        from price_display import price_line
        price_blocks=[price_line(product.get('price'),product['checkedAt']), '옵션 '+str(product['option'])]
        if product.get('shippingVerifiedByOwner') is True:
            shipping=product.get('shipping')
            if isinstance(shipping,bool) or not isinstance(shipping,(int,float)) or not math.isfinite(shipping) or shipping<0:
                raise ValueError('배송비 확인이 필요합니다.')
            price_blocks.append('배송비 무료' if shipping==0 else f'배송비 {shipping:,.0f}원')
        price_blocks.append('가격·쿠폰·배송 조건은 구매 화면에서 최종 확인해주세요')
    paragraphs=price_blocks+paragraphs
    text = '※ '+disclosure+'\n\n'+product['name']+'\n\n'+'\n\n'.join(paragraphs)+'\n\n'+url
    markup = '<p>※ '+html.escape(disclosure)+'</p><p>'+html.escape(product['name'])+'</p>'
    markup += ''.join('<p>'+html.escape(block)+'</p>' for block in price_blocks)
    for s in formatted:
        markup += '<h2><strong>'+html.escape(s['heading'])+'</strong></h2>'+''.join('<p>'+html.escape(block)+'</p>' for block in s['blocks'])
    markup += '<p><a href="'+html.escape(url,quote=True)+'">'+html.escape(url)+'</a></p>'
    markup = mobile_blog_html(markup)
    # The browser uploads the verified image AFTER all text, never inside a sentence.
    return {**data, 'text':text, 'html':markup, 'imagePosition':'last', 'status':'ready'}


@contextmanager
def connect(path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    os.chmod(path, 0o600)
    db.execute('CREATE TABLE IF NOT EXISTS queue(id TEXT PRIMARY KEY, slot TEXT UNIQUE, product_key TEXT UNIQUE, state TEXT, payload TEXT, public_url TEXT)')
    try:
        with db:
            yield db
    finally:
        db.close()


def enqueue(data, slot, path=DEFAULT):
    if not slot or not isinstance(slot, str):
        raise ValueError("예약 시간 식별자가 필요합니다.")
    if data.get('kind')=='comparison':
        from comparison_editorial import prepare_comparison_publication
        payload=prepare_comparison_publication(data)
        key='comparison:'+','.join(sorted(p['id']+':'+p['optionKey'] for p in data['products']))
    else:
        payload=prepare(data)
        key = data['provider']+':'+str(data['product'].get('id') or data['product']['affiliateUrl'])
    item_id = hashlib.sha256((slot+key).encode()).hexdigest()[:16]
    with connect(path) as db:
        db.execute('INSERT INTO queue VALUES(?,?,?,?,?,?)',(item_id,slot,key,'ready',json.dumps(payload,ensure_ascii=False),None))
    return item_id


def claim(item_id, path=DEFAULT):
    with connect(path) as db:
        row = db.execute('SELECT payload FROM queue WHERE id=? AND state=?',(item_id,'ready')).fetchone()
        if not row:raise ValueError('발행 중이거나 처리된 항목은 다시 시작할 수 없습니다.')
        saved=json.loads(row[0])
        if saved.get('kind')=='comparison':
            from comparison_editorial import prepare_comparison_publication
            payload=prepare_comparison_publication(saved)
        else:
            payload=prepare(saved)  # revalidate age immediately before editing
        changed = db.execute("UPDATE queue SET state='publishing' WHERE id=? AND state='ready'",(item_id,)).rowcount
        if not changed:raise ValueError('다른 작업이 이미 발행을 시작했습니다.')
    return payload


def finish(item_id, url, path=DEFAULT):
    parsed = urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!='blog.naver.com' or '/sallim-select/' not in parsed.path:
        raise ValueError('확인한 살림셀렉트 공개 글 주소가 필요합니다.')
    with connect(path) as db:
        if not db.execute("UPDATE queue SET state='published',public_url=? WHERE id=? AND state='publishing'",(url,item_id)).rowcount:
            raise ValueError('발행 시작 상태를 확인하세요.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['enqueue','claim','finish'])
    parser.add_argument('--input');parser.add_argument('--slot');parser.add_argument('--id');parser.add_argument('--url')
    args=parser.parse_args()
    try:
        if args.action=='enqueue':print('검수 통과 · 대기열 ID: '+enqueue(json.loads(Path(args.input).read_text()),args.slot))
        elif args.action=='claim':
            payload=claim(args.id)
            out=DEFAULT.parent/(args.id+'.json');out.write_text(json.dumps(payload,ensure_ascii=False,indent=2));out.chmod(0o600)
            print('발행 시작 · 보호 파일: '+str(out))
        else:finish(args.id,args.url);print('공개 발행 확인 기록 완료')
    except Exception as exc:
        print('검수 또는 대기열 처리 보류: '+type(exc).__name__)
        raise SystemExit(1) from None
