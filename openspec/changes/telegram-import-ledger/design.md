# Design: Telegram Import Ledger

## Kiến trúc tổng thể

```
Telegram App (điện thoại)        Web Browser
        │                              │
        ▼                              ▼
  Telegram Bot (Python)         FastAPI + Jinja2
        │                              │
        └──────────┬───────────────────┘
                   │
              PostgreSQL
              (Supabase)
                   │
              Claude Vision
                  (OCR)
```

Bot và web server cùng chạy trên Railway, chia sẻ 1 Supabase database.

---

## Database Schema

```sql
CREATE TABLE orders (
    id                SERIAL PRIMARY KEY,
    product_name      TEXT NOT NULL,          -- tên SP tiếng Việt
    quantity          INTEGER NOT NULL,
    unit_price_cny    NUMERIC(10,2),          -- đơn giá CNY
    total_cny         NUMERIC(10,2) NOT NULL, -- tổng CNY
    order_date        DATE,                   -- ngày đặt hàng
    tracking_number   VARCHAR(100),           -- NULL = chưa có
    carrier           VARCHAR(50),            -- YTO, SF, ZTO...
    delivered_at      DATE,                   -- ngày giao thành công, set trên dashboard
    telegram_message_id BIGINT,              -- để bot xóa message
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE settings (
    key   VARCHAR(50) PRIMARY KEY,
    value TEXT NOT NULL
);

-- Seed
INSERT INTO settings VALUES ('exchange_rate', '3500');
```

Index: `orders(tracking_number)`, `orders(order_date)`, `orders(delivered_at)`, `orders(created_at)`.

---

## Bot Commands & Handlers

| Trigger | Handler | Mô tả |
|---------|---------|-------|
| `/start` | `start_handler` | Hướng dẫn sử dụng |
| Gửi ảnh | `photo_handler` | OCR → confirm → lưu DB + post inbox message |
| Callback `add_tracking_<id>` | `add_tracking_handler` | Hỏi carrier + tracking number |
| Callback `confirm_tracking_<id>` | `confirm_tracking_handler` | Lưu tracking → xóa inbox message |
| `/report [MM/YYYY]` | `report_handler` | Báo cáo tháng |
| `/setrate <số>` | `setrate_handler` | Cập nhật tỷ giá |
| `/pending` | `pending_handler` | Liệt kê đơn chưa có tracking |

---

## Luồng chính: Upload ảnh → Lưu đơn

```
User gửi ảnh
    │
    ▼
bot.get_file() → download /tmp/
    │
    ▼
Claude Vision API:
  "Đây là ảnh đơn hàng Tmall/Taobao.
   Trích xuất: tên SP (dịch VN), SL, đơn giá CNY,
   tổng CNY, ngày đặt. Trả về JSON."
    │
    ▼
Parse JSON → validate (có tổng_cny?)
    │
    ▼
Gửi confirm message:
  "📦 Áo len x3
   💰 ¥60/cái — Tổng: ¥180
   📅 20/06/2026
   [✅ Lưu đơn] [❌ Hủy]"
    │
    ▼ (user nhấn ✅)
INSERT INTO orders (...)
    │
    ▼
Xóa confirm message
    │
    ▼
Post inbox message (PIN-able):
  "📦 Áo len x3 — ¥180
   📅 20/06/2026
   📮 Tracking: chưa có
   [✏️ Nhập tracking]"
  → Lưu message_id vào orders.telegram_message_id
```

---

## Luồng: Nhập tracking → Xóa inbox

```
User nhấn [✏️ Nhập tracking] trên inbox message
    │
    ▼
Bot hỏi carrier (inline keyboard):
  [YTO] [SF Express] [ZTO]
  [JD Logistics] [4PX] [Khác]
    │
    ▼ (chọn carrier)
Bot hỏi: "Nhập mã vận đơn:"
    │
    ▼ (user gõ số)
UPDATE orders SET tracking_number=..., carrier=... WHERE id=...
    │
    ▼
bot.delete_message(telegram_message_id)  -- xóa inbox message
    │
    ▼
Bot reply: "✅ Đã lưu tracking SF1234567"
```

Dùng `ConversationHandler` với state machine:
`AWAIT_CARRIER → AWAIT_TRACKING_NUMBER`

Context lưu `order_id` trong `context.user_data`.

---

## Báo cáo tháng (/report)

```
/report          → tháng hiện tại
/report 05/2026  → tháng 5/2026
```

