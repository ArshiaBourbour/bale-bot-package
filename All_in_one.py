import csv
import json
import logging
import os
import re
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
import jdatetime  
BOT_TOKEN = ""

DB_PATH           = "bot_data.db"
ADMIN_USERNAME    = "admin10"
ADMIN_PASSWORD    = "qweASD10"
MAX_FAIL_ATTEMPTS = 5
COOLDOWN_MINUTES  = 10
SESSION_MINUTES   = 10
POLL_TIMEOUT      = 30   


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))
BASE_URL  = f"https://tapi.bale.ai/bot{BOT_TOKEN}"


def api(method: str, data: dict = None, files=None) -> Optional[dict]:
    """ارسال درخواست به API بله"""
    url = f"{BASE_URL}/{method}"
    try:
        if files:
            resp = requests.post(url, data=data or {}, files=files, timeout=60)
        else:
            resp = requests.post(url, json=data or {}, timeout=60)
        result = resp.json()
        if not result.get("ok"):
            logger.warning(f"API خطا [{method}]: {result.get('description')}")
            return None
        return result.get("result")
    except requests.exceptions.Timeout:
        logger.debug(f"Timeout در {method}")
        return None
    except Exception as e:
        logger.error(f"خطا در API [{method}]: {e}")
        return None


def get_updates(offset: int) -> List[dict]:
    """دریافت آپدیت‌های جدید (Long Polling)"""
    result = api("getUpdates", {"offset": offset, "timeout": POLL_TIMEOUT})
    return result if isinstance(result, list) else []


def send_message(chat_id: int, text: str, reply_markup: dict = None) -> Optional[dict]:
    """ارسال پیام متنی"""
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    return api("sendMessage", data)


