import re
import logging

logger = logging.getLogger(__name__)

# نگاشت اعداد فارسی به انگلیسی
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_digits(text: str) -> str:
    return text.translate(PERSIAN_DIGITS)


def validate_phone(phone: str) -> tuple[bool, str]:
    if not phone:
        return False, ""

    # حذف فاصله و خط تیره احتمالی
    cleaned = phone.strip().replace("-", "").replace(" ", "")

    # تبدیل اعداد فارسی
    normalized = normalize_digits(cleaned)

    # بررسی فقط ارقام
    if not normalized.isdigit():
        return False, ""

    # بررسی طول (۱۱ رقم)
    if len(normalized) != 11:
        return False, ""

    # بررسی شروع با 09
    if not normalized.startswith("09"):
        return False, ""

    return True, normalized


def sanitize_name(name: str) -> str:
    """
    پاکسازی نام کاربر از کاراکترهای مشکل‌دار.
    فقط کاراکترهای فارسی، انگلیسی، فاصله و نقطه مجاز هستند.
    """
    if not name:
        return ""

    # حذف فضاهای اضافه
    name = " ".join(name.split())

    # فقط حروف فارسی، انگلیسی، اعداد، فاصله و نقطه مجاز است
    cleaned = re.sub(r"[^\u0600-\u06FFa-zA-Z0-9 .]", "", name)

    return cleaned.strip()


def is_valid_name(name: str) -> bool:
    """بررسی معتبر بودن نام (حداقل ۳ کاراکتر، حداکثر ۱۰۰)"""
    cleaned = sanitize_name(name)
    return 3 <= len(cleaned) <= 100
