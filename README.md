# CampusFix: Campus IT & Facility Issue Management System

Students report campus problems (Wi-Fi, projectors, lab computers, AC/fans/lights, printers,
classroom equipment, basic maintenance). Staff fix them. Admins oversee everything.

| Part | Technology |
|---|---|
| Frontend | Plain HTML, CSS, vanilla JavaScript (no framework, no build step) |
| Backend | Python 3 + FastAPI, run with uvicorn |
| Database | PostgreSQL, psycopg 3, plain SQL (no ORM) |
| Validation | Pydantic models for every request and response |
| Login | JWT (python-jose) + bcrypt password hashing (passlib) |
| Access control | RBAC with 3 roles: `student`, `staff`, `admin` |
| Background jobs | APScheduler (SLA escalation every 15 minutes) |
| Tests | pytest |

---

## Quick start (Windows)

1. Install **Python 3.11+** and **PostgreSQL 15+** (see Setup, Step 1 below).
2. Open `backend/.env` and set `DB_PASSWORD` to your PostgreSQL password.
3. **First time only:** create the database, tables and sample data:
   ```powershell
   cd backend
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt
   venv\Scripts\python setup_database.py
   ```
   `setup_database.py` does not need `psql`. Running it again **resets all data**.
4. **Every time:** double-click **`start.bat`**. It starts the backend and opens
   <http://localhost:8000/app/pages/login.html>.

The backend serves the frontend too, so only one server has to run.
API docs: <http://localhost:8000/docs>.

---

## 1. Folder structure

```
campusfix/
  frontend/
    index.html                 redirects to pages/login.html
    pages/                     login, register, student/staff/admin dashboards, complaint details
    css/style.css              dark blue + cyan theme, responsive
    js/
      api.js                   apiRequest(): every fetch() call, adds the Authorization header
      auth.js                  token in localStorage, login/logout, requireLogin()
      ui.js                    shared helpers: badges, dates, header, notifications, complaint table
      login.js, register.js, student-dashboard.js, staff-dashboard.js,
      admin-dashboard.js, complaint-details.js     one file per page
  backend/
    app/
      main.py                  creates the app, adds CORS, includes routers, starts the scheduler
      config.py                reads settings from .env
      constants.py             roles, statuses, priorities, categories
      database.py              PostgreSQL connection helpers
      security/                password_hashing.py, jwt_tokens.py, role_checker.py
      schemas/                 Pydantic models (user, complaint, notification, dashboard)
      routes/                  auth, complaint, user, notification, dashboard routes
      services/                business logic (complaint, classification, priority,
                               similarity, sla, notification, user, auth, history, dashboard)
      jobs/sla_escalation_job.py
    tests/                     pytest tests
    requirements.txt
    .env.example
  database/
    schema.sql                 tables, foreign keys, CHECK constraints, indexes
    seed.sql                   sample users + 11 complaints
  CampusFix_Concepts_Report.docx   every concept explained in simple language
  README.md
```

**Routes vs services:** a route only reads the request, calls one service function and returns
the result. All rules (who may do what, status flow, priority, SLA) live in `services/`.

---

## 2. Setup (step by step)

### Step 1: Install Python and PostgreSQL

1. **Python 3.11 or newer**: <https://www.python.org/downloads/>. On Windows, tick
   **"Add Python to PATH"** during installation. Check it with `python --version`.
2. **PostgreSQL 15 or newer**: <https://www.postgresql.org/download/>. Remember the password
   you choose for the `postgres` user. The installer also installs **pgAdmin** and **psql**.
   On Windows, add `C:\Program Files\PostgreSQL\<version>\bin` to PATH so `psql` works in a terminal.

### Step 2: Create the database

```bash
psql -U postgres -c "CREATE DATABASE campusfix;"
```

(Or in pgAdmin: right-click **Databases**, then **Create**, then **Database...**, and name it `campusfix`.)

### Step 3: Create the tables and add sample data

From the `campusfix` folder:

```bash
psql -U postgres -d campusfix -f database/schema.sql
psql -U postgres -d campusfix -f database/seed.sql
```

(pgAdmin: open the **Query Tool** on the `campusfix` database, open each file and press **Execute**,
`schema.sql` first.)

> Running `schema.sql` again **deletes all data** and recreates empty tables. Running `seed.sql`
> again resets the sample data.

