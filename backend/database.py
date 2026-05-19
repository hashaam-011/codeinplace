import os
import random
import sqlite3
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path

from seed_data import DEFAULT_HABITS


ROOT = Path(__file__).resolve().parents[1]
SQLITE_PATH = ROOT / "habit_coach.db"


class Database:
    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL", "").strip()
        self.driver = "sqlite"
        self.psycopg = None

        if self.database_url:
            try:
                import psycopg
                from psycopg.rows import dict_row

                self.psycopg = psycopg
                self.dict_row = dict_row
                self.driver = "postgres"
            except ImportError:
                print("DATABASE_URL is set, but psycopg is not installed. Using SQLite.")

        self.init_schema()
        self.seed_defaults()

    def connect(self):
        if self.driver == "postgres":
            return self.psycopg.connect(self.database_url, row_factory=self.dict_row)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def placeholder(self):
        return "%s" if self.driver == "postgres" else "?"

    def init_schema(self):
        if self.driver == "postgres":
            statements = [
                """
                CREATE TABLE IF NOT EXISTS habits (
                    id SERIAL PRIMARY KEY,
                    goal TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    minutes INTEGER NOT NULL,
                    difficulty TEXT NOT NULL,
                    custom BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS checkins (
                    id SERIAL PRIMARY KEY,
                    habit_id INTEGER REFERENCES habits(id),
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    checkin_date DATE NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
            ]
        else:
            statements = [
                """
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    minutes INTEGER NOT NULL,
                    difficulty TEXT NOT NULL,
                    custom INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    checkin_date TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (habit_id) REFERENCES habits(id)
                )
                """,
            ]

        with self.connect() as conn:
            cur = conn.cursor()
            for statement in statements:
                cur.execute(statement)
            conn.commit()

    def seed_defaults(self):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS total FROM habits")
            count = self.scalar(cur.fetchone(), "total")
            if count:
                return

            p = self.placeholder()
            cur.executemany(
                f"""
                INSERT INTO habits (goal, title, description, minutes, difficulty, custom)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p})
                """,
                [
                    (
                        habit["goal"],
                        habit["title"],
                        habit["description"],
                        habit["minutes"],
                        habit["difficulty"],
                        False if self.driver == "postgres" else 0,
                    )
                    for habit in DEFAULT_HABITS
                ],
            )
            conn.commit()

    def rows_to_dicts(self, rows):
        return [dict(row) for row in rows]

    def scalar(self, row, key):
        if isinstance(row, dict):
            return row[key]
        return row[0]

    def list_habits(self, goal=None):
        p = self.placeholder()
        with self.connect() as conn:
            cur = conn.cursor()
            if goal:
                cur.execute(f"SELECT * FROM habits WHERE goal = {p} ORDER BY custom DESC, title", (goal,))
            else:
                cur.execute("SELECT * FROM habits ORDER BY goal, custom DESC, title")
            return self.rows_to_dicts(cur.fetchall())

    def get_habit(self, habit_id):
        p = self.placeholder()
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM habits WHERE id = {p}", (habit_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def daily_habit(self, goal):
        habits = self.list_habits(goal)
        if not habits:
            habits = self.list_habits()
        random.seed(f"{date.today().isoformat()}-{goal}")
        return random.choice(habits) if habits else None

    def add_habit(self, goal, title, description, minutes, difficulty):
        p = self.placeholder()
        custom_value = True if self.driver == "postgres" else 1
        with self.connect() as conn:
            cur = conn.cursor()
            if self.driver == "postgres":
                cur.execute(
                    f"""
                    INSERT INTO habits (goal, title, description, minutes, difficulty, custom)
                    VALUES ({p}, {p}, {p}, {p}, {p}, {p})
                    RETURNING *
                    """,
                    (goal, title, description, minutes, difficulty, custom_value),
                )
                row = cur.fetchone()
            else:
                cur.execute(
                    f"""
                    INSERT INTO habits (goal, title, description, minutes, difficulty, custom)
                    VALUES ({p}, {p}, {p}, {p}, {p}, {p})
                    """,
                    (goal, title, description, minutes, difficulty, custom_value),
                )
                cur.execute("SELECT * FROM habits WHERE id = last_insert_rowid()")
                row = cur.fetchone()
            conn.commit()
            return dict(row)

    def add_checkin(self, habit_id, goal, status, note=""):
        p = self.placeholder()
        today = date.today().isoformat()
        with self.connect() as conn:
            cur = conn.cursor()
            if self.driver == "postgres":
                cur.execute(
                    f"""
                    INSERT INTO checkins (habit_id, goal, status, note, checkin_date)
                    VALUES ({p}, {p}, {p}, {p}, {p})
                    RETURNING *
                    """,
                    (habit_id, goal, status, note, today),
                )
                row = cur.fetchone()
            else:
                cur.execute(
                    f"""
                    INSERT INTO checkins (habit_id, goal, status, note, checkin_date)
                    VALUES ({p}, {p}, {p}, {p}, {p})
                    """,
                    (habit_id, goal, status, note, today),
                )
                cur.execute("SELECT * FROM checkins WHERE id = last_insert_rowid()")
                row = cur.fetchone()
            conn.commit()
            return dict(row)

    def recent_checkins(self, days=7):
        p = self.placeholder()
        start = (date.today() - timedelta(days=days - 1)).isoformat()
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT c.*, h.title AS habit_title
                FROM checkins c
                LEFT JOIN habits h ON h.id = c.habit_id
                WHERE c.checkin_date >= {p}
                ORDER BY c.checkin_date DESC, c.created_at DESC
                """,
                (start,),
            )
            return self.rows_to_dicts(cur.fetchall())

    def progress_summary(self):
        checkins = self.recent_checkins(30)
        completed_dates = sorted(
            {str(item["checkin_date"]) for item in checkins if item["status"] == "completed"},
            reverse=True,
        )
        total = len(checkins)
        completed = sum(1 for item in checkins if item["status"] == "completed")
        skipped = sum(1 for item in checkins if item["status"] == "skipped")
        streak = self.calculate_streak(set(completed_dates))

        week_start = date.today() - timedelta(days=6)
        week = []
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            iso = day.isoformat()
            day_items = [item for item in checkins if str(item["checkin_date"]) == iso]
            week.append(
                {
                    "date": iso,
                    "label": day.strftime("%a"),
                    "completed": sum(1 for item in day_items if item["status"] == "completed"),
                    "skipped": sum(1 for item in day_items if item["status"] == "skipped"),
                }
            )

        return {
            "total": total,
            "completed": completed,
            "skipped": skipped,
            "completion_rate": round((completed / total) * 100) if total else 0,
            "streak": streak,
            "week": week,
            "recent": checkins[:8],
            "goal_totals": self.goal_totals(30),
            "database": self.driver,
        }

    def goal_totals(self, days=30):
        p = self.placeholder()
        start = (date.today() - timedelta(days=days - 1)).isoformat()
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT goal,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                    COUNT(*) AS total
                FROM checkins
                WHERE checkin_date >= {p}
                GROUP BY goal
                ORDER BY completed DESC, total DESC, goal
                """,
                (start,),
            )
            return self.rows_to_dicts(cur.fetchall())

    def calendar_summary(self, year=None, month=None):
        today = date.today()
        year = int(year or today.year)
        month = int(month or today.month)
        first = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        after_last = date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
        p = self.placeholder()

        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT checkin_date, status, goal
                FROM checkins
                WHERE checkin_date >= {p} AND checkin_date < {p}
                ORDER BY checkin_date
                """,
                (first.isoformat(), after_last.isoformat()),
            )
            rows = self.rows_to_dicts(cur.fetchall())

        by_day = {}
        for row in rows:
            key = str(row["checkin_date"])
            by_day.setdefault(key, {"completed": 0, "skipped": 0, "goals": {}})
            by_day[key][row["status"]] += 1
            by_day[key]["goals"][row["goal"]] = by_day[key]["goals"].get(row["goal"], 0) + 1

        leading_blanks = first.weekday()
        days = [{"date": None, "day": "", "outside": True} for _ in range(leading_blanks)]

        for day_number in range(1, last_day + 1):
            current = date(year, month, day_number)
            iso = current.isoformat()
            data = by_day.get(iso, {"completed": 0, "skipped": 0, "goals": {}})
            days.append(
                {
                    "date": iso,
                    "day": day_number,
                    "today": iso == today.isoformat(),
                    "completed": data["completed"],
                    "skipped": data["skipped"],
                    "goals": data["goals"],
                }
            )

        while len(days) % 7:
            days.append({"date": None, "day": "", "outside": True})

        return {
            "year": year,
            "month": month,
            "month_label": first.strftime("%B %Y"),
            "days": days,
        }

    def calculate_streak(self, completed_dates):
        streak = 0
        current = date.today()
        while current.isoformat() in completed_dates:
            streak += 1
            current -= timedelta(days=1)
        return streak


def parse_json_date(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
