
# 🤖 Bale Bot

A production-ready **Bale Messenger Bot** built with Python.

<br>

![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Async](https://img.shields.io/badge/Async-Await-orange?style=for-the-badge)
![License](https://img.shields.io/github/license/ArshiaBourbour/bale-bot-package?style=for-the-badge)
![Stars](https://img.shields.io/github/stars/ArshiaBourbour/bale-bot-package?style=for-the-badge)
![Forks](https://img.shields.io/github/forks/ArshiaBourbour/bale-bot-package?style=for-the-badge)
![Issues](https://img.shields.io/github/issues/ArshiaBourbour/bale-bot-package?style=for-the-badge)
![Last Commit](https://img.shields.io/github/last-commit/ArshiaBourbour/bale-bot-package?style=for-the-badge)
![Repo Size](https://img.shields.io/github/repo-size/ArshiaBourbour/bale-bot-package?style=for-the-badge)

</div>

---![License](https://img.shields.io/badge/License-MIT-success.svg)

---

# ✨ Features

* 🚀 Production-ready architecture
* 🧩 Clean & Modular structure
* 💾 SQLite database (WAL Mode)
* 👤 User registration flow
* 📱 Phone number validation (Persian & English digits)
* 🔐 Secure Admin Panel
* 📊 CSV Export (UTF-8 BOM for Excel)
* 📈 Registration statistics
* 📝 Logging system
* ⚡ Async/Await implementation
* 🌍 Asia/Tehran timezone support
* 🔄 Long Polling (No HTTPS server required)

---

# 📂 Project Structure

```text
bale_bot/
├── main.py
├── database.py
├── requirements.txt
├── .env.example
├── .env
├── bot_data.db
├── bot.log
│
├── handlers/
│   ├── __init__.py
│   ├── start_handler.py
│   ├── message_handler.py
│   └── callback_handler.py
│
├── admin/
│   ├── __init__.py
│   ├── admin_handler.py
│   └── admin_callback.py
│
└── utils/
    ├── __init__.py
    ├── state_manager.py
    ├── validators.py
    └── csv_exporter.py
```

---

# 📋 Registration Flow

```text
/start
    │
    ▼
Welcome Message
    │
    ▼
Click "Start"
    │
    ▼
Request Full Name
    │
    ▼
Validate Name
    │
    ▼
Request Phone Number
    │
    ▼
Validate Phone Number
    │
    ▼
Save User Information
    │
    ▼
Send Free Course Link ✅
```

---

# 👑 Admin Panel

Login using:

```
/admin
```

Authentication:

* Username
* Password

Security Features:

* Maximum 5 failed login attempts
* 10-minute cooldown after multiple failures
* 10-minute admin session timeout
* Automatic logout

Available Actions:

* 📥 Export all users as CSV
* 📊 Registration statistics
* 🚪 Logout

---

# 📊 Database Schema

| Column       | Type    | Description              |
| ------------ | ------- | ------------------------ |
| id           | INTEGER | Primary Key              |
| chat_id      | INTEGER | Unique User ID           |
| full_name    | TEXT    | User Full Name           |
| phone_number | TEXT    | Mobile Number            |
| created_at   | TEXT    | Registration Date & Time |

---

# 🚀 Installation

## 1. Clone Repository

```bash
git clone <REPOSITORY_URL>
cd bale_bot
```

---

## 2. Create Virtual Environment

Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment

Create a `.env` file:

```env
BOT_TOKEN=YOUR_BALE_BOT_TOKEN
DB_PATH=bot_data.db
```

---

## 5. Run the Bot

```bash
python main.py
```

---

# ⚙️ Running as a Linux Service (systemd)

Create:

```bash
sudo nano /etc/systemd/system/bale-bot.service
```

```ini
[Unit]
Description=Bale Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/bale_bot
Environment=PATH=/opt/bale_bot/venv/bin
ExecStart=/opt/bale_bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bale-bot
sudo systemctl start bale-bot
sudo systemctl status bale-bot
```

---

# 📊 CSV Export

The admin panel can export all registered users to a CSV file.

Encoding:

* UTF-8 BOM

Columns:

* Full Name
* Phone Number
* Registration Date
* Registration Time

The temporary CSV file is automatically deleted after sending.

---

# 📱 Phone Number Validation

Supported formats:

```
09123456789
```

```
۰۹۱۲۳۴۵۶۷۸۹
```

Validation Rules:

* Starts with **09**
* Exactly **11 digits**
* Supports Persian and English numerals

---

# 📝 Logging

The bot automatically creates:

```
bot.log
```

Logged events include:

* User registrations
* Admin logins
* Export actions
* Errors
* Exceptions

---

# 🛠 Tech Stack

* Python
* SQLite
* Asyncio
* Long Polling
* python-dotenv
* CSV
* Logging
* Modular Architecture

---

# 📌 Roadmap

* PostgreSQL Support
* Redis State Manager
* Docker Deployment
* Webhook Support
* Multi-language Interface
* Analytics Dashboard
* REST API Integration


---

# 📄 License

This project is licensed under the **MIT License**.

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.

