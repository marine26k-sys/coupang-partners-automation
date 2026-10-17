"""Threads publishing with private credentials and a durable duplicate guard."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sqlite3
import time

import requests
from dotenv import set_key

ROOT = Path(__file__).resolve().parent
API = 'https://graph.threads.net/v1.0'


class ThreadsError(RuntimeError):
    pass


class ThreadsClient:
    def __init__(self, token=None, user_id=None, session=None):
        self.token = token or os.environ['THREADS_ACCESS_TOKEN']
        self.user_id = user_id or os.environ['THREADS_USER_ID']
        self.session = session or requests.Session()

    def request(self, method, path, data=None):
        try:
            base = 'https://graph.threads.net' if path == 'refresh_access_token' else API
            response = self.session.request(method, base + '/' + path,
                headers={'Authorization': 'Bearer ' + self.token},
                **({'params': data} if method == 'GET' else {'data': data}), timeout=30)
        except requests.RequestException:
            raise ThreadsError('Threads 연결 오류: 게시 상태 확인이 필요합니다.') from None
        try:
            body = response.json()
        except ValueError:
            raise ThreadsError('Threads 응답을 해석할 수 없습니다.') from None
        if not response.ok or body.get('error'):
            code = body.get('error', {}).get('code', 'unknown')
            raise ThreadsError(f'Threads API 오류 (HTTP {response.status_code}, code {code})')
        return body

    def verify_account(self):
        account = self.request('GET', 'me', {'fields': 'id,username'})
        if str(account.get('id')) != str(self.user_id):
            raise ThreadsError('연결된 Threads 계정 ID가 설정과 다릅니다.')
        return account

    def refresh_if_needed(self):
        expires = float(os.environ.get('THREADS_TOKEN_EXPIRES_AT', '0'))
        refreshed = float(os.environ.get('THREADS_TOKEN_REFRESHED_AT', '0'))
        if not expires:
            raise ThreadsError('Threads 토큰 만료 정보가 없습니다. 계정 연결을 다시 확인하세요.')
        now = time.time()
        if expires <= now:
            raise ThreadsError('Threads 토큰이 만료됐습니다. 재인증이 필요합니다.')
        if expires - now > 7 * 86400 or now - refreshed < 86400:
            return
        result = self.request('GET', 'refresh_access_token', {'grant_type': 'th_refresh_token'})
        if not result.get('access_token') or not result.get('expires_in'):
            raise ThreadsError('Threads 토큰 갱신 응답이 불완전합니다.')
        values = {'THREADS_ACCESS_TOKEN': result['access_token'],
                  'THREADS_TOKEN_EXPIRES_AT': str(int(now + result['expires_in'])),
                  'THREADS_TOKEN_REFRESHED_AT': str(int(now))}
        env_file = ROOT / '.env'
        if not env_file.exists() or os.environ.get('GITHUB_ACTIONS'):
            raise ThreadsError('Threads 토큰 갱신을 안전하게 저장할 로컬 설정이 필요합니다.')
        os.chmod(env_file, 0o600)
        for key, value in values.items():
            set_key(str(env_file), key, value)
            os.environ[key] = value
        self.token = values['THREADS_ACCESS_TOKEN']


@contextmanager
def journal_connect(path=None):
    path = Path(path) if path else ROOT / 'artifacts/threads.sqlite3'
    path.parent.mkdir(exist_ok=True, parents=True)
    db = sqlite3.connect(path, timeout=30)
    os.chmod(path, 0o600)
    db.row_factory = sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS posts (
        account TEXT, run_key TEXT, digest TEXT, state TEXT,
        container_id TEXT, post_id TEXT, permalink TEXT,
        PRIMARY KEY(account, run_key))''')
    try:
        with db:
            yield db
    finally:
        db.close()


def published_for_run(user_id, run_key, journal_path=None):
    with journal_connect(journal_path) as db:
        row = db.execute('SELECT * FROM posts WHERE account=? AND run_key=?',
                         (str(user_id), run_key)).fetchone()
        if row and row['state'] != 'published':
            raise ThreadsError('이 실행의 이전 게시 상태가 불확실합니다. Threads에서 확인 후 복구해야 합니다.')
        return dict(row) if row else None


def publish_text(text, run_key=None, client=None, journal_path=None, reply_to_id=None):
    from content_generator import DISCLOSURE_TEXT, SHORT_DISCLOSURE
    is_hook = text.startswith(SHORT_DISCLOSURE)
    if not is_hook and (not text.startswith(DISCLOSURE_TEXT) or 'https://link.coupang.com/' not in text):
        raise ThreadsError('제휴 고지와 제휴 링크가 있는 글만 게시합니다.')
    if len(text) > 500:
        raise ThreadsError('Threads 글이 500자를 초과했습니다. 초안만 저장합니다.')
    client = client or ThreadsClient()
    digest = hashlib.sha256(text.encode()).hexdigest()
    run_key = run_key or digest
    existing = published_for_run(client.user_id, run_key, journal_path)
    if existing:
        return existing
    client.refresh_if_needed()
    client.verify_account()
    with journal_connect(journal_path) as db:
        try:
            db.execute('INSERT INTO posts(account,run_key,digest,state) VALUES(?,?,?,?)',
                       (str(client.user_id), run_key, digest, 'creating'))
        except sqlite3.IntegrityError:
            raise ThreadsError('동일 실행의 게시가 이미 시작됐습니다.') from None
    # A failed/uncertain publish remains journaled. Do not blindly retry public posts.
    container = client.request('POST', client.user_id + '/threads',
                               {'media_type': 'TEXT', 'text': text, **({'reply_to_id': reply_to_id} if reply_to_id else {})})
    container_id = container.get('id')
    if not container_id:
        raise ThreadsError('Threads 게시 컨테이너 ID가 없습니다.')
    with journal_connect(journal_path) as db:
        db.execute('UPDATE posts SET state=?,container_id=? WHERE account=? AND run_key=?',
                   ('publishing', container_id, str(client.user_id), run_key))
    result = client.request('POST', client.user_id + '/threads_publish',
                            {'creation_id': container_id})
    post_id = result.get('id')
    if not post_id:
        raise ThreadsError('Threads 게시 ID를 받지 못했습니다. 수동 확인이 필요합니다.')
    with journal_connect(journal_path) as db:
        db.execute('UPDATE posts SET state=?,post_id=? WHERE account=? AND run_key=?',
                   ('published', post_id, str(client.user_id), run_key))
    permalink = ''
    try:
        permalink = client.request('GET', post_id, {'fields': 'permalink'}).get('permalink', '')
    except ThreadsError:
        pass
    with journal_connect(journal_path) as db:
        db.execute('UPDATE posts SET permalink=? WHERE account=? AND run_key=?',
                   (permalink, str(client.user_id), run_key))
    return {'post_id': post_id, 'permalink': permalink, 'state': 'published'}


def publish_pair(pair, run_key=None, client=None, journal_path=None):
    from content_generator import DISCLOSURE_TEXT, SHORT_DISCLOSURE
    if not pair['body'].startswith(SHORT_DISCLOSURE) or not pair['reply'].startswith(DISCLOSURE_TEXT):
        raise ThreadsError('본문과 댓글의 제휴 고지가 필요합니다.')
    if 'https://link.coupang.com/' not in pair['reply'] or any(len(v)>500 for v in pair.values()):
        raise ThreadsError('댓글 링크 또는 본문·댓글 길이를 확인하세요.')
    client = client or ThreadsClient()
    key = run_key or hashlib.sha256((pair['body']+pair['reply']).encode()).hexdigest()
    root = publish_text(pair['body'], key, client, journal_path)
    reply = publish_text(pair['reply'], key+':reply', client, journal_path, reply_to_id=root['post_id'])
    return {**root, 'reply_id': reply['post_id'], 'reply_permalink': reply.get('permalink','')}
