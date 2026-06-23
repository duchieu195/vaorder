# Tasks: Caption as Order Number

## Task 1 — Đọc caption trong `handle_tracking_photo`

**File:** `bot/handlers/tracking_photo.py`

- [x] Trong `handle_tracking_photo`: đọc `msg.caption`, bỏ qua nếu là `/order` hoặc rỗng
- [x] Lưu vào `context.user_data["caption_order_number"]`
- [x] Xử lý cả media group: với ảnh đầu tiên trong group, lưu caption; các ảnh sau bỏ qua

## Task 2 — Merge caption vào result trong `_process_photos`

**File:** `bot/handlers/tracking_photo.py`

- [x] Sau `merged = _merge_results(results)`, pop `caption_order_number` từ user_data
- [x] Nếu có caption → override `merged["order_number"]`
- [x] Hiển thị `🔖 Mã đơn: {order_number}` trong confirm message nếu có

## Task 3 — Inbox message không có nút nếu order_number đã có

**File:** `bot/handlers/tracking_photo.py`

- [x] Trong `handle_confirm_tracking_photo`: nếu `order_number` đã có → `edit_reply_markup(reply_markup=None)` (xóa nút)
- [x] Nếu không có → giữ nút "✏️ Nhập mã đơn" như cũ
