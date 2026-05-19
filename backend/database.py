import os
import random
import sqlite3
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

                self.psycopg = psycopg
                self.driver = "postgres"
            except ImportError:
                print("DATABASE_URL is set, but psycopg is not installed. Using SQLite.")

        self.init_schema()
        self.seed_defaults()

    def connect(self):
        if self.driver == "postgres":
            return self.psycopg.connect(self.database_url)
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
            cur.execute("SELECT COUNT(*) FROM habits")
            count = cur.fetchone()[0]
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
            "database": self.driver,
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
