import re
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.services.db import get_monthly_summary, get_orders_by_month, get_setting


async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    now = datetime.now()

    if args:
        m = re.match(r"^(\d{1,2})/(\d{4})$", args[0])
        if not m:
            await update.message.reply_text("❌ Dùng: /report hoặc /report MM/YYYY")
            return
        month, year = int(m.group(1)), int(m.group(2))
    else:
        month, year = now.month, now.year

    summary = await get_monthly_summary(year, month)
    orders = await get_orders_by_month(year, month)

    rate_str = await get_setting("exchange_rate")
    rate = float(rate_str) if rate_str else 3500.0

    total_cny = float(summary["total_cny"] or 0)
    total_vnd = total_cny * rate

    lines = [
        f"📊 <b>Báo cáo tháng {month:02d}/{year}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"Tổng đơn:     {summary['total_orders']}",
        f"Tổng CNY:    ¥{total_cny:,.0f}",
        f"Tổng VND:    {total_vnd:,.0f}đ (tỷ giá: {rate:,.0f})",
        "━━━━━━━━━━━━━━━━━━",
        f"Đã có tracking:    {summary['with_tracking']}",
        f"Chưa có tracking:  {summary['pending']}",
        "",
        "📦 <b>Danh sách đơn:</b>",
    ]

    if not orders:
        lines.append("(không có đơn nào)")
    else:
        for o in orders:
            icon = "✅" if o["tracking_number"] else "⏳"
            tracking = o["tracking_number"] or "chưa có"
            order_date = o["order_date"].strftime("%d/%m") if o["order_date"] else "?"
            lines.append(
                f"{icon} {o['product_name']} x{o['quantity']} — ¥{o['total_cny']:.0f}"
                f" — {tracking} [{order_date}]"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
