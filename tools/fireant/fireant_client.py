"""FireAnt.vn REST client — trọng tâm dữ liệu TỰ DOANH (proprietary trading).

FireAnt web app gọi API qua host ``https://restv2.fireant.vn`` với xác thực
``Authorization: Bearer <JWT>``. Client này bọc các endpoint hay dùng và thêm
retry/timeout/paging. Token KHÔNG hard-code — đọc từ biến môi trường
``FIREANT_TOKEN`` (hoặc truyền qua tham số ``token``).

Cách lấy token: đăng nhập fireant.vn → DevTools → Network → xem header
``Authorization: Bearer ...`` của một request tới restv2.fireant.vn, hoặc lấy
từ localStorage. Token là JWT, hết hạn theo phiên nên cần làm mới định kỳ.

Lưu ý endpoint: các path dữ liệu giá/nước ngoài/tin tức bên dưới là những
route ổn định, đã dùng rộng rãi. Route TỰ DOANH của FireAnt ít được公开 tài
liệu hơn nên được đặt trong ``ENDPOINTS`` để chỉnh một chỗ khi xác minh bằng
token thật (môi trường sandbox không truy cập được restv2.fireant.vn để dò).
"""

from __future__ import annotations

import os
import time
import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Iterable

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Thiếu thư viện 'requests'. Cài: pip install -r requirements.txt"
    ) from exc


log = logging.getLogger("fireant")

BASE_URL = "https://restv2.fireant.vn"

# Tập trung path ở một chỗ để dễ chỉnh khi xác minh với token thật.
# {symbol} sẽ được format bằng mã cổ phiếu (VNM, HPG, ...).
ENDPOINTS = {
    # Giá lịch sử — bản ghi đã kèm khối lượng/giá trị MUA-BÁN của khối NGOẠI.
    "historical_quotes": "/symbols/{symbol}/historical-quotes",
    # Tự doanh theo mã. Nếu route khác, chỉ cần sửa dòng này.
    "proprietary_trading": "/symbols/{symbol}/proprietary-trading",
    # Tự doanh toàn thị trường (net theo phiên), nếu FireAnt cung cấp.
    "proprietary_trading_market": "/markets/proprietary-trading",
    # Hồ sơ & cơ bản (dùng để enrich báo cáo).
    "fundamental": "/symbols/{symbol}/fundamental",
    "profile": "/symbols/{symbol}/profile",
    # Tin tức / bài viết theo mã.
    "posts": "/posts",
}