### Step 4: Create a virtual environment and install packages

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Step 5: Configure `.env`

A ready `.env` file is already included. Open `backend/.env` and set `DB_PASSWORD` to your
PostgreSQL password. If `.env` is missing, copy `.env.example` to `.env` first.

| Setting | Meaning |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL connection |
| `JWT_SECRET_KEY` | Secret used to sign tokens. Make a new one with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | How long a login lasts (default 60) |
| `ENABLE_SCHEDULER` | `true` to run the SLA job in the background |
| `SLA_CHECK_INTERVAL_MINUTES` | How often the SLA job runs (default 15) |
| `CORS_ALLOWED_ORIGINS` | `*` or a list such as `http://localhost:5500` |

### Step 6: Start the backend

From the `backend` folder, with the virtual environment active:

```bash
uvicorn app.main:app --reload
```

Open <http://localhost:8000>. It should say *"CampusFix API is running"*.

### Step 7: Open the frontend

Either:

- **Simplest:** double-click `frontend/index.html` (or `frontend/pages/login.html`), **or**
- **Recommended:** serve it from a second terminal:
  ```bash
  cd frontend
  python -m http.server 5500
  ```
  then open <http://localhost:5500/pages/login.html>.

The frontend calls the API at `http://localhost:8000/api` (set in `frontend/js/api.js`).

---

## 3. Test login accounts (from `seed.sql`)

| Role | Email | Password | Team |
|---|---|---|---|
| Admin | `admin@campusfix.edu` | `Admin@123` | |
| Staff | `it.staff@campusfix.edu` | `Staff@123` | IT |
| Staff | `maint.staff@campusfix.edu` | `Staff@123` | Maintenance |
| Student | `student1@campusfix.edu` | `Student@123` | |
| Student | `student2@campusfix.edu` | `Student@123` | |
| Student | `student3@campusfix.edu` | `Student@123` | |

The login page has links that fill these in for you.

**Demo scenarios in the seed data**

- Complaints #1 and #2: same category and location (Lab 3), so both are marked *Possible Common Incident*.
- Complaint #4 is past its SLA with no reminder. The next SLA check **sends a reminder**.
- Complaint #11 is past its SLA and was already reminded. The next SLA check **escalates** it.
- Complaint #5 (student2) is *Resolved*. Log in as student2 to **confirm** or **reopen** it.
- Complaint #9 (student3) is *Need More Info*. Log in as student3 to **reply**.
- Complaint #8 is already *Escalated*.

As admin, click **"Run SLA check now"** to see the reminder and escalation happen immediately.

---

## 4. How it works

### Complaint flow

```
Student submits ──► auto category ──► similar check ──► suggested priority ──► team ──► Open
                                                                                        │
            ┌──────────────── staff: "Need More Info" ◄─────────────────────────────────┤
            │  student replies ──► In Progress                                          ▼
            │                                                                   In Progress
            │                                                                        │
            │   SLA job (every 15 min): overdue ─► reminder ─► still overdue ─► Escalated
            │                                                                        ▼
            └─────────────────────────────────────────────────────────────────►  Resolved
                                                                           ┌─────────┴─────────┐
                                                                student confirms     student reopens
                                                                       Closed             Open
```

Allowed staff status changes:

| From | Staff may move to |
|---|---|
| Open | In Progress, Need More Info |
| In Progress | Resolved, Need More Info |
| Need More Info | In Progress |
| Escalated | In Progress, Resolved, Need More Info |
| Resolved / Closed | *(only the student acts: confirm or reopen)* |

Every change is saved in `complaint_history` (who, what, when) and creates an in-app notification.

### Keyword classification (`classification_service.py`)

The title and description are searched for whole-word keywords. The category with the most matches wins.

| Category | Example keywords | Team |
|---|---|---|
| Network/Wi-Fi | wifi, wi-fi, internet, network, lan, router | IT |
| Projector | projector, hdmi, vga | IT |
| Lab Computer | computer, pc, desktop, monitor, keyboard, mouse | IT |
| Printer | printer, print, toner, scanner | IT |
| Classroom Equipment | smart board, speaker, microphone | IT |
| Electrical | ac, fan, light, bulb, socket, power | Maintenance |
| General Maintenance | door, window, chair, leak, water, toilet | Maintenance |
| Other | *(nothing matched)* | Maintenance |

