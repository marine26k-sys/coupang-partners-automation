"""
10개 상품 후보를 한 번에 생성해 docs/data.json으로 저장한다.
GitHub Pages가 이 파일을 읽어 웹 대시보드에 카드로 보여준다.
"""

import os
import json
import random
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

from coupang_api import CoupangPartnersClient
from content_generator import generate_dashboard_post, build_comment

BATCH_SIZE = 10
KST = timezone(timedelta(hours=9))


def pick_keyword() -> str:
    keywords = [k.strip() for k in os.environ.get("SEARCH_KEYWORDS", "").split(",") if k.strip()]
    if not keywords:
        raise ValueError(".env의 SEARCH_KEYWORDS를 최소 1개 이상 설정해주세요.")
    return random.choice(keywords)


def build_plain_url(product: dict) -> str:
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
    return plain_url


def run():
    client = CoupangPartnersClient()
    keyword = pick_keyword()
    print(f"1) '{keyword}' 상품 검색 중...")
    products = client.search_products(keyword, limit=BATCH_SIZE)
    products = products[:BATCH_SIZE]

    if not products:
        print(f"'{keyword}' 검색 결과가 없습니다.")
        return

    print("2) 딥링크 일괄 생성 중...")
    plain_urls = [build_plain_url(p) for p in products]
    links = client.create_deeplinks(plain_urls, sub_id="dashboard_auto")
    deeplink_map = {link["originalUrl"]: link["shortenUrl"] for link in links}

    items = []
    for product, plain_url in zip(products, plain_urls):
        deeplink = deeplink_map.get(plain_url, product.get("productUrl", plain_url))
        product_name = product.get("productName", "")
        price = product.get("productPrice", "")
        price_text = f"{price:,}원" if price else ""

        print(f"   -> 글 생성: {product_name}")
        body = generate_dashboard_post(product_name, "(상품 검색 결과 기반)", price_text)
        comment = build_comment(deeplink)

        items.append({
            "productName": product_name,
            "price": price,
            "priceText": price_text,
            "image": product.get("productImage", ""),
            "deeplink": deeplink,
            "body": body,
            "comment": comment,
            "status": "대기",
        })

    now_kst = datetime.now(KST)
    data = {
        "generatedAt": now_kst.strftime("%Y-%m-%d %H:%M"),
        "keyword": keyword,
        "items": items,
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"완료! docs/data.json에 {len(items)}개 저장됨.")


if __name__ == "__main__":
    run()
