# SkillVerse

SkillVerse is a freelance skill marketplace where clients can hire service providers for various skills. The platform includes a wallet-based payment system, real-time chat, order management, certificate generation, and an AI assistant called AskVera.

---

## How to Run

**Requirements:**
- Python 3.x
- PostgreSQL (running locally)
- Database name: `skillverse_pg`

**First time setup:**
```bash
pip install -r requirements.txt
```

**Start the application:**
```bash
python run.py
```

**Open in browser:**
```
http://localhost:5000
```

**Admin login:**
```
Email:    admin@skillverse.com
Password: admin123
```

---

## Folder Structure

```
SKILLVERSE_VERA_BACKUP/
|
|-- .env                   (database URL, API keys, email config)
|-- run.py                 (entry point - run this to start the app)
|-- README.md
|
|-- BACKEND/
|   |-- core/
|   |   |-- app.py             (Flask app factory - creates the app)
|   |   |-- config.py          (database and app settings)
|   |   |-- extensions.py      (Flask-Login, SocketIO, OAuth, Mail setup)
|   |   |-- events.py          (Socket.IO real-time chat events)
|   |
|   |-- models/
|   |   |-- models.py          (14 SQLAlchemy database models)
|   |   |-- data_structures.py (custom data structures)
|   |
|   |-- routes/
|   |   |-- routes.py          (all URL routes and page logic)
|   |   |-- routes_chat.py     (AskVera chatbot endpoint)
|   |
|   |-- services/
|   |   |-- managers.py            (order and booking business logic)
|   |   |-- payment_system.py      (wallet and payment processing)
|   |   |-- certificate_generator.py (PDF certificate generation)
|   |   |-- email_utils.py         (email sending functions)
|   |   |-- chat_manager.py        (chat message handling)
|   |
|   |-- database/
|   |   |-- init_db.py             (creates admin user and seeds categories)
|   |   |-- migrate_db.py          (database schema migrations)
|   |   |-- create_pg_tables.py    (PostgreSQL table setup)
|   |   |-- add_rejection_reason.py
|   |   |-- add_rejection_reason_pg.py
|   |
|   |-- utils/
|       |-- requirements.txt       (all Python dependencies)
|       |-- start.bat              (Windows batch file to start app)
|
|-- FRONTEND/
|   |-- templates/             (40+ Jinja2 HTML templates)
|   |   |-- index.html             (homepage)
|   |   |-- base.html              (master layout - navbar and footer)
|   |   |-- about.html
|   |   |-- contact.html
|   |   |-- services.html          (browse all services)
|   |   |-- service_detail.html    (single service page)
|   |   |-- service_create.html
|   |   |-- service_edit.html
|   |   |-- verify_certificate.html
|   |   |
|   |   |-- auth/              (2 files)
|   |   |   |-- login.html
|   |   |   |-- register.html
|   |   |
|   |   |-- admin/             (9 files - admin only)
|   |   |   |-- dashboard.html
|   |   |   |-- users.html
|   |   |   |-- services.html
|   |   |   |-- pending_services.html
|   |   |   |-- orders.html
|   |   |   |-- bookings.html
|   |   |   |-- categories.html
|   |   |   |-- messages.html
|   |   |   |-- availability.html
|   |   |
|   |   |-- user/              (13 files)
|   |   |   |-- client_dashboard.html
|   |   |   |-- provider_dashboard.html
|   |   |   |-- profile.html
|   |   |   |-- settings.html
|   |   |   |-- orders.html
|   |   |   |-- order_detail.html
|   |   |   |-- wallet.html
|   |   |   |-- transactions.html
|   |   |   |-- chats.html
|   |   |   |-- notifications.html
|   |   |   |-- availability_manage.html
|   |   |   |-- my_certificates.html
|   |   |   |-- issued_certificates.html
|   |   |
|   |   |-- components/        (3 reusable components)
|   |   |   |-- header.html
|   |   |   |-- footer.html
|   |   |   |-- askvera_widget.html
|   |   |
|   |   |-- emails/            (10 email templates)
|   |   |   |-- welcome.html
|   |   |   |-- booking_confirmation.html
|   |   |   |-- booking_rejection.html
|   |   |   |-- order_placed_customer.html
|   |   |   |-- order_placed_provider.html
|   |   |   |-- order_accepted_customer.html
|   |   |   |-- order_accepted_provider.html
|   |   |   |-- order_completed_customer.html
|   |   |   |-- order_completed_provider.html
|   |   |   |-- order_rejected_customer.html
|   |   |
|   |   |-- legal/
|   |   |   |-- terms.html
|   |   |   |-- privacy.html
|   |   |
|   |   |-- errors/
|   |       |-- 404.html
|   |       |-- 500.html
|   |
|   |-- static/
|       |-- css/
|       |   |-- custom.css
|       |   |-- modern_dashboard.css
|       |   |-- dashboard_fix.css
|       |   |-- askvera.css
|       |
|       |-- js/
|       |   |-- main.js
|       |   |-- askvera.js
|       |
|       |-- images/
|       |-- fonts/
|       |-- avatars/
|       |-- certificates/
|       |-- portfolio/
|       |-- uploads/
|
|-- DATABASE/
|   |-- instance/
|   |-- transactions.txt
|   |-- wallets.txt
|
|-- DOCUMENTATION/
|   |-- PRESENTATION_GUIDE.md
|   |-- SkillVerse_ER_Diagram.png
|   |-- SkillVerse_ER_Diagram_Final.html
|   |-- learnproject.html
|   |-- skillverse_certificate_verified.png
|
|-- INVOICES_BACKUP/
```

