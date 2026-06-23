import asyncio
import logging
import os
from datetime import date, datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.services.db import insert_order, get_order, update_order_number
from bot.services.ocr import extract_tracking_from_image

logger = logging.getLogger(__name__)

AWAIT_MANUAL_TRACKING = 20
AWAIT_ORDER_NUMBER = 21

_MEDIA_GROUP_DELAY = 1.5  # seconds to wait for remaining photos in album


def _inbox_text(product_name, quantity, total_cny, delivered_at, tracking_number, carrier, order_number):
    tracking_str = f"🚚 {carrier}: {tracking_number}" if tracking_number else "📮 Tracking: chưa có"
    order_num_str = f"\n🔖 Mã đơn: {order_number}" if order_number else "\n🔖 Mã đơn: chưa có"
    date_str = f"✅ Ngày giao: {delivered_at.strftime('%d/%m/%Y')}" if delivered_at else "🕐 Chưa giao"
    price_str = f" — ¥{total_cny:.2f}" if total_cny else ""
    return (
        f"📦 <b>{product_name}</b> x{quantity}{price_str}\n"
        f"{date_str}\n"
        f"{tracking_str}"
        f"{order_num_str}"
    )


async def _process_photos(messages: list, context: ContextTypes.DEFAULT_TYPE):
    chat_id = messages[0].chat_id
    user_id = messages[0].from_user.id

    status_msg = await context.bot.send_message(chat_id=chat_id, text="⏳ Đang đọc ảnh...")

    paths = []
    for i, msg in enumerate(messages):
        photo = msg.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        path = f"/tmp/vaorder_track_{user_id}_{i}_{int(datetime.now().timestamp())}.jpg"
        await file.download_to_drive(path)
        paths.append(path)

    results = []
    try:
        loop = asyncio.get_running_loop()
        ocr_results = await asyncio.gather(*[
            loop.run_in_executor(None, extract_tracking_from_image, p)
            for p in paths
        ], return_exceptions=True)
        for r in ocr_results:
            if isinstance(r, Exception):
                logger.error("OCR error: %s", r)
            elif r:
                results.append(r)
    except Exception as e:
        logger.error("_process_photos error: %s", e)
    finally:
        for p in paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    if not results:
        await status_msg.edit_text("❌ Không đọc được thông tin từ ảnh. Thử lại hoặc gửi ảnh rõ hơn.")
        return

    # Merge results
    merged = _merge_results(results)

    # Caption override: ưu tiên caption hơn OCR-detected order_number
    caption_order = context.user_data.pop("caption_order_number", None)
    if caption_order:
        merged["order_number"] = caption_order

    context.user_data["pending_tracking"] = merged
    context.user_data["pending_tracking_status_msg_id"] = status_msg.message_id

    if merged["tracking_number"]:
        price_line = f"💰 ¥{merged['total_cny']:.2f}\n" if merged["total_cny"] else ""
        order_num_line = f"🔖 Mã đơn: <code>{merged['order_number']}</code>\n" if merged.get("order_number") else ""
        text = (
            f"📦 <b>{merged['product_name']}</b> x{merged['quantity']}\n"
            f"{price_line}"
            f"🚚 {merged['carrier']}: <code>{merged['tracking_number']}</code>\n"
            f"{order_num_line}"
        ).rstrip()
        keyboard = [[
            InlineKeyboardButton("✅ Lưu", callback_data="confirm_tracking_photo"),
            InlineKeyboardButton("❌ Hủy", callback_data="cancel_tracking_photo"),
        ]]
    else:
        price_line = f"💰 ¥{merged['total_cny']:.2f}\n" if merged["total_cny"] else ""
        text = (
            f"📦 <b>{merged['product_name']}</b> x{merged['quantity']}\n"
            f"{price_line}"
            f"⚠️ Không đọc được mã vận đơn. Nhập tay:"
        )
        keyboard = [[InlineKeyboardButton("❌ Hủy", callback_data="cancel_tracking_photo")]]

    await status_msg.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    if not merged["tracking_number"]:
        context.user_data["pending_tracking_needs_manual"] = True


def _merge_results(results: list) -> dict:
    tracking_number = next((r["tracking_number"] for r in results if r.get("tracking_number")), None)
    carrier = next((r["carrier"] for r in results if r.get("carrier")), None)
    order_number = next((r["order_number"] for r in results if r.get("order_number")), None)

    product_parts = []
    seen = set()
    for r in results:
        name = r.get("product_name", "")
        if name and name not in seen:
            product_parts.append(name)
            seen.add(name)
    product_name = " + ".join(product_parts) if product_parts else "Sản phẩm không rõ"

    total_cny = sum(r["total_cny"] for r in results if r.get("total_cny")) or None
    quantity = sum(r.get("quantity", 1) for r in results)

    unit_price_cny = None
    if len(results) == 1 and results[0].get("unit_price_cny"):
        unit_price_cny = results[0]["unit_price_cny"]

    return {
        "tracking_number": tracking_number,
        "carrier": carrier or "N/A",
        "order_number": order_number,
        "product_name": product_name,
        "quantity": quantity,
        "unit_price_cny": unit_price_cny,
        "total_cny": total_cny,
        "delivered_at": next((r["delivered_at"] for r in results if r.get("delivered_at")), None),
    }


