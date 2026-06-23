# Tasks: Tracking Image Import

## Task 1 — Cập nhật OCR prompt và parse result

**File:** `bot/services/ocr.py`

- [ ] Thay `EXTRACT_PROMPT` bằng prompt mới detect 2 loại ảnh (tracking vs order)
- [ ] Thêm carrier mapping trong prompt
- [ ] Cập nhật `extract_order_from_image` để trả về `image_type`, `tracking_number`, `carrier` trong dict kết quả
- [ ] Giữ validate: `total_cny` vẫn bắt buộc

## Task 2 — Cập nhật DB insert để nhận tracking

**File:** `bot/services/db.py`

- [ ] Thêm param `tracking_number: str | None = None` và `carrier: str | None = None` vào `insert_order`
- [ ] Truyền 2 param này vào câu INSERT SQL

## Task 3 — Cập nhật photo handler

**File:** `bot/handlers/photo.py`

- [ ] Trong `handle_confirm_order`: truyền `tracking_number` và `carrier` vào `insert_order`
- [ ] Inbox message: nếu có tracking → hiển thị `🚚 {carrier}: {tracking_number}`, không có nút nhập tracking
- [ ] Inbox message: nếu không có tracking → giữ nguyên như cũ (nút "✏️ Nhập tracking")
- [ ] Tương tự cho `manual_date` (manual entry vẫn không có tracking, không thay đổi)

## Task 4 — Test thủ công

- [ ] Gửi ảnh tracking page lên bot → kiểm tra bot extract đúng tracking number + carrier
- [ ] Gửi ảnh đơn hàng Tmall → kiểm tra flow cũ vẫn hoạt động (không có tracking)
- [ ] Kiểm tra DB: đơn từ tracking image có `tracking_number` và `carrier` được lưu đúng