---

## Database Tables (14 Tables - PostgreSQL)

| Table | Purpose |
|---|---|
| users | All users - admin, client, provider |
| categories | Service categories (Web Dev, Design, etc.) |
| services | Services listed by providers |
| orders | Orders placed by clients |
| reviews | Ratings after order completion |
| favorites | Services saved by users |
| notifications | In-app notifications |
| messages | Chat messages between users |
| availability_slots | Provider availability schedule |
| bookings | Booked time slots |
| transactions | Wallet transaction history |
| certificates | Completion certificates |
| testimonials | Homepage testimonials |
| contact_messages | Contact form submissions |

---

## Where Flask is Used

| File | Flask Usage |
|---|---|
| `app.py` | `Flask()` creates the app, blueprints registered, error handlers |
| `extensions.py` | Flask-Login, Flask-SocketIO, Flask-Mail, OAuth initialized |
| `config.py` | Database URL, secret key, mail config |
| `routes.py` | `@Blueprint`, `render_template()`, `redirect()`, `flash()`, `jsonify()` |
| `models.py` | Flask-SQLAlchemy ORM - all 14 DB models |
| `events.py` | Flask-SocketIO real-time events |
| `routes_chat.py` | `/chat/ask` - Groq AI API integration |

**Blueprints registered in app.py:**
- `main_bp` → `/` (homepage, about, contact)
- `auth_bp` → `/auth/` (login, register, Google OAuth)
- `service_bp` → `/service/` (create, edit, delete services)
- `user_bp` → `/user/` (dashboard, orders, wallet, chat)
- `admin_bp` → `/admin/` (admin panel)
- `api_bp` → `/api/` (JSON API for AJAX calls)
- `availability_bp` → `/availability/` (slot management)
- `chat_bp` → `/chat/` (AskVera chatbot)

---

## Request Flow

```
Browser → http://localhost:5000
       ↓
   run.py  →  sets sys.path, changes to BACKEND/core/
       ↓
   app.py  →  loads .env, connects DB, registers blueprints
       ↓
  routes.py →  matches URL, checks login, queries DB
       ↓
  models.py →  SQLAlchemy fetches data from PostgreSQL
       ↓
render_template() → loads HTML from FRONTEND/templates/
       ↓
  Browser  →  receives HTML + CSS + JS
```

---

## Available URLs

| URL | Page | Access |
|---|---|---|
| / | Homepage | Everyone |
| /auth/login | Login | Guest |
| /auth/register | Register | Guest |
| /services | Browse Services | Everyone |
| /user/dashboard | User Dashboard | Logged in |
| /user/wallet | Wallet & Payments | Logged in |
| /user/orders | My Orders | Logged in |
| /user/chats | Real-time Chat | Logged in |
| /admin/dashboard | Admin Panel | Admin only |
| /admin/pending_services | Approve Services | Admin only |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3 + Flask 3.0 |
| Database | PostgreSQL + SQLAlchemy ORM |
| Authentication | Flask-Login + Google OAuth (Authlib) |
| Real-time | Flask-SocketIO |
| Email | Flask-Mail + Gmail SMTP |
| AI Chatbot | Groq API - AskVera |
| PDF | ReportLab (certificates) |
| Frontend | Bootstrap 5 + Jinja2 |
| Compression | Flask-Compress |

---

*SkillVerse - LJ University Final Year Project*

# sem3-group-project
