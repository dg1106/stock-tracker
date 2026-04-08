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
SEOULOTC_URL = "https://www.seoulotc.com/stock/475040"
CHART_PERIODS = ["1m", "3m", "1y", "3y", "all"]

SOURCE_LABELS = {
    "ustockplus": "증권플러스",
    "seoulotc":   "서울거래소",
}

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


def _fetch_queries(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=5, verify=False)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag:
        raise ValueError("__NEXT_DATA__ not found")
    data = json.loads(tag.string)
    queries = data["props"]["pageProps"]["dehydratedState"]["queries"]
    return {tuple(q["queryKey"]): q["state"].get("data") for q in queries}


def _get_ustockplus() -> dict:
    try:
        qmap = _fetch_queries(STOCK_URL)

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

        # 6b. IPO 일정
        ipo_schedules_raw = (ipo.get("ipoSchedule") or {}).get("ipoSchedules", [])
        ipo_schedules = [
            {
                "state": e.get("ipoState", ""),
                "label": IPO_STATUS_MAP.get(e.get("ipoState", ""), e.get("ipoState", "")),
                "date": e.get("startBaseDate"),
            }
            for e in ipo_schedules_raw
        ]
        ipo_current_state = (ipo.get("ipoSchedule") or {}).get("ipoState", "")

        # 6c. IPO 재무 지표
        ipo_fin = (ipo.get("estimatedMarketCapAndIpoInformation") or {})
        ipo_shares    = ipo_fin.get("numberOfIpoShares")
        listed_shares = ipo_fin.get("numberOfListedStockShare")
        total_sales   = ipo_fin.get("totalSales")
        net_profit    = ipo_fin.get("netProfit")

        # 6d. 3개월 비교 / 거래 현황
        tip = (ipo.get("tradeInProgress") or {})
        three_month_ago_price = tip.get("threeMonthAgoCurrentPrice")
        monthly_avg_volume    = tip.get("monthlyAverageDailyTradingVolume")
        sell_stock_count      = tip.get("sellStockCount")

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
            "ipo_schedules": ipo_schedules,
            "ipo_current_state": ipo_current_state,
            "ipo_shares": ipo_shares,
            "listed_shares": listed_shares,
            "total_sales": total_sales,
            "net_profit": net_profit,
            "three_month_ago_price": three_month_ago_price,
            "monthly_avg_volume": monthly_avg_volume,
            "sell_stock_count": sell_stock_count,
            "charts": charts,
            "updated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "updated_at": datetime.now().isoformat(),
        }


def _get_seoulotc() -> dict | None:
    """서울거래소 비상장에서 매수/매도 주문 수 수집. 실패 시 None 반환."""
    try:
        qmap = _fetch_queries(SEOULOTC_URL)
        # TODO: 사이트 구조 확인 후 실제 키 이름으로 교체
        # 현재는 ustockplus와 동일한 키 이름 시도
        stats = qmap.get(("stockDetailStatistics", "475040")) or {}
        order_buy_today = stats.get("orderBuyToday")
        order_sell_today = stats.get("orderSellToday")
        if order_buy_today is None and order_sell_today is None:
            return None
        return {
            "order_buy_today":  order_buy_today or 0,
            "order_sell_today": order_sell_today or 0,
        }
    except Exception:
        return None


def get_price() -> dict:
    primary = _get_ustockplus()
    if not primary["success"]:
        return primary

    sources = {
        "ustockplus": {
            "buy":   primary["order_buy_today"],
            "sell":  primary["order_sell_today"],
            "label": SOURCE_LABELS["ustockplus"],
        }
    }

    for name, fn in [("seoulotc", _get_seoulotc)]:
        result = fn()
        if result:
            sources[name] = {
                "buy":   result["order_buy_today"],
                "sell":  result["order_sell_today"],
                "label": SOURCE_LABELS.get(name, name),
            }

    total_buy  = sum(s["buy"]  for s in sources.values())
    total_sell = sum(s["sell"] for s in sources.values())

    return {
        **primary,
        "order_buy_today":  total_buy,
        "order_sell_today": total_sell,
        "order_sources":    sources,
    }


if __name__ == "__main__":
    result = get_price()
    if result.get("charts"):
        for p in result["charts"]:
            result["charts"][p] = f"[{len(result['charts'][p])} points]"
    print(json.dumps(result, ensure_ascii=False, indent=2))
