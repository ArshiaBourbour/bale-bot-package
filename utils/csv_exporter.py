import csv
import os
import logging
import tempfile
from datetime import datetime
from typing import List, Dict, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def _format_datetime(iso_str: str) -> tuple[str, str]:
    """
    تبدیل رشته ISO به تاریخ و ساعت جداگانه
    Returns: (date_str, time_str)
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        # تبدیل به تهران اگر offset دارد
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TEHRAN_TZ)
        else:
            dt = dt.astimezone(TEHRAN_TZ)
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M:%S")
        return date_str, time_str
    except Exception:
        return iso_str, ""


def generate_csv(users: List[Dict[str, Any]], label: str = "users") -> str:
    """
    تولید فایل CSV موقت از لیست کاربران.
    UTF-8 BOM برای نمایش صحیح فارسی در Excel.

    Args:
        users: لیست دیکشنری کاربران از دیتابیس
        label: پسوند نام فایل

    Returns:
        مسیر فایل CSV موقت
    """
    # ساخت فایل موقت
    fd, path = tempfile.mkstemp(suffix=f"_{label}.csv", prefix="bale_bot_")
    os.close(fd)

    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)

            # هدر
            writer.writerow([
                "نام و نام خانوادگی",
                "شماره موبایل",
                "تاریخ ثبت",
                "ساعت ثبت"
            ])

            for user in users:
                date_str, time_str = _format_datetime(user.get("created_at", ""))
                writer.writerow([
                    user.get("full_name", ""),
                    user.get("phone_number", ""),
                    date_str,
                    time_str,
                ])

        logger.info(f"فایل CSV ساخته شد: {path} ({len(users)} کاربر)")
        return path

    except Exception as e:
        logger.error(f"خطا در ساخت CSV: {e}")
        # پاک کردن فایل ناقص
        if os.path.exists(path):
            os.remove(path)
        raise


def delete_csv(path: str):
    """حذف فایل CSV موقت بعد از ارسال"""
    try:
        if path and os.path.exists(path):
            os.remove(path)
            logger.info(f"فایل CSV حذف شد: {path}")
    except Exception as e:
        logger.warning(f"خطا در حذف CSV: {e}")
