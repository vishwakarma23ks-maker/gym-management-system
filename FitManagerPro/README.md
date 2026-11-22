# FitManager Pro

A local Gym Management System built with Flask, SQLAlchemy and MySQL support. Ready to run locally or deploy to Render.

## Features

- Dashboard with membership stats, revenue, upcoming renewals and recent members
- Member CRUD (add, edit, delete, search, filter by status)
- Membership plans (create, list)
- Payment records (cash, UPI, online) with CSV export
- Attendance check-in / check-out
- Trainer directory
- Activity log
- Health endpoint (`/healthz`) for uptime checks
- SQLite quick-start; MySQL supported via `DATABASE_URL`

## Requirements

- Python 3.10+ (3.11 recommended)
- Git
- MySQL Server (optional - SQLite is the default quick-start)

## Local development (Windows)

1. Open the `FitManagerPro` folder in VS Code.
2. Open Terminal > New Terminal and create a virtual environment:
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and edit it:
   ```powershell
   copy .env.example .env
   ```
5. Initialize the database and default plans:
   ```powershell
   flask --app app init-db
   ```
6. Start the website:
   ```powershell
   python app.py
   ```
7. Open http://127.0.0.1:5000

First login: username `admin`, password from `ADMIN_PASSWORD` in `.env` (default `ChangeMe123!`). **Change it before adding real member data.**

## Production hardening (before public deployment)

This starter is a local development edition. Before deploying publicly add:

- CSRF protection, rate limiting, password reset, stronger role permissions
- HTTPS, secure cookies, audit review and proper error monitoring
- Backups of the database
- Never commit `.env` - it is gitignored for a reason

WhatsApp and Razorpay are not live-connected in this starter. See `AUTOMATION.md` for the safe integration blueprint.

## Deploy on Render

Render deploys directly from this Git repository. Use the included `render.yaml` blueprint or connect manually.

### Option 1: Render blueprint (render.yaml)

1. Push this repo to GitHub.
2. In Render, create a **Web Service** and select "Deploy an existing repo from a Git repository".
3. Connect your GitHub repo and choose the **FitManagerPro** folder as the root directory.
4. Render detects `render.yaml` automatically. Set these environment variables in the Render dashboard:
   - `SECRET_KEY` - Render auto-generates this (`generateValue: true`)
   - `ADMIN_PASSWORD` - strong admin password (do not sync from repo)
   - `DATABASE_URL` - Render provides a managed Postgres, or use your own MySQL
   - `SESSION_COOKIE_SECURE=1`
   - `FLASK_DEBUG=0`
5. Deploy.

### Option 2: Manual Render web service

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn --bind 0.0.0.0:$PORT --workers 2 --preload app:app`
- **Environment:** Python
- Add a **PostgreSQL** database (or bring your own MySQL) and set `DATABASE_URL` to its internal connection string.
- The `release: flask --app app init-db` step in `Procfile` runs migrations/deploys automatically on each deploy.

If your database provider hands out a legacy `postgres://` URL, `app.py` automatically rewrites it to `postgresql://` for SQLAlchemy compatibility.

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing key *(required in production)* | dev-only secret |
| `DATABASE_URL` | SQLAlchemy database URI | `sqlite:///fitmanager.db` |
| `ADMIN_PASSWORD` | Default admin password | `ChangeMe123!` |
| `FLASK_DEBUG` | Debug mode (`0` or `1`) | `0` |
| `PORT` | Port to listen on | `5000` |
| `SESSION_COOKIE_SECURE` | Secure session cookies | `1` |

Generate a strong `SECRET_KEY`:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

## Project structure

```
FitManagerPro/
├── app.py              # Flask application
├── schema.sql          # MySQL database bootstrap
├── requirements.txt    # Python dependencies
├── Procfile            # Render / Heroku process definition
├── render.yaml         # Render blueprint
├── .env.example        # Environment template (copy to .env)
├── .flaskenv           # Flask CLI defaults
├── .gitignore          # Git ignore rules
├── LICENSE             # MIT License
├── README.md           # This file
├── AUTOMATION.md       # n8n automation integration blueprint
├── instance/           # SQLite database (created at runtime)
├── static/             # CSS and JS
└── templates/          # Jinja2 HTML templates
```

## License

MIT License - see [LICENSE](LICENSE).