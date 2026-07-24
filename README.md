# Employee Directory - Installation Guide

A production-ready Employee Directory Web Application built with Django 5+, custom CSS, and vanilla JavaScript.

## Requirements

- Python 3.12+ (3.13+ recommended)
- pip / virtualenv

> **Database:** Local development uses **SQLite** by default — no database setup required. PostgreSQL can be enabled later for production (see [DEPLOYMENT.md](DEPLOYMENT.md)).

## Quick Start

### 1. Clone and Set Up Virtual Environment

```bash
cd Directory
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Environment (Optional)

Copy the environment file if you want to customize settings:

```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS/Linux
```

No database configuration is needed — the app uses SQLite (`db.sqlite3`) automatically.

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Seed Sample Data

```bash
python manage.py seed_data
python manage.py seed_advanced
python manage.py seed_phase2
```

This creates:
- **Super Admin:** `admin` / `Admin@12345`
- **HR Manager:** `hr_manager` / `Hr@12345`
- Sample departments, positions, and employees
- Skills, leave types, timeline events, recognition awards
- Job openings, hiring pipeline candidates, performance reviews & goals

### 5. Run Development Server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) and log in.

## Project Structure

```
Directory/
├── config/                 # Project settings & URLs
├── accounts/               # Authentication, roles, user management
├── employees/              # Employee CRUD, directory, exports
├── departments/            # Department management
├── positions/              # Position management
├── dashboard/              # Dashboard, stats, charts
├── notifications/          # In-app notification center
├── attendance/             # Attendance & leave management
├── chat/                   # AI directory chat assistant
├── portal/                 # Employee self-service portal
├── recruitment/            # Job openings, hiring pipeline, onboarding
├── performance/            # Performance reviews & employee goals
├── api/                    # REST API with JWT
├── templates/              # HTML templates
├── static/                 # CSS & JavaScript
├── media/                  # Uploaded files
├── requirements.txt
├── DATABASE_SCHEMA.md
└── DEPLOYMENT.md
```

## User Roles

| Role | Permissions |
|------|-------------|
| Super Admin | Full access: users, employees, departments, positions |
| HR Manager | Manage employees, departments, positions |
| Employee | View directory, own profile |

## Portfolio Feature Map

This project is structured as a **portfolio-quality HR platform**. The full enterprise wishlist is large; these **10 priorities** are the core showcase:

| Priority | Feature | Status | Route |
|----------|---------|--------|-------|
| 1 | Employee Directory | ✅ Full | `/employees/` |
| 2 | Org Chart | ✅ Full | `/employees/org-chart/` |
| 3 | Employee Profiles | ✅ Full | `/employees/<id>/`, `/portal/profile/` |
| 4 | Leave Management | ✅ Enhanced | `/attendance/leave/` |
| 5 | Attendance | ✅ Partial | `/attendance/` |
| 6 | Announcements | ✅ Partial | `/employees/announcements/` |
| 7 | Notifications | ✅ New | `/notifications/` |
| 8 | Audit Logs | ✅ New | `/employees/audit-log/` |
| 9 | Reporting Dashboard | ✅ Enhanced | `/` |
| 10 | AI HR Assistant | ✅ Partial | `/chat/`, `/employees/ai-search/` |

### Employee Portal (New)

| Feature | Route |
|---------|-------|
| Self-Service Hub | `/portal/` |
| Personal Info Portal | `/portal/profile/` |
| Documents & Resume/CV | `/portal/documents/` |
| Manager Dashboard | `/portal/manager/` |
| Recognition Wall | `/employees/recognition/` |

### Phase 2 — HR Modules (New)

| Feature | Route |
|---------|-------|
| Job Openings | `/recruitment/` |
| Hiring Pipeline (Kanban) | `/recruitment/pipeline/` |
| Application Detail | `/recruitment/applications/<id>/` |
| Performance Dashboard | `/performance/` |
| Performance Reviews | `/performance/reviews/create/` |
| Employee Goals | `/performance/goals/` |

### Recently Added

- **Employee Self-Service Portal** — Profile, documents, leave balances, ID card access
- **Document Management** — Resume/CV, contracts, certificates with secure download
- **Career Timeline** — Promotions, transfers, hires on employee profiles
- **Recognition & Awards** — Company recognition wall + per-employee awards
- **Social Links** — LinkedIn, GitHub, Twitter, website on profiles
- **Leave Balance Tracking** — Entitlement vs used days per leave type
- **Manager Dashboard** — Team roster, pending leave, attendance snapshot

## Features

- Login / Logout / Password Reset / Change Password
- Admin-controlled user registration
- Employee CRUD with profile photos
- Department & Position management
- Employee directory with AJAX search, filters, sorting, pagination
- Card and table views
- Dashboard with canvas charts
- Dark / Light mode
- Export to Excel and PDF
- Print directory view
- Employee QR codes
- Activity audit logs + **global audit log browser**
- **In-app notification center** (leave, announcements)
- Company announcements
- Birthday & work anniversary notifications
- User profile avatars with image upload
- Employee profile completion tracking
- Work location (Office / Remote / Hybrid) & availability status

### Advanced Modules

- **Org Chart** — Interactive SVG organizational hierarchy
- **Team Hierarchy** — Department-based team visualization
- **AI Employee Search** — Natural language employee queries
- **Skills Matrix** — Employee proficiency grid by skill
- **Directory Chat** — AI assistant for employee lookups
- **ID Card Generator** — PDF employee ID cards with QR code
- **Attendance & Leave** — Check-in/out, leave requests, HR approval workflow, **leave balances**
- **Employee Portal** — Self-service profile, documents, digital ID card
- **Document Management** — Resume, contracts, certificates (upload & secure download)
- **Career Timeline** — Promotions, transfers, awards on employee record
- **Recognition Wall** — Company-wide employee awards
- **Manager Dashboard** — Team overview for line managers
- **Recruitment** — Job postings, candidate applications, hiring pipeline kanban
- **Interviews & Onboarding** — Schedule interviews, auto onboarding checklist on hire
- **Performance Management** — Reviews (1–5 rating), employee goals with progress tracking

## REST API

Base URL: `/api/`

### Authentication

```bash
# Obtain JWT token
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin@12345"}'

# Use token
curl http://localhost:8000/api/employees/ \
  -H "Authorization: Bearer <access_token>"
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/token/` | Obtain JWT access token |
| POST | `/api/token/refresh/` | Refresh JWT token |
| GET/POST | `/api/employees/` | List / Create employees |
| GET/PUT/PATCH/DELETE | `/api/employees/{id}/` | Employee detail |
| POST | `/api/employees/{id}/toggle_active/` | Toggle employee status |
| GET/POST | `/api/departments/` | List / Create departments |
| GET/PUT/PATCH/DELETE | `/api/departments/{id}/` | Department detail |
| GET/POST | `/api/positions/` | List / Create positions |
| GET/PUT/PATCH/DELETE | `/api/positions/{id}/` | Position detail |

## Management Commands

```bash
python manage.py seed_data          # Seed sample data
python manage.py seed_advanced      # Skills, leave types, timeline, recognition
python manage.py seed_phase2        # Recruitment pipeline & performance data
python manage.py createsuperuser    # Create admin manually
python manage.py collectstatic      # Collect static files (production)
```

## Database Schema

See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for the complete schema documentation.

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment instructions.

## Security Notes

- Change default passwords immediately
- Set a strong `SECRET_KEY` in production
- Set `DEBUG=False` in production
- Configure HTTPS and secure cookies
- Restrict `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`
