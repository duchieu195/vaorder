# Proposal: Tracking Page Flow

## Tóm tắt

Thay đổi hoàn toàn luồng nhập đơn: thay vì chụp ảnh đơn hàng Tmall/Taobao rồi sau đó nhập tracking thủ công, người dùng gửi **ảnh trang tracking** (Cainiao, YTO, SF, v.v.) — 1 hoặc 2 ảnh cùng lúc. Bot OCR lấy đủ thông tin và lưu đơn ngay với tracking. Không cần bước 2.

## Vấn đề với flow hiện tại

Flow hiện tại gồm 2 bước tách biệt:
1. Chụp ảnh đơn hàng Tmall/Taobao → OCR → confirm → lưu (chưa có tracking)
2. Nhấn nút "✏️ Nhập tracking" → chờ bot hỏi → nhập mã vận đơn

Bước 2 gây chờ đợi và tốn thêm thao tác. Trong thực tế khi hàng đang trên đường về, ảnh trang tracking đã có đủ: tracking number, carrier, tên sản phẩm, giá, số lượng — đủ để lưu đơn hoàn chỉnh trong 1 lần.

## Giải pháp

Thêm handler mới nhận ảnh tracking page:

1. Gửi 1 hoặc 2 ảnh cùng lúc (Telegram media group hoặc ảnh đơn)
2. Bot OCR từng ảnh: extract tracking number, carrier, tên SP, giá
3. Nếu tracking number detect được → lưu đơn ngay
4. Nếu không detect được → bot hỏi nhập tay tracking number, sau đó lưu
5. Đơn được lưu với tracking có sẵn, inbox message hiển thị trạng thái 🚚

## Phạm vi

**Có:**
- Handler xử lý media group (2 ảnh gửi cùng lúc) + ảnh đơn lẻ
- OCR prompt riêng cho tracking page (khác với OCR đơn hàng Tmall)
- Carrier mapping: 菜鸟/YTO, 顺丰/SF, 中通/ZTO, 京东/JD, 百世/BEST, 韵达/YUNDA, 申通/STO, EMS
- Fallback nhập tay tracking nếu OCR không detect được
- Inbox message hiển thị tracking ngay (không có nút "Nhập tracking")

**Không có:**
- Xóa flow cũ (vẫn giữ để nhập đơn hàng Tmall chưa có tracking)
- Gọi API carrier track tự động
- Thay đổi DB schema (tracking_number + carrier đã có sẵn)

## Lý do

Một ảnh tracking page có nhiều thông tin hơn ảnh đơn hàng. Gửi 2 ảnh cùng lúc cho đơn nhiều sản phẩm nhanh hơn nhiều so với flow 2 bước hiện tại.
