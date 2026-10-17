"""API 키를 화면에 노출하지 않고 로컬 및 GitHub Secrets에 등록합니다."""
import getpass
import os
from pathlib import Path
import subprocess
from dotenv import dotenv_values

REPO = 'marine26k-sys/coupang-partners-automation'
FIELDS = {
    'COUPANG_ACCESS_KEY': '쿠팡파트너스 Access Key',
    'COUPANG_SECRET_KEY': '쿠팡파트너스 Secret Key',
    'GEMINI_API_KEY': 'Google AI Studio API Key',
    'KAKAO_REST_API_KEY': '카카오 개발자 앱 REST API Key',
    'KAKAO_CLIENT_SECRET': '카카오 Client Secret (사용하지 않으면 Enter)',
    'KAKAO_REFRESH_TOKEN': '카카오 Refresh Token (아직 없으면 Enter)',
}


def main():
    values = dict(dotenv_values('.env'))
    for name, label in FIELDS.items():
        if values.get(name):
            print(f'{label}: 기존 설정 사용')
            continue
        value = getpass.getpass(f'{label}: ').strip()
        if value:
            values[name] = value
    values.setdefault('SEARCH_KEYWORDS', '주방 정리,수납 정리,생활용품')
    values.setdefault('KAKAO_REDIRECT_URI', 'http://localhost:8080/callback')
    target = Path('.env')
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.chmod(target, 0o600)
    with os.fdopen(fd, 'w') as out:
        for key, value in values.items():
            if value is not None:
                escaped = value.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '')
                out.write(f"{key}='{escaped}'\n")
    for key in FIELDS:
        if values.get(key):
            subprocess.run(['gh', 'secret', 'set', key, '--repo', REPO],
                           input=values[key], text=True, check=True)
    subprocess.run(['gh', 'variable', 'set', 'SEARCH_KEYWORDS', '--repo', REPO,
                    '--body', values['SEARCH_KEYWORDS']], check=True)
    print('입력한 인증 정보를 저장했습니다. 비밀 값은 출력하지 않습니다.')


if __name__ == '__main__':
    main()
