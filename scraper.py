import json
import warnings
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 기업 네트워크 SSL 인터셉트 프록시 환경에서 경고 억제
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

STOCK_URL = "https://www.ustockplus.com/stock/stradvision-475040"


def _fetch_queries() -> dict:
    """ustockplus 페이지의 __NEXT_DATA__ 쿼리 맵을 반환한다."""
    resp = requests.get(STOCK_URL, headers=HEADERS, timeout=15, verify=False)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag:
        raise ValueError("__NEXT_DATA__ not found")
    data = json.loads(tag.string)
    queries = data["props"]["pageProps"]["dehydratedState"]["queries"]
    # queryKey(tuple) → data 맵
    return {tuple(q["queryKey"]): q["state"].get("data") for q in queries}


def get_price() -> dict:
    """스트라드비젼(475040) 가격 정보를 반환한다."""
    try:
        qmap = _fetch_queries()

        # 1. 현재가 / 전일대비 정보
        stock = (qmap.get(("stockDetail", "475040")) or {}).get("stock", {})
        current_price = stock.get("currentPrice")
        prev_price = stock.get("prevClosingPrice")
        change_price = stock.get("changePrice")
        change_rate = stock.get("changeRate")

        # currentChangePrice가 0이 아니면 장중 변동가 우선 사용
        if stock.get("currentChangePrice"):
            change_price = stock["currentChangePrice"]
        if stock.get("currentChangeRate"):
            change_rate = stock["currentChangeRate"]

        # 2. 매수/매도 호가 (priceVolumeChart)
        chart = qmap.get(("priceVolumeChart", "475040")) or {}
        sell_orders = chart.get("sell", [])  # 매도 주문 목록
        buy_orders = chart.get("buy", [])    # 매수 주문 목록

        # 매도 최저가 (ask) / 매수 최고가 (bid)
        ask_price = min((o["price"] for o in sell_orders if o.get("price")), default=None)
        bid_price = max((o["price"] for o in buy_orders if o.get("price")), default=None)

        return {
            "success": True,
            "current_price": current_price,
            "prev_price": prev_price,
            "change_price": change_price,
            "change_rate": change_rate,
            "ask_price": ask_price,   # 매도 최저가
            "bid_price": bid_price,   # 매수 최고가
            "updated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "updated_at": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    result = get_price()
    print(json.dumps(result, ensure_ascii=False, indent=2))
