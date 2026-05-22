import logging
import os
import bale
from bale import Bot
from bale.ui import InlineKeyboardMarkup, InlineKeyboardButton
from bale.attachments import InputFile

from database import Database
from utils.state_manager import StateManager, AdminState
from utils.csv_exporter import generate_csv, delete_csv

logger = logging.getLogger(__name__)


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


async def handle_admin_callback(
    bot: Bot,
    callback: bale.CallbackQuery,
    db: Database,
    state_manager: StateManager
):
    """هندل مرکزی Callback های پنل ادمین"""
    data = callback.data or ""
    chat_id = callback.message.chat.id if callback.message else None

    if not chat_id:
        return

    # بررسی احراز هویت
    if not state_manager.is_admin_authenticated(chat_id):
        try:
            await bot.answer_callback_query(
                callback.id,
                "⏱️ نشست ادمین منقضی شده است. لطفاً دوباره /admin را بزنید."
            )
        except Exception:
            pass
        return

    # ─── CSV کامل ─────────────────────────────────────────────────────────
    if data == "admin_csv_all":
        await _send_csv(bot, callback, chat_id, db, days=None)

    # ─── منوی بازه زمانی ──────────────────────────────────────────────────
    elif data == "admin_range_menu":
        keyboard = _build_range_keyboard()
        try:
            await bot.answer_callback_query(callback.id)
            if callback.message:
                await callback.message.reply(
                    "📊 لطفاً بازه زمانی مورد نظر را انتخاب کنید:",
                    components=keyboard
                )
        except Exception as e:
            logger.error(f"خطا در نمایش منوی بازه: {e}")

    # ─── CSV بازه‌های زمانی ───────────────────────────────────────────────
    elif data == "admin_csv_today":
        await _send_csv(bot, callback, chat_id, db, days=0, label="امروز")

    elif data == "admin_csv_2days":
        await _send_csv(bot, callback, chat_id, db, days=2, label="2_روز_اخیر")

    elif data == "admin_csv_7days":
        await _send_csv(bot, callback, chat_id, db, days=7, label="7_روز_اخیر")

    # ─── برگشت به پنل اصلی ───────────────────────────────────────────────
    elif data == "admin_back":
        total = db.count_total_users()
        today = db.count_today_users()
        panel_text = (
            "👑 پنل مدیریت ربات 👑\n\n"
            "📊 آمار کلی ربات:\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"• تعداد کل ثبت‌نام‌ها: {total} نفر\n"
            f"• تعداد ثبت‌نام‌های امروز: {today} نفر\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
        )
        keyboard = _build_admin_panel_keyboard()
        try:
            await bot.answer_callback_query(callback.id)
            if callback.message:
                await callback.message.reply(panel_text, components=keyboard)
        except Exception as e:
            logger.error(f"خطا در برگشت به پنل: {e}")

    # ─── خروج از پنل ─────────────────────────────────────────────────────
    elif data == "admin_logout":
        state_manager.logout_admin(chat_id)
        try:
            await bot.answer_callback_query(callback.id, "✅ خروج موفقیت‌آمیز")
            if callback.message:
                await callback.message.reply(
                    "🚪 از پنل مدیریت خارج شدید.\n"
                    "برای ورود مجدد دستور /admin را ارسال کنید."
                )
            logger.info(f"ادمین chat_id={chat_id} از پنل خارج شد.")
        except Exception as e:
            logger.error(f"خطا در خروج ادمین: {e}")


async def _send_csv(
    bot: Bot,
    callback: bale.CallbackQuery,
    chat_id: int,
    db: Database,
    days: int = None,
    label: str = "all"
):
    """
    تولید و ارسال فایل CSV برای ادمین

    Args:
        days: None → همه، 0 → امروز، 2 → ۲ روز، 7 → ۷ روز
        label: برچسب نام فایل
    """
    csv_path = None
    try:
        # پاسخ سریع به callback
        await bot.answer_callback_query(callback.id, "⏳ در حال تولید فایل...")

        # دریافت داده از دیتابیس
        if days is None:
            users = db.get_all_users()
            label = "همه_کاربران"
        else:
            users = db.get_users_by_date_range(days)

        if not users:
            if callback.message:
                await callback.message.reply("📭 هیچ داده‌ای برای این بازه زمانی وجود ندارد.")
            return

        # تولید CSV
        csv_path = generate_csv(users, label)

        # ارسال فایل
        caption = f"📊 گزارش ثبت‌نام‌ها | {label.replace('_', ' ')}\nتعداد: {len(users)} نفر"

        if callback.message:
            with open(csv_path, "rb") as f:
                await bot.send_document(
                    chat_id,
                    InputFile(f, file_name=f"report_{label}.csv"),
                    caption=caption
                )
        logger.info(f"CSV '{label}' با {len(users)} کاربر برای ادمین {chat_id} ارسال شد.")

    except Exception as e:
        logger.error(f"خطا در ارسال CSV برای ادمین {chat_id}: {e}")
        try:
            if callback.message:
                await callback.message.reply(
                    "❌ خطا در تولید فایل CSV. لطفاً دوباره تلاش کنید."
                )
        except Exception:
            pass
    finally:
        # حذف فایل موقت
        if csv_path:
            delete_csv(csv_path)
