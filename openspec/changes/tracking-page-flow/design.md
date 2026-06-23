# Design: Tracking Page Flow

## Tổng quan

Thêm `bot/handlers/tracking_photo.py` — handler mới xử lý ảnh tracking page.  
Flow cũ (`photo.py` + `tracking.py`) giữ nguyên, chỉ đổi filter.

**Mục tiêu: 1 ảnh → 1 confirm → xong. Không nhập tay gì thêm.**

---

## Dashboard cần hiển thị

| Field | Nguồn |
|-------|-------|
| Tên sản phẩm | OCR từ ảnh |
| Số lượng | OCR từ ảnh |
| Giá (CNY) | OCR từ ảnh |
| Mã vận đơn | OCR từ ảnh |
| Hãng vận chuyển | OCR từ ảnh |
| Mã đơn hàng | OCR từ ảnh (nếu có), để trống nếu không detect được |
| Ngày giao hàng | Nhập thủ công trên web dashboard khi hàng về |

---

## OCR Prompt — `bot/services/ocr.py`

Thêm hàm `extract_tracking_from_image(image_path)`:

```
Đây là ảnh trang vận đơn / tracking page từ app giao hàng Trung Quốc
(Cainiao, YTO, SF Express, ZTO, JD Logistics, v.v.)

Trích xuất thông tin sau, trả về JSON:
{
  "tracking_number": "mã vận đơn số/chữ số",
  "carrier": "YTO/SF/ZTO/JD/4PX/YUNDA/STO/BEST/EMS",
  "product_name": "tên sản phẩm dịch sang tiếng Việt, ngắn gọn",
  "quantity": số_nguyên,
  "unit_price_cny": đơn_giá_hoặc_null,
  "total_cny": tổng_tiền_CNY_hoặc_null,
  "order_number": "mã đơn hàng Tmall/Taobao nếu có, null nếu không thấy"
}

Carrier mapping:
- 菜鸟速递, 圆通, YTO → YTO
- 顺丰速运, SF → SF
- 中通快递, ZTO → ZTO
- 京东物流, JD → JD
- 百世快递, BEST → BEST
- 韵达快递, YUNDA → YUNDA
- 申通快递, STO → STO
- 4PX → 4PX
- 邮政, EMS → EMS

Chỉ trả về JSON, không giải thích.
```

---

## Handler mới — `bot/handlers/tracking_photo.py`

### State machine

```
AWAIT_MANUAL_TRACKING = 20   # fallback nếu OCR không detect được tracking number
```

### Xử lý media group (2 ảnh gửi cùng lúc)

Telegram gửi album dưới dạng nhiều `Message` cùng `media_group_id`. Cần gom lại:

```python
# context.bot_data["media_groups"][media_group_id] = {
#   "messages": [...],
#   "timer_task": asyncio.Task
# }
```

1. Nhận `photo` message
2. Nếu có `media_group_id` → buffer, set/reset asyncio timer 1.5s
3. Khi timer fire → `_process_photos(messages, context)`
4. Nếu không có `media_group_id` → `_process_photos([msg], context)` ngay

### Merge kết quả 2 ảnh

| Field | Logic |
|-------|-------|
| `tracking_number` | Ảnh đầu tiên có tracking, ưu tiên ảnh 1 |
| `carrier` | Tương tự |
| `order_number` | Ảnh đầu tiên có giá trị |
| `product_name` | Nếu 2 ảnh khác SP → ghép "SP1 + SP2" |
| `total_cny` | Cộng lại |
| `quantity` | Cộng lại |

### Confirm message

Khi có tracking:
```
📦 Kem dưỡng Himalaya x1
💰 ¥18.64
🚚 YTO: 611693797159494

[✅ Lưu] [❌ Hủy]
```

Khi không detect được tracking:
```
📦 Kem dưỡng Himalaya x1
💰 ¥18.64
⚠️ Không đọc được mã vận đơn. Nhập tay:

[❌ Hủy]
```
→ Chuyển sang state `AWAIT_MANUAL_TRACKING`, user gõ tracking number → lưu luôn.

### Inbox message sau khi lưu

Luôn có nút "✏️ Nhập mã đơn" để nhập tay mã đơn hàng sau:

```
📦 Kem dưỡng Himalaya x1 — ¥18.64
📅 23/06/2026
🚚 YTO: 611693797159494
🔖 Mã đơn: chưa có

[✏️ Nhập mã đơn]
```

Nếu OCR đã detect được `order_number` thì hiển thị luôn nhưng vẫn giữ nút (để sửa nếu cần):

```
📦 Kem dưỡng Himalaya x1 — ¥18.64
📅 23/06/2026
🚚 YTO: 611693797159494
🔖 Mã đơn: 123456789012345

[✏️ Nhập mã đơn]
```

Khi nhấn nút → bot hỏi "Nhập mã đơn hàng:" → user gõ → lưu vào `order_number` → cập nhật inbox message, xóa nút.

Ngày giao hàng set trên web dashboard khi hàng về thực tế.

---

## Đăng ký handler trong `bot/main.py`

```python
from bot.handlers.tracking_photo import (
    build_tracking_photo_handler,
    handle_confirm_tracking_photo,
    handle_cancel_tracking_photo,
)

app.add_handler(CallbackQueryHandler(handle_confirm_tracking_photo, pattern=r"^confirm_tracking_photo$"))
app.add_handler(CallbackQueryHandler(handle_cancel_tracking_photo, pattern=r"^cancel_tracking_photo$"))
app.add_handler(build_tracking_photo_handler(user_only))  # trước build_photo_handler
```

---

## Phân biệt ảnh tracking vs ảnh đơn Tmall

Mặc định mọi ảnh = tracking page. Muốn nhập đơn Tmall cũ → gửi kèm caption `/order`.

- `build_tracking_photo_handler`: `filters.PHOTO & ~filters.Caption(strings=["/order"])`
- `build_photo_handler`: `filters.PHOTO & filters.Caption(strings=["/order"])`

---

## Cấu trúc file thay đổi

```
bot/handlers/
  tracking_photo.py   ← NEW
  photo.py            ← đổi filter: chỉ xử lý khi caption = "/order"
  tracking.py         ← giữ nguyên (fallback nhập tracking thủ công)
bot/services/
  ocr.py              ← thêm extract_tracking_from_image()
bot/main.py           ← đăng ký handler mới
```

---

## Không thay đổi

- DB schema (`order_number`, `tracking_number`, `delivered_at` đã có sẵn)
- Web dashboard — đã hiển thị đủ các field cần thiết
- `/report`, `/setrate`, `/pending`
