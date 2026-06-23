import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from bot.config import TELEGRAM_TOKEN, TELEGRAM_USER_ID
from bot.handlers.photo import build_photo_handler, handle_confirm_order, handle_cancel_order
from bot.handlers.tracking import build_tracking_handler
from bot.handlers.tracking_photo import (
    build_tracking_photo_handler,
    handle_confirm_tracking_photo,
    handle_cancel_tracking_photo,
    handle_add_order_number,
    handle_order_number_input,
)
from bot.handlers.report import report_handler
from bot.handlers.settings import setrate_handler, pending_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        pass  # tắt access log


def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health server on port %d", port)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 *VAorder Bot*\n\n"
        "*Cách nhập đơn:*\n"
        "• Gửi ảnh tracking page → tự động lưu đơn có tracking\n"
        "• Gửi ảnh + caption `/order` → nhập đơn hàng Tmall/Taobao\n\n"
        "*Lệnh:*\n"
        "/report — Báo cáo tháng hiện tại\n"
        "/report MM/YYYY — Báo cáo theo tháng\n"
        "/pending — Danh sách đơn chưa có tracking\n"
        "/setrate <tỷ giá> — Cập nhật tỷ giá CNY/VND",
        parse_mode="Markdown",
    )


def main():
    start_health_server()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    user_only = filters.User(user_id=TELEGRAM_USER_ID)

    app.add_handler(CommandHandler("start", start, filters=user_only))
    app.add_handler(CommandHandler("report", report_handler, filters=user_only))
    app.add_handler(CommandHandler("setrate", setrate_handler, filters=user_only))
    app.add_handler(CommandHandler("pending", pending_handler, filters=user_only))

    app.add_handler(CallbackQueryHandler(handle_confirm_order, pattern=r"^confirm_order$"))
    app.add_handler(CallbackQueryHandler(handle_cancel_order, pattern=r"^cancel_order$"))
    app.add_handler(CallbackQueryHandler(handle_confirm_tracking_photo, pattern=r"^confirm_tracking_photo$"))
    app.add_handler(CallbackQueryHandler(handle_cancel_tracking_photo, pattern=r"^cancel_tracking_photo$"))
    app.add_handler(CallbackQueryHandler(handle_add_order_number, pattern=r"^add_order_num_\d+$"))

    app.add_handler(build_tracking_photo_handler(user_only))  # trước build_photo_handler
    app.add_handler(build_photo_handler(user_only))
    app.add_handler(build_tracking_handler())
    # Top-level text handler cho nhập mã đơn (phải sau ConversationHandler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & user_only, handle_order_number_input))

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
