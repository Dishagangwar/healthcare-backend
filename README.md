# Healthcare Backend

A REST API for managing patient and doctor records, built with Django, Django REST
Framework and PostgreSQL, secured with JWT authentication.

Each user sees only the patient records they created. The doctor directory is shared
for reading, but only the user who added a doctor may change or remove that record.

---

## Stack

| Component | Version | Why |
|---|---|---|
| Django | 4.2 LTS | Supported on the installed Python 3.9; security fixes until April 2026 |
| Django REST Framework | 3.15.2 | Serializers, generic views, permissions |
| djangorestframework-simplejwt | 5.3.1 | JWT access/refresh tokens |
| PostgreSQL | 15 | Relational store, DB-level integrity constraints |
| psycopg2-binary | 2.9.9 | PostgreSQL driver |
| python-dotenv | 1.0.1 | Loads `.env` in development |
| django-filter | 24.3 | Query-string filtering on list endpoints |
| drf-spectacular | 0.30.0 | OpenAPI 3 schema and interactive docs, generated from the code |

---

## Project layout

```
hospital_management/
├── config/                 # Project settings, root URLconf, WSGI/ASGI
│   ├── settings.py         # All deployment values read from the environment
│   └── urls.py             # Mounts /api/auth, /api/patients, /api/doctors, /api/mappings
├── core/                   # Cross-cutting code shared by every app
│   ├── models.py           # TimeStampedModel abstract base
│   ├── mixins.py           # Uniform {"success": true, "data": ...} responses
│   ├── pagination.py       # Page-number pagination with bounded page_size
│   ├── permissions.py      # IsOwner object-level permission
│   ├── validators.py       # Shared phone-number format rule
│   ├── schema.py           # OpenAPI generation aware of the response envelopes
│   ├── fields.py           # PhoneNumberField: normalises before validating
│   └── exceptions.py       # Single error envelope for every failure
├── apps/
│   ├── accounts/           # Custom email-based User, register/login/refresh/profile
│   │   └── management/     # seed_demo: idempotent sample data
│   ├── patients/           # Patient model, serializer, views
│   ├── doctors/            # Doctor model, serializer, views
│   └── mappings/           # PatientDoctorMapping through-model
├── tests/                  # 82 API tests covering every endpoint
├── postman_collection.json # Importable request collection
├── .env.example            # Template for required environment variables
└── requirements.txt
```

Apps live under `apps/` and shared code under `core/` so that cross-cutting
concerns are written once; each app owns only its own domain.

---

## Setup

### 1. Prerequisites

- Python 3.9+
- PostgreSQL 13+ running locally

### 2. Install

```bash
cd hospital_management
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create the database

```bash
psql -d postgres -c "CREATE ROLE hospital_admin WITH LOGIN PASSWORD 'choose-a-password' CREATEDB;"
psql -d postgres -c "CREATE DATABASE hospital_management OWNER hospital_admin ENCODING 'UTF8';"
```

`CREATEDB` is needed only so the role can create the throwaway test database.

### 4. Configure the environment

```bash
cp .env.example .env
```

Fill in `.env`. Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

No secret is hard-coded: `config/settings.py` reads every sensitive value from the
environment and raises at startup if `DJANGO_SECRET_KEY`, `POSTGRES_DB` or
`POSTGRES_USER` is missing. `.env` is listed in `.gitignore` and never committed.

### 5. Migrate and run

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

The API is then at `http://127.0.0.1:8000/`.

### 6. Load demo data (optional)

```bash
python manage.py seed_demo
```

Creates a demo user with 4 patients, 5 doctors and 6 assignments so there is
something to look at. It is idempotent, so running it twice changes nothing.

### 7. Tests

```bash
python manage.py test tests
```

---

## Checking that it works

This is a JSON API, not a website, so there is no page to browse. There are four
ways to confirm it is working, in increasing order of effort.

**1. Interactive API docs** — the fastest way to see every endpoint and try it:

