import logging
import bale
from bale import Bot, Message

from database import Database
from utils.state_manager import StateManager, UserState, AdminState
from utils.validators import validate_phone, sanitize_name, is_valid_name
from admin.admin_handler import handle_admin_message

logger = logging.getLogger(__name__)


async def handle_message(
    bot: Bot,
    message: Message,
    db: Database,
    state_manager: StateManager
):
    """
    هندل پیام‌های متنی کاربران بر اساس وضعیت فعلی
    """
    chat_id = message.chat.id
    text = (message.text or "").strip()

    if not text:
        return

    admin_state = state_manager.get_admin_state(chat_id)
    if admin_state in (
        AdminState.WAITING_USERNAME,
        AdminState.WAITING_PASSWORD,
    ):
        await handle_admin_message(bot, message, db, state_manager)
        return

    user_state = state_manager.get_user_state(chat_id)

    if user_state == UserState.WAITING_NAME:
        await _handle_name_input(bot, message, chat_id, text, db, state_manager)

    elif user_state == UserState.WAITING_PHONE:
        await _handle_phone_input(bot, message, chat_id, text, db, state_manager)

    elif user_state in (UserState.IDLE, UserState.COMPLETED):
        try:
            await message.reply(
                "برای شروع دستور /start را ارسال کنید."
            )
        except Exception as e:
            logger.error(f"خطا در ارسال راهنما برای {chat_id}: {e}")


async def _handle_name_input(
    bot: Bot,
    message: Message,
    chat_id: int,
    text: str,
    db: Database,
    state_manager: StateManager
):
    """پردازش نام دریافتی از کاربر"""
    name = sanitize_name(text)

    if not is_valid_name(name):
        try:
            await message.reply(
                "⚠️ لطفاً نام و نام خانوادگی معتبر وارد کنید.\n"
                "مثال:\nالهام آقایی"
            )
        except Exception as e:
            logger.error(f"خطا در ارسال خطای نام برای {chat_id}: {e}")
        return

    # ذخیره نام در وضعیت و انتقال به مرحله بعد
    state_manager.set_user_state(chat_id, UserState.WAITING_PHONE, full_name=name)

    try:
        await message.reply(
            f"{name} خیلی ممنون! 🤝\n\n"
            "حالا شماره موبایل خودت رو وارد کن.\n"
            "مثال: 09123456789"
        )
        logger.info(f"نام '{name}' برای chat_id={chat_id} ذخیره شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال درخواست شماره برای {chat_id}: {e}")


async def _handle_phone_input(
    bot: Bot,
    message: Message,
    chat_id: int,
    text: str,
    db: Database,
    state_manager: StateManager
):
    """پردازش شماره موبایل دریافتی از کاربر"""
    is_valid, phone = validate_phone(text)

    if not is_valid:
        try:
            await message.reply(
                "⚠️ شماره موبایل نامعتبر است!\n\n"
                "لطفاً توجه کنید:\n"
                "• شماره باید دقیقاً ۱۱ رقم باشد\n"
                "• باید با ۰۹ شروع شود\n\n"
                "مثال صحیح: 09123456789\n"
                "لطفاً دوباره وارد کنید:"
            )
        except Exception as e:
            logger.error(f"خطا در ارسال خطای شماره برای {chat_id}: {e}")
        return

    # دریافت نام از state
    full_name = state_manager.get_user_data(chat_id, "full_name") or "کاربر"

    # ذخیره در دیتابیس
    saved = db.save_user(chat_id, full_name, phone)

    # انتقال به حالت تکمیل‌شده
    state_manager.set_user_state(chat_id, UserState.COMPLETED)

    success_message = (
        "تبریک ... 😊\n\n"
        "اینم لینک دوره ی رایگان خدمت شما\n"
        "👇👇👇\n\n"
        "https://www.aparat.com/v/jjap3x5\n\n"
        "ضمناً هر سوالی داشتی میتونی از پشتیبانی 💙\n"
        "لینک پشتیبانی:\n"
        "@support"
    )

    try:
        await message.reply(success_message)
        logger.info(
            f"ثبت‌نام کامل شد: chat_id={chat_id}, name={full_name}, phone={phone}, "
            f"saved_to_db={saved}"
        )
    except Exception as e:
        logger.error(f"خطا در ارسال پیام موفقیت برای {chat_id}: {e}")
