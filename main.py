import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from scraper import get_price

# 인메모리 캐시
_cache: dict = {"data": None}


async def _refresh_loop():
    """60초마다 가격을 갱신한다."""
    while True:
        try:
            data = await asyncio.get_event_loop().run_in_executor(None, get_price)
            _cache["data"] = data
        except Exception as e:
            print(f"[refresh] error: {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 즉시 첫 데이터 수집 후 백그라운드 루프 시작
    try:
        _cache["data"] = await asyncio.get_event_loop().run_in_executor(None, get_price)
    except Exception as e:
        print(f"[startup] initial fetch error: {e}")
    task = asyncio.create_task(_refresh_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/price")
@app.head("/api/price")
async def api_price():
    if _cache["data"] is None:
        return JSONResponse({"success": False, "error": "데이터 로딩 중입니다. 잠시 후 새로고침 해주세요."}, status_code=503)
    return JSONResponse(_cache["data"])


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


# static 파일 서빙 (CSS, JS 등 추가될 경우 대비)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
