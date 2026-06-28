# 🤖 ربات بله - دوره رایگان

ربات کامل و Production-Ready برای پیام‌رسان بله، با پنل ادمین، دیتابیس SQLite، و خروجی CSV.

---

## 📁 ساختار پروژه

```
bale_bot/
├── main.py                  # نقطه ورود اصلی ربات
├── database.py              # مدیریت دیتابیس SQLite
├── requirements.txt         # وابستگی‌های پایتون
├── .env.example             # نمونه فایل تنظیمات
├── .env                     # فایل تنظیمات (باید ایجاد کنید)
├── bot_data.db              # دیتابیس (خودکار ایجاد می‌شود)
├── bot.log                  # فایل لاگ (خودکار ایجاد می‌شود)
│
├── handlers/
│   ├── __init__.py
│   ├── start_handler.py     # هندل دستور /start
│   ├── message_handler.py   # هندل پیام‌های کاربر (نام + شماره)
│   └── callback_handler.py  # هندل Callback دکمه‌های Inline
│
├── admin/
│   ├── __init__.py
│   ├── admin_handler.py     # هندل /admin + لاگین
│   └── admin_callback.py    # هندل دکمه‌های پنل ادمین + CSV
│
└── utils/
    ├── __init__.py
    ├── state_manager.py     # مدیریت وضعیت کاربران و ادمین
    ├── validators.py        # اعتبارسنجی (شماره موبایل + نام)
    └── csv_exporter.py      # تولید فایل CSV با UTF-8 BOM
```

---

## ⚙️ پیش‌نیازها

- Python **3.9** یا بالاتر
- دسترسی به اینترنت (برای Long Polling)
- توکن ربات از `@BotFather` در پیام‌رسان بله

---

## 🚀 نصب و راه‌اندازی

### ۱. دریافت سورس کد

```bash
# کلون کردن یا کپی کردن پروژه
cd /opt  # یا هر مسیر دلخواه
git clone <REPO_URL> bale_bot
cd bale_bot
```

### ۲. ایجاد محیط مجازی

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# یا روی Windows:
# venv\Scripts\activate
```

### ۳. نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

### ۴. تنظیم فایل محیطی

```bash
cp .env.example .env
nano .env   # یا هر ویرایشگر دیگری
```

محتوای فایل `.env`:

```env
BOT_TOKEN=توکن_ربات_خود_را_اینجا_بگذارید
DB_PATH=bot_data.db
```

> **توکن را چطور بگیریم؟**
> در بله به `@BotFather` پیام دهید، ربات جدید بسازید، توکن دریافت کنید.

### ۵. اجرای ربات

```bash
python main.py
```

---

## 🔄 اجرا به عنوان سرویس (systemd)

برای اجرای دائمی روی سرور لینوکس:

```bash
sudo nano /etc/systemd/system/bale-bot.service
```

محتوا:

```ini
[Unit]
Description=Bale Bot Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/bale_bot
Environment=PATH=/opt/bale_bot/venv/bin
ExecStart=/opt/bale_bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/bale_bot/bot.log
StandardError=append:/opt/bale_bot/bot.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable bale-bot
sudo systemctl start bale-bot
sudo systemctl status bale-bot
```

---

## 🤖 جریان ربات

```
کاربر /start می‌زند
        ↓
پیام خوش‌آمدگویی + دکمه "شروع"
        ↓
کاربر روی "شروع" کلیک می‌کند
        ↓
ربات درخواست نام می‌کند
        ↓
کاربر نام می‌فرستد (اعتبارسنجی)
        ↓
ربات تشکر + درخواست شماره موبایل
        ↓
کاربر شماره می‌فرستد (اعتبارسنجی)
        ↓
ذخیره در دیتابیس
        ↓
ارسال لینک دوره رایگان ✅
```

---

## 👑 پنل ادمین

### ورود:
```
دستور: /admin
نام کاربری: username
رمز عبور: psw
```

### امنیت:
- ۵ بار خطا → ۱۰ دقیقه Cooldown
- نشست ادمین: ۱۰ دقیقه (بعد خودکار Logout می‌شود)

### امکانات:
- 📥 دریافت CSV کل کاربران
- 📊 گزارش بازه‌ای (امروز / ۲ روز / ۷ روز)
- 🚪 خروج از پنل

---

## 📊 ساختار دیتابیس

جدول `users`:

| ستون | نوع | توضیح |
|------|-----|-------|
| id | INTEGER | کلید اصلی (Auto) |
| chat_id | INTEGER | شناسه یکتای کاربر |
| full_name | TEXT | نام و نام خانوادگی |
| phone_number | TEXT | شماره موبایل (نرمال‌شده) |
| created_at | TEXT | تاریخ ثبت با Timezone تهران |

---

## 📄 فایل CSV

- فرمت: UTF-8 BOM (نمایش صحیح فارسی در Excel)
- ستون‌ها: نام، شماره موبایل، تاریخ ثبت، ساعت ثبت
- فایل موقت بعد از ارسال حذف می‌شود

---

## ✅ اعتبارسنجی شماره موبایل

- دقیقاً ۱۱ رقم
- شروع با `09`
- پشتیبانی از اعداد فارسی (`۰۹۱۲۳...`) و انگلیسی

---

## 📝 لاگ‌ها

فایل `bot.log` به صورت خودکار ایجاد می‌شود و شامل:
- اطلاعات کاربران ثبت‌نام‌کرده
- تلاش‌های ورود ادمین
- خطاها و استثناها

---

## 🛠️ عیب‌یابی

**مشکل: خطای Import**
```bash
pip install -r requirements.txt --upgrade
```

**مشکل: Timezone**
```bash
pip install tzdata
```

**مشکل: ربات پاسخ نمی‌دهد**
- توکن را در `.env` بررسی کنید
- لاگ را چک کنید: `tail -f bot.log`

---

## 📌 نکات فنی

- معماری: ماژولار و تمیز
- Concurrency: Async/Await
- State Management: In-Memory (قابل ارتقا به Redis)
- Database: SQLite با WAL mode
- Timezone: Asia/Tehran (UTC+3:30)
- Long Polling (بدون نیاز به سرور HTTPS)
