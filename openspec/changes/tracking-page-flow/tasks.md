# Tasks: Tracking Page Flow

## Task 1 — Thêm `extract_tracking_from_image` vào `bot/services/ocr.py`

- [x] Thêm hàm `extract_tracking_from_image(image_path: str) -> dict | None`
- [x] Prompt extract: `tracking_number`, `carrier`, `product_name`, `quantity`, `unit_price_cny`, `total_cny`, `order_number`
- [x] `total_cny` và `order_number` không bắt buộc — trả về null nếu không thấy
- [x] Giữ nguyên hàm `extract_order_from_image` hiện tại (dùng cho flow `/order`)

## Task 2 — Tạo `bot/handlers/tracking_photo.py`

- [x] States: `AWAIT_MANUAL_TRACKING = 20`, `AWAIT_ORDER_NUMBER = 21`
- [x] `handle_tracking_photo`: entry point, phân nhánh media group vs ảnh đơn lẻ
- [x] `_buffer_media_group`: buffer ảnh cùng `media_group_id`, asyncio timer 1.5s
- [x] `_process_photos(messages, context)`: download + OCR song song (`asyncio.gather`), merge kết quả, gửi confirm
- [x] Merge logic: tracking/carrier/order_number lấy ảnh đầu tiên có; product_name ghép; total_cny + quantity cộng
- [x] `handle_confirm_tracking_photo` (callback `confirm_tracking_photo`):
  - Lưu đơn vào DB với tracking, carrier, order_number, total_cny, quantity
  - Post inbox message với nút "✏️ Nhập mã đơn" (callback `add_order_num_{id}`)
  - Nếu OCR đã có order_number → hiển thị luôn nhưng vẫn giữ nút để sửa nếu cần
- [x] `handle_add_order_number` (callback `add_order_num_{id}`): edit inbox message → "Nhập mã đơn hàng:" → state `AWAIT_ORDER_NUMBER`
- [x] `handle_order_number_input`: nhận text → UPDATE order_number → edit inbox message (hiện mã đơn, xóa nút), xóa message vừa gõ
- [x] `handle_cancel_tracking_photo` (callback `cancel_tracking_photo`): hủy, xóa pending
- [x] Fallback AWAIT_MANUAL_TRACKING: khi OCR không detect tracking → bot yêu cầu nhập tay → nhận text → lưu
- [x] `build_tracking_photo_handler`: filter `filters.PHOTO & ~filters.Caption(strings=["/order"])`

## Task 3 — Cập nhật `bot/handlers/photo.py`

- [x] Đổi filter trong `build_photo_handler`: thêm `& filters.Caption(strings=["/order"])`

## Task 4 — Đăng ký handler trong `bot/main.py`

- [x] Import các symbol từ `tracking_photo.py`
- [x] Thêm `CallbackQueryHandler` cho `confirm_tracking_photo` và `cancel_tracking_photo`
- [x] `build_tracking_photo_handler` đăng ký **trước** `build_photo_handler`

## Task 5 — Cập nhật `/start` message

- [x] Gửi ảnh thường = tracking page (tự động lưu đơn)
- [x] Gửi ảnh + caption `/order` = nhập đơn hàng Tmall/Taobao (flow cũ)

## Task 6 — Test thủ công

- [ ] Gửi 1 ảnh tracking → OCR đúng tracking + giá + SP → inbox message đúng
- [ ] Gửi 2 ảnh cùng lúc → merge đúng → lưu 1 đơn tổng hợp
- [ ] Gửi ảnh không detect được tracking → fallback nhập tay tracking
- [ ] Gửi ảnh + caption `/order` → flow Tmall cũ vẫn hoạt động
- [ ] Kiểm tra DB: order_number lưu đúng khi detect được, NULL khi không
- [ ] Kiểm tra web dashboard: hiển thị đủ số lượng, tiền, mã đơn, mã vận đơn
