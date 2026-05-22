import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TEHRAN_TZ = ZoneInfo("Asia/Tehran")

# حالت‌های مختلف ربات
class UserState:
    IDLE          = "idle"           
    WAITING_NAME  = "waiting_name"   
    WAITING_PHONE = "waiting_phone"  
    COMPLETED     = "completed"      


# حالت‌های پنل ادمین
class AdminState:
    IDLE             = "idle"             
    WAITING_USERNAME = "waiting_username"  
    WAITING_PASSWORD = "waiting_password"  
    AUTHENTICATED    = "authenticated"     
    WAITING_RANGE    = "waiting_range"     


class StateManager:

    def __init__(self):
        self._user_states: Dict[int, Dict[str, Any]] = {}
        self._admin_states: Dict[int, Dict[str, Any]] = {}

    # User State

    def get_user_state(self, chat_id: int) -> str:
        """دریافت وضعیت فعلی کاربر"""
        return self._user_states.get(chat_id, {}).get("state", UserState.IDLE)

    def set_user_state(self, chat_id: int, state: str, **extra_data):
        """تنظیم وضعیت کاربر به همراه داده اضافه"""
        if chat_id not in self._user_states:
            self._user_states[chat_id] = {}
        self._user_states[chat_id]["state"] = state
        self._user_states[chat_id].update(extra_data)
        logger.debug(f"user {chat_id} state → {state}")

    def get_user_data(self, chat_id: int, key: str) -> Optional[Any]:
        """دریافت داده ذخیره‌شده برای کاربر"""
        return self._user_states.get(chat_id, {}).get(key)

    def clear_user_state(self, chat_id: int):
        """پاک کردن وضعیت کاربر"""
        self._user_states.pop(chat_id, None)

    #Admin State

    def _init_admin(self, chat_id: int):
        """مقداردهی اولیه وضعیت ادمین در صورت عدم وجود"""
        if chat_id not in self._admin_states:
            self._admin_states[chat_id] = {
                "state":          AdminState.IDLE,
                "expires_at":     None,
                "fail_count":     0,
                "cooldown_until": None,
            }

    def get_admin_state(self, chat_id: int) -> str:
        """دریافت وضعیت ادمین"""
        self._init_admin(chat_id)
        admin = self._admin_states[chat_id]

        # بررسی انقضای نشست
        if admin["state"] == AdminState.AUTHENTICATED:
            if admin["expires_at"] and datetime.now(TEHRAN_TZ) > admin["expires_at"]:
                logger.info(f"نشست ادمین {chat_id} منقضی شد.")
                self._admin_states[chat_id]["state"] = AdminState.IDLE
                self._admin_states[chat_id]["expires_at"] = None

        return self._admin_states[chat_id]["state"]

    def set_admin_state(self, chat_id: int, state: str):
        """تنظیم وضعیت ادمین"""
        self._init_admin(chat_id)
        self._admin_states[chat_id]["state"] = state
        logger.debug(f"admin {chat_id} state → {state}")

    def is_admin_authenticated(self, chat_id: int) -> bool:
        """بررسی احراز هویت ادمین"""
        return self.get_admin_state(chat_id) == AdminState.AUTHENTICATED

    def authenticate_admin(self, chat_id: int):
        """ثبت احراز هویت موفق با مدت ۱۰ دقیقه"""
        self._init_admin(chat_id)
        self._admin_states[chat_id]["state"] = AdminState.AUTHENTICATED
        self._admin_states[chat_id]["expires_at"] = (
            datetime.now(TEHRAN_TZ) + timedelta(minutes=10)
        )
        self._admin_states[chat_id]["fail_count"] = 0
        logger.info(f"ادمین {chat_id} احراز هویت شد (10 دقیقه).")

    def logout_admin(self, chat_id: int):
        """خروج ادمین از پنل"""
        self._init_admin(chat_id)
        self._admin_states[chat_id]["state"] = AdminState.IDLE
        self._admin_states[chat_id]["expires_at"] = None
        logger.info(f"ادمین {chat_id} خروج کرد.")

    def increment_admin_fail(self, chat_id: int) -> int:
        """افزایش شمارنده خطای ادمین، برگرداندن تعداد خطاها"""
        self._init_admin(chat_id)
        self._admin_states[chat_id]["fail_count"] += 1
        count = self._admin_states[chat_id]["fail_count"]
        logger.warning(f"ادمین {chat_id} خطای ورود: {count}")
        return count

    def set_admin_cooldown(self, chat_id: int, minutes: int = 10):
        """تنظیم cooldown برای ادمین"""
        self._init_admin(chat_id)
        self._admin_states[chat_id]["cooldown_until"] = (
            datetime.now(TEHRAN_TZ) + timedelta(minutes=minutes)
        )
        self._admin_states[chat_id]["state"] = AdminState.IDLE
        logger.warning(f"ادمین {chat_id} به مدت {minutes} دقیقه cooldown شد.")

    def is_admin_in_cooldown(self, chat_id: int) -> Optional[datetime]:
        """
        بررسی cooldown ادمین
        Returns: زمان پایان cooldown اگر فعال است، None اگر نیست
        """
        self._init_admin(chat_id)
        cooldown = self._admin_states[chat_id].get("cooldown_until")
        if cooldown and datetime.now(TEHRAN_TZ) < cooldown:
            return cooldown
        # اگر cooldown تمام شده، ریست کن
        if cooldown:
            self._admin_states[chat_id]["cooldown_until"] = None
            self._admin_states[chat_id]["fail_count"] = 0
        return None

    def get_admin_fail_count(self, chat_id: int) -> int:
        """دریافت تعداد خطاهای ورود"""
        self._init_admin(chat_id)
        return self._admin_states[chat_id].get("fail_count", 0)
