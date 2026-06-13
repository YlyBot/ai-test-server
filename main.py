from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
from datetime import datetime

app = FastAPI()

# Разрешаем запросы с любых источников (для расширения)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем SQLite
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

# ===== ЭНДПОИНТЫ =====

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "AI Test Assistant server is running"}

@app.post("/events")
async def add_event(request: Request):
    try:
        data = await request.json()
        cursor.execute(
            "INSERT INTO events (timestamp, event_type, user_id, data) VALUES (?, ?, ?, ?)",
            (
                datetime.now().isoformat(),
                data.get("type", "unknown"),
                data.get("userId", "anonymous"),
                json.dumps(data.get("data", {}))
            )
        )
        conn.commit()
        return {"status": "ok", "id": cursor.lastrowid}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/events")
async def get_events(limit: int = 100):
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    return {
        "events": [
            {
                "id": row[0],
                "timestamp": row[1],
                "type": row[2],
                "userId": row[3],
                "data": json.loads(row[4]) if row[4] else {}
            }
            for row in rows
        ]
    }

@app.get("/")
async def root():
    return {
        "message": "AI Test Assistant Server",
        "endpoints": ["/ping", "/events", "/events?limit=N", "/admin"]
    }

@app.get("/admin")
async def admin():
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    html = """
    <html>
    <head>
        <title>AI Test Assistant - Админка</title>
        <style>
            body { font-family: sans-serif; margin: 20px; background: #0a0a0a; color: #e0e0e0; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #333; padding: 8px; text-align: left; }
            th { background: #1a1a1a; }
            tr:hover { background: #1a1a1a; }
        </style>
    </head>
    <body>
        <h1>📊 События с расширения</h1>
        <p>Всего записей: """ + str(len(rows)) + """</p>
        <table>
            <tr><th>ID</th><th>Время</th><th>Тип</th><th>User ID</th><th>Данные</th></tr>
    """
    for row in rows:
        html += f"""
            <tr>
                <td>{row[0]}</td>
                <td>{row[1]}</td>
                <td>{row[2]}</td>
                <td>{row[3][:20] if row[3] else '-'}</td>
                <td>{row[4][:100] if row[4] else '-'}</td>
            </tr>
        """
    html += """
        </table>
    </body>
    </html>
    """
    return html
