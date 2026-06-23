# Proposal: Caption as Order Number

## Tóm tắt

Khi gửi ảnh tracking page lên bot, người dùng có thể gõ mã đơn hàng vào phần caption (chú thích ảnh) ngay trên Telegram. Bot tự động đọc caption đó làm `order_number` — bỏ hoàn toàn bước ấn nút "✏️ Nhập mã đơn" sau khi lưu.

## Vấn đề

Hiện tại flow có 2 bước:
1. Gửi ảnh → xác nhận → lưu đơn
2. Ấn "✏️ Nhập mã đơn" → gõ mã → lưu

Bước 2 thừa vì người dùng đã có mã đơn hàng trong tay khi chuẩn bị gửi ảnh. Telegram cho phép thêm caption trực tiếp khi chọn ảnh — đây là thời điểm tự nhiên nhất để nhập mã đơn.

## Giải pháp

- Nếu ảnh gửi kèm caption → dùng caption làm `order_number`
- Nếu không có caption → vẫn hoạt động bình thường, inbox message vẫn có nút "✏️ Nhập mã đơn" như cũ (fallback)
- Caption `/order` vẫn giữ nguyên để phân biệt flow Tmall cũ

## Phạm vi

**Có:**
- Đọc caption từ photo message làm order_number
- Hiển thị order_number ngay trong confirm message nếu có caption
- Bỏ nút "✏️ Nhập mã đơn" nếu order_number đã có từ caption
- Giữ nút nếu không có caption (fallback)

**Không có:**
- Thay đổi DB schema
- Thay đổi flow Tmall (`/order` caption)
- Xóa handler nhập mã đơn thủ công (vẫn giữ làm fallback)
