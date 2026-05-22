import logging
import bale
from bale import Bot, Message
from bale.ui import InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from utils.state_manager import StateManager, UserState

logger = logging.getLogger(__name__)


async def handle_start(
    bot: Bot,
    message: Message,
    db: Database,
    state_manager: StateManager
):
    """
    هندل دستور /start:
    - ارسال پیام خوش‌آمدگویی
    - نمایش دکمه Inline "شروع"
    """
    chat_id = message.chat.id

    # ریست وضعیت کاربر (شروع مجدد)
    state_manager.set_user_state(chat_id, UserState.IDLE)

    # ساخت دکمه Inline
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text="شروع",
            callback_data="btn_start"
        )
    )

    welcome_text = (
        "درود و نور ✨\n"
        "خوش اومدی 😊\n\n"
        "برای مشاهده \"دوره ی رایگان\" ا\n"
        "روی دکمه ی زیر کلیک کن\n"
        "👇👇👇"
    )

    try:
        await message.reply(welcome_text, components=keyboard)
        logger.info(f"پیام /start برای chat_id={chat_id} ارسال شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال پیام start برای {chat_id}: {e}")
