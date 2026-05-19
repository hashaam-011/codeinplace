# Micro Habit Coach

A final project for Code in Place: a full-stack habit coach for busy
professionals. The frontend is plain HTML, CSS, and JavaScript. The backend is
Python and can use Neon Postgres through `DATABASE_URL`, with a local SQLite
fallback for easy demos.

## Short Description

Micro Habit Coach helps busy professionals build healthier routines through
small daily actions. Users choose a goal, receive a tiny habit, mark it complete
or skipped, and track streaks plus weekly progress.

## Features

- Pick a professional wellness goal
- Get a tiny daily habit suggestion
- Mark habits complete or skipped
- Track streak, completion rate, and weekly progress
- Add custom habits
- Works locally without external services
- Ready for Neon Postgres when you add a database URL

## Project Structure

```text
backend/
  app.py          Python HTTP API for local development
  api/index.py    Vercel serverless API entrypoint
  database.py     SQLite/Postgres storage layer
  seed_data.py    Starter habit ideas
frontend/
  index.html
  styles.css
  app.js
  config.js       Frontend API URL config
```

## Run Locally

If Python is installed normally:

```bash
python backend/app.py
```

In this Codex workspace, Python is available at:

```powershell
& 'C:\Users\Hashaam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' backend\app.py
```

Then open:

```text
http://localhost:8000
```

## Use Neon Postgres

1. Create a Neon database.
2. Copy the connection string.
3. Install a Postgres driver:

```bash
pip install psycopg[binary]
```

4. Set the environment variable:

```powershell
$env:DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"
python backend/app.py
```

If `DATABASE_URL` is missing, the app automatically uses `habit_coach.db`.

## Deploy Backend to Vercel

Deploy the `backend` folder as its own Vercel project and set:

```text
DATABASE_URL=your_neon_connection_string
```

The backend exposes:

```text
/api/health
/api/habits
/api/habits/today
/api/checkins
/api/progress
```

## Deploy Frontend to Vercel

Deploy the `frontend` folder as a separate Vercel project. After the backend is
deployed, update `frontend/config.js`:

```js
window.MICRO_HABIT_API_URL = "https://your-backend-project.vercel.app";
```

## Code in Place Demo Pitch

Micro Habit Coach helps busy professionals build healthier routines with tiny,
realistic habits. Instead of overwhelming users with big goals, it recommends
small actions, records daily check-ins, and shows progress over time.
