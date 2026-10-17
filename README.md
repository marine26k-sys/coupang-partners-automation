# 쿠팡파트너스 초안 자동화

상품 검색 → 제휴 링크 → Gemini 초안 → 카카오 나에게 보내기.
Threads 자동 게시 기능은 아직 포함하지 않습니다.

## 로컬 실행

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --demo
python main.py --check
python main.py --no-send
python main.py
```

`.env`에 API 키를 입력합니다. 키를 커밋하지 마세요.
`--demo`는 외부 호출 없이 샘플을 저장합니다.
`--no-send`는 실제 API를 이용해 초안을 만들되 카카오 전송은 하지 않습니다.
결과는 `artifacts/draft.json`에 저장됩니다.

## GitHub 예약 실행

Actions에서 실행 모드 demo/draft/kakao를 선택합니다.
예약 시간은 한국시간 오전 9시와 오후 6시입니다.
저장소 변수 `AUTOMATION_ENABLED=true`일 때만 예약 실행합니다.
인증 전에는 예약 실행을 켜지 않습니다.
GitHub Secrets: COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY, GEMINI_API_KEY,
KAKAO_REST_API_KEY, KAKAO_REFRESH_TOKEN, 선택 KAKAO_CLIENT_SECRET.
GitHub Variables: SEARCH_KEYWORDS, 선택 GEMINI_MODEL.
GitHub Actions 아티팩트에서 초안 JSON을 받을 수 있습니다.
대시보드는 로컬에서 `python dashboard.py` 실행 후
`python -m http.server 8080 --bind 127.0.0.1 --directory docs`로 확인합니다.

## 계정 연결

쿠팡파트너스 계정의 API 이용 권한과 키가 필요합니다.
Gemini 키는 Google AI Studio에서 발급합니다.
카카오는 개발자 앱의 카카오 로그인, talk_message 동의 및 리다이렉트 URI를 설정합니다.
키 등록: `python setup_credentials.py` (입력값 비표시, .env 및 GitHub Secrets 동시 저장).
인증 지원 스크립트: `python kakao_auth.py` (로컬 콜백 및 state 검증, 토큰 자동 저장).
실행 중 `artifacts/kakao_authorize.url`의 주소를 브라우저에서 엽니다.
인증 주소·코드·토큰을 채팅이나 실행 인수에 붙여넣지 마세요.
카카오 앱은 기존 서비스와 분리한 전용 앱 사용을 권장합니다.
Gemini 기본 모델은 실제 호출로 검증한 `gemini-3.5-flash`이며 `GEMINI_MODEL`로 변경할 수 있습니다.

생성 글은 입력에 없는 사용 경험·효능·후기를 꾸며내지 않도록 지시하며,
제휴 고지는 본문에 프로그램으로 추가합니다. 생성 결과의 사실 여부는 게시 전 확인해야 합니다.


## Mac 예약 실행

`run_scheduled.py`는 로컬 `.env`의 `AUTOMATION_ENABLED=true`일 때 실행합니다.
동시에 여러 실행이 겹치지 않도록 잠그며, 기록은 비밀값을 가려 `artifacts/scheduler.log`에 저장합니다.
카카오 갱신 토큰이 교체되면 로컬 `.env`도 갱신합니다.
Mac에 등록된 LaunchAgent `com.marine26k.coupang-partners`는 오전 9시와 오후 6시에 실행합니다.
Mac의 시간대는 한국시간이어야 하며, 로그인된 Mac과 인터넷 연결이 필요합니다. 잠자기 중 놓친 실행은 깨어날 때 실행될 수 있습니다.
중지하려면 로컬 `.env`의 `AUTOMATION_ENABLED=false`로 바꾸세요.
GitHub 예약 활성화 변수와 로컬 활성화 값은 별개이며, 두 실행을 동시에 켜면 중복 발송됩니다.
GitHub Actions의 결제·사용 한도 문제는 별도로 해결해야 합니다.
로컬에서 갱신된 카카오 토큰은 GitHub Secrets와 다를 수 있으므로, Actions로 전환 전 `setup_credentials.py`로 다시 동기화하세요.
