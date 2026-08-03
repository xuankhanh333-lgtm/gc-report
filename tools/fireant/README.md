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

API FireAnt xác thực bằng `Authorization: Bearer <JWT>`. **Không hard-code** —
đặt qua biến môi trường:

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

- Các route giá lịch sử / cơ bản / tin tức là những path ổn định, dùng rộng rãi.
- Route **tự doanh** ít tài liệu công khai hơn nên được gom trong biến
  `ENDPOINTS` ở đầu `fireant_client.py`. Nếu gọi trả **404**, chỉ cần sửa một
  dòng `ENDPOINTS["proprietary_trading"]` cho khớp API thật.
- Xác minh endpoint cần chạy ở môi trường có mạng tới `restv2.fireant.vn` với
  token thật (sandbox tạo báo cáo này bị chặn host đó qua network policy, nên
  không dò trực tiếp được từ đây).

## Xử lý lỗi

- `401/403`: token sai/hết hạn hoặc thiếu quyền → làm mới token.
- `404`: sai path → chỉnh `ENDPOINTS`.
- `429`/`5xx`: tự retry với backoff luỹ thừa (tối đa 4 lần).