async def handle_tracking_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # Lưu caption làm order_number nếu có (bỏ qua "/order")
    caption = (msg.caption or "").strip()
    if caption and caption.lower() != "/order":
        context.user_data["caption_order_number"] = caption

    if not msg.media_group_id:
        await _process_photos([msg], context)
        return

    # Buffer media group — chỉ lưu caption từ ảnh đầu tiên
    group_id = msg.media_group_id
    groups = context.bot_data.setdefault("media_groups", {})

    if group_id not in groups:
        groups[group_id] = {"messages": [], "task": None}
    else:
        # Ảnh sau trong album — không override caption đã lưu
        context.user_data.pop("caption_order_number_temp", None)

    groups[group_id]["messages"].append(msg)

    if groups[group_id]["task"]:
        groups[group_id]["task"].cancel()

    async def _fire():
        await asyncio.sleep(_MEDIA_GROUP_DELAY)
        entry = groups.pop(group_id, None)
        if entry:
            await _process_photos(entry["messages"], context)

    groups[group_id]["task"] = asyncio.create_task(_fire())


async def handle_confirm_tracking_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = context.user_data.pop("pending_tracking", None)
    context.user_data.pop("pending_tracking_status_msg_id", None)
    context.user_data.pop("pending_tracking_needs_manual", None)

    if not data:
        try:
            await query.edit_message_text("⚠️ Phiên đã hết hạn (bot vừa restart). Gửi lại ảnh để tiếp tục.")
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Phiên đã hết hạn. Gửi lại ảnh để tiếp tục.",
            )
        return

    try:
        inbox_text = _inbox_text(
            product_name=data["product_name"],
            quantity=data["quantity"],
            total_cny=data.get("total_cny"),
            delivered_at=data.get("delivered_at"),
            tracking_number=data.get("tracking_number"),
            carrier=data.get("carrier"),
            order_number=data.get("order_number"),
        )
        inbox_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=inbox_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✏️ Nhập mã đơn", callback_data="add_order_num_PLACEHOLDER")
            ]]),
        )

        order_id = await insert_order(
            product_name=data["product_name"],
            quantity=data["quantity"],
            unit_price_cny=data.get("unit_price_cny"),
            total_cny=data.get("total_cny") or 0,
            order_date=date.today(),
            telegram_message_id=inbox_msg.message_id,
            order_number=data.get("order_number"),
            tracking_number=data.get("tracking_number"),
            carrier=data.get("carrier"),
            delivered_at=data.get("delivered_at"),
        )

        # Có order_number rồi → xóa nút; chưa có → giữ nút nhập tay
        if data.get("order_number"):
            await inbox_msg.edit_reply_markup(reply_markup=None)
        else:
            await inbox_msg.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✏️ Nhập mã đơn", callback_data=f"add_order_num_{order_id}")
                ]])
            )

        try:
            await query.edit_message_text("✅ Đã lưu đơn hàng!")
        except Exception:
            pass
        await asyncio.sleep(3)
        try:
            await query.delete_message()
        except Exception:
            pass

    except Exception as e:
        logger.error("handle_confirm_tracking_photo error: %s", e)
        try:
            await query.edit_message_text("❌ Lỗi lưu đơn. Thử lại sau.")
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Lỗi lưu đơn. Thử lại sau.")


async def handle_cancel_tracking_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("pending_tracking", None)
    context.user_data.pop("pending_tracking_status_msg_id", None)
    context.user_data.pop("pending_tracking_needs_manual", None)
    await query.edit_message_text("❌ Đã hủy.")


async def handle_add_order_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        order_id = int(query.data.split("_", 3)[3])
    except (ValueError, IndexError):
        logger.error("Bad callback data: %s", query.data)
        return

    context.user_data["order_num_order_id"] = order_id
    context.user_data["order_num_msg_id"] = query.message.message_id
    context.user_data["waiting_for_order_num"] = True

    logger.info("Waiting for order number input, order_id=%s", order_id)

    try:
        await query.edit_message_text(
            query.message.text_html + "\n\n💬 Nhập mã đơn hàng:",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("edit_message_text error in handle_add_order_number: %s", e)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="💬 Nhập mã đơn hàng:")