### Priority rules (`priority_service.py`)

Points are added up:

| Rule | Points |
|---|---|
| Category: Wi-Fi, Lab Computer, Electrical, Projector | 2 |
| Category: Printer, Classroom Equipment, General Maintenance, Other | 1 |
| 1-2 similar open complaints / 3 or more | +1 / +2 |
| "urgent", "emergency", "asap", "immediately" | +2 |
| "exam", "examination", "viva", "practical" | +2 |
| "lab", "laboratory" (also in the location) | +1 |

**0-1 = Low, 2-3 = Medium, 4-5 = High, 6+ = Critical.** Safety words (fire, smoke, spark,
shock, short circuit, flood...) always give **Critical**. Staff can override the priority.

Example: *"Wi-Fi not working in Lab 3"* scores 2 (Wi-Fi) + 1 (lab) = 3, so **Medium**.
Add *"exam tomorrow, urgent"* and it scores 7, so **Critical**.

### Similarity detection (`similarity_service.py`)

A new complaint is compared with **open** complaints (not Resolved or Closed) with the **same
category** and the **same location** (case and extra spaces ignored). Matches are all flagged
*Possible Common Incident*. Staff check them on the details page and click **"Group under #X"**
to confirm, which sets `incident_group_id`.

### SLA escalation (`sla_service.py` + `jobs/sla_escalation_job.py`)

| Priority | Time limit |
|---|---|
| Critical | 4 hours |
| High | 24 hours |
| Medium | 48 hours |
| Low | 72 hours |

APScheduler runs `check_sla_and_escalate()` every 15 minutes for complaints that are *Open* or
*In Progress*:

1. Past the deadline with no reminder yet: **send a reminder** to the team.
2. Still past the deadline after the reminder: set status to **Escalated**, notify admins,
   the team and the student.

Overriding the priority recalculates the deadline from the creation time. Reopening gives a
fresh deadline.

---

## 5. Testing the API with Swagger UI (`/docs`)

FastAPI creates an interactive API page automatically.

1. Start the backend and open <http://localhost:8000/docs>.
2. Open **POST /api/auth/login**, click **Try it out**, enter:
   ```json
   { "email": "student1@campusfix.edu", "password": "Student@123" }
   ```
   then click **Execute**.
3. Copy the `access_token` value from the response (without quotes).
4. Click the green **Authorize** button at the top, paste the token, click **Authorize**, then **Close**.
5. Every request now sends `Authorization: Bearer <token>`. Try **GET /api/complaints/my**.
6. To test RBAC, while logged in as the student, try **GET /api/complaints/assigned**. You
   get **403 Forbidden**. Log in as `it.staff@campusfix.edu`, re-authorize with the new token,
   and the same call works.
7. To switch user, click **Authorize**, then **Logout**, and paste another token.

The other documentation page is at <http://localhost:8000/redoc>.

### Error codes used

| Code | Meaning |
|---|---|
| 400 | Bad request: e.g. invalid status change, email already registered |
| 401 | Not logged in, wrong password, or invalid/expired token |
| 403 | Logged in, but your role is not allowed to do this |
| 404 | Complaint / user / notification not found |
| 422 | Pydantic validation failed (missing field, too short, wrong value) |

---

## 6. API endpoints

All URLs start with `http://localhost:8000`. **Auth** means the `Authorization: Bearer <token>` header.

### Authentication

| Method | URL | Role | Description |
|---|---|---|---|
| POST | `/api/auth/register` | public | Create a student account |
| POST | `/api/auth/login` | public | Log in, get a JWT |
| GET | `/api/auth/me` | any logged in | My profile |

**POST /api/auth/register**
```json
// request
{ "full_name": "Riya Sharma", "email": "riya@campusfix.edu", "password": "Student@123" }
// response 201
{ "id": 7, "full_name": "Riya Sharma", "email": "riya@campusfix.edu", "role": "student",
  "team": null, "is_active": true, "created_at": "2026-03-12T10:15:00Z" }
```

**POST /api/auth/login**
```json
// request
{ "email": "student1@campusfix.edu", "password": "Student@123" }
// response 200
{ "access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer",
  "user": { "id": 4, "full_name": "Priya Sharma", "email": "student1@campusfix.edu",
            "role": "student", "team": null, "is_active": true, "created_at": "..." } }
// wrong password: 401 {"detail": "Incorrect email or password."}
```

