"""로컬 콜백으로 카카오 동의를 받고 토큰을 비공개 저장한다."""
import hmac
import os
from pathlib import Path
import secrets
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv, set_key

REPO = 'marine26k-sys/coupang-partners-automation'


def main():
    load_dotenv()
    redirect = os.environ.get('KAKAO_REDIRECT_URI', 'http://localhost:8080/callback')
    target = urlparse(redirect)
    if target.scheme != 'http' or target.hostname not in ('localhost', '127.0.0.1'):
        raise SystemExit('인증 콜백은 로컬 HTTP 주소만 지원합니다.')
    state = secrets.token_urlsafe(32)
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            valid = parsed.path == target.path and hmac.compare_digest(
                params.get('state', [''])[0], state)
            if not valid:
                self.send_error(400, 'Invalid callback')
                return
            result['code'] = params.get('code', [''])[0]
            result['error'] = bool(params.get('error'))
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write('인증 응답을 받았습니다. 이 창을 닫아도 됩니다.'.encode())

    server = HTTPServer(('127.0.0.1', target.port or 80), Callback)
    server.timeout = 600
    auth_url = 'https://kauth.kakao.com/oauth/authorize?' + urlencode({
        'client_id': os.environ['KAKAO_REST_API_KEY'], 'redirect_uri': redirect,
        'response_type': 'code', 'scope': 'talk_message', 'state': state,
    })
    Path('artifacts').mkdir(exist_ok=True)
    auth_file = Path('artifacts/kakao_authorize.url')
    fd = os.open(auth_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.chmod(auth_file, 0o600)
    with os.fdopen(fd, 'w') as out:
        out.write(auth_url)
    print('로컬 카카오 동의 응답 대기 중 (인증 주소·코드·토큰 출력 없음)', flush=True)
    try:
        deadline = time.monotonic() + 600
        while not result:
            server.timeout = max(0.1, deadline - time.monotonic())
            server.handle_request()
            if not result and time.monotonic() >= deadline:
                raise SystemExit('인증 응답 대기 시간이 만료됐습니다. 다시 실행하세요.')
        if result.get('error') or not result.get('code'):
            raise SystemExit('카카오 동의가 완료되지 않았습니다.')
        data = {'grant_type': 'authorization_code',
                'client_id': os.environ['KAKAO_REST_API_KEY'],
                'redirect_uri': redirect, 'code': result['code']}
        if os.environ.get('KAKAO_CLIENT_SECRET'):
            data['client_secret'] = os.environ['KAKAO_CLIENT_SECRET']
        response = requests.post('https://kauth.kakao.com/oauth/token', data=data, timeout=20)
        if not response.ok:
            raise SystemExit(f'카카오 토큰 발급 실패 (HTTP {response.status_code})')
        tokens = response.json()
        if 'talk_message' not in tokens.get('scope', '').split():
            raise SystemExit('카카오톡 메시지 전송 항목에 체크하고 다시 동의해주세요.')
        token = tokens.get('refresh_token')
        if not token:
            raise SystemExit('카카오 갱신 토큰이 없습니다.')
        Path('.env').touch(mode=0o600, exist_ok=True)
        os.chmod('.env', 0o600)
        set_key('.env', 'KAKAO_REFRESH_TOKEN', token)
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--repo', REPO],
                       input=token, text=True, capture_output=True, check=True)
        print('인증 완료: 로컬 및 GitHub Secrets에 토큰 저장')
    finally:
        server.server_close()
        auth_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