def answer_callback(callback_id: str, text: str = ""):
    """پاسخ به callback query"""
    api("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


def send_document(chat_id: int, file_path: str, filename: str, caption: str = ""):
    """ارسال فایل"""
    with open(file_path, "rb") as f:
        api(
            "sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (filename, f, "text/csv")},
        )



def kb_start() -> dict:
    return {"inline_keyboard": [[{"text": "شروع", "callback_data": "btn_start"}]]}

def kb_admin_panel() -> dict:
    return {"inline_keyboard": [
        [{"text": "📥 دریافت فایل CSV",       "callback_data": "admin_csv_all"}],
        [{"text": "📊 دریافت گزارش بازه‌ای",  "callback_data": "admin_range_menu"}],
        [{"text": "🚪 خروج از پنل",            "callback_data": "admin_logout"}],
    ]}

def kb_range() -> dict:
    return {"inline_keyboard": [
        [{"text": "📅 بازه امروز",             "callback_data": "admin_csv_today"}],
        [{"text": "📅 بازه ۲ روز گذشته",      "callback_data": "admin_csv_2days"}],
        [{"text": "📅 بازه ۷ روز گذشته",      "callback_data": "admin_csv_7days"}],
        [{"text": "🔙 برگشت به مرحله قبل",    "callback_data": "admin_back"}],
    ]}

# SQLite database

class Database:
    def __init__(self):
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id      INTEGER UNIQUE NOT NULL,
                full_name    TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                created_at   TEXT NOT NULL
            )
        """)
        self._conn.commit()
        logger.info("دیتابیس آماده است.")

    def _now(self) -> str:
        return datetime.now(TEHRAN_TZ).isoformat()

    def save_user(self, chat_id: int, full_name: str, phone: str):
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO users (chat_id,full_name,phone_number,created_at) VALUES (?,?,?,?)",
                (chat_id, full_name, phone, self._now())
            )
            self._conn.commit()
            logger.info(f"کاربر ذخیره: {chat_id} | {full_name} | {phone}")
        except sqlite3.Error as e:
            logger.error(f"save_user خطا: {e}")

    def get_all(self) -> List[dict]:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ).fetchall()]

    def get_by_range(self, days: int) -> List[dict]:
        now = datetime.now(TEHRAN_TZ)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if days > 0:
            start -= timedelta(days=days)
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM users WHERE created_at >= ? ORDER BY created_at DESC",
            (start.isoformat(),)
        ).fetchall()]

    def count_total(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def count_today(self) -> int:
        return len(self.get_by_range(0))

#  State Manager

class S:  # UserState
    IDLE = "idle"; WAITING_NAME = "waiting_name"
    WAITING_PHONE = "waiting_phone"; COMPLETED = "completed"

class A:  # AdminState
    IDLE = "idle"; WAITING_USER = "waiting_user"
    WAITING_PASS = "waiting_pass"; AUTH = "auth"

class StateManager:
    def __init__(self):
        self._u: Dict[int, dict] = {}   # user states
        self._a: Dict[int, dict] = {}   # admin states

    def uset(self, cid: int, state: str, **kw):
        self._u.setdefault(cid, {})["state"] = state
        self._u[cid].update(kw)

    def uget(self, cid: int) -> str:
        return self._u.get(cid, {}).get("state", S.IDLE)

    def udata(self, cid: int, key: str) -> Any:
        return self._u.get(cid, {}).get(key)

    def _ai(self, cid: int):
        self._a.setdefault(cid, {
            "state": A.IDLE, "expires": None,
            "fails": 0, "cooldown": None, "tmp": ""
        })

    def astate(self, cid: int) -> str:
        self._ai(cid)
        a = self._a[cid]
        if a["state"] == A.AUTH and a["expires"] and datetime.now(TEHRAN_TZ) > a["expires"]:
            a["state"] = A.IDLE; a["expires"] = None
            logger.info(f"نشست ادمین {cid} منقضی شد.")
        return a["state"]

    def is_auth(self, cid: int) -> bool:
        return self.astate(cid) == A.AUTH

    def aset(self, cid: int, state: str):
        self._ai(cid); self._a[cid]["state"] = state

    def authenticate(self, cid: int):
        self._ai(cid)
        self._a[cid].update({
            "state": A.AUTH,
            "expires": datetime.now(TEHRAN_TZ) + timedelta(minutes=SESSION_MINUTES),
            "fails": 0,
        })

    def logout(self, cid: int):
        self._ai(cid)
        self._a[cid].update({"state": A.IDLE, "expires": None})

    def fail(self, cid: int) -> int:
        self._ai(cid); self._a[cid]["fails"] += 1
        return self._a[cid]["fails"]

    def set_cooldown(self, cid: int):
        self._ai(cid)
        self._a[cid]["cooldown"] = datetime.now(TEHRAN_TZ) + timedelta(minutes=COOLDOWN_MINUTES)
        self._a[cid]["state"] = A.IDLE

    def get_cooldown(self, cid: int) -> Optional[datetime]:
        self._ai(cid)
        cd = self._a[cid].get("cooldown")
        if cd and datetime.now(TEHRAN_TZ) < cd:
            return cd
        if cd:
            self._a[cid]["cooldown"] = None; self._a[cid]["fails"] = 0
        return None

    def set_tmp(self, cid: int, v: str): self._ai(cid); self._a[cid]["tmp"] = v
    def get_tmp(self, cid: int) -> str:  self._ai(cid); return self._a[cid].get("tmp", "")


_FA = str.maketrans("۰۱۲۳۴۵۶تر۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def norm(text: str) -> str:
    return text.translate(_FA)

def valid_phone(p: str) -> tuple:
    c = norm(p.strip().replace("-","").replace(" ",""))
    if c.isdigit() and len(c)==11 and c.startswith("09"):
        return True, c
    return False, ""

def clean_name(n: str) -> str:
    n = " ".join(n.split())
    return re.sub(r"[^\u0600-\u06FFa-zA-Z0-9 .]", "", n).strip()

def valid_name(n: str) -> bool:
    return 3 <= len(clean_name(n)) <= 100

# CSV Export

def make_csv(users: List[dict], label: str) -> str:
    fd, path = tempfile.mkstemp(suffix=f"_{label}.csv", prefix="bale_")
    os.close(fd)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["نام و نام خانوادگی", "شماره موبایل", "تاریخ ثبت (شمسی)", "ساعت ثبت"])
        for u in users:
            try:
                dt = datetime.fromisoformat(u.get("created_at",""))
                dt = dt.astimezone(TEHRAN_TZ)
                
                # تبدیل تاریخ میلادی به شمسی به وقت تهران
                shamsi_dt = jdatetime.datetime.fromgregorian(datetime=dt)
                d = shamsi_dt.strftime("%Y/%m/%d")
                t = shamsi_dt.strftime("%H:%M:%S")
            except Exception:
                d, t = u.get("created_at",""), ""
            w.writerow([u.get("full_name",""), u.get("phone_number",""), d, t])
    return path


db = Database()
sm = StateManager()


def handle_start(cid: int):
    sm.uset(cid, S.IDLE)
    send_message(
        cid,
        'درود و نور ✨\nخوش اومدی 😊\n\nبرای مشاهده "دوره ی رایگان" \nروی دکمه ی زیر کلیک کن\n👇👇👇',
        kb_start()
    )


def handle_admin(cid: int):
    cd = sm.get_cooldown(cid)
    if cd:
        # نمایش زمان مسدودی به شمسی و وقت تهران
        shamsi_cd = jdatetime.datetime.fromgregorian(datetime=cd.astimezone(TEHRAN_TZ))
        t = shamsi_cd.strftime("%H:%M:%S")
        send_message(cid, f"🚫 دسترسی تا ساعت {t} مسدود است.")
        return
    if sm.is_auth(cid):
        send_panel(cid); return
    sm.aset(cid, A.WAITING_USER)
    send_message(cid, "👤 لطفاً نام کاربری را وارد کنید:\nUsername:")


def handle_text(cid: int, text: str):
    astate = sm.astate(cid)
    if astate == A.WAITING_USER:
        sm.set_tmp(cid, text)
        sm.aset(cid, A.WAITING_PASS)
        send_message(cid, "🔑 لطفاً رمز عبور را وارد کنید:\nPassword:")
        return
    if astate == A.WAITING_PASS:
        check_login(cid, text); return

    ustate = sm.uget(cid)
    if ustate == S.WAITING_NAME:
        do_name(cid, text)
    elif ustate == S.WAITING_PHONE:
        do_phone(cid, text)
    else:
        send_message(cid, "برای شروع دستور /start را ارسال کنید.")


def do_name(cid: int, text: str):
    name = clean_name(text)
    if not valid_name(name):
        send_message(cid, "⚠️ نام معتبر وارد کنید.\nمثال:\nالهام آقایی")
        return
    sm.uset(cid, S.WAITING_PHONE, full_name=name)
    send_message(cid, f"{name} خیلی ممنون! 🤝\n\nحالا شماره موبایل خودت رو وارد کن.\nمثال: 09123456789")


def do_phone(cid: int, text: str):
    ok, phone = valid_phone(text)
    if not ok:
        send_message(cid,
            "⚠️ شماره نامعتبر!\n\n"
            "• دقیقاً ۱۱ رقم\n"
            "• باید با ۰۹ شروع شود\n\n"
            "مثال: 09123456789\nدوباره وارد کنید:")
        return
    name = sm.udata(cid, "full_name") or "کاربر"
    db.save_user(cid, name, phone)
    sm.uset(cid, S.COMPLETED)
    send_message(cid,
        "تبریک ... 😊\n\n"
        "اینم لینک دوره ی رایگان خدمت شما\n"
        "👇👇👇\n\n"
        "https://www.aparat.com/v/jjap3x5\n\n"
        " ضمناً هر سوالی داشتی میتونی از پشتیبانی بپرسی 💙\n"
        "لینک پشتیبانی:\n@support")


def check_login(cid: int, password: str):
    username = sm.get_tmp(cid)
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        sm.authenticate(cid)
        send_panel(cid)
    else:
        fails = sm.fail(cid)
        if fails >= MAX_FAIL_ATTEMPTS:
            sm.set_cooldown(cid)
            send_message(cid, f"🚫 {MAX_FAIL_ATTEMPTS} بار خطا!\nدسترسی {COOLDOWN_MINUTES} دقیقه مسدود شد.")
        else:
            sm.aset(cid, A.WAITING_USER); sm.set_tmp(cid, "")
            send_message(cid, f"❌ اطلاعات اشتباه. تلاش باقیمانده: {MAX_FAIL_ATTEMPTS-fails}\n\nUsername:")


def send_panel(cid: int):
    send_message(cid,
        "👑 ورود موفقیت‌آمیز به پنل مدیریت ربات 👑\n\n"
        "📊 آمار کلی ربات:\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"• تعداد کل ثبت‌نام‌ها: {db.count_total()} نفر\n"
        f"• تعداد ثبت‌نام‌های امروز: {db.count_today()} نفر\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏱️ شما به مدت ۱۰ دقیقه در پنل ادمین احراز هویت شده‌اید.\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        kb_admin_panel()
    )


def handle_callback(cid: int, cb_id: str, data: str):
    answer_callback(cb_id)

    if data == "btn_start":
        sm.uset(cid, S.WAITING_NAME)
        send_message(cid,
            "عالی ! 🙌\n"
            "فقط اول نام و نام خانوادگی خودت رو در یک پیام ارسال کن.\n"
            "مثال:\nالهام آقایی")
        return

    if not data.startswith("admin_"):
        return

    if not sm.is_auth(cid):
        answer_callback(cb_id, "⏱️ نشست منقضی. دوباره /admin بزنید.")
        return

    if data == "admin_csv_all":
        do_csv(cid, days=None, label="همه_کاربران")

    elif data == "admin_range_menu":
        send_message(cid, "📊 بازه زمانی را انتخاب کنید:", kb_range())

    elif data == "admin_csv_today":
        do_csv(cid, days=0, label="امروز")

    elif data == "admin_csv_2days":
        do_csv(cid, days=2, label="2_روز_اخیر")

    elif data == "admin_csv_7days":
        do_csv(cid, days=7, label="7_روز_اخیر")

    elif data == "admin_back":
        send_panel(cid)

    elif data == "admin_logout":
        sm.logout(cid)
        send_message(cid, "🚪 از پنل مدیریت خارج شدید.\nبرای ورود مجدد /admin را بزنید.")


def do_csv(cid: int, days: Optional[int], label: str):
    send_message(cid, "⏳ در حال تولید فایل...")
    users = db.get_all() if days is None else db.get_by_range(days)
    if not users:
        send_message(cid, "📭 داده‌ای در این بازه وجود ندارد."); return
    path = None
    try:
        path = make_csv(users, label)
        send_document(
            cid, path,
            filename=f"report_{label}.csv",
            caption=f"📊 گزارش | {label.replace('_',' ')} | {len(users)} نفر"
        )
    except Exception as e:
        logger.error(f"خطا در ارسال CSV: {e}")
        send_message(cid, "❌ خطا در تولید فایل. دوباره تلاش کنید.")
    finally:
        if path and os.path.exists(path):
            os.remove(path)

# main
def process_update(update: dict):
    """پردازش هر آپدیت دریافتی"""
    try:
        if "message" in update:
            msg  = update["message"]
            cid  = msg["chat"]["id"]
            text = msg.get("text", "")

            if text == "/start":
                handle_start(cid)
            elif text == "/admin":
                handle_admin(cid)
            elif text:
                handle_text(cid, text)

        elif "callback_query" in update:
            cb   = update["callback_query"]
            cid  = cb["message"]["chat"]["id"]
            data = cb.get("data", "")
            cb_id= cb["id"]
            handle_callback(cid, cb_id, data)

    except Exception as e:
        logger.error(f"خطا در process_update: {e}", exc_info=True)


def main():
    logger.info("ربات بله در حال راه‌اندازی...")
    api("deleteWebhook")
    logger.info("آماده دریافت پیام (Long Polling)...")

    offset = 0
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                process_update(update)
        except KeyboardInterrupt:
            logger.info("ربات متوقف شد.")
            break
        except Exception as e:
            logger.error(f"خطا در حلقه اصلی: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
