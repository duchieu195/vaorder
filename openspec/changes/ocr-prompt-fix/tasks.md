# Tasks: OCR Prompt Fix

## Task 1 — Cập nhật `EXTRACT_TRACKING_PROMPT` trong `bot/services/ocr.py`

- [x] Thêm mô tả cấu trúc trang (phần trên = đơn hàng, phần dưới = gợi ý)
- [x] Thêm chỉ thị rõ ràng: chỉ đọc sản phẩm từ đơn hàng đang vận chuyển
- [x] Liệt kê các keyword cần bỏ qua: 猜你喜欢, 为你推荐, 相关推荐, Recommended, Suggested
- [x] Giữ nguyên tất cả fields JSON và carrier mapping
