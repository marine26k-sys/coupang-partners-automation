"""
전체 파이프라인 실행 스크립트
"""

import argparse
import json
from pathlib import Path
import os
import random
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

from coupang_api import CoupangPartnersClient
from content_generator import generate_daily_post, generate_hook_and_recommend, generate_threads_post
from mailer import send_draft_kakao


def pick_keyword() -> str:
    keywords = [k.strip() for k in os.environ.get("SEARCH_KEYWORDS", "").split(",") if k.strip()]
    if not keywords:
        raise ValueError(".env의 SEARCH_KEYWORDS를 최소 1개 이상 설정해주세요.")
    return random.choice(keywords)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="API 호출 없이 샘플 초안 저장")
    parser.add_argument("--check", action="store_true", help="설정 유무만 확인")
    parser.add_argument("--no-send", action="store_true", help="공개 게시·카카오 전송 없이 초안 저장")
    args = parser.parse_args()
    threads_enabled = os.environ.get('THREADS_ENABLED', '').lower() == 'true' and not args.no_send
    required = ["COUPANG_ACCESS_KEY", "COUPANG_SECRET_KEY", "GEMINI_API_KEY", "SEARCH_KEYWORDS"]
    if not args.no_send:
        required += ["KAKAO_REST_API_KEY", "KAKAO_REFRESH_TOKEN"]
    if threads_enabled:
        required += ['THREADS_ACCESS_TOKEN', 'THREADS_USER_ID', 'THREADS_TOKEN_EXPIRES_AT']
    if args.demo:
        from content_generator import DISCLOSURE_TEXT
        draft = {"demo": True, "productName": "샘플 수납용품 (실제 상품 아님)",
                 "body": DISCLOSURE_TEXT + "\n\n[테스트] 수납용품을 고를 때는 크기와 설치 공간을 먼저 확인해보세요.",
                 "comment": "테스트 데이터입니다. 제휴 링크가 아닙니다."}
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
        print("데모 검증 완료: artifacts/draft.json (외부 API 호출 및 전송 없음)")
        return
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        raise SystemExit("필수 설정 누락: " + ", ".join(missing))
    if args.check:
        print("필수 설정 확인 완료 (API 연결 검증은 별도)")
        return
    if threads_enabled and os.environ.get('AUTOMATION_RUN_KEY'):
        from threads_api import published_for_run
        if published_for_run(os.environ['THREADS_USER_ID'], os.environ['AUTOMATION_RUN_KEY']):
            print('이 예약 시간의 Threads 게시가 이미 완료돼 중복 실행을 건너뜁니다.')
            return
    print("1) 상품 검색 중...")
    keyword = pick_keyword()
    client = CoupangPartnersClient()
    products = client.search_products(keyword, limit=10)

    if not products:
        print(f"'{keyword}' 검색 결과가 없습니다.")
        return

    product = random.choice(products)
    product_name = product.get("productName", "")
    price = f"{product.get('productPrice', ''):,}원" if product.get("productPrice") else ""

    product_id = product.get("productId")
    tracked_params = parse_qs(urlparse(product.get("productUrl", "")).query)
    item_id = tracked_params.get("itemId", [None])[0]
    vendor_item_id = tracked_params.get("vendorItemId", [None])[0]

    plain_url = f"https://www.coupang.com/vp/products/{product_id}"
    params = []
    if item_id:
        params.append(f"itemId={item_id}")
    if vendor_item_id:
        params.append(f"vendorItemId={vendor_item_id}")
    if params:
        plain_url += "?" + "&".join(params)

    print(f"   -> 선택된 상품: {product_name}")

    print("2) 딥링크 생성 중...")
    links = client.create_deeplinks([plain_url], sub_id="threads_auto")
    if not links or not links[0].get("shortenUrl"):
        raise RuntimeError("제휴 링크 생성 실패: 일반 상품 링크로 대체하지 않습니다.")
    deeplink = links[0]["shortenUrl"]

    print("3) Gemini로 글 생성 중...")
    daily_post = generate_daily_post(keyword, deeplink)
    hook_post = generate_hook_and_recommend(
        product_name=product_name,
        product_features="(상품 검색 결과 기반)",
        price=price,
        deeplink=deeplink,
    )

    Path("artifacts").mkdir(exist_ok=True)
    draft = {
        "demo": False, "productName": product_name, "deeplink": deeplink,
        "dailyPost": daily_post, "hookPost": hook_post,
    }
    draft_path = Path('artifacts/draft.json')
    if threads_enabled:
        draft['threadsPost'] = generate_threads_post(product_name, deeplink)
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding='utf-8')
    threads_result = None
    if threads_enabled:
        from threads_api import publish_text, ThreadsError
        print('4) Threads 게시 중...')
        try:
            threads_result = publish_text(draft['threadsPost'], os.environ.get('AUTOMATION_RUN_KEY'))
        except ThreadsError:
            send_draft_kakao('Threads 자동발행에 실패했습니다. 초안은 저장됐습니다. 게시 여부를 확인해주세요.',
                             hook_post, product_name, deeplink)
            raise
        draft['threadsPublication'] = threads_result
        draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding='utf-8')
    if not args.no_send:
        print("4) 카카오톡 발송 중...")
        if threads_result:
            send_draft_kakao('Threads 발행 완료\n' + threads_result.get('permalink', ''),
                             draft['threadsPost'], product_name, deeplink)
        else:
            send_draft_kakao(daily_post, hook_post, product_name, deeplink)
    print("초안 생성 완료: artifacts/draft.json")


if __name__ == "__main__":
    run()
