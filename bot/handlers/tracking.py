import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.services.db import update_tracking, get_order
from bot.config import TELEGRAM_USER_ID

logger = logging.getLogger(__name__)

AWAIT_TRACKING_NUMBER = 10


async def handle_add_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != TELEGRAM_USER_ID:
        await query.answer()
        return

    await query.answer()
    order_id = int(query.data.split("_", 2)[2])
    context.user_data["tracking_order_id"] = order_id
    context.user_data["tracking_prompt_msg_id"] = query.message.message_id

    order = await get_order(order_id)
    if not order:
        await query.message.reply_text("❌ Không tìm thấy đơn hàng.")
        return ConversationHandler.END

    await query.edit_message_text(
        f"📦 <b>{order['product_name']}</b>\n\nNhập mã vận đơn:",
        parse_mode="HTML",
    )
    return AWAIT_TRACKING_NUMBER


async def handle_tracking_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tracking = update.message.text.strip()
    order_id = context.user_data.get("tracking_order_id")
    prompt_msg_id = context.user_data.get("tracking_prompt_msg_id")

    if not order_id:
        await update.message.reply_text("❌ Phiên hết hạn. Thử lại.")
        return ConversationHandler.END

    order = await get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Không tìm thấy đơn hàng.")
        return ConversationHandler.END

    await update_tracking(order_id, tracking, "")

    chat_id = update.effective_chat.id

    # Xóa inbox message (đơn chưa có tracking)
    if order["telegram_message_id"]:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=order["telegram_message_id"])
        except Exception as e:
            logger.warning("Could not delete inbox message: %s", e)

    # Xóa message "Nhập mã vận đơn"
    if prompt_msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=prompt_msg_id)
        except Exception as e:
            logger.warning("Could not delete prompt message: %s", e)

    # Xóa message tracking number vừa gõ
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning("Could not delete tracking input message: %s", e)

    # Clear state
    context.user_data.pop("tracking_order_id", None)
    context.user_data.pop("tracking_prompt_msg_id", None)

    confirm_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Đã lưu tracking <code>{tracking}</code>",
        parse_mode="HTML",
    )

    # Tự xóa message xác nhận sau 3 giây
    import asyncio
    await asyncio.sleep(3)
    try:
        await confirm_msg.delete()
    except Exception:
        pass

    return ConversationHandler.END


async def handle_cancel_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("tracking_order_id", None)
    context.user_data.pop("tracking_prompt_msg_id", None)
    await query.edit_message_text("❌ Đã hủy.")
    return ConversationHandler.END


def build_tracking_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_add_tracking, pattern=r"^add_tracking_\d+$"),
        ],
        states={
            AWAIT_TRACKING_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tracking_number),
                CallbackQueryHandler(handle_cancel_tracking, pattern=r"^cancel_tracking_\d+$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handle_cancel_tracking, pattern=r"^cancel_tracking_\d+$"),
        ],
        per_user=True,
        per_chat=True,
        per_message=False,
    )
