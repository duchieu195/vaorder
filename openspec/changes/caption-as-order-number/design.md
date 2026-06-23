# Design: Caption as Order Number

## Thay đổi duy nhất: `bot/handlers/tracking_photo.py`

### 1. Đọc caption trong `handle_tracking_photo`

Khi nhận photo message, lưu caption vào `context.user_data`:

```python
async def handle_tracking_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    # Lưu caption (nếu có) làm order_number
    caption = msg.caption or ""
    if caption and caption.strip().lower() != "/order":
        context.user_data["caption_order_number"] = caption.strip()
    ...
```

### 2. Merge caption vào OCR result trong `_process_photos`

Sau khi OCR xong và merge results, override `order_number` bằng caption nếu có:

```python
merged = _merge_results(results)

# Caption override: ưu tiên caption hơn OCR-detected order_number
caption_order = context.user_data.pop("caption_order_number", None)
if caption_order:
    merged["order_number"] = caption_order
```

### 3. Confirm message — hiển thị order_number nếu có caption

```
📦 Mặt nạ Himalaya x1
💰 ¥17.52
🚚 YTO: 611693797159494
🔖 Mã đơn: 123456789012345678   ← từ caption

[✅ Lưu] [❌ Hủy]
```

Nếu không có caption, confirm message không hiện dòng mã đơn (như hiện tại).

### 4. Inbox message — bỏ nút "✏️ Nhập mã đơn" nếu đã có order_number

Trong `handle_confirm_tracking_photo`:

```python
# Nếu đã có order_number → không cần nút nhập
if order_id_saved and data.get("order_number"):
    await inbox_msg.edit_reply_markup(reply_markup=None)
else:
    await inbox_msg.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Nhập mã đơn", callback_data=f"add_order_num_{order_id}")
        ]])
    )
```

### 5. Filter caption

Caption `/order` → flow Tmall (giữ nguyên, handled by `build_photo_handler`)

Mọi caption khác (kể cả không có) → flow tracking page

`build_tracking_photo_handler` filter:
```python
filters.PHOTO & ~filters.Caption(strings=["/order"]) & user_filter
```
Không đổi — caption bất kỳ (trừ `/order`) đều vào handler này, bot đọc caption làm mã đơn.

## Không thay đổi

- DB schema
- `handle_add_order_number` + `handle_order_number_input` (giữ làm fallback)
- Media group (2 ảnh): caption lấy từ ảnh đầu tiên trong group
