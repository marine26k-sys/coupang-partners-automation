"""
전체 파이프라인 실행 스크립트
"""

import os
import random
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

from coupang_api import CoupangPartnersClient
from content_generator import generate_daily_post, generate_hook_and_recommend
from mailer import send_draft_kakao


def pick_keyword() -> str:
    keywords = [k.strip() for k in os.environ.get("SEARCH_KEYWORDS", "").split(",") if k.strip()]
    if not keywords:
        raise ValueError(".env의 SEARCH_KEYWORDS를 최소 1개 이상 설정해주세요.")
    return random.choice(keywords)


def run():
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
    deeplink = links[0]["shortenUrl"] if links else product.get("productUrl", plain_url)

    print("3) Gemini로 글 생성 중...")
    daily_post = generate_daily_post(keyword, deeplink)
    hook_post = generate_hook_and_recommend(
        product_name=product_name,
        product_features="(상품 검색 결과 기반)",
        price=price,
        deeplink=deeplink,
    )

    print("4) 카카오톡 발송 중...")
    send_draft_kakao(daily_post, hook_post, product_name, deeplink)
    print("완료! 카카오톡 '나에게 보내기'를 확인해주세요.")


if __name__ == "__main__":
    run()