### Complaints

| Method | URL | Role | Description |
|---|---|---|---|
| POST | `/api/complaints` | student | Create a complaint (auto category, priority, team, similarity) |
| GET | `/api/complaints/my` | student | Only my complaints |
| GET | `/api/complaints/assigned?status=&priority=&category=` | staff, admin | My team's complaints (admin: all) |
| GET | `/api/complaints?status=&priority=&category=&team=` | admin | All complaints |
| GET | `/api/complaints/escalated` | admin | Escalated complaints |
| GET | `/api/complaints/{id}` | any (own / team / all) | One complaint |
| GET | `/api/complaints/{id}/history` | any (own / team / all) | Status timeline |
| GET | `/api/complaints/{id}/comments` | any (own / team / all) | Messages (students don't see internal notes) |
| PATCH | `/api/complaints/{id}/status` | staff, admin | Change status |
| PATCH | `/api/complaints/{id}/priority` | staff, admin | Override priority |
| POST | `/api/complaints/{id}/request-info` | staff, admin | Ask the student a question (Need More Info) |
| POST | `/api/complaints/{id}/notes` | staff, admin | Internal staff note |
| GET | `/api/complaints/{id}/similar` | staff, admin | Similar open complaints |
| POST | `/api/complaints/{id}/group` | staff, admin | Confirm a common incident |
| POST | `/api/complaints/{id}/reply` | student (owner) | Reply to an info request (back to In Progress) |
| POST | `/api/complaints/{id}/confirm` | student (owner) | Resolved to Closed |
| POST | `/api/complaints/{id}/reopen` | student (owner) | Resolved to Open |

**POST /api/complaints** (student)
```json
// request
{ "title": "Wi-Fi not working in Lab 3",
  "description": "Wi-Fi keeps disconnecting. We have a lab exam tomorrow, urgent.",
  "location": "Lab 3" }
// response 201
{ "complaint": { "id": 12, "title": "Wi-Fi not working in Lab 3", "location": "Lab 3",
                 "category": "Network/Wi-Fi", "priority": "Critical", "suggested_priority": "Critical",
                 "status": "Open", "assigned_team": "IT", "student_id": 4, "student_name": "Priya Sharma",
                 "is_possible_common_incident": true, "incident_group_id": null,
                 "sla_due_at": "2026-03-12T14:15:00Z", "created_at": "2026-03-12T10:15:00Z", "...": "..." },
  "similar_open_complaints_count": 2,
  "message": "Complaint submitted and assigned to the IT team. 2 similar open complaint(s) found - marked as a Possible Common Incident." }
```

**PATCH /api/complaints/3/status** (staff)
```json
// request
{ "new_status": "In Progress", "note": "Technician on the way" }
// response 200: the updated complaint
// invalid jump, e.g. Open to Resolved: 400
{ "detail": "Cannot change status from 'Open' to 'Resolved'. Allowed: In Progress, Need More Info." }
```

**PATCH /api/complaints/3/priority** (staff)
```json
{ "priority": "High", "reason": "Exam hall projector" }
```

**POST /api/complaints/3/request-info** (staff), **/notes** (staff), **/reply** (student)
```json
{ "message": "Which computer number is affected?" }
```

**POST /api/complaints/5/reopen** (student)
```json
{ "reason": "The printer is jamming again" }
```

**POST /api/complaints/2/group** (staff)
```json
{ "parent_complaint_id": 1 }
```

**GET /api/complaints/{id}/history** response
```json
[ { "id": 1, "complaint_id": 1, "changed_by": 4, "changed_by_name": "Priya Sharma",
    "action": "created", "old_value": null, "new_value": "Open",
    "note": "Category: Network/Wi-Fi. Suggested priority: Medium. Assigned to IT team.",
    "created_at": "..." } ]
```

### Users (admin)

| Method | URL | Role | Description |
|---|---|---|---|
| GET | `/api/users` | admin | List users |
| POST | `/api/users` | admin | Create a user with any role |
| PATCH | `/api/users/{id}/role` | admin | Change role/team |
| PATCH | `/api/users/{id}/active` | admin | Activate / deactivate |

```json
// POST /api/users
{ "full_name": "Kiran Das", "email": "kiran@campusfix.edu", "password": "Staff@123",
  "role": "staff", "team": "IT" }
// PATCH /api/users/6/role
{ "role": "staff", "team": "Maintenance" }
// PATCH /api/users/6/active
{ "is_active": false }
```
Staff without a team gets `400`. An admin cannot change or deactivate their own account (`400`).

### Notifications

| Method | URL | Role | Description |
|---|---|---|---|
| GET | `/api/notifications` | any logged in | My 50 newest notifications |
| PATCH | `/api/notifications/{id}/read` | any logged in | Mark one as read |
| PATCH | `/api/notifications/read-all` | any logged in | Mark all as read |

```json
// GET /api/notifications
[ { "id": 5, "user_id": 5, "complaint_id": 2, "message": "Your complaint #2 is now 'In Progress'.",
    "is_read": false, "created_at": "..." } ]
```

### Admin dashboard

| Method | URL | Role | Description |
|---|---|---|---|
| GET | `/api/dashboard/stats` | admin | Numbers for the dashboard |
| POST | `/api/dashboard/run-sla-check` | admin | Run the SLA job immediately |

```json
// GET /api/dashboard/stats
{ "total_complaints": 11, "open_complaints": 9, "escalated_complaints": 1,
  "resolved_or_closed_complaints": 2, "total_users": 6, "average_resolution_hours": 24.0,
  "complaints_by_status": { "Open": 5, "In Progress": 2, "...": 0 },
  "complaints_by_priority": { "High": 3, "...": 0 },
  "complaints_by_category": { "Electrical": 4, "...": 0 },
  "complaints_by_team": { "IT": 6, "Maintenance": 5 } }
// POST /api/dashboard/run-sla-check
{ "complaints_checked": 2, "reminders_sent": 1, "complaints_escalated": 1 }
```

### Health

| Method | URL | Role |
|---|---|---|
| GET | `/` | public |

---

## 7. Running the tests

The tests **do not need PostgreSQL**. Where code would read the database, the test replaces that
function with a fake one (pytest `monkeypatch`).

```bash
cd backend
venv\Scripts\activate        # or: source venv/bin/activate
pytest -v
```

| File | What it checks |
|---|---|
| `tests/test_login.py` | bcrypt hashing, JWT create/decode, login success (no password hash in the response), wrong password returns 401, bad email returns 422 |
| `tests/test_rbac.py` | no token returns 401, fake token returns 401, student on staff/admin routes returns 403, staff on admin route returns 403, staff/admin allowed, students only see their own complaints |
| `tests/test_classification.py` | keyword categories, whole-word matching, team assignment |
| `tests/test_priority.py` | each priority rule and the point limits |
| `tests/test_sla_escalation.py` | SLA hours, reminder-then-escalate decision, the job loop, staff status-flow rules |

---

## 8. Security summary

- Passwords are stored only as **bcrypt hashes**. No API response includes `password_hash`.
- Every protected route uses `Depends(get_current_user)` or `Depends(require_roles(...))`.
  Hiding buttons in the frontend is only for convenience. The **backend** is what blocks access.
- The user is re-loaded from the database on every request, so a deactivated account or a
  changed role takes effect immediately.
- All SQL uses `%s` placeholders (parameterized queries), so it is safe from SQL injection.
- All input is validated by Pydantic (lengths, email format, allowed values).
- The frontend escapes all user text before inserting it into the page (prevents XSS).
- Keep `.env` private. It contains the JWT secret and the database password.

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `psql` is not recognized | Add PostgreSQL's `bin` folder to PATH, or use pgAdmin's Query Tool |
| `password authentication failed for user "postgres"` | Set the correct `DB_PASSWORD` in `backend/.env` |
| `database "campusfix" does not exist` | Do Step 2 |
| `relation "users" does not exist` | Run `schema.sql` (Step 3) |
| Frontend says "Cannot reach the server" | Start uvicorn, and check `API_BASE_URL` in `frontend/js/api.js` |
| Logged out unexpectedly | The token expired (default 60 minutes). Log in again |
| `ModuleNotFoundError: app` | Run uvicorn/pytest from inside the `backend` folder |

---

## 10. Future ideas (not built)

- Replace keyword classification with NLP / Sentence Transformers
- Use pgvector for meaning-based similarity search
- RAG-based campus AI assistant
- Mobile / PWA app
- Docker deployment