| URL | What it is |
|---|---|
| <http://127.0.0.1:8000/api/docs/> | Swagger UI — browse and execute requests |
| <http://127.0.0.1:8000/api/redoc/> | ReDoc — a cleaner read-only reference |
| <http://127.0.0.1:8000/api/schema/> | The raw OpenAPI 3 document (YAML) |

Log in through **Authorize**: call `POST /api/auth/login/` from the page, copy the
`access` token out of the response, and paste it in. Every secured endpoint is then
executable straight from the browser.

**2. Health check** — no authentication needed:

```bash
curl http://127.0.0.1:8000/health/
# {"success": true, "status": "healthy"}
```

**3. Django admin** — the quickest visual view of the data. Create a login, then open
<http://127.0.0.1:8000/admin/>:

```bash
python manage.py createsuperuser
```

Patients, doctors, mappings and users are all registered there with search and filters.

**4. The browsable API** — while `DJANGO_DEBUG=True`, session authentication is enabled
alongside JWT, so after logging in at `/admin/` you can click through the API itself in
a browser: <http://127.0.0.1:8000/api/patients/>. Each endpoint renders with its own
forms for `POST` and `PUT`. Production stays JWT-only, so the API has no cookie-based
authentication to protect against CSRF.

**5. Postman or curl** — the real test of the API. Import `postman_collection.json` and
run it top to bottom, or follow the curl walkthrough below.

To confirm nothing is broken without any of the above, run the test suite; it exercises
every endpoint against a real database:

```bash
python manage.py test tests
```

---

## Authentication

Obtain a token pair from `/api/auth/register/` or `/api/auth/login/`, then send the
access token on every subsequent request:

```
Authorization: Bearer <access_token>
```

Access tokens last 60 minutes and refresh tokens 7 days (both configurable in `.env`).
Refresh tokens rotate on use. Passwords are stored with Django's PBKDF2 hasher and are
never returned by any endpoint.

---

## Response format

Every response uses one of two shapes, so clients need only one parser.

**Success**

```json
{
  "success": true,
  "message": "Patient created successfully.",
  "data": { "id": 1, "full_name": "Asha Mehta" }
}
```

**Paginated list**

```json
{
  "success": true,
  "count": 42,
  "total_pages": 3,
  "current_page": 1,
  "next": "http://127.0.0.1:8000/api/patients/?page=2",
  "previous": null,
  "results": []
}
```

**Error**

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "phone: Enter a valid phone number.",
    "details": { "phone": ["Enter a valid phone number."] }
  }
}
```

`code` is a stable string to branch on, `message` is displayable as-is, and `details`
maps field names to their errors for attaching to form inputs.

---

## API reference

All endpoints require `Authorization: Bearer <token>` except register and login.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register with name, email, password; returns user + tokens |
| POST | `/api/auth/login/` | Log in; returns user + tokens |
| POST | `/api/auth/refresh/` | Exchange a refresh token for a new access token |
| GET | `/api/auth/profile/` | The authenticated user's own record |

**Register** — `POST /api/auth/register/`

```json
{
  "name": "Disha Gangwar",
  "email": "disha@example.com",
  "password": "StrongPass!234",
  "confirm_password": "StrongPass!234"
}
```

Returns `201` with the user and a token pair. Passwords run through Django's
validators (minimum 8 characters, not common, not all numeric, not similar to the
name or email).

**Login** — `POST /api/auth/login/`

```json
{ "email": "disha@example.com", "password": "StrongPass!234" }
```

A wrong password and an unregistered email return exactly the same error, so the
endpoint cannot be used to discover which emails have accounts.

### Patients

Scoped to the authenticated user: `GET /api/patients/` lists only their own records,
and another user's patient id returns `404`, not `403`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/patients/` | Add a patient |
| GET | `/api/patients/` | List the caller's patients |
| GET | `/api/patients/<id>/` | Retrieve one patient |
| PUT / PATCH | `/api/patients/<id>/` | Update a patient (`PATCH` for partial) |
| DELETE | `/api/patients/<id>/` | Delete a patient |

