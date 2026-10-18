# 쿠팡파트너스 초안 자동화

상품 검색 → 제휴 링크 → Gemini 초안 → 카카오 나에게 보내기.
Threads 자동 게시 기능은 별도 계정 연결 후 `THREADS_ENABLED=true`로 활성화합니다. 현재는 인증 대기 상태입니다.

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


## Threads 자동발행

Threads 공식 API용 Meta 앱과 게시할 Threads 계정의 권한 연결이 필요합니다.
필요한 권한은 `threads_basic`, `threads_content_publish`입니다.
앱 개발자 로그인과 실제 게시할 Threads 계정 로그인은 별개입니다.
공식 API 참고: https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api

로컬 `.env`에 `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN`,
`THREADS_TOKEN_EXPIRES_AT`(Unix 초), `THREADS_TOKEN_REFRESHED_AT`(Unix 초)를 보호 저장합니다.
최초 토큰과 앱 시크릿을 보호된 `.env`에 저장한 후 `python threads_connect.py`로 장기 토큰을 교환·저장할 수 있습니다.
장기 토큰 연결과 실제 계정 검증을 마친 뒤 `THREADS_ENABLED=true`로 켭니다.
토큰 만료 7일 전부터 실행 시 갱신하고 로컬 설정에 저장합니다. 만료되거나 권한이 철회되면 재인증이 필요합니다.

활성화하면 기존 Mac 오전 9시·오후 6시 예약이 상품 검색 → 글 생성 → Threads 게시 → 카카오 알림을 실행합니다.
게시 형식은 상품명 기반 소개·제휴 고지·제휴 링크를 포함한 500자 이내 단일 텍스트 글입니다.
`--demo`, `--no-send`, `--check`는 공개 게시하지 않습니다.
게시 이력은 `artifacts/threads.sqlite3`에 저장하며, 같은 계정·같은 예약 시간은 중복 게시하지 않습니다.
게시 도중 연결이 끊기는 등 결과가 불확실하면 자동 재시도를 멈춥니다. 해당 계정에서 실제 게시 여부를 확인한 뒤 복구해야 합니다.
중복 방지 기록이므로 운영 중 이 파일을 삭제하지 마세요.
현재 Threads 연결·실제 게시 검증은 완료되지 않았으며, 자동발행 기본값은 OFF입니다.
GitHub Actions에는 이 로컬 게시 이력이 보존되지 않으므로 Threads 게시를 연결하지 않았습니다.

## 상품 중복 방지·게시 이력

`publication_history.py`가 `artifacts/publications.sqlite3`에 상품 ID·이름·검색어·초안·본문/댓글 게시 주소·실행 상태를 저장합니다.
최근 30일간 선택·초안 저장·게시 중·게시 완료·알림 실패·게시 불확실 상태의 상품 ID 또는 이름은 다시 선택하지 않습니다.
`PRODUCT_COOLDOWN_DAYS`로 기간을 변경할 수 있습니다. 후보가 모두 제외되면 그 회차는 건너뜁니다.
초안 생성에 실패한 상품은 재시도할 수 있지만, 게시 여부가 불확실한 상품은 확인 전 재선정하지 않습니다.
상품 후보 내 중복 제거와 선택 예약은 한 데이터베이스 트랜잭션으로 처리합니다.
검색 키워드는 가장 오래 사용하지 않은 것부터 순환합니다.
`--no-send` 실행도 초안 이력에 남습니다. `--demo`, `--check`는 실제 상품 예약을 만들지 않습니다.
기본 이력 보고서는 `artifacts/publication-history.html`이며, `PUBLICATION_HISTORY_REPORT`로 다른 로컬 경로를 지정할 수 있습니다.
이력 갱신 시 HTML도 다시 생성됩니다. 외부 서비스 연결 없이 로컬에서 열어 확인합니다.
과거 데이터에 상품 ID가 없으면 기존 이름을 이용해 중복을 차단합니다.
본문만 게시된 예약을 다시 실행하면 새 상품을 붙이지 않고 복구가 필요하다고 중단합니다.
데이터베이스는 운영 이력이므로 삭제하지 마세요. GitHub Actions는 이 로컬 이력의 영속성을 보장하지 않습니다.

### 성과 확인과 문구 재작성

`python content_tools.py insights`는 최근 이력 20개 중 삭제되지 않은 게시물의 실제 조회·좋아요·댓글·재게시·인용·공유 수를 수집합니다. 게시 이력 HTML에 수집 시각을 표시하며, API가 제공하지 않은 값은 ‘미제공’, 미수집 이력은 ‘성과 미수집’으로 표시합니다. API 오류 시 기존 수집값은 보존됩니다. 수동 실행과 Mac 예약 발행 후 자동 수집을 지원합니다.

`python content_tools.py rewrite --id <이력 ID>`는 저장된 상품명·제휴 링크로 본문과 첫 댓글을 다시 만듭니다. 대안은 게시 이력의 ‘미발행 재작성 초안’에 보존되며 기존 게시물이나 원본 초안은 변경하지 않습니다. 이 명령은 게시·메시지 발송을 수행하지 않습니다. 성과 수집과 재작성은 로컬 `.env` 연결을 사용하며 토큰은 화면에 출력하지 않습니다.

