import logging
import bale
from bale import Bot
from bale.ui import InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from utils.state_manager import StateManager, UserState
from admin.admin_callback import handle_admin_callback

logger = logging.getLogger(__name__)


async def handle_callback(
    bot: Bot,
    callback: bale.CallbackQuery,
    db: Database,
    state_manager: StateManager
):
    """
    هندل مرکزی همه Callback ها
    """
    data = callback.data or ""
    chat_id = callback.message.chat.id if callback.message else None

    if not chat_id:
        logger.warning("Callback بدون chat_id دریافت شد.")
        return

    logger.info(f"Callback از chat_id={chat_id}: data={data}")

    if data == "btn_start":
        await _handle_btn_start(bot, callback, chat_id, state_manager)

    #  دکمه‌های پنل ادمین
    elif data.startswith("admin_"):
        await handle_admin_callback(bot, callback, db, state_manager)

    else:
        logger.warning(f"Callback ناشناخته: {data}")
        try:
            await bot.answer_callback_query(callback.id, "عملیات نامعتبر")
        except Exception:
            pass


async def _handle_btn_start(
    bot: Bot,
    callback: bale.CallbackQuery,
    chat_id: int,
    state_manager: StateManager
):
    """هندل کلیک روی دکمه شروع"""
    # تنظیم وضعیت منتظر نام
    state_manager.set_user_state(chat_id, UserState.WAITING_NAME)

    text = (
        "عالی ! 🙌\n"
        "فقط اول نام و نام خانوادگی خودت رو در یک پیام ارسال کن.\n"
        "مثال:\n"
        "الهام آقایی"
    )

    try:
        # پاسخ به callback
        await bot.answer_callback_query(callback.id)
        # ارسال پیام جدید
        if callback.message:
            await callback.message.reply(text)
        logger.info(f"دکمه شروع توسط chat_id={chat_id} کلیک شد.")
    except Exception as e:
        logger.error(f"خطا در هندل btn_start برای {chat_id}: {e}")