```json
{
  "full_name": "Asha Mehta",
  "date_of_birth": "1990-05-17",
  "gender": "FEMALE",
  "blood_group": "O+",
  "phone": "+919876543210",
  "email": "asha@example.com",
  "address": "12 Linking Road, Mumbai",
  "medical_history": "Mild asthma."
}
```

`gender`: `MALE`, `FEMALE`, `OTHER`, `UNDISCLOSED`.
`blood_group`: `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`, `UNKNOWN`.
`age` is computed from `date_of_birth` and returned read-only.

Phone numbers are normalised before validation, so `+91 98450-12345`,
`+91 (98450) 12345` and `+919845012345` are all accepted and stored as
`+919845012345`. A user cannot register two patients on the same number, though
two different users can each register the same one.

Query parameters: `?gender=`, `?blood_group=`, `?is_active=`, `?search=` (name, phone,
email), `?ordering=` (`created_at`, `full_name`, `date_of_birth`; prefix `-` to
reverse), `?page=`, `?page_size=`.

### Doctors

Readable by every authenticated user; writable only by the user who added the record.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/doctors/` | Add a doctor |
| GET | `/api/doctors/` | List all doctors |
| GET | `/api/doctors/<id>/` | Retrieve one doctor |
| PUT / PATCH | `/api/doctors/<id>/` | Update (creator only) |
| DELETE | `/api/doctors/<id>/` | Delete (creator only) |

```json
{
  "full_name": "Rohan Kapoor",
  "specialization": "CARDIOLOGY",
  "license_number": "MCI-10045",
  "email": "rohan.kapoor@example.com",
  "phone": "+919812345678",
  "years_of_experience": 12,
  "consultation_fee": "850.00"
}
```

`specialization`: `GENERAL_PRACTICE`, `CARDIOLOGY`, `DERMATOLOGY`, `ENDOCRINOLOGY`,
`GASTROENTEROLOGY`, `NEUROLOGY`, `ONCOLOGY`, `ORTHOPAEDICS`, `PAEDIATRICS`,
`PSYCHIATRY`, `PULMONOLOGY`, `RADIOLOGY`, `SURGERY`, `UROLOGY`.

`license_number` is stored uppercase and is unique across the directory; `email` is
stored lowercase and is also unique.

Query parameters: `?specialization=`, `?is_available=`, `?search=`, `?ordering=`.

### Patient-doctor mappings

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/mappings/` | Assign a doctor to a patient |
| GET | `/api/mappings/` | All mappings across the caller's patients |
| GET | `/api/mappings/<patient_id>/` | Every doctor assigned to one patient |
| DELETE | `/api/mappings/<id>/` | Remove one assignment |

```json
{ "patient": 1, "doctor": 3, "notes": "Referred for ECG.", "is_primary": true }
```

A patient may have many doctors and a doctor many patients. The same doctor cannot be
assigned to the same patient twice, and a patient may have at most one `is_primary`
doctor — both enforced by database constraints as well as in the serializer.
Assigning a doctor to a patient the caller does not own is rejected.

> **Note on the two `<id>` routes.** The specification puts
> `GET /api/mappings/<patient_id>/` and `DELETE /api/mappings/<id>/` on the same path,
> so the path parameter means a **patient id** on `GET` and a **mapping id** on
> `DELETE`. Both are implemented exactly as specified. Because that overloading is
> easy to misread, two unambiguous aliases are also available and are the better
> choice for new clients:
>
> - `GET /api/mappings/by-patient/<patient_id>/`
> - `GET|PUT|PATCH|DELETE /api/mappings/assignment/<id>/`

### Utility

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health/` | Liveness probe; no authentication |
| GET | `/api/docs/` | Swagger UI (interactive) |
| GET | `/api/redoc/` | ReDoc reference |
| GET | `/api/schema/` | OpenAPI 3 document |
| — | `/admin/` | Django admin |

---

## Walkthrough with curl

```bash
# 1. Register
curl -s -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Disha Gangwar","email":"disha@example.com","password":"StrongPass!234","confirm_password":"StrongPass!234"}'

