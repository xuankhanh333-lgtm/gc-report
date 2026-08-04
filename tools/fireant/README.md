# FireAnt connector — dữ liệu Tự doanh

Kết nối FireAnt.vn REST API (`https://restv2.fireant.vn`) để kéo dữ liệu
**tự doanh** (proprietary trading của các CTCK), kèm tuỳ chọn đối chiếu với
ròng khối ngoại. Đầu ra là JSON để pipeline nhúng vào các dashboard
(`vnpool.html`…) giống object `D = {...}` sẵn có.

## Cài đặt

```bash
cd tools/fireant
pip install -r requirements.txt
```

## Token (bắt buộc)

API FireAnt xác thực bằng `Authorization: Bearer <JWT>`. **Không hard-code**.
Có 2 cách lưu token, chọn 1:

**Cách 1 — file `.env` (khuyến nghị, tiện lưu).** File `.env` đã được
`.gitignore` nên KHÔNG bao giờ bị commit/push:

```bash
cp .env.example .env
# mở .env, dán token vào dòng FIREANT_TOKEN=...
```

Connector tự động nạp `tools/fireant/.env` nếu chưa có biến môi trường.

**Cách 2 — biến môi trường:**

```bash
export FIREANT_TOKEN="eyJ...jwt..."
```

Lấy token: đăng nhập fireant.vn → mở DevTools → tab **Network** → chọn một
request tới `restv2.fireant.vn` → copy giá trị header `Authorization` (phần sau
`Bearer `). Token là JWT có hạn theo phiên, cần làm mới định kỳ.

## Dùng

```bash
# Ba mã, 30 ngày gần nhất, in ra stdout
python fetch_tudoanh.py --symbols VNM HPG SSI

# Đọc mã từ file, ghi ra JSON, kèm ròng khối ngoại để đối chiếu
python fetch_tudoanh.py --symbols-file watchlist.txt --days 45 \
    --with-foreign --out tudoanh.json
```

Dùng như thư viện:

```python
from fireant_client import FireAntClient
c = FireAntClient()                      # đọc FIREANT_TOKEN
print(c.proprietary_trading("VNM", "2026-07-01", "2026-08-01"))
print(c.foreign_net_series("VNM", "2026-07-01", "2026-08-01"))
raw = c.request("/symbols/VNM/fundamental")   # gọi endpoint bất kỳ
```

## Ghi chú endpoint

- **Tự doanh KHÔNG có endpoint riêng.** FireAnt nhúng sẵn số liệu tự doanh
  trong mỗi bản ghi `historical-quotes` (đã xác minh bằng token thật):
  - `propTradingNetValue` — tổng ròng tự doanh (VND)
  - `propTradingNetDealValue` — ròng tự doanh khớp lệnh
  - `propTradingNetPTValue` — ròng tự doanh thoả thuận

  `proprietary_trading()` đọc historical-quotes rồi trích các field này ra chuỗi
  theo ngày. Bản ghi cũng có sẵn dữ liệu khối ngoại (`buy/sellForeign*`).
- `probe_endpoints.py` + workflow **"FireAnt dò endpoint"** là công cụ chẩn đoán
  (in toàn bộ field FireAnt trả về) nếu sau này cần kiểm tra thêm.

## Xử lý lỗi

- `401/403`: token sai/hết hạn hoặc thiếu quyền → làm mới token.
- `404`: sai path → chỉnh `ENDPOINTS`.
- `429`/`5xx`: tự retry với backoff luỹ thừa (tối đa 4 lần).
