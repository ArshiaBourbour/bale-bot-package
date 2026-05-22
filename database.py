import sqlite3
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Timezone تهران
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

DB_PATH = os.getenv("DB_PATH", "bot_data.db")


class Database:
    """کلاس مدیریت دیتابیس SQLite"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        """دریافت اتصال به دیتابیس"""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
        return self._connection

    def initialize(self):
        """مقداردهی اولیه - ساخت جداول"""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER UNIQUE NOT NULL,
                    full_name   TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    created_at  TEXT NOT NULL
                )
            """)
            conn.commit()
            logger.info("جدول users آماده است.")
        except sqlite3.Error as e:
            logger.error(f"خطا در مقداردهی دیتابیس: {e}")
            raise

    def _now_tehran(self) -> str:
        """برگرداندن زمان فعلی با timezone تهران به فرمت ISO"""
        return datetime.now(TEHRAN_TZ).isoformat()

    def user_exists(self, chat_id: int) -> bool:
        """بررسی وجود کاربر"""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT 1 FROM users WHERE chat_id = ?", (chat_id,)
            )
            return cur.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"خطا در user_exists: {e}")
            return False

    def save_user(self, chat_id: int, full_name: str, phone_number: str) -> bool:
        """
        ذخیره کاربر جدید در دیتابیس
        Returns True اگر موفق بود، False اگر تکراری بود
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO users (chat_id, full_name, phone_number, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, full_name, phone_number, self._now_tehran())
            )
            conn.commit()
            logger.info(f"کاربر ذخیره شد: chat_id={chat_id}, name={full_name}")
            return True
        except sqlite3.Error as e:
            logger.error(f"خطا در save_user: {e}")
            return False

    def get_all_users(self) -> List[Dict[str, Any]]:
        """دریافت تمام کاربران"""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM users ORDER BY created_at DESC"
            )
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"خطا در get_all_users: {e}")
            return []

    def get_users_by_date_range(self, days: int) -> List[Dict[str, Any]]:
        """
        دریافت کاربران در بازه زمانی مشخص
        days=0 → فقط امروز
        days=2 → ۲ روز گذشته
        days=7 → ۷ روز گذشته
        """
        conn = self._get_connection()
        try:
            now = datetime.now(TEHRAN_TZ)

            if days == 0:
                # فقط امروز (از ابتدای روز)
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                from datetime import timedelta
                start = now - timedelta(days=days)
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)

            start_str = start.isoformat()

            cur = conn.execute(
                "SELECT * FROM users WHERE created_at >= ? ORDER BY created_at DESC",
                (start_str,)
            )
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"خطا در get_users_by_date_range: {e}")
            return []

    def count_total_users(self) -> int:
        """تعداد کل کاربران"""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT COUNT(*) FROM users")
            return cur.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"خطا در count_total_users: {e}")
            return 0

    def count_today_users(self) -> int:
        """تعداد ثبت‌نام‌های امروز"""
        return len(self.get_users_by_date_range(0))

    def close(self):
        """بستن اتصال"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("اتصال دیتابیس بسته شد.")