# 2. Log in and keep the access token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"disha@example.com","password":"StrongPass!234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['tokens']['access'])")

# 3. Add a patient
curl -s -X POST http://127.0.0.1:8000/api/patients/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"full_name":"Asha Mehta","date_of_birth":"1990-05-17","gender":"FEMALE","blood_group":"O+","phone":"+919876543210"}'

# 4. Add a doctor
curl -s -X POST http://127.0.0.1:8000/api/doctors/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"full_name":"Rohan Kapoor","specialization":"CARDIOLOGY","license_number":"MCI-10045","email":"rohan@example.com","phone":"+919812345678","years_of_experience":12}'

# 5. Assign the doctor to the patient
curl -s -X POST http://127.0.0.1:8000/api/mappings/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"patient":1,"doctor":1,"is_primary":true}'

# 6. List that patient's doctors
curl -s "http://127.0.0.1:8000/api/mappings/1/" -H "Authorization: Bearer $TOKEN"
```

### Postman

Import `postman_collection.json`. The register and login requests save the returned
tokens and ids into collection variables automatically, so the remaining requests
authenticate without any copy-pasting. Run the requests top to bottom.

---

## How the docs stay accurate

The schema is generated from the code, so it cannot drift from the routes or
serializers. Two things need help, though, and both live in `core/schema.py`:

- **The response envelope.** Views render through `StandardResponseMixin`, so the
  real body is `{"success": true, "data": ...}` rather than the bare serializer a
  generator would assume. `EnvelopeAutoSchema` applies that envelope during
  generation, and the matching error envelopes with it, instead of each view being
  annotated by hand.
- **The exceptions to it.** A paginated list carries its own envelope from
  `StandardResultsPagination.get_paginated_response_schema`, so it must not be
  wrapped twice. Views that build a response themselves — register, login, the
  per-patient doctor list — declare an explicit response serializer. SimpleJWT's
  token refresh is the one endpoint that answers without an envelope at all, so
  only views that actually use the mixin get wrapped.

`tests/test_schema.py` pins each of those cases, and the suite fails if
drf-spectacular emits a single warning, which is what it does when an endpoint is
being documented by guesswork.

## Security notes

- Secrets and database credentials come from the environment, never from source.
- `DEFAULT_PERMISSION_CLASSES` is `IsAuthenticated`, so a new endpoint is private
  unless it explicitly opts out; register and login are the only public ones.
- Querysets are filtered by owner, so an authorization bug cannot leak another user's
  rows — a missing record yields `404` rather than confirming it exists.
- `created_by` is taken from the token, so sending it in the request body does nothing.
- Login responses are identical for an unknown email and a wrong password.
- Request throttling is on by default: 30/min anonymous, 120/min per user.
- Unhandled exceptions are logged server-side and return a generic message, so stack
  traces and internals are never exposed to clients.
- With `DJANGO_DEBUG=False`, HSTS, secure cookies and SSL redirect switch on
  automatically.

## Data integrity

Validation is enforced in the serializer for a helpful error message *and* at the
database level so concurrent requests cannot slip past it:

- `unique_patient_phone_per_user` — one user cannot register the same phone twice,
  while two different users still can.
- `unique_patient_doctor_assignment` — a doctor is assigned to a patient at most once.
- `unique_primary_doctor_per_patient` — a conditional constraint allowing many
  non-primary doctors but only one primary.
- Doctor `license_number` and `email` are globally unique.

Deleting a patient or a doctor cascades to their mappings, leaving no orphans.

## Testing

82 tests in `tests/` cover every endpoint, run against a real PostgreSQL database:
registration and login (including duplicate email, weak password, mismatched
confirmation and account enumeration), token refresh and rejection of invalid tokens,
full CRUD on patients and doctors, cross-user isolation, every validation rule, the
uniqueness constraints, phone-number normalisation, filtering, search, ordering, and
the mapping routes including cascade deletes. A further 14 check that the published
OpenAPI schema matches what the endpoints really return.

```bash
python manage.py test tests
```
