# 스트라드비젼 비상장주식 트래커

스트라드비젼(475040) 비상장 주식 가격을 1분 주기로 갱신하는 웹 대시보드입니다.

## 기능

- 현재가 / 전일대비 / 변동률
- 매도 최저가 / 매수 최고가
- 오늘 고가·저가·거래량·체결 수
- 52주 가격 범위 (현재가 위치 바)
- 시가총액 / IPO 상태
- 최근 체결 내역 5건
- 가격 추이 차트 (1개월 / 3개월 / 1년 / 3년 / 전체)

데이터 출처: [증권플러스 비상장](https://www.ustockplus.com/stock/stradvision-475040)

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

브라우저에서 `http://localhost:8000` 접속

## 배포 (Render.com)

1. GitHub 리포에 코드 푸시
2. [Render.com](https://render.com) → New Web Service → GitHub 연결
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Plan: Free

슬립 방지를 위해 [UptimeRobot](https://uptimerobot.com)에서 `/api/price` 엔드포인트를 5분 주기로 모니터링 등록 권장.
