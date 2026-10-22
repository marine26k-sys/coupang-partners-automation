"""Publish one non-affiliate household selection tip per day."""
from datetime import datetime
from zoneinfo import ZoneInfo
import os

from dotenv import load_dotenv

load_dotenv('.env')

from threads_api import publish_text


POSTS = (
    "정리함은 물건보다 놓을 자리를 먼저 봐\n\n선반의 가로와 깊이를 재고\n손을 넣어 꺼낼 여유가 있는지 확인해\n\n수납용품이 예뻐도 꺼내기 불편하면 손이 안 가",
    "주방용품은 개수보다 쓰는 장면을 먼저 떠올려\n\n매일 쓰는지 가끔 쓰는지 나누고\n손이 자주 가는 물건은 앞쪽에 둘 수 있는지 봐\n\n보관할 자리까지 정해져야 구매가 끝나",
    "생활용품을 고를 때 설명보다 먼저 볼 것\n\n내가 해결하려는 불편이 한 문장으로 말해지는지\n기존 물건과 역할이 겹치지 않는지\n\n이 두 가지가 흐리면 장바구니에서 잠깐 멈춰도 돼",
    "수납용품 크기는 외부 치수만 보면 놓치기 쉬워\n\n실제로 담을 물건 중 가장 큰 포장을 기준으로\n내부 치수와 꺼내는 방향을 함께 봐\n\n들어가는 것과 쓰기 좋은 것은 다른 문제야",
    "주방 소모품은 묶음 수량부터 계산해\n\n한 달에 얼마나 쓰는지\n남은 수량을 어디에 보관할지\n\n가격보다 먼저 정하면 필요 이상으로 쌓이지 않아",
    "세척이 필요한 생활용품은 모양보다 관리 방법을 봐\n\n분리 세척이 되는지\n물을 빼고 말릴 자리가 있는지\n\n깨끗하게 유지할 방법이 없으면 좋은 기능도 오래 못 써",
    "같은 생활용품도 집마다 맞는 조건이 달라\n\n놓을 공간과 사용하는 빈도\n보관할 수량을 먼저 정하고\n\n그다음 재질과 구성 차이를 비교하면 선택이 훨씬 쉬워져",
)


def main():
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    run_key = 'value-' + now.strftime('%Y-%m-%d')
    body = POSTS[now.toordinal() % len(POSTS)]
    result = publish_text(body, run_key=run_key, paired_root=True)
    print(result.get('permalink', ''))


if __name__ == '__main__':
    main()
