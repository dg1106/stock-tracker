import json
import warnings
import requests
from bs4 import BeautifulSoup
from datetime import datetime

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

IPO_STATUS_MAP = {
    "IPO_ORGANIZER_SELECTION": "주관사선정",
    "TECHNOLOGY_EVALUATIONS_PASS": "기술평가통과",
    "EXAMINATION_REQUESTED": "심사신청",
    "EXAMINATION_IN_PROGRESS": "심사중",
    "EXAMINATION_ACCEPTED": "심사승인",
    "SUBMIT_REPORT": "증권신고서제출",
    "DEMAND_FORECAST": "수요예측",
    "OFFER_SUBSCRIPTION": "청약",
    "TO_BE_LISTED": "상장예정",
    "ALLOTMENT_DATE": "배정일",
    "REFUND_DATE": "환불일",
    "LISTED": "상장완료",
    "WITHDRAWAL": "철회",
}


def _fetch_queries() -> dict:
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
    try:
        qmap = _fetch_queries()

        # 1. 현재가 / 전일대비
        stock = (qmap.get(("stockDetail", "475040")) or {}).get("stock", {})
        current_price = stock.get("currentPrice")
        prev_price = stock.get("prevClosingPrice")
        change_price = stock.get("changePrice")
        change_rate = stock.get("changeRate")
        if stock.get("currentChangePrice"):
            change_price = stock["currentChangePrice"]
        if stock.get("currentChangeRate"):
            change_rate = stock["currentChangeRate"]

        # 2. 매수/매도 호가
        ov = qmap.get(("priceVolumeChart", "475040")) or {}
        sell_orders = ov.get("sell", [])
        buy_orders = ov.get("buy", [])
        ask_price = min((o["price"] for o in sell_orders if o.get("price")), default=None)
        bid_price = max((o["price"] for o in buy_orders if o.get("price")), default=None)

        # 3. 오늘 현황 + 52주 + 시가총액
        vs = qmap.get(("valueSummary", "475040")) or {}
        today_info = vs.get("todayMarketPriceInformation") or {}
        today_high = today_info.get("todayHighestPrice")
        today_low = today_info.get("todayLowestPrice")
        today_volume = today_info.get("todayTradingVolume")
        high_52w = today_info.get("highestPrice52Week")
        low_52w = today_info.get("lowestPrice52Week")
        market_cap = vs.get("marketCap")

        # 4. 오늘 주문/체결 통계
        stats = qmap.get(("stockDetailStatistics", "475040")) or {}
        order_buy_today = stats.get("orderBuyToday", 0)
        order_sell_today = stats.get("orderSellToday", 0)
        trade_count_today = stats.get("countTradeToday", 0)

        # 5. 최근 체결 내역 (최근 5건)
        histories = (qmap.get(("tradeCompleteHistories", "475040")) or {}).get("tradeCompleteHistories", [])
        recent_trades = []
        for h in histories[:5]:
            traded_at = h.get("tradedAt", "")
            try:
                dt = datetime.fromisoformat(traded_at)
                time_str = dt.strftime("%m/%d %H:%M")
            except Exception:
                time_str = traded_at[:16]
            recent_trades.append({
                "time": time_str,
                "price": h.get("price"),
                "quantity": h.get("quantity"),
            })

        # 6. IPO 상태
        ipo = qmap.get(("stockIpoDetail", "475040")) or {}
        ipo_detail_state = (ipo.get("progress") or {}).get("ipoDetailState")
        ipo_status = IPO_STATUS_MAP.get(ipo_detail_state, "해당없음")

        # 7. 기간별 차트
        charts = {}
        for period in CHART_PERIODS:
            raw = qmap.get(("dailyBasePriceLineChart", "475040", period)) or {}
            charts[period] = [
                {"date": p["date"], "price": p["price"]}
                for p in raw.get("data", [])
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
            "today_high": today_high,
            "today_low": today_low,
            "today_volume": today_volume,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "market_cap": market_cap,
            "order_buy_today": order_buy_today,
            "order_sell_today": order_sell_today,
            "trade_count_today": trade_count_today,
            "recent_trades": recent_trades,
            "ipo_status": ipo_status,
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
    if result.get("charts"):
        for p in result["charts"]:
            result["charts"][p] = f"[{len(result['charts'][p])} points]"
    print(json.dumps(result, ensure_ascii=False, indent=2))
