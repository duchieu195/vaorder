# Design: Tracking Image Import

## Thay đổi OCR Prompt

Prompt mới cho `bot/services/ocr.py` phải detect 2 loại ảnh:

**Loại 1 — Trang đơn hàng (Tmall/Taobao order page):** Như hiện tại, trả về JSON không có tracking.

**Loại 2 — Trang tracking (Cainiao, YTO, SF, etc.):** Extract thêm `tracking_number` và `carrier`.

### Prompt mới

```
Đây là ảnh từ app mua hàng Trung Quốc (Tmall, Taobao, Cainiao, hoặc trang vận đơn).

Xác định loại ảnh và trích xuất thông tin:

Nếu là TRANG VẬN ĐƠN / TRACKING (có mã vận đơn, trạng thái vận chuyển):
{
  "image_type": "tracking",
  "tracking_number": "mã vận đơn",
  "carrier": "tên hãng vận chuyển tiếng Anh viết tắt: YTO/SF/ZTO/JD/4PX/EMS/YUNDA/BEST",
  "product_name": "tên sản phẩm dịch sang tiếng Việt, ngắn gọn",
  "quantity": số_nguyên,
  "unit_price_cny": đơn_giá_hoặc_null,
  "total_cny": tổng_tiền_CNY,
  "order_date": "YYYY-MM-DD hoặc null"
}

Nếu là TRANG ĐƠN HÀNG (Tmall/Taobao order detail, không có tracking):
{
  "image_type": "order",
  "tracking_number": null,
  "carrier": null,
  "product_name": "...",
  "quantity": ...,
  "unit_price_cny": ...,
  "total_cny": ...,
  "order_date": "..."
}

Carrier mapping (từ tên Trung Quốc sang viết tắt):
- 菜鸟速递, YTO快递, 圆通 → YTO
- 顺丰速运, SF → SF
- 中通快递, ZTO → ZTO
- 京东物流, JD → JD
- 4PX → 4PX
- 韵达快递, YUNDA → YUNDA
- 申通快递, STO → STO
- 百世快递, BEST → BEST
- 邮政, EMS → EMS

Chỉ trả về JSON, không giải thích.
```

---

## Thay đổi `bot/services/ocr.py`

Hàm `extract_order_from_image` trả về dict với thêm 2 field:
- `image_type`: `"tracking"` hoặc `"order"`
- `tracking_number`: string hoặc `None`
- `carrier`: string hoặc `None`

---

## Thay đổi `bot/handlers/photo.py`

### `handle_confirm_order`

Khi lưu đơn vào DB, truyền thêm `tracking_number` và `carrier` nếu có:

```python
order_id = await insert_order(
    ...
    tracking_number=data.get("tracking_number"),
    carrier=data.get("carrier"),
)
```

### Inbox message — 2 trường hợp

**Nếu có tracking (image_type = "tracking"):**
```
📦 Kem dưỡng Himalaya x1 — ¥18.64
📅 23/06/2026
🚚 YTO: 611693797159494
```
Không có nút "Nhập tracking".

**Nếu không có tracking (image_type = "order"):**
```
📦 Quần jeans x2 — ¥120
📅 23/06/2026
📮 Tracking: chưa có
[✏️ Nhập tracking]
```
Giữ nguyên như cũ.

---

## Thay đổi `bot/services/db.py`

Hàm `insert_order` nhận thêm 2 param:
```python
async def insert_order(
    ...
    tracking_number: str | None = None,
    carrier: str | None = None,
) -> int:
```

Schema DB không thay đổi (các cột `tracking_number` và `carrier` đã có sẵn).

---

## Không thay đổi

- Database schema
- `bot/handlers/tracking.py` — vẫn giữ cho trường hợp nhập tracking thủ công
- `/report`, `/setrate`, web dashboard
- Flow manual entry fallback
