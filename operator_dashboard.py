"""Read-only local operations dashboard. Never serves credentials or arbitrary files."""
from contextlib import closing
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import html
import json
from pathlib import Path
import plistlib
import sqlite3
import tomllib
from urllib.parse import urlparse
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parent
ARTIFACTS=ROOT/'artifacts'
KST=ZoneInfo('Asia/Seoul')
LABELS={'published':'발행 완료','notified':'발행 완료','notification_failed':'알림 실패','selected':'상품 선택','draft_ready':'초안 준비','publishing':'발행 결과 확인 필요','generation_failed':'초안 검수·생성 보류','publication_uncertain':'발행 결과 확인 필요','deleted':'삭제됨','ready':'발행 대기'}
SUCCESS={'published','notified','notification_failed'}
esc=lambda x:html.escape(str(x if x is not None else '미확인'))


def read_json(path, default=None):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return default


def rows(path, query):
    if not path.exists():return []
    try:
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute(query)]
    except sqlite3.Error:return []


def safe_link(url, label):
    try:
        u=urlparse(url or '')
        if u.scheme=='https' and u.hostname in {'www.threads.com','threads.com','blog.naver.com','sallim-select.pages.dev','link.coupang.com','toss.shopping','toss.im'}:
            return '<a target="_blank" rel="noopener noreferrer" href="'+esc(url)+'">'+esc(label)+' ↗</a>'
    except ValueError:pass
    return ''


def stamp(epoch):
    try:return datetime.fromtimestamp(float(epoch),KST).strftime('%m/%d %H:%M')
    except (ValueError,TypeError,OSError):return '시각 미확인'


def next_slot(now,hours):
    for day in (0,1):
        for hour in sorted(hours):
            candidate=(now+timedelta(days=day)).replace(hour=hour,minute=0,second=0,microsecond=0)
            if candidate>now:return candidate.strftime('%m/%d %H:%M')
    return '예약 없음'


def snapshot(root=ROOT, now=None):
    root=Path(root);folder=root/'artifacts';now=now or datetime.now(KST)
    flags=dotenv_values(root/'.env') if (root/'.env').exists() else {}
    threads=rows(folder/'publications.sqlite3','SELECT id,run_key,product_name,status,created,updated,draft,publication,error_type FROM runs ORDER BY created DESC LIMIT 30')
    for r in threads:
        for field in ('draft','publication'):
            try:r[field]=json.loads(r[field] or '{}')
            except ValueError:r[field]={}
    queue=rows(folder/'blog-drafts/queue.sqlite3','SELECT id,slot,state,payload,public_url FROM queue ORDER BY slot DESC LIMIT 20')
    for r in queue:
        try:r['payload']=json.loads(r['payload'])
        except ValueError:r['payload']={}
    blog_config={}
    try:blog_config=tomllib.loads((Path.home()/'.codex/automations/automation/automation.toml').read_text())
    except (OSError,ValueError):pass
    hours=[]
    try:
        config=plistlib.loads((Path.home()/'Library/LaunchAgents/com.marine26k.coupang-partners.plist').read_bytes())
        hours=[x['Hour'] for x in config.get('StartCalendarInterval',[]) if 'Hour' in x]
    except (OSError,ValueError,KeyError):pass
    enabled=flags.get('AUTOMATION_ENABLED','').lower()=='true' and flags.get('THREADS_ENABLED','').lower()=='true'
    issues=[]
    expiry=flags.get('THREADS_TOKEN_EXPIRES_AT')
    try:
        days=(float(expiry)-now.timestamp())/86400
        if days<7:issues.append('Threads 인증 '+('만료됨' if days<0 else f'만료까지 {int(days)}일'))
    except (TypeError,ValueError):issues.append('Threads 인증 만료 시각 미확인')
    for r in threads:
        if r['status'] in {'generation_failed','publication_uncertain','publishing'}:issues.append('Threads · '+LABELS[r['status']]+' · '+r['product_name'])
    for r in queue:
        if r['state']=='publishing':issues.append('블로그 · 발행 결과를 확인한 뒤 재시도하세요 · '+str(r['slot']))
    catalog=read_json(root.parent/'sallim-select-catalog/catalog.json',{})
    for p in catalog.get('products',[]):
        if p.get('reviewReason'):issues.append('상품 확인 · '+p['name']+' · '+p['reviewReason'])
    try:
        age=(now-datetime.fromisoformat(catalog['updatedAt'])).total_seconds()
        if age>21600:issues.append('홈페이지 상품 정보가 6시간 넘게 갱신되지 않았습니다.')
    except (KeyError,ValueError,TypeError):issues.append('홈페이지 최근 수집 시각 미확인')
    analytics=read_json(folder/'analytics/summary.json',{})
    for key,ok in analytics.get('availability',{}).items():
        if not ok:issues.append('성과 리포트 연결 확인 필요 · '+key)
    return {'now':now,'threads':threads,'queue':queue,'analytics':analytics,'browserMetrics':read_json(folder/'analytics/browser-metrics.json',[]),'legacyBlogs':read_json(folder/'blog-drafts/publication-tests.json',{}).get('posts',[]),'learning':read_json(folder/'analytics/learning.json',{}),'issues':list(dict.fromkeys(issues))[:15],'catalog':catalog,'threadsHours':hours,'threadsEnabled':enabled,'threadsNext':next_slot(now,hours) if enabled and hours else '비활성 또는 예약 확인 필요','blogEnabled':blog_config.get('status')=='ACTIVE','blogNext':next_slot(now,[10,19]) if blog_config.get('status')=='ACTIVE' else '비활성 또는 예약 확인 필요'}


