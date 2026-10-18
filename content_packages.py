"""Generate evidence-based bundle drafts and uncropped 12-second product videos."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlparse
import requests
from growth_analytics import private_json
from publication_history import ROOT


def fresh(product, now=None):
    try:
        stamp=datetime.fromisoformat(product['observedAt'])
        return stamp.tzinfo is not None and 0<=((now or datetime.now(timezone.utc))-stamp).total_seconds()<=21600 and not product.get('stale') and not product.get('reviewReason') and isinstance(product.get('price'),(int,float)) and product['price']>0
    except (KeyError,TypeError,ValueError):return False


def bundle(products, category='주방', budget=30000, now=None):
    chosen=[];seen=set()
    for p in products:
        if p['id'] in seen or p.get('category')!=category or not fresh(p,now):continue
        if sum(x['price'] for x in chosen)+p['price']>budget:continue
        chosen.append(p);seen.add(p['id'])
        if len(chosen)==3:break
    if len(chosen)<2:raise ValueError('같은 용도의 신선한 상품 후보가 부족합니다.')
    lines=[f'{budget:,.0f}원 안쪽에서 살펴보는 {category}용품 {len(chosen)}가지','', '한꺼번에 살 목록보다, 지금 필요한 것부터 골라요. 이미 가진 물건과 역할이 겹치지 않는지 먼저 확인해요.','']
    for p in chosen:
        if urlparse(p['url']).hostname!='link.coupang.com':raise ValueError('본인 제휴 링크를 확인하세요.')
        lines += [p['name'],f"조회 가격 {p['price']:,.0f}원 · {p['observedAt']}",'구성과 수량을 확인하고, 보관할 자리와 사용하는 빈도를 함께 살펴요.',p['url'],'']
    total=sum(x['price'] for x in chosen)
    lines += [f'상품 표시가격 합계 {total:,.0f}원. 배송비·쿠폰·회원 혜택은 포함하지 않았어요. 결제 화면에서 최종 금액을 확인하세요.','※ 이 게시물은 쿠팡파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.']
    return {'status':'draft_only','title':lines[0],'text':'\n'.join(lines),'productIds':[p['id'] for p in chosen],'displayPriceTotal':total,'createdAt':datetime.now(timezone.utc).isoformat(),'notCheckoutTotal':True}


def wrap(draw, text, font, width):
    lines=[];line=''
    for char in text:
        if char=='\n' or draw.textlength(line+char,font=font)>width:
            lines.append(line);line='' if char=='\n' else char
        else:line+=char
    if line:lines.append(line)
    return lines


def video(product, folder):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    if not fresh(product):raise ValueError('6시간 이내 검증 후보만 영상으로 만들 수 있습니다.')
    url=urlparse(product.get('image',''))
    if url.scheme!='https' or not url.hostname or not (url.hostname.endswith('.coupangcdn.com') or url.hostname=='ads-partners.coupang.com'):raise ValueError('공식 상품 사진이 필요합니다.')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    response=requests.get(url.geturl(),timeout=20);response.raise_for_status()
    if len(response.content)>20_000_000:raise ValueError('사진 크기를 확인하세요.')
    from io import BytesIO
    photo=Image.open(BytesIO(response.content)).convert('RGB')
    photo=ImageOps.contain(photo,(880,840))
    fontpath='/System/Library/Fonts/AppleSDGothicNeo.ttc'
    def font(size):return ImageFont.truetype(fontpath,size)
    cards=[]
    for i,(heading,note) in enumerate([('필요한 것부터, 간결하게.','이미 가진 물건과 역할이 겹치지 않는지 살펴요.'),('구성부터 확인해요.','상품명에 표시된 수량과 선택 옵션을 확인해요.'),('놓을 자리까지 생각해요.','크기와 보관 공간을 구매 전에 비교해요.')]):
        canvas=Image.new('RGB',(1080,1920),'#f7f5ed');draw=ImageDraw.Draw(canvas)
        draw.text((90,120),'SALLIM SELECT',font=font(35),fill='#193e30')
        y=220
        for line in wrap(draw,heading,font(58),900):draw.text((90,y),line,font=font(58),fill='#193e30');y+=76
        canvas.paste(photo,((1080-photo.width)//2,430+(840-photo.height)//2))
        y=1320
        for line in wrap(draw,product['name'],font(37),900):draw.text((90,y),line,font=font(37),fill='#193e30');y+=52
        y=max(y+30,1510)
        for line in wrap(draw,note,font(32),900):draw.text((90,y),line,font=font(32),fill='#526b5d');y+=48
        disclosure='※ 쿠팡파트너스 활동으로 링크 구매 시 수수료를 받습니다.'
        for n,line in enumerate(wrap(draw,disclosure,font(27),900)):draw.text((90,1715+n*40),line,font=font(27),fill='#193e30')
        if y>1700:raise ValueError('상품명이 길어 영상 안전 여백을 초과합니다.')
        frame=folder/f'frame-{i}.png';canvas.save(frame);cards.append(frame)
    playlist=folder/'frames.txt';playlist.write_text(''.join(f"file '{f.name}'\nduration 4\n" for f in cards)+f"file '{cards[-1].name}'\n")
    ffmpeg=shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
    output=folder/'sallim-product.mp4'
    subprocess.run([ffmpeg,'-y','-f','concat','-safe','0','-i',str(playlist),'-t','12','-r','25','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],check=True,capture_output=True,timeout=180)
    private_json(folder/'source.json',{'productId':product['id'],'name':product['name'],'url':product['url'],'observedAt':product['observedAt'],'status':'unpublished'})
    return output


def run(make_video=False):
    catalog=json.loads((ROOT.parent/'sallim-select-catalog/catalog.json').read_text())
    folder=ROOT/'artifacts/content-packages';folder.mkdir(exist_ok=True)
    candidates=[p for p in catalog['products'] if fresh(p)]
    for category in ('주방','수납','생활'):
        try:
            draft=bundle(candidates,category)
            private_json(folder/(category+'-bundle.json'),draft)
            path=folder/(category+'-bundle.md');path.write_text(draft['text']);path.chmod(0o600)
        except ValueError:continue
    if make_video:
        selected=next((p for p in candidates if p['category']=='수납'),None)
        if not selected:raise ValueError('영상 후보가 없습니다.')
        return video(selected,folder/'video')
    return folder

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--video',action='store_true');args=parser.parse_args()
    try:print('콘텐츠 생성 완료 · 외부 발행 없음: '+str(run(args.video)))
    except Exception as exc:print('콘텐츠 생성 보류: '+type(exc).__name__);raise SystemExit(1) from None
