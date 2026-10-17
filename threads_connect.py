"""Exchange a privately stored short-lived Threads token; never print credentials."""
import os
from pathlib import Path
import subprocess
import time
import requests
from dotenv import load_dotenv, set_key, unset_key
from threads_api import ThreadsClient

ROOT = Path(__file__).resolve().parent


def main():
    env_file = ROOT / '.env'
    load_dotenv(env_file)
    short_token = os.environ.get('THREADS_SHORT_LIVED_TOKEN')
    secret = os.environ.get('THREADS_APP_SECRET')
    if not short_token or not secret:
        raise SystemExit('보호된 로컬 설정에 Threads 앱 시크릿과 최초 토큰이 필요합니다.')
    try:
        response = requests.get('https://graph.threads.net/access_token',
            params={'grant_type': 'th_exchange_token', 'client_secret': secret,
                    'access_token': short_token}, timeout=30)
    except requests.RequestException:
        raise SystemExit('Threads 장기 토큰 교환 연결 실패') from None
    if not response.ok:
        raise SystemExit(f'Threads 장기 토큰 교환 실패 (HTTP {response.status_code})')
    result = response.json()
    token = result.get('access_token')
    expires = result.get('expires_in')
    if not token or not expires:
        raise SystemExit('Threads 장기 토큰 응답이 불완전합니다.')
    client = ThreadsClient(token=token, user_id='pending')
    account = client.request('GET', 'me', {'fields': 'id,username'})
    if not account.get('id'):
        raise SystemExit('Threads 계정 ID를 확인하지 못했습니다.')
    now = int(time.time())
    values = {'THREADS_ACCESS_TOKEN': token, 'THREADS_USER_ID': str(account['id']),
              'THREADS_TOKEN_EXPIRES_AT': str(now + int(expires)),
              'THREADS_TOKEN_REFRESHED_AT': str(now), 'THREADS_ENABLED': 'false'}
    os.chmod(env_file, 0o600)
    for key, value in values.items():
        set_key(str(env_file), key, value)
    unset_key(str(env_file), 'THREADS_SHORT_LIVED_TOKEN')
    # Retain a backup of the token, but keep GitHub publication disabled.
    subprocess.run(['gh', 'secret', 'set', 'THREADS_ACCESS_TOKEN', '--repo',
                    'marine26k-sys/coupang-partners-automation'],
                   input=token, text=True, capture_output=True, check=True)
    print('Threads 장기 토큰 보호 저장 완료')
    print('연결 계정: @' + account.get('username', '(확인 필요)'))
    print('자동발행은 첫 게시 검증 전까지 OFF 상태입니다.')


if __name__ == '__main__':
    main()
