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
CHART_PERIODS = ["1m", "3m", "1y", "3y", "all"]


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
    return {tuple(q["queryKey"]): q["state"].get("data") for q in queries}


def get_price() -> dict:
    """스트라드비젼(475040) 가격 + 차트 정보를 반환한다."""
    try:
        qmap = _fetch_queries()

        # 1. 현재가 / 전일대비 정보
        stock = (qmap.get(("stockDetail", "475040")) or {}).get("stock", {})
        current_price = stock.get("currentPrice")
        prev_price = stock.get("prevClosingPrice")
        change_price = stock.get("changePrice")
        change_rate = stock.get("changeRate")

        if stock.get("currentChangePrice"):
            change_price = stock["currentChangePrice"]
        if stock.get("currentChangeRate"):
            change_rate = stock["currentChangeRate"]

        # 2. 매수/매도 호가 (priceVolumeChart)
        chart = qmap.get(("priceVolumeChart", "475040")) or {}
        sell_orders = chart.get("sell", [])
        buy_orders = chart.get("buy", [])

        ask_price = min((o["price"] for o in sell_orders if o.get("price")), default=None)
        bid_price = max((o["price"] for o in buy_orders if o.get("price")), default=None)

        # 3. 기간별 가격 추이 차트 데이터
        charts = {}
        for period in CHART_PERIODS:
            raw = qmap.get(("dailyBasePriceLineChart", "475040", period)) or {}
            points = raw.get("data", [])
            charts[period] = [
                {"date": p["date"], "price": p["price"]}
                for p in points
                if p.get("price") is not None
            ]

        return {
            "success": True,
            "current_price": current_price,
            "prev_price": prev_price,
            "change_price": change_price,
            "change_rate": change_rate,
            "ask_price": ask_price,
            "bid_price": bid_price,
            "charts": charts,
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
    # 차트 데이터는 길어서 요약 출력
    if result.get("charts"):
        for p, pts in result["charts"].items():
            result["charts"][p] = f"[{len(pts)} points]"
    print(json.dumps(result, ensure_ascii=False, indent=2))