참고한 공개 저장소: [threads-auto](https://github.com/pmpdoit73-lang/threads-auto), [COUPANG-AI-SYSTEM](https://github.com/cnc2052-create/COUPANG-AI-SYSTEM). 기존 코드에 맞춰 성과 확인과 재작성 흐름을 구현했으며 가상 경험·예측 수치를 실제 성과로 사용하지 않습니다.

### 상품 후보 비교와 시간별 성과

`python content_tools.py candidates --keyword 팬트리정리함`으로 쿠팡 API 검색 후보를 비교 화면에 저장합니다. 상품명·검색 당시 가격·로켓배송 여부·최근 선택 이력을 표시합니다. 다른 계정의 링크·문구를 가져오지 않으며, 검색 순서를 인기나 구매 성과로 표시하지 않습니다. 정기 발행 시 검색한 후보도 자동 저장됩니다.

성과 수집은 이제 기존 Mac 예약 실행(09시·18시)의 발행 작업 뒤에 별도로 실행됩니다. 수집 실패는 발행을 재시도시키지 않습니다. 각 측정값은 누적 저장되며 실제 API 게시 시각으로 게시 후 경과 시간을 계산합니다. 24·48·72시간부터 각각 12시간 이내의 첫 측정치를 비교 화면에 표시합니다. 정확히 해당 시각에 측정한 값이 아니므로 실제 경과 시간도 표시하며, 지나간 구간을 역산하지 않습니다. Mac이 꺼져 있거나 예약 간격 때문에 측정이 없으면 ‘기록 없음’으로 남습니다.

### 공개 프로필 상품 사이트

살림셀렉트 Sites 원본은 인접한 `../sallim-select` 폴더에 있으며, 공개 상품 데이터는 `marine26k-sys/sallim-select` 저장소의 `catalog.json`입니다. 공개 데이터에는 상품명·가격·공식 이미지·본인 제휴 링크·목록 순서·수집 시각만 포함합니다. 인증 키·토큰·개인 게시 이력은 포함하지 않습니다.

`python catalog.py --publish`는 골드박스 8개, 주방 베스트 8개, 생활용품 베스트 8개, 팬트리 검색 8개를 수집하고 본인 제휴 링크로 변환해 공개 목록을 갱신합니다. 기존 Mac 오전 9시·오후 6시 예약 실행에도 연결되어 있습니다. Mac이 켜져 있고 GitHub 인증이 유효해야 갱신됩니다. 사이트는 Mac이 꺼져도 마지막 공개 자료를 표시합니다. GitHub Actions나 추가 결제는 사용하지 않습니다.

동일 상품 ID와 vendorItemId의 이전 관측일 가격이 있을 때만 가격 변화를 표시합니다. 첫날이나 옵션 식별이 안 되는 상품은 ‘가격 기록 수집 중’으로 표시하며 시장 최저가를 주장하지 않습니다. 사이트에서 상품 검색·카테고리 선택·가격 정렬·브라우저 내 관심 상품 저장이 가능합니다.

참고 사이트 [todaydeal](https://github.com/HyaC1107/todaydeal)의 상품 모음 흐름을 참고하여 살림셀렉트 화면과 수집기를 새로 작성했습니다. 다른 계정의 제휴 링크나 사용 후기는 복사하지 않았습니다.

공개 주소: https://marine26k-sys.github.io/sallim-select/ (GitHub Pages). Sites 기본 주소에 워크스페이스 이름과 chatgpt가 포함되어, 사용자 요청에 따라 공개 운영을 GitHub Pages로 이전했습니다. 공개 파일은 `../sallim-select-catalog` 로컬 폴더에서 `marine26k-sys/sallim-select`로 반영됩니다.


### Cloudflare Pages 무료 호스팅 이전

현재 공식 프로필 사이트는 https://sallim-select.pages.dev/ 입니다. 주소에 GitHub 사용자명이나 ChatGPT 워크스페이스 이름이 포함되지 않습니다. Cloudflare Pages Direct Upload로 공개 화면 파일 5개만 배포했습니다.

가격 수집은 기존 Mac 예약 실행(09:00·18:00 KST)을 그대로 사용합니다. `catalog.py --publish`가 공개 상품 저장소의 catalog.json을 갱신하면 새 사이트도 브라우저에서 이를 읽습니다. 가격 갱신을 위해 Cloudflare에 파일을 매번 올리거나 키를 추가할 필요는 없습니다. GitHub 연결 장애 시에는 업로드 당시 저장 자료를 수집 시각과 함께 표시합니다. 화면 디자인 변경은 별도 재배포가 필요합니다.

Cloudflare 프로젝트 이름: sallim-select. 인증정보나 개인 게시 이력은 배포에 포함하지 않습니다. 무료 기본 pages.dev 주소를 사용하며 유료 플랜·도메인 구매는 진행하지 않았습니다.

### 본문 한 개로 발행

현재 예약 자동발행은 첫 댓글을 생성하지 않습니다. 짧은 제휴 고지 → 구매 기준 → 상품명·제휴 링크 → 전체 제휴 고지를 한 본문에 담습니다. 500자를 초과하거나 댓글 안내·과장 표현이 포함되면 발행하지 않습니다. 재작성 초안도 같은 본문 형식으로 생성합니다. 과거 본문+첫 댓글 이력과 중복 방지 기록은 보존합니다.
