"""Verify the production Pages URL serves a complete, usable catalog site."""
import json
from html.parser import HTMLParser
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stylesheets = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'link' and 'stylesheet' in values.get('rel', '').split():
            self.stylesheets.append(values.get('href', ''))
        elif tag == 'script' and values.get('src'):
            self.scripts.append(values['src'])


def get(url):
    request = Request(url, headers={'User-Agent': 'SallimSiteHealthCheck/1.0'})
    with urlopen(request, timeout=15) as response:
        body = response.read()
        if response.status != 200 or not body:
            raise RuntimeError(f'빈 응답 또는 HTTP {response.status}: {url}')
        return body, response.headers.get('Content-Type', '')


def verify(base):
    base = base.rstrip('/') + '/'
    origin = urlparse(base).netloc
    html, content_type = get(base)
    if 'text/html' not in content_type:
        raise RuntimeError('홈페이지 응답 형식이 HTML이 아닙니다.')
    parser = Assets()
    parser.feed(html.decode('utf-8'))
    if not parser.stylesheets or not parser.scripts:
        raise RuntimeError('홈페이지에서 CSS 또는 스크립트 연결을 찾지 못했습니다.')
    for asset in [*parser.stylesheets, *parser.scripts, 'logo.png']:
        url = urljoin(base, asset)
        if urlparse(url).netloc != origin:
            continue
        body, asset_type = get(url)
        if len(body) < 100:
            raise RuntimeError(f'정적 파일 응답이 비정상적으로 작습니다: {asset}')
        path = urlparse(url).path
        if path.endswith('.css') and 'text/css' not in asset_type:
            raise RuntimeError(f'스타일 파일 형식이 올바르지 않습니다: {asset}')
        if path.endswith('.js') and 'javascript' not in asset_type:
            raise RuntimeError(f'스크립트 파일 형식이 올바르지 않습니다: {asset}')
        if path.endswith('.png') and not body.startswith(b'\x89PNG\r\n\x1a\n'):
            raise RuntimeError(f'로고 이미지 파일 형식이 올바르지 않습니다: {asset}')
    raw, content_type = get(urljoin(base, 'catalog.json'))
    if 'json' not in content_type.lower():
        raise RuntimeError('상품 목록 응답 형식이 JSON이 아닙니다.')
    catalog = json.loads(raw)
    if not isinstance(catalog.get('products'), list) or not catalog['products']:
        raise RuntimeError('상품 목록이 비어 있거나 형식이 올바르지 않습니다.')
    if not catalog.get('updatedAt'):
        raise RuntimeError('상품 목록 갱신 시각이 없습니다.')
    return len(catalog['products'])


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'https://sallim-select.pages.dev/'
    last_error = None
    for attempt in range(6):
        try:
            count = verify(target)
            print(f'홈페이지 확인 완료: 화면·CSS·스크립트·로고·상품 {count}개 정상')
            raise SystemExit(0)
        except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt < 5:
                time.sleep(5)
    print(f'홈페이지 확인 실패: {type(last_error).__name__}: {last_error}', file=sys.stderr)
    raise SystemExit(1)
