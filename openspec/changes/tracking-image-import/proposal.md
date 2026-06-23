# Proposal: Tracking Image Import

## Tóm tắt

Thay đổi cách nhập đơn hàng: thay vì chụp ảnh đơn hàng Tmall/Taobao rồi sau đó nhập tracking thủ công, người dùng chỉ cần **chụp 1 ảnh trang tracking** khi hàng đang vận chuyển — bot tự động trích xuất đầy đủ thông tin và lưu đơn ở trạng thái có tracking ngay.

## Vấn đề

Flow hiện tại có 2 bước tách biệt:
1. Chụp ảnh đơn hàng → lưu vào DB (chưa có tracking)
2. Sau đó nhấn nút "Nhập tracking" → nhập carrier + tracking number

Đây là thao tác thừa. Trong thực tế, khi chụp trang tracking (ví dụ Cainiao/YTO), ảnh đã có đủ:
- Tracking number (vd: 611693797159494)
- Carrier (vd: 菜鸟速递 / YTO Express)
- Tên sản phẩm và giá (vd: 自然堂喜马拉... ¥18.64 x1)
- Trạng thái vận chuyển (运输中 — In Transit)
- Vị trí hiện tại

## Giải pháp

Thêm khả năng nhận dạng **ảnh tracking page** vào OCR:
- Bot detect loại ảnh: tracking page hay order page
- Nếu là tracking page → extract tracking number + carrier + thông tin sản phẩm
- Lưu đơn trực tiếp với tracking number đã có — bỏ qua bước "nhập tracking" thủ công
- Inbox message hiển thị đơn có tracking, không có nút "Nhập tracking" nữa

## Phạm vi

**Có:**
- Detect ảnh tracking vs ảnh đơn hàng trong prompt OCR
- Extract tracking_number + carrier từ ảnh tracking
- Carrier mapping: 菜鸟速递/YTO, 顺丰/SF, 中通/ZTO, 京东/JD, etc.
- Lưu đơn trực tiếp với tracking (không cần bước 2)
- Inbox message khác biệt: hiện tracking number thay vì nút nhập

**Không có:**
- Gọi API carrier để track tự động (ngoài phạm vi)
- Thay đổi flow đơn hàng Tmall/Taobao (vẫn giữ nguyên)
- Thay đổi database schema

## Lý do chọn cách này

Người dùng duy nhất — không cần flow phức tạp. Một ảnh, một action, xong. Giảm từ ~5 tap xuống còn 1.
