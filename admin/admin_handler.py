import logging
import bale
from bale import Bot, Message
from bale.ui import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from zoneinfo import ZoneInfo

from database import Database
from utils.state_manager import StateManager, AdminState

logger = logging.getLogger(__name__)

TEHRAN_TZ = ZoneInfo("Asia/Tehran")

# اطلاعات ورود ادمین
ADMIN_USERNAME = "username"
ADMIN_PASSWORD = "psw"

# حداکثر تعداد خطا قبل از cooldown
MAX_FAIL_ATTEMPTS = 5
COOLDOWN_MINUTES = 10
SESSION_MINUTES = 10


def _build_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """ساخت کیبورد پنل ادمین"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📥 دریافت فایل CSV", callback_data="admin_csv_all"))
    keyboard.add(InlineKeyboardButton("📊 دریافت گزارش بازه‌ای", callback_data="admin_range_menu"))
    keyboard.add(InlineKeyboardButton("🚪 خروج از پنل", callback_data="admin_logout"))
    return keyboard


def _build_range_keyboard() -> InlineKeyboardMarkup:
    """ساخت کیبورد انتخاب بازه زمانی"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📅 بازه امروز", callback_data="admin_csv_today"))
    keyboard.add(InlineKeyboardButton("📅 بازه ۲ روز گذشته", callback_data="admin_csv_2days"))
    keyboard.add(InlineKeyboardButton("📅 بازه ۷ روز گذشته", callback_data="admin_csv_7days"))
    keyboard.add(InlineKeyboardButton("🔙 برگشت به مرحله قبل", callback_data="admin_back"))
    return keyboard


async def handle_admin_command(
    bot: Bot,
    message: Message,
    db: Database,
    state_manager: StateManager
):
    """هندل دستور /admin"""
    chat_id = message.chat.id

    # بررسی cooldown
    cooldown_until = state_manager.is_admin_in_cooldown(chat_id)
    if cooldown_until:
        remaining = cooldown_until.astimezone(TEHRAN_TZ)
        remaining_str = remaining.strftime("%H:%M:%S")
        try:
            await message.reply(
                f"🚫 به دلیل تلاش‌های ناموفق متعدد، دسترسی شما تا ساعت "
                f"{remaining_str} مسدود است.\n"
                f"لطفاً بعد از این زمان دوباره تلاش کنید."
            )
        except Exception as e:
            logger.error(f"خطا در ارسال پیام cooldown: {e}")
        return

    # اگر قبلاً احراز هویت شده
    if state_manager.is_admin_authenticated(chat_id):
        await _send_admin_panel(bot, message, db, state_manager, chat_id)
        return

    # شروع فرآیند لاگین
    state_manager.set_admin_state(chat_id, AdminState.WAITING_USERNAME)
    try:
        await message.reply("👤 لطفاً نام کاربری را وارد کنید:\nUsername:")
    except Exception as e:
        logger.error(f"خطا در شروع لاگین ادمین: {e}")


async def handle_admin_message(
    bot: Bot,
    message: Message,
    db: Database,
    state_manager: StateManager
):
    """هندل پیام‌های مرحله لاگین ادمین"""
    chat_id = message.chat.id
    text = (message.text or "").strip()
    admin_state = state_manager.get_admin_state(chat_id)

    # مرحله Username 
    if admin_state == AdminState.WAITING_USERNAME:
        state_manager.set_admin_state(chat_id, AdminState.WAITING_PASSWORD)
        # ذخیره موقت username در state 
        state_manager._admin_states[chat_id]["tmp_username"] = text
        try:
            await message.reply("🔑 لطفاً رمز عبور را وارد کنید:\nPassword:")
        except Exception as e:
            logger.error(f"خطا در درخواست رمز: {e}")

    # مرحله Password 
    elif admin_state == AdminState.WAITING_PASSWORD:
        tmp_username = state_manager._admin_states.get(chat_id, {}).get("tmp_username", "")

        if tmp_username == ADMIN_USERNAME and text == ADMIN_PASSWORD:
            # ورود موفق
            state_manager.authenticate_admin(chat_id)
            await _send_admin_panel(bot, message, db, state_manager, chat_id)
        else:
            # ورود ناموفق
            fail_count = state_manager.increment_admin_fail(chat_id)

            if fail_count >= MAX_FAIL_ATTEMPTS:
                state_manager.set_admin_cooldown(chat_id, COOLDOWN_MINUTES)
                try:
                    await message.reply(
                        f"🚫 {MAX_FAIL_ATTEMPTS} بار اطلاعات اشتباه وارد کردید.\n"
                        f"دسترسی شما به مدت {COOLDOWN_MINUTES} دقیقه مسدود شد."
                    )
                except Exception as e:
                    logger.error(f"خطا در ارسال پیام cooldown: {e}")
            else:
                remaining_attempts = MAX_FAIL_ATTEMPTS - fail_count
                state_manager.set_admin_state(chat_id, AdminState.WAITING_USERNAME)
                state_manager._admin_states[chat_id]["tmp_username"] = ""
                try:
                    await message.reply(
                        f"❌ نام کاربری یا رمز عبور اشتباه است.\n"
                        f"تعداد تلاش باقیمانده: {remaining_attempts}\n\n"
                        "لطفاً دوباره نام کاربری را وارد کنید:\nUsername:"
                    )
                except Exception as e:
                    logger.error(f"خطا در ارسال خطای لاگین: {e}")


async def _send_admin_panel(
    bot: Bot,
    message: Message,
    db: Database,
    state_manager: StateManager,
    chat_id: int
):
    """ارسال پنل ادمین پس از احراز هویت موفق"""
    total = db.count_total_users()
    today = db.count_today_users()

    panel_text = (
        "👑 ورود موفقیت‌آمیز به پنل مدیریت ربات 👑\n\n"
        "📊 آمار کلی ربات:\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"• تعداد کل ثبت‌نام‌ها: {total} نفر\n"
        f"• تعداد ثبت‌نام‌های امروز: {today} نفر\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏱️ شما به مدت ۱۰ دقیقه در پنل ادمین احراز هویت شده‌اید.\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )

    keyboard = _build_admin_panel_keyboard()

    try:
        await message.reply(panel_text, components=keyboard)
        logger.info(f"پنل ادمین برای chat_id={chat_id} نمایش داده شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال پنل ادمین: {e}")
