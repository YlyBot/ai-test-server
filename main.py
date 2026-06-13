from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
from datetime import datetime
from typing import List, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        event_type TEXT,
        user_id TEXT,
        data TEXT,
        url TEXT,
        browser TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        action TEXT,
        params TEXT,
        is_active INTEGER DEFAULT 1
    )
""")
conn.commit()


@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "AI Test Assistant server is running"}

@app.post("/events")
async def add_event(request: Request):
    try:
        data = await request.json()
        cursor.execute("""
            INSERT INTO events (timestamp, event_type, user_id, data, url, browser) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get("timestamp", datetime.now().isoformat()),
            data.get("type", "unknown"),
            data.get("userId", "anonymous"),
            json.dumps(data.get("data", {})),
            data.get("url", ""),
            data.get("browser", "")
        ))
        conn.commit()
        return {"status": "ok", "id": cursor.lastrowid}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/events")
async def get_events(limit: int = 100, event_type: Optional[str] = None):
    if event_type:
        cursor.execute("SELECT * FROM events WHERE event_type = ? ORDER BY id DESC LIMIT ?", (event_type, limit))
    else:
        cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    return {
        "events": [
            {
                "id": row[0],
                "timestamp": row[1],
                "type": row[2],
                "userId": row[3],
                "data": json.loads(row[4]) if row[4] else {},
                "url": row[5],
                "browser": row[6]
            }
            for row in rows
        ]
    }

# ЭНДПОИНТ ДЛЯ КОМАНД (расширение будет их получать)
@app.get("/commands")
async def get_commands():
    cursor.execute("SELECT action, params FROM commands WHERE is_active = 1 ORDER BY id DESC")
    rows = cursor.fetchall()
    commands = []
    for row in rows:
        cmd = {"action": row[0]}
        if row[1]:
            cmd.update(json.loads(row[1]))
        commands.append(cmd)
    return commands

# ЭНДПОИНТ ДЛЯ ДОБАВЛЕНИЯ КОМАНД (через админку)
@app.post("/commands")
async def add_command(request: Request):
    data = await request.json()
    cursor.execute("""
        INSERT INTO commands (created_at, action, params, is_active)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        data.get("action"),
        json.dumps(data.get("params", {})),
        data.get("is_active", 1)
    ))
    conn.commit()
    return {"status": "ok", "id": cursor.lastrowid}

@app.get("/stats")
async def get_stats():
    cursor.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
    rows = cursor.fetchall()
    return {"stats": [{"type": r[0], "count": r[1]} for r in rows]}

@app.get("/admin")
async def admin():
    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]
    
    cursor.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
    stats = cursor.fetchall()
    
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 30")
    rows = cursor.fetchall()
    
    html = f"""
    <html>
    <head>
        <title>YAI'ly - Админка</title>
        <style>
            body {{ font-family: sans-serif; margin: 20px; background: #0a0a0a; color: #e0e0e0; }}
            h1, h2 {{ color: #10a37f; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #333; padding: 8px; text-align: left; }}
            th {{ background: #1a1a1a; }}
            tr:hover {{ background: #1a1a1a; }}
            .stat {{ display: inline-block; margin-right: 20px; padding: 10px; background: #1a1a1a; border-radius: 8px; }}
            .command-form {{ background: #1a1a1a; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            input, select, textarea {{ background: #2a2a2a; color: white; border: 1px solid #444; padding: 8px; margin: 5px; }}
            button {{ background: #10a37f; color: white; border: none; padding: 8px 16px; cursor: pointer; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <h1>📊 YAI'ly - Панель управления</h1>
        <p>Всего событий: {total_events}</p>
        
        <h2>📈 Статистика по типам событий</h2>
        <div>
    """
    for stat in stats:
        html += f'<div class="stat">📌 {stat[0]}: {stat[1]}</div>'
    
    html += f"""
        </div>
        
        <h2>🎮 Отправить команду расширениям</h2>
        <div class="command-form">
            <form id="commandForm">
                <select name="action" id="action">
                    <option value="show_notification">Показать уведомление</option>
                    <option value="block_sites">Заблокировать сайты</option>
                    <option value="update_settings">Обновить настройки</option>
                </select>
                <input type="text" name="params" id="params" placeholder='{{"message":"Текст", "sites":["vk.com"], "model":"..."}}' size="50">
                <button type="submit">📤 Отправить команду</button>
            </form>
        </div>
        
        <h2>📋 Последние события</h2>
        <table>
            <tr><th>ID</th><th>Время</th><th>Тип</th><th>User ID</th><th>URL</th><th>Данные</th></tr>
    """
    for row in rows:
        html += f"""
            <tr>
                <td>{row[0]}</td>
                <td>{row[1]}</td>
                <td>{row[2]}</td>
                <td>{row[3][:30] if row[3] else '-'}</td>
                <td>{row[5][:50] if row[5] else '-'}</td>
                <td>{row[4][:80] if row[4] else '-'}</td>
            </tr>
        """
    html += """
        </table>
        
        <script>
            document.getElementById('commandForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const action = document.getElementById('action').value;
                const paramsRaw = document.getElementById('params').value;
                let params = {};
                try {
                    params = JSON.parse(paramsRaw);
                } catch(e) {
                    alert('Ошибка парсинга JSON');
                    return;
                }
                const response = await fetch('/commands', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action, params})
                });
                if (response.ok) {
                    alert('Команда отправлена! Расширения получат её в течение 5 минут');
                    location.reload();
                }
            });
        </script>
    </body>
    </html>
    """
    return html
