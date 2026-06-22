# Tasks: Telegram Import Ledger

## Phase 1: Setup & Infrastructure

- [x] **T01** Khởi tạo project structure (`bot/`, `db/`, `requirements.txt`, `.env.example`, `Procfile`)
- [x] **T02** Tạo `db/schema.sql` — bảng `orders` (có cột `delivered_at DATE`) và `settings` với seed tỷ giá
- [ ] **T03** Tạo Supabase project, chạy schema, lấy `DATABASE_URL`
- [ ] **T04** Tạo Telegram bot qua BotFather, lấy `TELEGRAM_TOKEN`
- [x] **T05** Tạo `bot/config.py` — load env vars, validate khi startup
- [x] **T06** Tạo `bot/services/db.py` — connection pool + helper queries (insert_order, update_tracking, update_delivered, get_settings, get_monthly_report)
- [x] **T07** Tạo `bot/main.py` — Application setup, user_id filter middleware, register handlers

## Phase 2: OCR Flow (Photo Handler)

- [x] **T08** Tạo `bot/services/ocr.py` — gọi Claude Vision API với prompt trích xuất JSON (tên SP, SL, đơn giá, tổng CNY, ngày đặt)
- [x] **T09** Tạo `bot/handlers/photo.py` — download ảnh, gọi OCR, parse JSON
- [x] **T10** Hiển thị confirm message với inline buttons `[✅ Lưu đơn]` `[❌ Hủy]`
- [x] **T11** Xử lý callback confirm: INSERT vào DB, post inbox message, lưu `telegram_message_id`
- [x] **T12** Fallback nhập tay khi OCR thất bại (ConversationHandler: tên / SL / CNY / ngày)

## Phase 3: Tracking Flow

- [x] **T13** Tạo `bot/handlers/tracking.py`
- [x] **T14** Callback `add_tracking_<id>`: show carrier keyboard
- [x] **T15** Nhận carrier selection → hỏi tracking number
- [x] **T16** Nhận tracking number → UPDATE DB, xóa inbox message, reply confirm
- [x] **T17** Nút `[❌ Hủy]` trong flow tracking

## Phase 4: Report & Settings

- [x] **T18** Tạo `bot/handlers/report.py`
- [x] **T19** Query tổng hợp theo tháng, format message báo cáo
- [x] **T20** Tạo `bot/handlers/settings.py` — `/setrate`
- [x] **T21** `/pending` command

## Phase 5: Web Dashboard

- [x] **T22** Tạo `web/main.py` — FastAPI app
- [x] **T23** Tạo `web/templates/base.html`
- [x] **T24** Tạo `web/templates/orders.html`
- [x] **T25** Tạo `web/templates/order_detail.html` + date picker
- [x] **T26** API endpoint `POST /orders/{id}/delivered`
- [x] **T27** `Procfile` đã có từ T01

## Phase 6: Deploy & Test

- [ ] **T28** Tạo Railway project, set environment variables
- [ ] **T29** Deploy, test end-to-end với ảnh Tmall thật
- [ ] **T30** Test edge cases: ảnh mờ, đơn trùng, tracking sai format
- [ ] **T31** Test dashboard trên mobile: chọn ngày giao, filter tháng
