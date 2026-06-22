from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.services.db import get_setting, set_setting, get_pending_orders


async def setrate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        current = await get_setting("exchange_rate")
        await update.message.reply_text(
            f"Tỷ giá hiện tại: <b>{float(current):,.0f}</b> VND/CNY\n"
            "Dùng: /setrate <tỷ_giá> để cập nhật",
            parse_mode="HTML",
        )
        return

    try:
        rate = float(context.args[0].replace(",", ""))
        if rate <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Tỷ giá không hợp lệ.")
        return

    await set_setting("exchange_rate", str(rate))
    await update.message.reply_text(
        f"✅ Đã cập nhật tỷ giá: <b>{rate:,.0f}</b> VND/CNY",
        parse_mode="HTML",
    )


async def pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = await get_pending_orders()
    if not orders:
        await update.message.reply_text("✅ Không có đơn nào chưa có tracking.")
        return

    await update.message.reply_text(
        f"⏳ <b>{len(orders)} đơn chưa có tracking:</b>",
        parse_mode="HTML",
    )

    for o in orders:
        order_date = o["order_date"].strftime("%d/%m/%Y") if o["order_date"] else "?"
        text = (
            f"📦 <b>{o['product_name']}</b> x{o['quantity']} — ¥{o['total_cny']:.0f}\n"
            f"📅 {order_date}\n"
            f"📮 Tracking: <i>chưa có</i>"
        )
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✏️ Nhập tracking", callback_data=f"add_tracking_{o['id']}")
            ]]),
        )
