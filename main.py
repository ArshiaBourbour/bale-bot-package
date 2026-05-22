import asyncio
import logging
import os
from dotenv import load_dotenv

import bale
from bale import Bot
from bale.handlers import CommandHandler, MessageHandler, CallbackQueryHandler

from database import Database
from handlers.start_handler import handle_start
from handlers.message_handler import handle_message
from handlers.callback_handler import handle_callback
from admin.admin_handler import handle_admin_command
from utils.state_manager import StateManager

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# توکن ربات از محیط
BOT_TOKEN = os.getenv("BOT_TOKEN")

# مقداردهی اولیه سینگلتون‌ها
db = Database()
state_manager = StateManager()


def create_bot() -> Bot:
    """ساخت و تنظیم ربات"""
    client = Bot(token=BOT_TOKEN)

    @client.listen("on_before_ready")
    async def on_before_ready():
        """حذف webhook قبل از شروع Long Polling"""
        logger.info("در حال حذف webhook...")
        await client.delete_webhook()
        logger.info("Webhook حذف شد.")

    @client.listen("on_ready")
    async def on_ready():
        """اجرا بعد از آماده شدن ربات"""
        logger.info(f"ربات آماده است: {client.user}")
        db.initialize()
        logger.info("دیتابیس مقداردهی شد.")

    @client.handle(CommandHandler("start"))
    async def start_command(message: bale.Message):
        """هندل دستور /start"""
        try:
            await handle_start(client, message, db, state_manager)
        except Exception as e:
            logger.error(f"خطا در هندل /start: {e}", exc_info=True)

    @client.handle(CommandHandler("admin"))
    async def admin_command(message: bale.Message):
        """هندل دستور /admin"""
        try:
            await handle_admin_command(client, message, db, state_manager)
        except Exception as e:
            logger.error(f"خطا در هندل /admin: {e}", exc_info=True)

    @client.handle(CallbackQueryHandler())
    async def callback_query(callback: bale.CallbackQuery):
        """هندل callback دکمه‌های Inline"""
        try:
            await handle_callback(client, callback, db, state_manager)
        except Exception as e:
            logger.error(f"خطا در هندل callback: {e}", exc_info=True)

    @client.handle(MessageHandler())
    async def message_handler(message: bale.Message):
        """هندل پیام‌های عادی کاربران"""
        try:
            # نادیده گرفتن دستورات (قبلاً هندل شده)
            if message.text and message.text.startswith("/"):
                return
            await handle_message(client, message, db, state_manager)
        except Exception as e:
            logger.error(f"خطا در هندل پیام: {e}", exc_info=True)

    return client


def main():
    """تابع اصلی اجرا"""
    logger.info("در حال راه‌اندازی ربات بله...")
    bot = create_bot()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("ربات متوقف شد.")
    except Exception as e:
        logger.critical(f"خطای بحرانی: {e}", exc_info=True)


if __name__ == "__main__":
    main()
