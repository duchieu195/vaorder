import os
import logging
from datetime import datetime, date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from bot.services.ocr import extract_order_from_image
from bot.services.db import insert_order

logger = logging.getLogger(__name__)

# ConversationHandler states for manual entry fallback
(MANUAL_NAME, MANUAL_QTY, MANUAL_PRICE, MANUAL_DATE) = range(4)


def _format_confirm(data: dict) -> str:
    qty = data["quantity"]
    unit = data.get("unit_price_cny")
    total = data["total_cny"]
    order_date = data.get("order_date") or "không rõ"
    order_num = data.get("order_number")

    unit_str = f"¥{unit:.2f}/cái — " if unit else ""
    order_num_str = f"\n🔖 Mã đơn: <code>{order_num}</code>" if order_num else ""
    return (
        f"📦 <b>{data['product_name']}</b>\n"
        f"🔢 Số lượng: {qty}x\n"
        f"💰 {unit_str}Tổng: <b>¥{total:.2f}</b>\n"
        f"📅 Ngày đặt: {order_date}"
        f"{order_num_str}\n\n"
        "Xác nhận lưu đơn này?"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Đang đọc ảnh...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    path = f"/tmp/vaorder_{update.effective_user.id}_{int(datetime.now().timestamp())}.jpg"
    await file.download_to_drive(path)

    try:
        data = extract_order_from_image(path)
    except Exception as e:
        logger.error("OCR error: %s", e)
        data = None
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    if not data:
        await msg.edit_text(
            "❌ Không đọc được thông tin đơn hàng.\n\n"
            "Bạn muốn nhập tay không? Gõ tên sản phẩm:",
        )
        return MANUAL_NAME

    context.user_data["pending_order"] = data
    keyboard = [
        [
            InlineKeyboardButton("✅ Lưu đơn", callback_data="confirm_order"),
            InlineKeyboardButton("❌ Hủy", callback_data="cancel_order"),
        ]
    ]
    await msg.edit_text(
        _format_confirm(data),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END


async def handle_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = context.user_data.pop("pending_order", None)
    if not data:
        await query.edit_message_text("❌ Không tìm thấy thông tin đơn hàng.")
        return

    order_date = None
    if data.get("order_date"):
        try:
            order_date = date.fromisoformat(data["order_date"])
        except ValueError:
            pass
    if order_date is None:
        order_date = date.today()

    # Post inbox message first (we need its message_id)
    order_num = data.get("order_number")
    order_num_str = f"\n🔖 <code>{order_num}</code>" if order_num else ""
    inbox_text = (
        f"📦 <b>{data['product_name']}</b> x{data['quantity']} — ¥{data['total_cny']:.2f}\n"
        f"📅 {order_date.strftime('%d/%m/%Y')}"
        f"{order_num_str}\n"
        f"📮 Tracking: <i>chưa có</i>"
    )
    inbox_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=inbox_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Nhập tracking", callback_data="add_tracking_PLACEHOLDER")
        ]]),
    )

    try:
        order_id = await insert_order(
            product_name=data["product_name"],
            quantity=data["quantity"],
            unit_price_cny=data.get("unit_price_cny"),
            total_cny=data["total_cny"],
            order_date=order_date,
            telegram_message_id=inbox_msg.message_id,
            order_number=data.get("order_number"),
        )
    except Exception as e:
        logger.error("DB insert error: %s", e)
        await inbox_msg.delete()
        await query.edit_message_text("❌ Lỗi lưu DB. Thử lại sau.")
        return

    # Re-edit inbox message with correct order_id in callback_data
    await inbox_msg.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Nhập tracking", callback_data=f"add_tracking_{order_id}")
        ]])
    )

    await query.edit_message_text("✅ Đã lưu đơn hàng!", parse_mode="HTML")

    # Tự xóa message xác nhận sau 3 giây
    import asyncio
    await asyncio.sleep(3)
    try:
        await query.delete_message()
    except Exception:
        pass


async def handle_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("pending_order", None)
    await query.edit_message_text("❌ Đã hủy.")


# ── Manual entry fallback ──────────────────────────────────────────────────

async def manual_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["manual"] = {"product_name": update.message.text.strip()}
    await update.message.reply_text("Số lượng (nguyên):")
    return MANUAL_QTY


async def manual_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qty = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập số nguyên. Số lượng:")
        return MANUAL_QTY
    context.user_data["manual"]["quantity"] = qty
    await update.message.reply_text("Tổng tiền CNY (ví dụ: 180):")
    return MANUAL_PRICE


async def manual_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        total = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập số. Tổng tiền CNY:")
        return MANUAL_PRICE
    context.user_data["manual"]["total_cny"] = total
    await update.message.reply_text("Ngày đặt hàng (DD/MM/YYYY) hoặc bỏ qua gõ '-':")
    return MANUAL_DATE


async def manual_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    order_date = None
    if text != "-":
        try:
            order_date = datetime.strptime(text, "%d/%m/%Y").date()
        except ValueError:
            await update.message.reply_text("❌ Sai định dạng. Dùng DD/MM/YYYY hoặc '-':")
            return MANUAL_DATE
    if order_date is None:
        order_date = date.today()

    m = context.user_data.pop("manual")
    qty = m["quantity"]
    total = m["total_cny"]

    inbox_text = (
        f"📦 <b>{m['product_name']}</b> x{qty} — ¥{total:.2f}\n"
        f"📅 {order_date.strftime('%d/%m/%Y')}\n"
        f"📮 Tracking: <i>chưa có</i>"
    )
    inbox_msg = await update.message.reply_text(
        inbox_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Nhập tracking", callback_data="add_tracking_PLACEHOLDER")
        ]]),
    )

    try:
        order_id = await insert_order(
            product_name=m["product_name"],
            quantity=qty,
            unit_price_cny=None,
            total_cny=total,
            order_date=order_date,
            telegram_message_id=inbox_msg.message_id,
        )
    except Exception as e:
        logger.error("DB insert error (manual): %s", e)
        await inbox_msg.delete()
        await update.message.reply_text("❌ Lỗi lưu DB.")
        return ConversationHandler.END

    await inbox_msg.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Nhập tracking", callback_data=f"add_tracking_{order_id}")
        ]])
    )
    await update.message.reply_text("✅ Đã lưu đơn hàng!")
    return ConversationHandler.END


def build_photo_handler(user_filter):
    order_filter = filters.PHOTO & filters.Caption(strings=["/order"]) & user_filter
    return ConversationHandler(
        entry_points=[MessageHandler(order_filter, handle_photo)],
        states={
            MANUAL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_name)],
            MANUAL_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_qty)],
            MANUAL_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_price)],
            MANUAL_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_date)],
        },
        fallbacks=[],
        per_user=True,
        per_chat=True,
    )