def render(data):
    now=data['now'];today=now.strftime('%Y-%m-%d')
    successful=[r for r in data['threads'] if r['status'] in SUCCESS and datetime.fromtimestamp(r['updated'],KST).date()==now.date()]
    scheduled={r.get('run_key') for r in successful if r.get('run_key') in {today+f'-{h:02d}' for h in data.get('threadsHours',[])}}
    manual=sum(not r.get('run_key') for r in successful)
    completed=f"{len(scheduled)} / {len(data.get('threadsHours',[]))}"
    blog_done=sum(r['state']=='published' and r['slot'] in {today+'-10',today+'-19'} for r in data['queue'])
    manual_blogs={p.get('url') for p in data['legacyBlogs'] if p.get('url') and p.get('status') in {'published_verified','published'}}
    manual_queue_urls={r.get('public_url') for r in data['queue'] if r['state']=='published' and 'manual' in str(r['slot']) and r.get('public_url')}
    manual_count=len(manual_blogs | manual_queue_urls)
    cards=''.join('<div class="stat"><small>'+title+'</small><strong>'+esc(value)+'</strong><span>'+note+'</span></div>' for title,value,note in [('오늘 Threads 예약 발행',completed,f'예약 완료 / 하루 예약 · 수동·시험 {manual}건 별도'),('오늘 블로그 예약 발행',f'{blog_done} / 2',f'예약 완료 / 하루 예약 · 수동 {manual_count}건 누적'),('다음 Threads',data['threadsNext'],'09시 · 13시 · 18시 / 한국시간'),('다음 블로그',data['blogNext'],'10시 쿠팡 · 19시 토스 / 한국시간')])
    thread_rows=''
    for r in data['threads']:
        publication=r['publication'];draft=r['draft']
        body=draft.get('threadsPost') or (draft.get('threadsPair') or {}).get('body') or ''
        thread_rows+='<article><div class="row"><span class="badge">'+esc(LABELS.get(r['status'],r['status']))+'</span><small>'+stamp(r['updated'])+'</small></div><h3>'+esc(r['product_name'])+'</h3>'+safe_link(publication.get('permalink'),'Threads 글 보기')+'<details><summary>저장된 본문 미리보기</summary><pre>'+esc(body or '저장된 본문이 없습니다.')+'</pre></details></article>'
    blog_rows=''
    for r in data['queue']:
        payload=r['payload']
        blog_rows+='<article><small>'+esc(r['slot'])+' · '+esc(LABELS.get(r['state'],r['state']))+'</small><h3>'+esc(payload.get('title','제목 미확인'))+'</h3>'+safe_link(r.get('public_url'),'블로그 글 보기')+'<details><summary>초안 보기</summary><pre>'+esc(payload.get('text',''))+'</pre></details></article>'
    if not blog_rows:blog_rows='<p class="empty">새 발행 대기열에 저장된 글이 없습니다. 상품은 예약 실행 시 검토하며 아직 정해지지 않은 후보는 표시하지 않습니다.</p>'
    legacy=''.join('<li>'+safe_link(p.get('url'),p.get('title') or p.get('name') or '기존 블로그 글')+' <span class="badge">수동 게시</span></li>' for p in data['legacyBlogs'] if p.get('url') in manual_blogs)
    metrics=data['analytics'];metric_rows=''
    for channel,m in metrics.get('channels',{}).items():metric_rows+='<tr><th>'+esc(channel)+'</th>'+''.join('<td>'+esc(m.get(k,'미확인'))+'</td>' for k in ('clicks','orders','cancels','commission'))+'</tr>'
    period=metrics.get('period',{})
    external=''.join('<article><h3>'+esc(x.get('provider'))+'</h3><small>'+esc(x.get('date'))+' · '+esc(x.get('scope'))+'</small><p>클릭 '+esc(x.get('clicks','미확인'))+' · 판매 '+esc(x.get('orders','미확인'))+' · 환불 '+esc(x.get('cancels','미확인'))+' · 예상 수익 '+esc(x.get('estimatedCommission','미확인'))+'원</p><small>관리 화면 확인 '+esc(x.get('capturedAt'))+'</small></article>' for x in data['browserMetrics'])
    issues=''.join('<li>'+esc(x)+'</li>' for x in data['issues']) or '<li>저장된 기록에서 감지된 문제가 없습니다. 실시간 로그인 상태를 보장하지는 않습니다.</li>'
    learning=''
    for axis,label in [('topic','주제'),('budget','가격대'),('hour','발행 시각')]:
        groups=data['learning'].get('groups',{}).get(axis,{})
        learning+='<h3>'+label+'</h3>'+(''.join('<p>'+esc(k)+' · '+esc(v.get('posts'))+'건 · 평균 조회 '+esc(v.get('averageViews'))+' · '+('학습 반영 가능' if v.get('eligible') else '표본 수집 중')+'</p>' for k,v in groups.items()) or '<p class="empty">분석 가능한 표본을 수집하고 있습니다.</p>')
    packages=''
    for path in sorted((ROOT/'artifacts/content-packages').glob('*-bundle.json')):
        value=read_json(path,{})
        if value:packages+='<details><summary>'+esc(value.get('title','묶음 초안'))+'</summary><p class="muted">미발행 초안 · '+esc(value.get('createdAt'))+'</p><pre>'+esc(value.get('text',''))+'</pre></details>'
    video=ROOT/'artifacts/content-packages/video/sallim-product.mp4'
    if video.exists():packages+='<h3>12초 세로 영상 · 미발행 샘플</h3><video controls preload="none" poster="/preview.png" src="/video.mp4"></video>'
    return '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="60"><title>살림셀렉트 관리</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f7f5ed;color:#193e30;font:15px/1.7 -apple-system,BlinkMacSystemFont,sans-serif}main{max-width:1200px;margin:auto;padding:32px 24px 70px}header{display:flex;justify-content:space-between;align-items:center;gap:20px;border-bottom:1px solid #d9dfd5;padding-bottom:20px}h1{font-size:27px;margin:0}h2{font-size:21px;margin:0 0 14px}h3{font-size:16px;margin:10px 0}.muted,small,.empty{color:#637368}small{font-size:12px}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:24px 0}.stat,section{background:white;border:1px solid #dde2d8;border-radius:16px;padding:20px}.stat strong{display:block;font-size:25px;margin:8px 0}.stat span{font-size:11px;color:#637368}.columns{display:grid;grid-template-columns:1.2fr 1fr;gap:20px}.columns>div{min-width:0}section{margin-bottom:20px}article{padding:14px 0;border-bottom:1px solid #e8ebe3}article:last-child{border:0}a{color:#225b44;text-underline-offset:4px}button{background:#193e30;color:white;border:0;border-radius:9px;padding:10px 16px;font:inherit}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;font-size:14px;background:#f7f8f3;padding:14px;border-radius:10px}summary{cursor:pointer;font-weight:600;padding:10px 0}.badge{display:inline-block;background:#e9eee5;border-radius:16px;font-size:12px;padding:3px 10px}.row{display:flex;justify-content:space-between;gap:10px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;border-bottom:1px solid #e3e7dd;padding:10px 7px}td{font-variant-numeric:tabular-nums}.table-wrap{overflow:auto}.warning{border-left:4px solid #9b7c38}ul{padding-left:20px}video{display:block;width:100%;max-width:280px;max-height:500px;border-radius:12px;background:#eee}nav{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;margin-top:14px}@media(max-width:800px){.stats{grid-template-columns:1fr 1fr}.columns{grid-template-columns:1fr}}@media(max-width:450px){main{padding:20px 14px}.stat{padding:13px}.stat strong{font-size:20px}header{display:block}h1{font-size:24px}}
    </style></head><body><main><header><div><small>PRIVATE WORKSPACE</small><h1>살림셀렉트 관리</h1><p class="muted">이 Mac 전용 · 읽기 전용 · 60초마다 화면 갱신</p></div><small>화면 확인 '''+esc(now.strftime('%m/%d %H:%M:%S'))+'''<br>한국시간</small></header><nav><a href="#publishing">발행 기록</a><a href="#performance">성과</a><a href="#issues">확인할 문제</a><a href="#previews">콘텐츠</a></nav><div class="stats">'''+cards+'''</div><p class="muted">예약 시각은 설정 기준입니다. Mac이 켜져 있고 인터넷에 연결돼야 하며, 블로그는 ChatGPT 앱과 로그인이 필요합니다. 예약 상품은 실행 시 선정합니다.</p><div class="columns"><div><section id="publishing"><h2>Threads 발행 기록</h2>'''+(thread_rows or '<p class="empty">저장된 발행 기록 없음</p>')+'''</section><section><h2>블로그 대기열·발행</h2>'''+blog_rows+'<details open><summary>수동 게시 기록 ('+str(len(manual_blogs))+')건</summary><p class="muted">대기열 도입 전 확인한 누적 기록입니다. 발행 날짜가 없어 오늘 예약 건수에는 포함하지 않습니다.</p><ul>'+legacy+'''</ul></details></section><section id="previews"><h2>콘텐츠 미리보기</h2>'''+(packages or '<p>초안과 영상이 아직 없습니다.</p>')+'''</section></div><div><section id="issues" class="warning"><h2>확인할 문제</h2><ul>'''+issues+'''</ul></section><section id="performance"><h2>최근 7일 쿠팡 성과</h2><small>'''+esc(period.get('start','기간 미확인'))+' ~ '+esc(period.get('end',''))+'''</small><div class="table-wrap"><table><thead><tr><th>채널</th><th>클릭</th><th>주문</th><th>취소</th><th>수수료</th></tr></thead><tbody>'''+metric_rows+'''</tbody></table></div><p class="muted">리포트 수수료는 확정 입금액이 아닙니다. 미수집 값은 0으로 바꾸지 않습니다. 과거 미분류 유입은 소급 구분하지 않습니다.</p></section><section><h2>관리 화면 확인 지표</h2>'''+(external or '<p class="empty">관리 화면 확인 기록 없음</p>')+'''<p class="muted">서비스별 집계 기간이 달라 합산하지 않습니다. 네이버 조회 통계·확정 정산액은 별도 확인이 필요합니다.</p></section><section><h2>다음 상품 선정 참고</h2>'''+learning+'''<p class="muted">24시간 지난 글만 비교합니다. 그룹별 5건·조회 100 이상 확보 후 반영하며 시간대는 자동 변경하지 않습니다.</p></section></div></div></main></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.headers.get('Host') not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}:
            self.send_error(403);return
        if self.headers.get('Sec-Fetch-Site')=='cross-site':self.send_error(403);return
        assets={'/preview.png':(ARTIFACTS/'content-packages/video/frame-0.png','image/png'),'/video.mp4':(ARTIFACTS/'content-packages/video/sallim-product.mp4','video/mp4')}
        try:
            if self.path=='/health':body=b'sallim-operator-v1';kind='text/plain'
            elif self.path in {'/','/index.html'}:body=render(snapshot()).encode();kind='text/html; charset=utf-8'
            elif self.path in assets:
                file,kind=assets[self.path];body=file.read_bytes()
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; media-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");self.end_headers();self.wfile.write(body)
        except (OSError,ValueError,TypeError):self.send_error(500,'Dashboard data unavailable')
    def do_POST(self):self.send_error(405)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8876);args=parser.parse_args()
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
