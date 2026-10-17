"""Durable content history and atomic recent-product reservations."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

ROOT = Path(__file__).resolve().parent


class History:
    def __init__(self, path=None):
        self.path = Path(path) if path else ROOT / 'artifacts/publications.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, run_key TEXT, product_id TEXT, product_name TEXT,
                keyword TEXT, created REAL, updated REAL, status TEXT,
                draft TEXT, publication TEXT, error_type TEXT)''')
            db.execute('CREATE INDEX IF NOT EXISTS recent_product ON runs(product_id,created)')
            db.execute('CREATE TABLE IF NOT EXISTS insights(run_id TEXT PRIMARY KEY,captured REAL,metrics TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY,run_id TEXT,created REAL,draft TEXT)')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=30)
        os.chmod(self.path, 0o600)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def next_keyword(self, keywords):
        if not keywords:
            raise ValueError('검색어가 필요합니다.')
        with self.db() as db:
            recent = dict(db.execute('SELECT keyword,MAX(created) FROM runs GROUP BY keyword'))
        return min(keywords, key=lambda key: recent.get(key, 0))

    def reserve(self, products, keyword, run_key=None, days=30):
        if days < 1:
            raise ValueError('중복 제외 기간은 1일 이상이어야 합니다.')
        now = time.time()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            recent = list(db.execute('''SELECT product_id FROM runs
                WHERE created>=? AND status IN ('selected','draft_ready','publishing',
                'published','notified','notification_failed','publication_uncertain')''',
                (now-days*86400,)))
            blocked = {r[0] for r in recent}
            blocked_names = {r[0] for r in db.execute('SELECT product_name FROM runs WHERE created>=? AND status NOT IN (\'generation_failed\',\'deleted\')',(now-days*86400,))}
            for product in products:
                pid = str(product.get('productId') or '')
                if not pid or pid in blocked or product.get('productName') in blocked_names or not product.get('productName'):
                    continue
                identifier = uuid.uuid4().hex
                db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    (identifier,run_key,pid,product['productName'],keyword,now,now,
                     'selected',None,None,None))
                return identifier, product
        return None, None

    def update(self, identifier, status, draft=None, publication=None, error_type=None):
        with self.db() as db:
            db.execute('''UPDATE runs SET updated=?,status=?,
                draft=COALESCE(?,draft),publication=COALESCE(?,publication),error_type=? WHERE id=?''',
                (time.time(),status,json.dumps(draft,ensure_ascii=False) if draft is not None else None,
                 json.dumps(publication,ensure_ascii=False) if publication is not None else None,
                 error_type,identifier))

        self.export_html()

    def records(self):
        with self.db() as db:
            records = [dict(r) for r in db.execute('SELECT * FROM runs ORDER BY created DESC')]
        for record in records:
            for field in ('draft','publication'):
                record[field] = json.loads(record[field]) if record[field] else None
        return records

    def import_existing(self, source_key, product, draft, publication, status='published'):
        with self.db() as db:
            if db.execute('SELECT 1 FROM runs WHERE run_key=?',(source_key,)).fetchone():
                return
            now=time.time()
            db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (uuid.uuid4().hex,source_key,str(product['productId']),product['productName'],
                 '기존 게시 이력',now,now,status,json.dumps(draft,ensure_ascii=False),
                 json.dumps(publication,ensure_ascii=False),None))

    def export_html(self, target=None):
        import html
        target = Path(target) if target else Path(os.environ.get('PUBLICATION_HISTORY_REPORT', str(self.path.parent / 'publication-history.html')))
        def esc(value):
            return html.escape(str(value or ''))
        labels={'selected':'상품 선택','draft_ready':'초안 저장','publishing':'게시 중',
                'published':'게시 완료','notified':'완료','notification_failed':'알림 실패',
                'generation_failed':'초안 생성 실패','publication_uncertain':'게시 상태 확인 필요',
                'deleted':'삭제됨'}
        cards=[]
        with self.db() as db:
            metrics = {r['run_id']: dict(r) for r in db.execute('SELECT * FROM insights')}
            revisions = list(db.execute('SELECT * FROM revisions ORDER BY created DESC'))
        for r in self.records():
            draft=r['draft'] or {}; pair=draft.get('threadsPair') or draft.get('pair') or {}
            publication=r['publication'] or {}
            url=publication.get('permalink','')
            link=f'<a href="{esc(url)}" target="_blank" rel="noopener">게시물 보기 ↗</a>' if url.startswith('https://www.threads.com/') else ''
            stats = metrics.get(r['id'])
            performance = '성과 미수집'
            if stats:
                values = json.loads(stats['metrics'])
                names = {'views':'조회','likes':'좋아요','replies':'댓글','reposts':'재게시','quotes':'인용','shares':'공유'}
                performance = ' · '.join(f'{label} {values.get(key, "미제공")}' for key,label in names.items())
                performance += ' (수집 ' + datetime.fromtimestamp(stats['captured']).strftime('%m-%d %H:%M') + ')'
            alternatives = ''
            for rev in revisions:
                if rev['run_id'] == r['id']:
                    pair_rev = json.loads(rev['draft'])['threadsPair']
                    alternatives += '<details><summary>미발행 재작성 초안</summary><pre>' + esc(pair_rev['body']) + '</pre><pre>' + esc(pair_rev['reply']) + '</pre></details>'
            stamp=datetime.fromtimestamp(r['created'],timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M')
            cards.append(f'''<article><small>{esc(stamp)} · {esc(r['keyword'])}</small>
                <h2>{esc(r['product_name'])}</h2><b>{esc(labels.get(r['status'],r['status']))}</b> {link}
                <details><summary>본문·첫 댓글 보기</summary><h3>본문</h3><pre>{esc(pair.get('body') or draft.get('dailyPost',''))}</pre>
                <h3>첫 댓글</h3><pre>{esc(pair.get('reply') or draft.get('hookPost',''))}</pre></details>
                <p>{esc(performance)}</p>{alternatives}<small>이력 ID {esc(r["id"])} · 상품 ID {esc(r['product_id'])} · 오류 유형 {esc(r['error_type']) or '없음'}</small></article>''')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>살림셀렉트 게시 이력</title>
        <style>body{font:16px/1.6 -apple-system,sans-serif;background:#f7f6ef;color:#173d2d;max-width:900px;margin:40px auto;padding:0 20px}article{background:white;border:1px solid #dedfd7;border-radius:16px;padding:24px;margin:18px 0}h2{font-size:20px}small{color:#666}pre{white-space:pre-wrap;font:inherit;color:#333}a{color:#1c6650}summary{cursor:pointer;margin:18px 0}</style>
        <h1>살림셀렉트 게시 이력</h1><p>본문·첫 댓글·발행 결과를 모아 봅니다. 파일을 다시 열거나 새로고침하면 최근 저장 내용을 확인할 수 있습니다.</p>'''+''.join(cards)+'</html>',encoding='utf-8')
        os.chmod(target,0o600)
        return target
