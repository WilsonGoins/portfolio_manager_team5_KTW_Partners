# portfolio_manager_team5_KTW_Partners

A portfolio management app created by Senior Developers at KTW Partners.

## Prerequisites

- **Python 3.12+**
- **Node.js 20.19+ or 22.12+** (required by Vite 8) and npm
- **A PostgreSQL database.** The team uses a hosted [Neon](https://neon.tech)
  database; a local Postgres works too.

---

## First-time setup

### 1. Clone the repo

```bash
git clone https://github.com/WilsonGoins/portfolio_manager_team5_KTW_Partners.git
cd portfolio_manager_team5_KTW_Partners
```

### 2. Create the Python virtual environment

macOS / Linux:

```bash
./create_venv.sh
source venv/bin/activate
```

Windows (PowerShell):

```powershell
.\create_venv.ps1
.\venv\Scripts\Activate.ps1
```

Both scripts create `venv/` and install everything in `requirements.txt`.

> **Using `uv` instead?** A venv created by `uv venv` has no `pip` inside it, so
> the scripts above will fail with `No module named pip`. Install dependencies
> with uv instead:
> ```bash
> VIRTUAL_ENV=venv uv pip install -r requirements.txt
> ```

### 3. Configure the database connection

Copy the example env file and fill in your connection string:

```bash
cp .env.example .env
```

Then edit `.env`:

```
DB_CONNECTION_STRING=postgresql://user:password@host/dbname?sslmode=require
UPDATE_PORTFOLIO_VALUE=True/False
```

`.env` lives at the **repo root** (not in `server/`) and is gitignored — never
commit it. Ask a teammate for the shared Neon string.


### 5. Install frontend dependencies

```bash
cd client/port_manager
npm install
```

## Running the app

You need **two terminals**

### Terminal 1 — backend

```bash
source venv/bin/activate     # Windows: .\venv\Scripts\Activate.ps1
cd server
flask --app api --debug run
```

Serves on http://127.0.0.1:5000.

Use `--debug`. Without it the backend does **not** reload when you edit files, and
because the frontend *does* hot-reload you get a confusing split where the UI is
running new code against an old API — new fields come back `undefined` and render
as `--` or blank. Drop the flag only when you want the server to ignore edits.

### Terminal 2 — frontend

```bash
cd client/port_manager
npm run dev
```

Serves on http://localhost:5173 — **open this one in your browser**, not the
backend URL. Vite prints the exact URL when it starts.
