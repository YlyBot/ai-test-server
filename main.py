from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import sqlite3
import json
from datetime import datetime
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# База данных
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

# ===== API ЭНДПОИНТЫ =====

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "YAI'ly server is running"}

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

@app.get("/commands")
async def get_commands():
    cursor.execute("SELECT id, action, params FROM commands WHERE is_active = 1 ORDER BY id ASC")
    rows = cursor.fetchall()
    commands = []
    for row in rows:
        cmd = {"id": row[0], "action": row[1]}
        if row[2]:
            cmd.update(json.loads(row[2]))
        commands.append(cmd)
    return commands

@app.delete("/commands/{command_id}")
async def delete_command(command_id: int):
    cursor.execute("DELETE FROM commands WHERE id = ?", (command_id,))
    conn.commit()
    return {"status": "ok", "deleted": cursor.rowcount}

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

@app.get("/admin", response_class=HTMLResponse)
async def admin():
    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]
    
    cursor.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
    stats = cursor.fetchall()
    
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    
    stats_html = ""
    for stat in stats:
        emoji = {
            'install': '🎉', 'update': '🔄', 'chat_usage': '💬', 
            'auto_answer': '🤖', 'error': '⚠️'
        }.get(stat[0], '📌')
        stats_html += f'<div class="stat"><span class="stat-emoji">{emoji}</span> {stat[0]}: <strong>{stat[1]}</strong></div>'
    
    if stats_html == "":
        stats_html = '<div class="stat" style="background: #2a2a2a;">📭 Нет событий. Спроси что-нибудь в расширении!</div>'
    
    events_html = ""
    if len(rows) == 0:
        events_html = '<tr><td colspan="6" style="text-align: center;">📭 Нет событий. Начни использовать расширение!</td></tr>'
    else:
        for row in rows:
            events_html += f"""
            <tr>
                <td>{row[0]}</td>
                <td>{row[1][:19]}</td>
                <td><span class="type-{row[2]}">{row[2]}</span></td>
                <td>{row[3][:25] if row[3] else '-'}</td>
                <td>{row[5][:50] if row[5] else '-'}</td>
                <td>{row[4][:50] if row[4] else '-'}</td>
            </tr>
            """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>YAI'ly - Админка</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0a0a0a; color: #e0e0e0; padding: 20px;
            }}
            .container {{ max-width: 1400px; margin: 0 auto; }}
            h1 {{ color: #10a37f; margin-bottom: 20px; font-size: 28px; }}
            h2 {{ color: #10a37f; margin: 20px 0 15px 0; font-size: 20px; border-bottom: 1px solid #2a2a2a; padding-bottom: 8px; }}
            .stats {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }}
            .stat {{ 
                background: #1a1a1a; padding: 12px 20px; border-radius: 12px; 
                border-left: 3px solid #10a37f; font-size: 14px;
            }}
            .stat-emoji {{ font-size: 18px; margin-right: 8px; }}
            .total-events {{ 
                background: linear-gradient(135deg, #10a37f20, #0d8c6b10);
                padding: 12px 20px; border-radius: 12px; margin-bottom: 20px;
                border: 1px solid #10a37f40;
            }}
            table {{ width: 100%; border-collapse: collapse; background: #0f0f0f; border-radius: 12px; overflow: hidden; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #2a2a2a; }}
            th {{ background: #1a1a1a; color: #10a37f; font-weight: 600; }}
            tr:hover {{ background: #1a1a1a; }}
            .type-install {{ color: #10a37f; }}
            .type-update {{ color: #f5a623; }}
            .type-chat_usage {{ color: #10a37f; }}
            .type-auto_answer {{ color: #7c3aed; }}
            .type-error {{ color: #ff6b6b; }}
            .command-form {{ background: #1a1a1a; padding: 20px; border-radius: 12px; margin-bottom: 20px; }}
            .command-form input, .command-form select {{
                background: #2a2a2a; color: white; border: 1px solid #3a3a3a;
                padding: 10px 12px; border-radius: 8px; margin: 5px; font-size: 14px;
            }}
            .command-form input {{ width: 400px; }}
            .command-form button {{
                background: #10a37f; color: white; border: none; padding: 10px 20px;
                border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500;
            }}
            .command-form button:hover {{ background: #0d8c6b; transform: translateY(-1px); }}
            .badge {{ 
                background: #10a37f20; color: #10a37f; padding: 2px 8px; border-radius: 20px;
                font-size: 12px; display: inline-block;
            }}
            .refresh-btn {{
                background: #2a2a2a; border: 1px solid #3a3a3a; padding: 8px 16px;
                border-radius: 8px; color: #e0e0e0; cursor: pointer; margin-left: 15px;
            }}
            .refresh-btn:hover {{ background: #3a3a3a; }}
            footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #2a2a2a; text-align: center; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 YAI'ly — Панель управления</h1>
            
            <div class="total-events">
                📦 Всего событий в БД: <strong>{total_events}</strong>
            </div>
            
            <h2>📈 Статистика</h2>
            <div class="stats">
                {stats_html}
            </div>
            
            <h2>🎮 Отправить команду</h2>
            <div class="command-form">
                <form id="commandForm">
                    <select name="action" id="action">
                        <option value="show_notification">🔔 Показать уведомление</option>
                        <option value="block_sites">🚫 Заблокировать сайты</option>
                        <option value="update_settings">⚙️ Обновить настройки</option>
                    </select>
                    <input type="text" name="params" id="params" placeholder='{{"message":"Текст уведомления"}}' size="50">
                    <button type="submit">📤 Отправить команду</button>
                </form>
                <div style="margin-top: 10px; font-size: 12px; color: #666;">
                    💡 Примеры: {{"message":"Привет!"}} | {{"sites":["vk.com","t.me"]}} | {{"model":"deepseek/deepseek-v4-flash"}}
                </div>
            </div>
            
            <h2>📋 Последние события</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th><th>Время</th><th>Тип</th><th>User ID</th><th>URL</th><th>Данные</th>
                        </tr>
                    </thead>
                    <tbody>
                        {events_html}
                    </tbody>
                </table>
            </div>
            <footer>
                🚀 YAI'ly — сервер работает | Refresh страницы для обновления данных
            </footer>
        </div>
        
        <script>
            document.getElementById('commandForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const action = document.getElementById('action').value;
                const paramsRaw = document.getElementById('params').value;
                let params = {{}};
                try {{
                    params = JSON.parse(paramsRaw);
                }} catch(e) {{
                    alert('❌ Ошибка парсинга JSON\\nПример правильного формата: {{"message":"Текст"}}');
                    return;
                }}
                const response = await fetch('/commands', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{action, params}})
                }});
                if (response.ok) {{
                    alert('✅ Команда отправлена!\\nРасширения получат её в течение 5 минут.');
                    document.getElementById('params').value = '';
                }} else {{
                    alert('❌ Ошибка отправки команды');
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
    <head><meta charset="UTF-8"><title>YAI'ly Server</title></head>
    <body style="font-family: sans-serif; background: #0a0a0a; color: #e0e0e0; text-align: center; padding: 50px;">
        <h1>🤖 YAI'ly Server</h1>
        <p>Сервер работает! <a href="/admin" style="color: #10a37f;">Перейти в админку →</a></p>
    </body>
    </html>
    """
