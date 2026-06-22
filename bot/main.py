import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from bot.config import TELEGRAM_TOKEN, TELEGRAM_USER_ID
from bot.handlers.photo import build_photo_handler
from bot.handlers.tracking import build_tracking_handler
from bot.handlers.report import report_handler
from bot.handlers.settings import setrate_handler, pending_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 *VAorder Bot*\n\n"
        "Gửi ảnh đơn hàng Tmall/Taobao để lưu vào sổ nhập.\n\n"
        "*Lệnh:*\n"
        "/report — Báo cáo tháng hiện tại\n"
        "/report MM/YYYY — Báo cáo theo tháng\n"
        "/pending — Danh sách đơn chưa có tracking\n"
        "/setrate <tỷ giá> — Cập nhật tỷ giá CNY/VND",
        parse_mode="Markdown",
    )


def user_filter(update: Update) -> bool:
    if update.effective_user is None:
        return False
    return update.effective_user.id == TELEGRAM_USER_ID


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Only allow the configured user
    user_only = filters.User(user_id=TELEGRAM_USER_ID)

    app.add_handler(CommandHandler("start", start, filters=user_only))
    app.add_handler(CommandHandler("report", report_handler, filters=user_only))
    app.add_handler(CommandHandler("setrate", setrate_handler, filters=user_only))
    app.add_handler(CommandHandler("pending", pending_handler, filters=user_only))

    # ConversationHandlers (photo OCR flow + tracking flow)
    app.add_handler(build_photo_handler(user_only))
    app.add_handler(build_tracking_handler())

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
