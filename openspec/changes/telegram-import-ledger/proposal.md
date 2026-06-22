# Proposal: Telegram Import Ledger

## Tóm tắt

Xây dựng hệ thống sổ nhập hàng điện tử qua Telegram bot để quản lý đơn nhập hàng Tmall/Taobao phục vụ việc bán lại tại Việt Nam. Toàn bộ thao tác trên điện thoại qua Telegram — không cần ghi chép thủ công, không cần web dashboard.

## Vấn đề

Khi nhập hàng Trung Quốc để bán lại, cần theo dõi:
- Đã đặt những đơn nào, tổng chi tiêu bao nhiêu
- Đơn nào đã có mã vận đơn (đang trên đường về)
- Đơn nào chưa có tracking (cần theo dõi thêm)
- Tổng chi tiêu theo tháng để kiểm soát vốn

Hiện tại làm thủ công (chụp ảnh, ghi chép) — tốn thời gian và dễ sót.

## Giải pháp

Telegram bot đóng vai trò là **inbox các đơn chưa hoàn thành** + **sổ cái lưu trữ**:

1. Chụp ảnh màn hình đơn hàng Tmall/Taobao → gửi lên bot
2. Bot dùng Claude Vision OCR trích xuất thông tin + dịch sang tiếng Việt
3. Đơn hàng hiển thị như một message trên chat — tồn tại cho đến khi có tracking
4. Khi có mã vận đơn → nhập vào → message biến mất → đơn lưu vào DB
5. /report xem báo cáo tháng

## Phạm vi

**Có:**
- OCR ảnh đơn hàng Tmall/Taobao bằng Claude Vision
- Inbox đơn chưa có tracking trên Telegram chat
- Nhập tracking number + carrier → xóa khỏi inbox
- Báo cáo tháng (tổng CNY/VND, danh sách đơn)
- Tỷ giá CNY/VND do user tự set

**Không có:**
- Web dashboard
- Gọi API carrier để track tự động
- Multi-user / authentication
- Cronjob

## Người dùng

1 người dùng duy nhất — chủ shop nhập hàng Trung Quốc.

## Tech Stack

- **Bot**: Python + python-telegram-bot v20
- **OCR + dịch**: Claude API (claude-haiku-4-5 — nhanh và rẻ cho vision task)
- **Database**: PostgreSQL trên Supabase (free tier)
- **Hosting**: Railway (free tier, hoặc $5/tháng nếu cần)
