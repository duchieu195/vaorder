# Proposal: OCR Prompt Fix — Ignore Suggested Products

## Vấn đề

Trang tracking (Cainiao, YTO, v.v.) thường có phần "Gợi ý sản phẩm" / "Có thể bạn thích" ở cuối ảnh. OCR đọc nhầm tên sản phẩm gợi ý vào thay vì tên sản phẩm trong đơn hàng đang vận chuyển, dẫn đến dữ liệu sai.

## Giải pháp

Cập nhật prompt OCR để:
1. Chỉ đọc thông tin từ **phần trên của trang** — thông tin đơn hàng và vận đơn
2. Bỏ qua mọi nội dung ở phần dưới trang (gợi ý sản phẩm, quảng cáo, banner)
3. Mô tả rõ ràng cấu trúc trang tracking để model biết đâu là dữ liệu cần lấy

## Phạm vi

Chỉ thay đổi `EXTRACT_TRACKING_PROMPT` trong `bot/services/ocr.py`. Không thay đổi code logic.
