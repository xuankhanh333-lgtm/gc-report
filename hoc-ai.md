# Sổ AI thực chiến — khái niệm đã dạy trong chat

Mỗi dòng 1 khái niệm (mới nhất dưới cùng). Liếc trước khi dạy để không lặp.

| Ngày | Khái niệm | Tóm tắt 1 câu | Ngữ cảnh |
|---|---|---|---|
| 14/07/2026 | Calibrated probability | Model tốt không chỉ đoán đúng lớp mà xác suất phải "thật": pf 0.556 nghĩa là nhóm setup giống vậy thắng ~55.6% — nhờ đó nhân ra EV được | TAKE LONG pf 0.556 trước CPI → TP; ngưỡng TAKE≥0.40 của pooldir chính là cắt theo EV |
| 14/07/2026 | Pre-registration vs hindsight bias | Dự đoán phải GHI TRƯỚC khi có kết quả rồi mới chấm — nhìn lại sau khi biết đáp án thì cái gì cũng "thấy trước được", win-rate ảo | Checklist CPI→VN 4 ô đăng ký tối 14/07 chấm sáng 15/07; cùng luật với "test model mới phải đăng ký dự đoán trước" của vnpool D1 vs H4 |
| 14/07/2026 | AUC ngược (inverted classifier) | AUC < 0.5 không phải "không có tín hiệu" mà là tín hiệu NGƯỢC — model đảo dấu sẽ được AUC = 1−x; nhưng đừng vội đảo: phải tìm nguyên nhân (feature chết, leak, regime) trước | gc-llm RT AUC 0.29–0.35 (đảo ra 0.65–0.71) trong lúc DXY/US10Y đóng băng 99.88/4.483 hơn 1 tháng — nghi feature chết chứ chưa chắc edge ngược |
| 14/07/2026 | Undersampling (lấy mẫu thưa hơn tín hiệu) | Điều kiện biến đổi nhanh (M5) mà chỉ kiểm tra ở nhịp chậm (H4 close, 6 lần/ngày) thì sự kiện xảy ra giữa 2 lần lấy mẫu bị mất sạch — sửa bằng tăng tần suất check, không phải nới ngưỡng | gc-llm entry: 3/3 lần M5 score≥2 đều bị block "price_outside_zone_hard" vì tới H4 close giá đã rời zone; khi giá còn trong zone thì score=0-1 → 0 lệnh khớp từ 12/06 |
