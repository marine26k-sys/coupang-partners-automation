"""Read real post insights or create an unpublished alternative draft."""
import argparse
import json
import os
from pathlib import Path
import time
from dotenv import load_dotenv
from publication_history import History, ROOT

METRICS = ('views', 'likes', 'replies', 'reposts', 'quotes', 'shares')


def collect(history, client):
    client.verify_account()
    count = 0
    for record in history.records()[:20]:
        post_id = (record['publication'] or {}).get('post_id')
        if record['status'] == 'deleted' or not post_id:
            continue
        try:
            result = client.request('GET', str(post_id) + '/insights', {'metric': ','.join(METRICS)})
        except Exception:
            continue
        published = None
        try:
            from datetime import datetime
            metadata = client.request('GET', str(post_id), {'fields':'timestamp'})
            published = datetime.fromisoformat(metadata['timestamp'].replace('Z','+00:00')).timestamp()
        except Exception:
            pass
        values = {}
        for item in result.get('data', []):
            rows = item.get('values') or []
            value = rows[-1].get('value') if rows else None
            if item.get('name') in METRICS and isinstance(value, (int, float)):
                values[item['name']] = value
        if values:
            with history.db() as db:
                db.execute('INSERT OR REPLACE INTO insights VALUES(?,?,?)',
                           (record['id'], time.time(), json.dumps(values)))
                db.execute('INSERT INTO insight_samples VALUES(?,?,?,?)',
                           (record['id'],time.time(),published,json.dumps(values)))
            count += 1
    history.export_html()
    return count


def rewrite(history, identifier, generator=None):
    from content_generator import generate_threads_pair
    record = next((r for r in history.records() if r['id'] == identifier), None)
    if not record or not record['draft']:
        raise ValueError('저장된 초안 ID를 확인하세요.')
    draft = record['draft']
    link = draft.get('deeplink')
    if not link or not link.startswith('https://link.coupang.com/'):
        raise ValueError('원본 제휴 링크가 필요합니다.')
    pair = (generator or generate_threads_pair)(record['product_name'], link)
    result = {'source_id': identifier, 'productName': record['product_name'],
              'deeplink': link, 'threadsPair': pair, 'status': 'unpublished'}
    with history.db() as db:
        db.execute('INSERT INTO revisions(run_id,created,draft) VALUES(?,?,?)',
                   (identifier, time.time(), json.dumps(result, ensure_ascii=False)))
    history.export_html()
    return result


def main():
    load_dotenv(ROOT / '.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['insights', 'rewrite', 'candidates'])
    parser.add_argument('--id')
    parser.add_argument('--keyword')
    args = parser.parse_args()
    history = History()
    try:
        if args.action == 'insights':
            from threads_api import ThreadsClient
            print(f'성과 수집 완료: {collect(history, ThreadsClient())}개')
        elif args.action == 'candidates':
            from coupang_api import CoupangPartnersClient
            keyword = args.keyword or history.next_keyword([k.strip() for k in os.environ.get('SEARCH_KEYWORDS','').split(',') if k.strip()])
            products = CoupangPartnersClient().search_products(keyword, limit=10)
            history.save_candidates(products, keyword)
            print(f'비교 후보 {len(products)}개 저장 완료 (발행 없음)')
        else:
            if not args.id:
                parser.error('rewrite에는 --id가 필요합니다.')
            rewrite(history, args.id)
            print('재작성 초안을 게시 이력에 저장했습니다. 발행하지 않았습니다.')
    except Exception as exc:
        print(f'작업 실패: {type(exc).__name__} (인증정보 보호를 위해 상세 응답 생략)')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
