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

AWAIT_CARRIER, AWAIT_TRACKING_NUMBER = range(10, 12)

CARRIERS = [
    ("YTO (圆通)", "YTO"),
    ("SF Express (顺丰)", "SF"),
    ("ZTO (中通)", "ZTO"),
    ("JD Logistics (京东)", "JD"),
    ("4PX (菜鸟)", "4PX"),
    ("Khác", "OTHER"),
]


def _carrier_keyboard(order_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(name, callback_data=f"carrier_{code}_{order_id}")
        for name, code in CARRIERS
    ]
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("❌ Hủy", callback_data=f"cancel_tracking_{order_id}")])
    return InlineKeyboardMarkup(rows)


async def handle_add_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != TELEGRAM_USER_ID:
        await query.answer()
        return

    await query.answer()
    order_id = int(query.data.split("_", 2)[2])
    context.user_data["tracking_order_id"] = order_id

    order = await get_order(order_id)
    if not order:
        await query.message.reply_text("❌ Không tìm thấy đơn hàng.")
        return AWAIT_CARRIER

    await query.message.reply_text(
        f"📦 <b>{order['product_name']}</b>\nChọn nhà vận chuyển:",
        parse_mode="HTML",
        reply_markup=_carrier_keyboard(order_id),
    )
    return AWAIT_CARRIER


async def handle_carrier_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 2)  # carrier_CODE_ORDERID
    carrier_code = parts[1]
    order_id = int(parts[2])

    carrier_name = next((name for name, code in CARRIERS if code == carrier_code), carrier_code)
    context.user_data["tracking_carrier_code"] = carrier_code
    context.user_data["tracking_carrier_name"] = carrier_name
    context.user_data["tracking_order_id"] = order_id

    await query.edit_message_text(
        f"✅ <b>{carrier_name}</b>\n\nNhập mã vận đơn:",
        parse_mode="HTML",
    )
    return AWAIT_TRACKING_NUMBER


async def handle_tracking_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tracking = update.message.text.strip()

    order_id = context.user_data.get("tracking_order_id")
    carrier_code = context.user_data.get("tracking_carrier_code")
    carrier_name = context.user_data.get("tracking_carrier_name")

    if not order_id or not carrier_code:
        await update.message.reply_text("❌ Phiên hết hạn. Thử lại.")
        return ConversationHandler.END

    order = await get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Không tìm thấy đơn hàng.")
        return ConversationHandler.END

    await update_tracking(order_id, tracking, carrier_name)

    # Delete inbox message
    if order["telegram_message_id"]:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=order["telegram_message_id"],
            )
        except Exception as e:
            logger.warning("Could not delete inbox message: %s", e)

    # Clear state
    for key in ("tracking_order_id", "tracking_carrier_code", "tracking_carrier_name"):
        context.user_data.pop(key, None)

    await update.message.reply_text(
        f"✅ Đã lưu tracking <code>{tracking}</code> ({carrier_name})",
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def handle_cancel_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    for key in ("tracking_order_id", "tracking_carrier_code", "tracking_carrier_name"):
        context.user_data.pop(key, None)
    await query.edit_message_text("❌ Đã hủy nhập tracking.")
    return ConversationHandler.END


def build_tracking_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_add_tracking, pattern=r"^add_tracking_\d+$"),
        ],
        states={
            AWAIT_CARRIER: [
                CallbackQueryHandler(handle_carrier_selected, pattern=r"^carrier_[^_]+_\d+$"),
                CallbackQueryHandler(handle_cancel_tracking, pattern=r"^cancel_tracking_\d+$"),
            ],
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
