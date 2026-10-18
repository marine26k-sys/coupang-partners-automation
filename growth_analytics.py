"""Private channel reports and cautious editorial feedback; no public publication."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import argparse
import json
import os
from pathlib import Path
import time
from urllib.parse import urlencode
from publication_history import History, ROOT

CHANNELS={'threads_auto':'Threads','sallim_select':'홈페이지','blog_auto':'블로그'}
KINDS=('clicks','orders','cancels','commission')


def private_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2));temp.chmod(0o600);temp.replace(path)


def fetch_reports(client, start, end, pause=time.sleep):
    results={}
    for kind in KINDS:
        rows=[]
        try:
            for page in range(10):
                response=client._request('GET','/v2/providers/affiliate_open_api/apis/openapi/v1/reports/'+kind,query=urlencode({'startDate':start,'endDate':end,'page':page}))
                data=response.get('data')
                if not isinstance(data,list):raise ValueError('Unexpected report schema')
                rows.extend(data)
                if len(data)<1000:break
                if page==9:raise ValueError('Report pagination incomplete')
                pause(1)
            results[kind]={'available':True,'rows':rows}
        except Exception as exc:
            if getattr(getattr(exc,'response',None),'status_code',None)==429:
                for remaining in KINDS:
                    if remaining not in results:results[remaining]={'available':False,'rows':[],'errorType':'RateLimited'}
                break
            results[kind]={'available':False,'rows':[],'errorType':type(exc).__name__}
    return {'start':start,'end':end,'capturedAt':datetime.now(timezone.utc).isoformat(),'reports':results}


def aggregate(snapshot):
    # Keep API totals separated: a commission row may repeat clicks already in clicks report.
    fields={'clicks':('click',),'orders':('quantity','orderCount','order'),'cancels':('quantity','cancelCount','cancel'),'commission':('commission',)}
    grouped={}
    for kind,report in snapshot['reports'].items():
        for row in report['rows']:
            channel=CHANNELS.get(row.get('subId'),'미분류')
            entry=grouped.setdefault(channel,{})
            field=next((f for f in fields[kind] if isinstance(row.get(f),(int,float))),None)
            if field:entry[kind]=entry.get(kind,0)+row[field]
    return {'period':{'start':snapshot['start'],'end':snapshot['end']},'availability':{k:v['available'] for k,v in snapshot['reports'].items()},'channels':grouped,'notes':['수수료 리포트 값은 확정 입금액이 아닙니다.','채널을 구분하지 않은 과거 링크는 미분류로 남깁니다.','조회·클릭·주문은 집계 기준이 달라 개별 게시물 구매로 단정하지 않습니다.']}


def feedback(history, now=None):
    now=now or time.time();cutoff=now-30*86400
    with history.db() as db:metrics={r['run_id']:json.loads(r['metrics']) for r in db.execute('SELECT * FROM insights')}
    groups={'topic':{},'budget':{},'hour':{}}
    for record in history.records():
        if record['status'] not in ('published','notified','notification_failed') or record['created']<cutoff or now-record['created']<86400:continue
        m=metrics.get(record['id']);draft=record.get('draft') or {}
        if not m or not isinstance(m.get('views'),(int,float)):continue
        price=draft.get('productPrice');budget='미확인' if not isinstance(price,(int,float)) or price<=0 else '1만원 이하' if price<=10000 else '3만원 이하' if price<=30000 else '3만원 초과'
        hour=str(datetime.fromtimestamp(record['created'],ZoneInfo('Asia/Seoul')).hour)
        engagement=sum(m.get(k,0) for k in ('likes','replies','reposts','quotes','shares'))
        for axis,key in [('topic',record['keyword']),('budget',budget),('hour',hour)]:
            g=groups[axis].setdefault(key,{'posts':0,'views':0,'engagement':0})
            g['posts']+=1;g['views']+=m['views'];g['engagement']+=engagement
    for axis in groups.values():
        for item in axis.values():
            item['averageViews']=round(item['views']/item['posts'],1)
            item['engagementRate']=round(item['engagement']/item['views'],4) if item['views'] else None
            item['eligible']=item['posts']>=5 and item['views']>=100
    return {'capturedAt':datetime.now(timezone.utc).isoformat(),'groups':groups,'minimumPosts':5,'minimumViews':100,'notes':['발행 후 24시간 이상 지난 글만 비교합니다. 노출 기간 차이가 있어 관찰 자료로만 사용합니다.','시간대는 자동 변경하지 않습니다. 표본 기준 충족 전에는 상품 선정 가중치를 바꾸지 않습니다.']}


def prefer_learned(products, report):
    topics=report.get('groups',{}).get('topic',{})
    eligible={k:v for k,v in topics.items() if v.get('eligible')}
    if len(eligible)<2:return products
    # Small bounded score preserves strong observed-price signals and editorial budget priority.
    best=max(v['averageViews'] for v in eligible.values()) or 1
    return sorted(products,key=lambda p:-(p.get('observedScore',0)+10*eligible.get(p.get('selectionSource'),{}).get('averageViews',0)/best))


def write_summary(summary, learning, folder):
    lines=['# 살림셀렉트 성과 요약',f"집계 기간: {summary['period']['start']}~{summary['period']['end']}",'','|채널|클릭|주문 수량|취소 수량|리포트 수수료(원)|','|---|---:|---:|---:|---:|']
    for channel,values in summary['channels'].items():lines.append('|'+channel+'|'+ '|'.join(str(values.get(k,'미확인')) for k in KINDS)+'|')
    lines+=['','성공한 리포트의 빈 목록은 해당 기간 기록 없음입니다. 수집 실패는 0으로 표시하지 않습니다.','수집 상태: '+', '.join(k+(' 정상' if v else ' 확인 필요') for k,v in summary['availability'].items()),'']+summary['notes']
    lines+=['','## 게시물 학습','기준: 24시간 지난 글, 그룹당 5건 이상·조회 100 이상. 구매 전환 성과로 해석하지 않습니다.']
    for axis,groups in learning['groups'].items():
        lines+=['',axis]+[f"- {k}: {v['posts']}건 / 평균 조회 {v['averageViews']} / {'학습 가능' if v['eligible'] else '표본 수집 중'}" for k,v in groups.items()]
    browser=folder/'browser-metrics.json'
    if browser.exists():
        try:
            external=json.loads(browser.read_text())
            lines+=['','## 관리 화면에서 확인한 성과', 'API 집계와 기간·채널이 다를 수 있으므로 합산하지 않습니다.']
            for row in external:
                lines.append('- '+row['provider']+' / '+row['date']+' / '+row['scope']+': 클릭 '+str(row.get('clicks','미확인'))+', 판매 '+str(row.get('orders','미확인'))+', 환불 '+str(row.get('cancels','미확인'))+', 예상 수익 '+str(row.get('estimatedCommission','미확인'))+'원 · 확인 '+row['capturedAt'])
        except (OSError,ValueError,KeyError,TypeError):lines.append('관리 화면 지표 확인 필요')
    lines+=['','네이버 방문/조회 지표와 토스 정산 확정액은 별도 관리 화면 확인이 필요합니다. 누락은 0으로 처리하지 않습니다.']
    path=folder/'weekly-summary.md';path.write_text('\n'.join(lines));path.chmod(0o600)


def run():
    from dotenv import load_dotenv
    from coupang_api import CoupangPartnersClient
    load_dotenv(ROOT/'.env');folder=ROOT/'artifacts/analytics'
    end=datetime.now(ZoneInfo('Asia/Seoul')).date()-timedelta(days=1);start=end-timedelta(days=6)
    snapshot=fetch_reports(CoupangPartnersClient(),start.strftime('%Y%m%d'),end.strftime('%Y%m%d'))
    private_json(folder/'coupang-latest.json',snapshot)
    summary=aggregate(snapshot);learning=feedback(History())
    private_json(folder/'summary.json',summary);private_json(folder/'learning.json',learning);write_summary(summary,learning,folder)
    print('성과 보고서 갱신 완료 · 정상 리포트 '+str(sum(summary['availability'].values()))+'/4 · 비공개 저장')

if __name__=='__main__':run()
