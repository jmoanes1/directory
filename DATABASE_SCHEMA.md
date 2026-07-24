# Database Schema

## Entity Relationship Overview

```
User (accounts_user)
  │
  ├── 1:1 ── Employee (employees_employee)
  │            ├── N:1 ── Department (departments_department)
  │            ├── N:1 ── Position (positions_position)
  │            └── N:1 ── Employee (self-referencing manager)
  │
  ├── 1:N ── ActivityLog (employees_activitylog)
  └── 1:N ── CompanyAnnouncement (employees_companyannouncement)

Department
  ├── 1:N ── Position
  ├── 1:N ── Employee
  └── N:1 ── Employee (department head)

Position
  └── 1:N ── Employee
```

## Tables

### accounts_user

Extended Django AbstractUser with role-based access.

| Column | Type | Constraints |
|--------|------|-------------|
| id | BigAutoField | PK |
| username | VARCHAR(150) | UNIQUE, NOT NULL |
| email | VARCHAR(254) | |
| password | VARCHAR(128) | NOT NULL |
| first_name | VARCHAR(150) | |
| last_name | VARCHAR(150) | |
| role | VARCHAR(20) | INDEX, choices: super_admin, hr_manager, employee |
| phone | VARCHAR(20) | |
| avatar | VARCHAR(100) | nullable, file path |
| is_registration_approved | BOOLEAN | default False |
| is_active | BOOLEAN | default True |
| is_staff | BOOLEAN | default False |
| is_superuser | BOOLEAN | default False |
| date_joined | TIMESTAMP | auto |
| created_at | TIMESTAMP | auto |
| updated_at | TIMESTAMP | auto |

**Indexes:** `(role, is_active)`, `(email)`

---

### departments_department

| Column | Type | Constraints |
|--------|------|-------------|
| id | BigAutoField | PK |
| name | VARCHAR(100) | UNIQUE, NOT NULL |
| code | VARCHAR(20) | UNIQUE |
| description | TEXT | |
| head_id | BIGINT | FK → employees_employee, SET NULL, nullable |
| is_active | BOOLEAN | INDEX, default True |
| created_at | TIMESTAMP | auto |
| updated_at | TIMESTAMP | auto |

**Indexes:** `(is_active, name)`

---

### positions_position

| Column | Type | Constraints |
|--------|------|-------------|
| id | BigAutoField | PK |
| title | VARCHAR(100) | NOT NULL |
| department_id | BIGINT | FK → departments_department, CASCADE |
| description | TEXT | |
| is_active | BOOLEAN | INDEX, default True |
| created_at | TIMESTAMP | auto |
| updated_at | TIMESTAMP | auto |

**Unique Together:** `(title, department_id)`
**Indexes:** `(department_id, is_active)`, `(title)`

---

### employees_employee

| Column | Type | Constraints |
|--------|------|-------------|
| id | BigAutoField | PK |
| employee_id | VARCHAR(20) | UNIQUE, auto-generated (EMP-000001) |
| user_id | BIGINT | FK → accounts_user, SET NULL, nullable, 1:1 |
| first_name | VARCHAR(100) | NOT NULL |
| middle_name | VARCHAR(100) | |
| last_name | VARCHAR(100) | NOT NULL |
| email | VARCHAR(254) | UNIQUE, INDEX |
| phone_number | VARCHAR(20) | |
| date_of_birth | DATE | nullable |
| gender | VARCHAR(20) | choices: male, female, other, prefer_not |
| address | TEXT | |
| date_hired | DATE | default today |
| department_id | BIGINT | FK → departments_department, PROTECT |
| position_id | BIGINT | FK → positions_position, PROTECT |
| manager_id | BIGINT | FK → self, SET NULL, nullable |
| employment_status | VARCHAR(20) | INDEX, choices: active, inactive, on_leave, terminated |
| profile_photo | VARCHAR(100) | nullable, validated extensions |
| emergency_contact | VARCHAR(200) | |
| bio | TEXT | |
| is_active | BOOLEAN | INDEX, default True |
| created_at | TIMESTAMP | auto |
| updated_at | TIMESTAMP | auto |

**Indexes:**
- `(last_name, first_name)`
- `(department_id, is_active)`
- `(position_id, is_active)`
- `(employment_status, is_active)`
- `(date_hired)`

**Validation:**
- Position must belong to selected department
- Employee cannot be their own manager

---

### employees_activitylog

| Column | Type | Constraints |
|--------|------|-------------|
| id | BigAutoField | PK |
| user_id | BIGINT | FK → accounts_user, SET NULL, nullable |
| action | VARCHAR(20) | INDEX, choices: create, update, delete, login, logout, view, export, activate, deactivate |
| model_name | VARCHAR(50) | |
| object_id | VARCHAR(50) | |
| object_repr | VARCHAR(200) | |
| description | TEXT | NOT NULL |
| ip_address | INET | nullable |
| user_agent | VARCHAR(500) | |
| created_at | TIMESTAMP | INDEX, auto |

**Indexes:** `(user_id, created_at)`, `(model_name, object_id)`

---

### employees_companyannouncement

| Column | Type | Constraints |
|--------|------|-------------|
| id | BigAutoField | PK |
| title | VARCHAR(200) | NOT NULL |
| content | TEXT | NOT NULL |
| created_by_id | BIGINT | FK → accounts_user, CASCADE |
| is_active | BOOLEAN | INDEX, default True |
| created_at | TIMESTAMP | auto |
| updated_at | TIMESTAMP | auto |

## Auto-Generated Employee ID

Format: `EMP-XXXXXX` (zero-padded 6 digits)

Generated sequentially on first save via `Employee._generate_employee_id()`.
