from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import sqlite3
import json
from datetime import datetime
from typing import Optional

app = FastAPI()

# Разрешаем запросы с расширения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем БД
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

# Таблица для событий
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

# Таблица для команд
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

# ===== ЭНДПОИНТЫ =====

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
                "data": json.loads(row[4]) if row[4] else {},
                "url": row[5],
                "browser": row[6]
            }
            for row in rows
        ]
    }

# ===== КОМАНДЫ =====

@app.get("/commands")
async def get_commands():
    """Получить все активные команды"""
    cursor.execute("SELECT id, action, params FROM commands WHERE is_active = 1 ORDER BY id ASC")
    rows = cursor.fetchall()
    commands = []
    for row in rows:
        cmd = {"id": row[0], "action": row[1]}
        if row[2]:
            try:
                params = json.loads(row[2])
                cmd.update(params)
            except:
                pass
        commands.append(cmd)
    print(f"📟 Возвращаем команды: {commands}")  # Лог для отладки
    return commands

@app.post("/commands")
async def add_command(request: Request):
    """Добавить новую команду"""
    data = await request.json()
    cursor.execute("""
        INSERT INTO commands (created_at, action, params, is_active)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        data.get("action"),
        json.dumps(data.get("params", {})),
        1
    ))
    conn.commit()
    print(f"✅ Добавлена команда: {data}")  # Лог для отладки
    return {"status": "ok", "id": cursor.lastrowid}

@app.delete("/commands/{command_id}")
async def delete_command(command_id: int):
    """Удалить выполненную команду"""
    cursor.execute("DELETE FROM commands WHERE id = ?", (command_id,))
    conn.commit()
    print(f"🗑️ Удалена команда ID: {command_id}")  # Лог для отладки
    return {"status": "ok", "deleted": cursor.rowcount}

@app.delete("/commands")
async def delete_all_commands():
    """Очистить все команды"""
    cursor.execute("DELETE FROM commands")
    conn.commit()
    return {"status": "ok", "deleted": cursor.rowcount}

@app.get("/stats")
async def get_stats():
    cursor.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
    rows = cursor.fetchall()
    return {"stats": [{"type": r[0], "count": r[1]} for r in rows]}

@app.get("/admin", response_class=HTMLResponse)
async def admin():
    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM commands")
    total_commands = cursor.fetchone()[0]
    
    cursor.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
    stats = cursor.fetchall()
    
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 30")
    rows = cursor.fetchall()
    
    cursor.execute("SELECT * FROM commands ORDER BY id DESC")
    commands_rows = cursor.fetchall()
    
    stats_html = ""
    for stat in stats:
        emoji = {
            'install': '🎉', 'update': '🔄', 'chat_usage': '💬', 
            'auto_answer': '🤖', 'error': '⚠️'
        }.get(stat[0], '📌')
        stats_html += f'<div class="stat">{emoji} {stat[0]}: <strong>{stat[1]}</strong></div>'
    
    if stats_html == "":
        stats_html = '<div class="stat">📭 Нет событий</div>'
    
    events_html = ""
    if len(rows) == 0:
        events_html = '<tr><td colspan="6" style="text-align: center;">📭 Нет событий</td></tr>'
    else:
        for row in rows:
            events_html += f"""
            <tr>
                <td>{row[0]}</td>
                <td>{row[1][:19]}</td>
                <td>{row[2]}</td>
                <td>{row[3][:25] if row[3] else '-'}</td>
                <td>{row[5][:50] if row[5] else '-'}</td>
                <td>{row[4][:50] if row[4] else '-'}</td>
            </tr>
            """
    
    commands_html = ""
    if len(commands_rows) == 0:
        commands_html = '<div style="color: #888;">📭 Нет активных команд</div>'
    else:
        commands_html = '<ul style="margin: 0; padding-left: 20px;">'
        for row in commands_rows:
            commands_html += f'<li>ID:{row[0]} | {row[2]} | {row[3][:50]}</li>'
        commands_html += '</ul>'
    
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
            h1 {{ color: #10a37f; margin-bottom: 20px; }}
            h2 {{ color: #10a37f; margin: 20px 0 15px 0; border-bottom: 1px solid #2a2a2a; padding-bottom: 8px; }}
            .stats {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }}
            .stat {{ background: #1a1a1a; padding: 10px 16px; border-radius: 8px; }}
            .info {{ background: #1a1a1a; padding: 12px 20px; border-radius: 12px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; background: #0f0f0f; border-radius: 12px; overflow: hidden; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #2a2a2a; }}
            th {{ background: #1a1a1a; color: #10a37f; }}
            tr:hover {{ background: #1a1a1a; }}
            .command-form {{ background: #1a1a1a; padding: 20px; border-radius: 12px; margin-bottom: 20px; }}
            .command-form input, .command-form select {{
                background: #2a2a2a; color: white; border: 1px solid #3a3a3a;
                padding: 10px 12px; border-radius: 8px; margin: 5px;
            }}
            .command-form input {{ width: 300px; }}
            .command-form button {{
                background: #10a37f; color: white; border: none; padding: 10px 20px;
                border-radius: 8px; cursor: pointer;
            }}
            .command-form button:hover {{ background: #0d8c6b; }}
            .clear-btn {{ background: #dc2626; }}
            .clear-btn:hover {{ background: #b91c1c; }}
            footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #2a2a2a; text-align: center; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 YAI'ly — Панель управления</h1>
            
            <div class="info">
                📦 Всего событий: <strong>{total_events}</strong> | 
                🎮 Активных команд: <strong>{total_commands}</strong>
            </div>
            
            <h2>📈 Статистика</h2>
            <div class="stats">
                {stats_html}
            </div>
            
            <h2>🎮 Отправить команду</h2>
            <div class="command-form">
                <form id="commandForm">
                    <select id="action">
                        <option value="show_notification">🔔 Уведомление</option>
                        <option value="block_sites">🚫 Блокировка сайтов</option>
                        <option value="update_settings">⚙️ Обновить настройки</option>
                    </select>
                    <input type="text" id="params" placeholder='{{"message":"Текст"}}' size="40">
                    <button type="submit">📤 Отправить</button>
                    <button type="button" id="clearBtn" class="clear-btn">🗑️ Очистить все</button>
                </form>
                <div style="margin-top: 10px; font-size: 12px; color: #666;">
                    💡 Примеры: {{"message":"Привет!"}} | {{"sites":["vk.com"]}} | {{"model":"deepseek/deepseek-v4-flash"}}
                </div>
            </div>
            
            <h2>📋 Активные команды</h2>
            {commands_html}
            
            <h2>📋 Последние события</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead><tr><th>ID</th><th>Время</th><th>Тип</th><th>User ID</th><th>URL</th><th>Данные</th></tr></thead>
                    <tbody>{events_html}</tbody>
                </table>
            </div>
            <footer>🚀 YAI'ly сервер работает | Обнови страницу для просмотра новых данных</footer>
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
                    alert('❌ Ошибка JSON\\nПример: {{"message":"Текст"}}');
                    return;
                }}
                const response = await fetch('/commands', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{action, params}})
                }});
                if (response.ok) {{
                    alert('✅ Команда добавлена! Расширение получит её при следующем опросе');
                    document.getElementById('params').value = '';
                    location.reload();
                }}
            }});
            
            document.getElementById('clearBtn').addEventListener('click', async () => {{
                if (confirm('Удалить все команды?')) {{
                    await fetch('/commands', {{method: 'DELETE'}});
                    location.reload();
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html

@app.get("/")
async def root():
    return {"message": "YAI'ly server is running. Go to /admin for admin panel"}
