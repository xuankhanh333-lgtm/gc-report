#!/usr/bin/env python3
"""Dò các endpoint FireAnt để tìm đúng route dữ liệu TỰ DOANH.

Chạy trên môi trường có mạng tới restv2.fireant.vn (vd GitHub Actions) với
FIREANT_TOKEN. In ra:
  1) Toàn bộ KEY của một bản ghi historical-quotes (biết đâu tự doanh nằm sẵn ở đây).
  2) HTTP status + đoạn body đầu của hàng loạt route ứng viên.

Không sửa gì trên repo — chỉ in log để quyết định ENDPOINTS.
"""

from __future__ import annotations

import os
import json
import requests

BASE = "https://restv2.fireant.vn"
SYM = os.environ.get("PROBE_SYMBOL", "VNM")
TOKEN = os.environ.get("FIREANT_TOKEN", "").strip()

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Origin": "https://fireant.vn",
    "Referer": "https://fireant.vn/",
    "User-Agent": "gc-report-probe/1.0",
}


def hit(path: str, params=None) -> None:
    url = f"{BASE}{path}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"  ERR  {path}  -> {exc}")
        return
    body = r.text or ""
    snippet = body[:180].replace("\n", " ")
    print(f"  {r.status_code}  {path}  -> {snippet}")


def main() -> None:
    if not TOKEN:
        raise SystemExit("Thiếu FIREANT_TOKEN")

    print(f"== 1) historical-quotes[{SYM}] — xem có field tự doanh sẵn không ==")
    try:
        r = requests.get(
            f"{BASE}/symbols/{SYM}/historical-quotes",
            headers=HEADERS,
            params={"startDate": "2026-07-01", "endDate": "2026-08-01",
                    "offset": 0, "limit": 1},
            timeout=20,
        )
        print("  status:", r.status_code)
        data = r.json() if r.status_code == 200 else None
        if data:
            rec = data[0] if isinstance(data, list) else data
            print("  KEYS:", sorted(rec.keys()))
            print("  RECORD:", json.dumps(rec, ensure_ascii=False)[:600])
    except Exception as exc:  # noqa: BLE001
        print("  ERR:", exc)

    print(f"\n== 2) Các route TỰ DOANH ứng viên (mã {SYM}) ==")
    per_symbol = [
        f"/symbols/{SYM}/proprietary-trades",
        f"/symbols/{SYM}/proprietary",
        f"/symbols/{SYM}/prop-trading",
        f"/symbols/{SYM}/prop-trades",
        f"/symbols/{SYM}/self-trading",
        f"/symbols/{SYM}/proprietary-quotes",
        f"/symbols/{SYM}/proprietary-trading-quotes",
        f"/symbols/{SYM}/trading-proprietary",
        f"/symbols/{SYM}/proptrade",
        f"/symbols/{SYM}/dealer",
        f"/symbols/{SYM}/net-trading",
    ]
    for p in per_symbol:
        hit(p, params={"startDate": "2026-07-01", "endDate": "2026-08-01"})

    print(f"\n== 3) Route tự doanh cấp THỊ TRƯỜNG ==")
    market = [
        "/markets/proprietary",
        "/markets/proprietary-trading",
        "/markets/proprietary-trades",
        "/markets/HOSE/proprietary",
        "/proprietary-trading",
        "/proprietary",
    ]
    for p in market:
        hit(p)

    print(f"\n== 4) Vài route dữ liệu khác để tham chiếu ==")
    for p in [f"/symbols/{SYM}/fundamental", f"/symbols/{SYM}/profile"]:
        hit(p)


if __name__ == "__main__":
    main()
