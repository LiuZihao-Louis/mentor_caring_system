# Mentor Caring System

A complete runnable Flask project for **Design and Implementation of a Mentor Caring System**.

The system follows a layered architecture:

- domain/entity dataclasses in `mentor_caring/models.py`
- in-memory repositories in `mentor_caring/repositories.py`
- service/control classes in `mentor_caring/services/`
- Flask JSON APIs in `mentor_caring/routes/api.py`
- Flask Jinja2 frontend pages in `mentor_caring/routes/frontend.py` and `mentor_caring/templates/`
- pytest tests in `tests/`

No external database, Redis, Docker, or cloud service is required.

## Folder Structure

```text
mentor_caring_system/
├── app.py
├── requirements.txt
├── README.md
├── exports/
├── mentor_caring/
│   ├── __init__.py
│   ├── app.py
│   ├── exceptions.py
│   ├── models.py
│   ├── repositories.py
│   ├── seed.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   └── frontend.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── admin_service.py
│   │   ├── appointment_service.py
│   │   ├── auth_service.py
│   │   ├── base.py
│   │   ├── coordinator_service.py
│   │   ├── excel_utils.py
│   │   ├── faculty_consultant_service.py
│   │   ├── mentor_service.py
│   │   ├── message_service.py
│   │   ├── student_service.py
│   │   ├── supporting_staff_service.py
│   │   └── utils.py
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/main.js
│   └── templates/
│       ├── _table.html
│       ├── appointments.html
│       ├── base.html
│       ├── dashboard_admin.html
│       ├── dashboard_coordinator.html
│       ├── dashboard_faculty_consultant.html
│       ├── dashboard_mentor.html
│       ├── dashboard_student.html
│       ├── dashboard_supporting_staff.html
│       ├── export.html
│       ├── feedback.html
│       ├── login.html
│       ├── logs.html
│       ├── messages.html
│       └── records.html
└── tests/
    ├── conftest.py
    ├── test_api_frontend.py
    ├── test_services.py
    └── test_student_service.py
```

## Installation

```bash
cd mentor_caring_system
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Run Tests

```bash
pytest -q
```

If your local Python environment loads many third-party pytest plugins and the command hangs, run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
```

On Windows PowerShell:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
pytest -q
```

## Run Flask

```bash
flask --app mentor_caring.app:create_app run
```

or:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000/login
```

## Seed Accounts

| Role | Account | Password |
|---|---|---|
| Administrator | admin | admin123 |
| Faculty Consultant | alice | consultant123 |
| Mentor | mary | mentor123 |
| MCP Coordinator | ruth | coord123 |
| Supporting Staff | sam | staff123 |
| Student | 123456789 | student123 |

## Sample API Requests

Login:

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account":"123456789","password":"student123"}'
```

Get student mentor:

```bash
curl http://127.0.0.1:5000/api/students/123456789/mentor
```

Submit feedback:

```bash
curl -X POST http://127.0.0.1:5000/api/students/123456789/feedback \
  -H "Content-Type: application/json" \
  -d '{"content":"The mentor caring system is helpful."}'
```

Create interview record:

```bash
curl -X POST http://127.0.0.1:5000/api/mentors/MTR001/records \
  -H "Content-Type: application/json" \
  -d '{"student_id":"123456789","date":"2026-05-01","time":"10:00","problem_statement":"Study difficulty","interview_summary":"Discussed study plan","follow_up_action":"Check progress next month"}'
```

## Implemented Features

- Role-based login and dashboards
- Student mentor lookup
- Student feedback submission and feedback history
- Student message sending with 300-character boundary validation
- General message sending/responding with notification records
- Mentor student search with permission checks
- Interview record create/update/delete
- 30-minute appointment slot creation
- Student appointment booking
- Mentor appointment confirmation with venue
- Special case forwarding to coordinator/faculty consultant
- Faculty consultant organization import from dictionary rows or `.xlsx`
- Faculty consultant student/mentor allocation import from dictionary rows or `.xlsx`
- Group mentor changes without deleting previous records
- Student add/remove group while keeping student data
- Student/mentor/log search
- Supporting staff view logs and respond to feedback
- Administrator organization import and staff/consultant management
- Word export under `exports/`
- JSON error responses and HTTP status codes
- Unit tests and Flask `test_client` tests

## Notes

This project uses in-memory data. Restarting the server resets data to seed data.