Query:
```sql
SELECT
    COUNT(*) as total_orders,
    SUM(total_cny) as total_cny,
    COUNT(*) FILTER (WHERE tracking_number IS NULL) as pending,
    COUNT(*) FILTER (WHERE tracking_number IS NOT NULL) as with_tracking
FROM orders
WHERE DATE_TRUNC('month', order_date) = DATE_TRUNC('month', $1::date)
```

Output format:
```
📊 Báo cáo tháng 6/2026
━━━━━━━━━━━━━━━━━━
Tổng đơn:     12
Tổng CNY:    ¥2,340
Tổng VND:    8,190,000đ (tỷ giá: 3,500)
━━━━━━━━━━━━━━━━━━
Đã có tracking:  8
Chưa có tracking: 4

📦 Danh sách đơn:
✅ Áo len x3 — ¥180 — SF1234567
✅ Giày x2 — ¥220 — YTO9876543
⏳ Quần jeans x5 — ¥450 — chưa có tracking
...
```

---

## Xử lý lỗi OCR

Nếu Claude Vision không extract được (ảnh mờ, layout lạ):
- Bot reply: "❌ Không đọc được ảnh. Bạn có thể nhập tay không?"
- Hiện form nhập tay: tên SP / SL / tổng CNY / ngày

---

## Cấu trúc file

```
vaorder/
├── bot/
│   ├── main.py              # Entry point, Application setup
│   ├── handlers/
│   │   ├── photo.py         # OCR flow
│   │   ├── tracking.py      # Add tracking flow
│   │   ├── report.py        # /report command
│   │   └── settings.py      # /setrate command
│   ├── services/
│   │   ├── ocr.py           # Claude Vision wrapper
│   │   └── db.py            # DB queries (shared với web)
│   └── config.py            # Env vars
├── web/
│   ├── main.py              # FastAPI app
│   ├── templates/
│   │   ├── base.html
│   │   ├── orders.html      # Danh sách + filter
│   │   └── order_detail.html # Chi tiết + date picker
│   └── static/
│       └── style.css
├── db/
│   └── schema.sql
├── .env.example
├── requirements.txt
└── Procfile                 # Railway: 2 processes
```

Railway Procfile:
```
bot: python bot/main.py
web: uvicorn web.main:app --host 0.0.0.0 --port $PORT
```

---

## Web Dashboard

**Stack:** FastAPI + Jinja2 + HTML/CSS thuần — không cần build step, deploy đơn giản.

### Trang chính (`/`) — Danh sách đơn

```
┌─────────────────────────────────────────────────┐
│  VAorder Dashboard          [Tháng: 06/2026 ▼]  │
├─────────────────────────────────────────────────┤
│  Tổng: 12 đơn │ ¥2,340 │ 8,190,000đ            │
│  ✅ Đã giao: 8  │ 🚚 Đang về: 3  │ ⏳ Chờ: 1   │
├─────────────────────────────────────────────────┤
│  Tên SP          │ SL │  CNY  │ Tracking │ Giao │
│  ──────────────────────────────────────────────│
│  Áo len          │  3 │ ¥180  │ SF12345  │ 20/06│
│  Giày da         │  2 │ ¥220  │ YTO9876  │  --  │
│  Quần jeans      │  5 │ ¥450  │   --     │  --  │
└─────────────────────────────────────────────────┘
```

Filter theo tháng qua dropdown. Mỗi hàng click vào → trang detail.

### Trang detail (`/orders/{id}`) — Set ngày giao

```
┌─────────────────────────────────────┐
│  ← Quay lại                         │
│                                     │
│  Giày da x2                         │
│  ¥110/đôi — Tổng: ¥220             │
│  Đặt ngày: 18/06/2026               │
│  Tracking: YTO9876543               │
│                                     │
│  Ngày giao thành công:              │
│  [    chọn ngày    ] 📅  [Lưu]     │
│                                     │
└─────────────────────────────────────┘
```

Date picker native HTML `<input type="date">` — hoạt động tốt trên mobile Safari/Chrome.

### API endpoint

```
POST /orders/{id}/delivered
Body: { "delivered_at": "2026-06-20" }
→ UPDATE orders SET delivered_at = $1 WHERE id = $2
```

---

## Environment Variables

```
TELEGRAM_TOKEN=
TELEGRAM_USER_ID=       # Chỉ cho phép 1 user ID này
ANTHROPIC_API_KEY=
DATABASE_URL=           # Supabase postgres://...
```

`TELEGRAM_USER_ID` dùng để filter — bot ignore mọi message từ user khác.