class FireAntError(RuntimeError):
    """Lỗi khi gọi FireAnt API."""

    def __init__(self, message: str, status: Optional[int] = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def _iso(d: Any) -> str:
    """Chuẩn hoá ngày về chuỗi YYYY-MM-DD."""
    if isinstance(d, (date, datetime)):
        return d.strftime("%Y-%m-%d")
    return str(d)


class FireAntClient:
    """Client tối giản, có retry, cho FireAnt REST API."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = BASE_URL,
        timeout: float = 20.0,
        max_retries: int = 4,
        session: Optional["requests.Session"] = None,
    ):
        self.token = token or os.environ.get("FIREANT_TOKEN", "").strip()
        if not self.token:
            raise FireAntError(
                "Chưa có token. Đặt biến môi trường FIREANT_TOKEN hoặc truyền token=..."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                # FireAnt kiểm tra Origin/Referer với một số route.
                "Origin": "https://fireant.vn",
                "Referer": "https://fireant.vn/",
                "User-Agent": "gc-report-fireant-connector/1.0",
            }
        )

    # ------------------------------------------------------------------ core
    def request(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Gọi GET tới ``path`` (tương đối so với base_url) và trả JSON.

        Có retry với backoff luỹ thừa cho lỗi mạng và HTTP 429/5xx.
        """
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt > self.max_retries:
                    raise FireAntError(f"Lỗi mạng khi gọi {url}: {exc}") from exc
                self._backoff(attempt, reason=str(exc))
                continue

            if resp.status_code == 200:
                if not resp.content:
                    return None
                try:
                    return resp.json()
                except ValueError as exc:
                    raise FireAntError(
                        f"Phản hồi không phải JSON từ {url}", resp.status_code,
                        resp.text[:500],
                    ) from exc

            if resp.status_code in (401, 403):
                raise FireAntError(
                    f"Bị từ chối ({resp.status_code}). Token sai/hết hạn hoặc "
                    f"không đủ quyền cho {url}.",
                    resp.status_code,
                    resp.text[:500],
                )

            if resp.status_code == 404:
                raise FireAntError(
                    f"Không tìm thấy endpoint (404): {url}. "
                    f"Kiểm tra lại path trong ENDPOINTS.",
                    404,
                    resp.text[:300],
                )

            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt > self.max_retries:
                    raise FireAntError(
                        f"Quá số lần thử ({resp.status_code}) cho {url}.",
                        resp.status_code,
                        resp.text[:300],
                    )
                self._backoff(attempt, reason=f"HTTP {resp.status_code}")
                continue

            raise FireAntError(
                f"HTTP {resp.status_code} cho {url}",
                resp.status_code,
                resp.text[:500],
            )

    def _backoff(self, attempt: int, reason: str = "") -> None:
        wait = min(2 ** attempt, 30)
        log.warning("Thử lại lần %d sau %ss (%s)", attempt, wait, reason)
        time.sleep(wait)

    # -------------------------------------------------------------- endpoints
    def historical_quotes(
        self,
        symbol: str,
        start: Any,
        end: Any,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Giá lịch sử theo mã, có phân trang gộp sẵn.

        Mỗi bản ghi thường kèm dữ liệu khối ngoại:
        ``buyForeignQuantity/Value``, ``sellForeignQuantity/Value`` — dùng để
        tính ròng nước ngoài. Đây cũng là nguồn để đối chiếu với tự doanh.
        """
        symbol = symbol.upper()
        path = ENDPOINTS["historical_quotes"].format(symbol=symbol)
        out: List[Dict[str, Any]] = []
        offset = 0
        page = min(limit, 500)
        while True:
            batch = self.request(
                path,
                params={
                    "startDate": _iso(start),
                    "endDate": _iso(end),
                    "offset": offset,
                    "limit": page,
                },
            )
            if not batch:
                break
            out.extend(batch)
            if len(batch) < page:
                break
            offset += page
            if len(out) >= limit:
                break
        return out[:limit] if limit else out

    def proprietary_trading(
        self,
        symbol: str,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
    ) -> Any:
        """Dữ liệu TỰ DOANH theo mã.

        Trả nguyên payload FireAnt. Nếu route trả 404, sửa
        ``ENDPOINTS['proprietary_trading']`` cho khớp API thật (xác minh bằng
        token trong môi trường có mạng tới restv2.fireant.vn).
        """
        symbol = symbol.upper()
        path = ENDPOINTS["proprietary_trading"].format(symbol=symbol)
        params: Dict[str, Any] = {}
        if start:
            params["startDate"] = _iso(start)
        if end:
            params["endDate"] = _iso(end)
        return self.request(path, params=params or None)

    def proprietary_trading_market(
        self, start: Optional[Any] = None, end: Optional[Any] = None
    ) -> Any:
        """Tự doanh ròng toàn thị trường (nếu FireAnt cung cấp route này)."""
        path = ENDPOINTS["proprietary_trading_market"]
        params: Dict[str, Any] = {}
        if start:
            params["startDate"] = _iso(start)
        if end:
            params["endDate"] = _iso(end)
        return self.request(path, params=params or None)

    def fundamental(self, symbol: str) -> Any:
        path = ENDPOINTS["fundamental"].format(symbol=symbol.upper())
        return self.request(path)

    def profile(self, symbol: str) -> Any:
        path = ENDPOINTS["profile"].format(symbol=symbol.upper())
        return self.request(path)

    def posts(self, symbol: str, limit: int = 20, offset: int = 0) -> Any:
        """Tin tức/bài viết theo mã (nguồn giống mục news trong vnpool.html)."""
        return self.request(
            ENDPOINTS["posts"],
            params={"symbol": symbol.upper(), "offset": offset, "limit": limit},
        )

    # ---------------------------------------------------------------- helpers
    def foreign_net_series(
        self, symbol: str, start: Any, end: Any
    ) -> List[Dict[str, Any]]:
        """Rút gọn giá lịch sử thành chuỗi ròng KHỐI NGOẠI theo ngày.

        Hữu ích để đặt cạnh dữ liệu tự doanh khi so dòng tiền.
        """
        rows = self.historical_quotes(symbol, start, end)
        series = []
        for r in rows:
            bq = r.get("buyForeignQuantity") or 0
            sq = r.get("sellForeignQuantity") or 0
            bv = r.get("buyForeignValue") or 0
            sv = r.get("sellForeignValue") or 0
            series.append(
                {
                    "date": (r.get("date") or "")[:10],
                    "close": r.get("priceClose"),
                    "foreignNetVolume": bq - sq,
                    "foreignNetValue": bv - sv,
                }
            )
        series.sort(key=lambda x: x["date"])
        return series


def default_range(days: int = 30) -> tuple[str, str]:
    """Khoảng ngày mặc định [hôm nay - days, hôm nay]."""
    today = (datetime.utcnow() + timedelta(hours=7)).date()  # giờ VN (GMT+7)
    start = today - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


if __name__ == "__main__":
    # Smoke test nhỏ: cần FIREANT_TOKEN và mạng tới restv2.fireant.vn.
    logging.basicConfig(level=logging.INFO)
    sym = os.environ.get("SYMBOL", "VNM")
    s, e = default_range(15)
    client = FireAntClient()
    try:
        data = client.proprietary_trading(sym, s, e)
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    except FireAntError as err:
        log.error("Tự doanh lỗi: %s", err)
