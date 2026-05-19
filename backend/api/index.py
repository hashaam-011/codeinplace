import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import Database, parse_json_date


DB = Database()


class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            return self.send_json({"ok": True, "database": DB.driver})

        if path == "/api/habits":
            goal = query.get("goal", [None])[0]
            return self.send_json({"habits": DB.list_habits(goal)})

        if path == "/api/habits/today":
            goal = query.get("goal", ["focus"])[0]
            return self.send_json({"habit": DB.daily_habit(goal)})

        if path == "/api/progress":
            return self.send_json(DB.progress_summary())

        return self.send_json({"error": "Endpoint not found."}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        data = self.read_json()

        if parsed.path == "/api/checkins":
            habit_id = int(data.get("habit_id") or 0)
            status = str(data.get("status") or "completed").strip().lower()
            note = str(data.get("note") or "").strip()
            habit = DB.get_habit(habit_id)

            if not habit:
                return self.send_json({"error": "Habit not found."}, status=404)
            if status not in {"completed", "skipped"}:
                return self.send_json({"error": "Status must be completed or skipped."}, status=400)

            checkin = DB.add_checkin(habit_id, habit["goal"], status, note)
            return self.send_json({"checkin": checkin, "progress": DB.progress_summary()}, status=201)

        if parsed.path == "/api/habits":
            title = str(data.get("title") or "").strip()
            description = str(data.get("description") or "").strip()
            goal = str(data.get("goal") or "focus").strip().lower()
            difficulty = str(data.get("difficulty") or "Easy").strip()

            try:
                minutes = int(data.get("minutes") or 5)
            except ValueError:
                minutes = 5

            if not title or not description:
                return self.send_json({"error": "Title and description are required."}, status=400)

            habit = DB.add_habit(goal, title, description, max(minutes, 1), difficulty)
            return self.send_json({"habit": habit}, status=201)

        return self.send_json({"error": "Endpoint not found."}, status=404)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def send_json(self, payload, status=200):
        body = json.dumps(payload, default=parse_json_date).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