async def handle_order_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_order_num"):
        return  # không phải đang chờ nhập mã đơn
    order_number = update.message.text.strip()
    order_id = context.user_data.pop("order_num_order_id", None)
    msg_id = context.user_data.pop("order_num_msg_id", None)
    context.user_data.pop("waiting_for_order_num", None)

    if not order_id:
        await update.message.reply_text("❌ Phiên hết hạn. Thử lại.")
        return

    try:
        await update_order_number(order_id, order_number)
    except Exception as e:
        logger.error("DB update order_number error: %s", e)
        await update.message.reply_text("❌ Lỗi lưu DB.")
        return

    try:
        await update.message.delete()
    except Exception:
        pass

    if msg_id:
        order = await get_order(order_id)
        if order:
            new_text = _inbox_text(
                product_name=order["product_name"],
                quantity=order["quantity"],
                total_cny=float(order["total_cny"]) if order["total_cny"] else None,
                delivered_at=order["delivered_at"],
                tracking_number=order["tracking_number"],
                carrier=order["carrier"],
                order_number=order_number,
            )
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=msg_id,
                    text=new_text,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Could not edit inbox message: %s", e)


def build_tracking_photo_handler(user_filter):
    photo_filter = filters.PHOTO & ~filters.Caption(strings=["/order"]) & user_filter
    return ConversationHandler(
        entry_points=[
            MessageHandler(photo_filter, handle_tracking_photo),
        ],
        states={
            AWAIT_MANUAL_TRACKING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, handle_manual_tracking_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handle_cancel_tracking_photo, pattern=r"^cancel_tracking_photo$"),
        ],
        per_user=True,
        per_chat=True,
        per_message=False,
        allow_reentry=True,
    )


async def handle_order_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_number = update.message.text.strip()
    order_id = context.user_data.pop("order_num_order_id", None)
    msg_id = context.user_data.pop("order_num_msg_id", None)
    context.user_data.pop("order_num_original_text", None)

    if not order_id:
        await update.message.reply_text("❌ Phiên hết hạn. Thử lại.")
        return ConversationHandler.END

    try:
        await update_order_number(order_id, order_number)
    except Exception as e:
        logger.error("DB update order_number error: %s", e)
        await update.message.reply_text("❌ Lỗi lưu DB.")
        return ConversationHandler.END

    # Xóa message vừa gõ
    try:
        await update.message.delete()
    except Exception:
        pass

    # Cập nhật inbox message — xóa nút, thêm mã đơn
    if msg_id:
        order = await get_order(order_id)
        if order:
            new_text = _inbox_text(
                product_name=order["product_name"],
                quantity=order["quantity"],
                total_cny=float(order["total_cny"]) if order["total_cny"] else None,
                delivered_at=order["delivered_at"],
                tracking_number=order["tracking_number"],
                carrier=order["carrier"],
                order_number=order_number,
            )
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=msg_id,
                    text=new_text,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Could not edit inbox message: %s", e)

    return ConversationHandler.END


async def handle_manual_tracking_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback: user types tracking number when OCR failed."""
    tracking = update.message.text.strip()
    pending = context.user_data.pop("pending_tracking", None)
    context.user_data.pop("pending_tracking_needs_manual", None)

    if not pending:
        await update.message.reply_text("❌ Phiên hết hạn. Gửi lại ảnh.")
        return ConversationHandler.END

    pending["tracking_number"] = tracking

    try:
        await update.message.delete()
    except Exception:
        pass

    inbox_text = _inbox_text(
        product_name=pending["product_name"],
        quantity=pending["quantity"],
        total_cny=pending.get("total_cny"),
        order_date=date.today(),
        tracking_number=tracking,
        carrier=pending.get("carrier"),
        order_number=pending.get("order_number"),
    )
    inbox_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=inbox_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Nhập mã đơn", callback_data="add_order_num_PLACEHOLDER")
        ]]),
    )

    try:
        order_id = await insert_order(
            product_name=pending["product_name"],
            quantity=pending["quantity"],
            unit_price_cny=pending.get("unit_price_cny"),
            total_cny=pending.get("total_cny") or 0,
            order_date=date.today(),
            telegram_message_id=inbox_msg.message_id,
            order_number=pending.get("order_number"),
            tracking_number=tracking,
            carrier=pending.get("carrier"),
        )
    except Exception as e:
        logger.error("DB insert error: %s", e)
        await inbox_msg.delete()
        await update.message.reply_text("❌ Lỗi lưu DB.")
        return ConversationHandler.END

    await inbox_msg.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Nhập mã đơn", callback_data=f"add_order_num_{order_id}")
        ]])
    )

    confirm = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Đã lưu tracking <code>{tracking}</code>",
        parse_mode="HTML",
    )
    await asyncio.sleep(3)
    try:
        await confirm.delete()
    except Exception:
        pass

    return ConversationHandler.END


def build_tracking_photo_handler(user_filter):
    photo_filter = filters.PHOTO & ~filters.Caption(strings=["/order"]) & user_filter
    return ConversationHandler(
        entry_points=[
            MessageHandler(photo_filter, handle_tracking_photo),
            CallbackQueryHandler(handle_add_order_number, pattern=r"^add_order_num_\d+$"),
        ],
        states={
            AWAIT_MANUAL_TRACKING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, handle_manual_tracking_input),
            ],
            AWAIT_ORDER_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, handle_order_number_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handle_cancel_tracking_photo, pattern=r"^cancel_tracking_photo$"),
        ],
        per_user=True,
        per_chat=True,
        per_message=False,
        allow_reentry=True,
    )
