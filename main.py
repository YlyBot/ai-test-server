from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
from datetime import datetime

app = FastAPI()

# Разрешаем запросы с расширения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаём БД
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        event_type TEXT,
        user_id TEXT,
        data TEXT
    )
""")
conn.commit()

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Сервер работает"}

@app.post("/events")
async def add_event(request: Request):
    data = await request.json()
    cursor.execute(
        "INSERT INTO events (timestamp, event_type, user_id, data) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), data.get("type"), data.get("userId"), json.dumps(data.get("data")))
    )
    conn.commit()
    return {"status": "ok"}

@app.get("/events")
async def get_events():
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 100")
    rows = cursor.fetchall()
    return {"events": rows}

@app.get("/commands")
async def get_commands():
    # Здесь можно вернуть команды для расширения
    return {"commands": []}