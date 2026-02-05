#!/usr/bin/env python3
"""
Простой веб-интерфейс для SQLite - не требует установки программ!
"""
import sqlite3
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import html


class SQLiteWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            html_content = self.get_index_html()
            self.wfile.write(html_content.encode('utf-8'))

        elif parsed.path == '/tables':
            self.send_tables_json()

        elif parsed.path.startswith('/table/'):
            table_name = parsed.path.split('/')[-1]
            params = parse_qs(parsed.query)
            limit = int(params.get('limit', [100])[0])
            offset = int(params.get('offset', [0])[0])
            self.send_table_data(table_name, limit, offset)

        elif parsed.path == '/schema':
            self.send_schema_json()

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == '/execute':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            query = data.get('query', '')

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            result = self.execute_query(query)
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")

    def get_index_html(self):
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>SQLite Browser - Экспертная система</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
                .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                .sidebar { float: left; width: 250px; margin-right: 20px; }
                .content { margin-left: 270px; }
                .tables-list { max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; }
                .table-item { padding: 8px; margin: 5px 0; background: #f8f9fa; cursor: pointer; border-left: 3px solid #3498db; }
                .table-item:hover { background: #e9ecef; }
                textarea { width: 100%; height: 150px; padding: 10px; font-family: monospace; }
                button { padding: 10px 20px; background: #3498db; color: white; border: none; cursor: pointer; margin: 5px; }
                button:hover { background: #2980b9; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background: #f2f2f2; position: sticky; top: 0; }
                .result-container { max-height: 500px; overflow: auto; margin-top: 20px; }
                .error { color: #e74c3c; padding: 10px; background: #fde8e8; }
                .success { color: #27ae60; padding: 10px; background: #e8f8ef; }
                .tab { display: inline-block; padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; }
                .tab.active { border-bottom-color: #3498db; font-weight: bold; }
                .tab-content { display: none; }
                .tab-content.active { display: block; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧪 SQLite Browser - Экспертная система извлечения металлов</h1>
                    <p>База данных: data/database.db</p>
                </div>

                <div class="sidebar">
                    <h3>📋 Таблицы</h3>
                    <div id="tables-list" class="tables-list"></div>

                    <h3 style="margin-top: 20px;">⚡ Быстрые запросы</h3>
                    <button onclick="runQuery('SELECT * FROM batches LIMIT 10')">Показать партии</button>
                    <button onclick="runQuery('SELECT COUNT(*) FROM batches')">Кол-во партий</button>
                    <button onclick="runQuery('SELECT name FROM sqlite_master WHERE type=\"table\"')">Все таблицы</button>
                </div>

                <div class="content">
                    <div style="margin-bottom: 20px;">
                        <span class="tab active" onclick="switchTab('query')">📝 SQL Запрос</span>
                        <span class="tab" onclick="switchTab('structure')">🏗️ Структура</span>
                        <span class="tab" onclick="switchTab('data')">👁️ Данные</span>
                    </div>

                    <div id="query-tab" class="tab-content active">
                        <h3>SQL Запрос</h3>
                        <textarea id="sql-query" placeholder="Введите SQL запрос..."></textarea>
                        <div>
                            <button onclick="executeQuery()">▶ Выполнить</button>
                            <button onclick="clearQuery()">🗑️ Очистить</button>
                            <button onclick="saveQuery()">💾 Сохранить</button>
                        </div>
                        <div id="query-result" class="result-container"></div>
                    </div>

                    <div id="structure-tab" class="tab-content">
                        <h3>Структура таблиц</h3>
                        <div id="structure-content"></div>
                    </div>

                    <div id="data-tab" class="tab-content">
                        <h3>Просмотр данных</h3>
                        <div id="data-content">
                            <p>Выберите таблицу слева</p>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                let currentTable = '';

                function switchTab(tabName) {
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

                    document.querySelectorAll('.tab').forEach(t => {
                        if (t.textContent.includes(tabName)) t.classList.add('active');
                    });
                    document.getElementById(tabName + '-tab').classList.add('active');

                    if (tabName === 'structure') loadStructure();
                    if (tabName === 'data' && currentTable) loadTableData(currentTable);
                }

                function loadTables() {
                    fetch('/tables')
                        .then(r => r.json())
                        .then(data => {
                            const list = document.getElementById('tables-list');
                            list.innerHTML = '';
                            data.tables.forEach(table => {
                                const div = document.createElement('div');
                                div.className = 'table-item';
                                div.textContent = `📊 ${table}`;
                                div.onclick = () => selectTable(table);
                                list.appendChild(div);
                            });
                        });
                }

                function selectTable(table) {
                    currentTable = table;
                    document.querySelectorAll('.table-item').forEach(el => {
                        el.style.background = el.textContent.includes(table) ? '#e3f2fd' : '#f8f9fa';
                    });
                    document.getElementById('sql-query').value = `SELECT * FROM ${table} LIMIT 100`;
                    if (document.getElementById('data-tab').classList.contains('active')) {
                        loadTableData(table);
                    }
                }

                function loadStructure() {
                    fetch('/schema')
                        .then(r => r.json())
                        .then(data => {
                            const content = document.getElementById('structure-content');
                            let html = '';
                            for (let table in data) {
                                html += `<h4>${table}</h4><table>`;
                                html += '<tr><th>Поле</th><th>Тип</th><th>NOT NULL</th><th>PK</th></tr>';
                                data[table].forEach(col => {
                                    html += `<tr>
                                        <td><b>${col.name}</b></td>
                                        <td><code>${col.type}</code></td>
                                        <td>${col.notnull ? '✓' : ''}</td>
                                        <td>${col.pk ? '🔑' : ''}</td>
                                    </tr>`;
                                });
                                html += '</table><br>';
                            }
                            content.innerHTML = html || '<p>Нет таблиц</p>';
                        });
                }

                function loadTableData(table) {
                    fetch(`/table/${table}?limit=50`)
                        .then(r => r.json())
                        .then(data => {
                            const content = document.getElementById('data-content');
                            if (data.error) {
                                content.innerHTML = `<div class="error">${data.error}</div>`;
                                return;
                            }

                            let html = `<h4>${table} (${data.count} записей)</h4>`;
                            if (data.rows.length > 0) {
                                html += '<table>';
                                html += '<tr>' + Object.keys(data.rows[0]).map(k => `<th>${k}</th>`).join('') + '</tr>';
                                data.rows.forEach(row => {
                                    html += '<tr>' + Object.values(row).map(v => `<td>${v}</td>`).join('') + '</tr>';
                                });
                                html += '</table>';
                            }
                            content.innerHTML = html;
                        });
                }

                function executeQuery() {
                    const query = document.getElementById('sql-query').value.trim();
                    if (!query) return;

                    const resultDiv = document.getElementById('query-result');
                    resultDiv.innerHTML = '<p>Выполняю запрос...</p>';

                    fetch('/execute', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: query})
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.error) {
                            resultDiv.innerHTML = `<div class="error"><b>Ошибка:</b> ${data.error}</div>`;
                        } else {
                            let html = `<div class="success"><b>Успешно!</b> Записей: ${data.affected || 0}</div>`;
                            if (data.results && data.results.length > 0) {
                                html += '<table>';
                                html += '<tr>' + Object.keys(data.results[0]).map(k => `<th>${k}</th>`).join('') + '</tr>';
                                data.results.slice(0, 100).forEach(row => {
                                    html += '<tr>' + Object.values(row).map(v => `<td>${v}</td>`).join('') + '</tr>';
                                });
                                html += '</table>';
                                if (data.results.length > 100) {
                                    html += `<p><small>Показано 100 из ${data.results.length} записей</small></p>`;
                                }
                            }
                            resultDiv.innerHTML = html;
                            loadTables(); // Обновить список таблиц
                        }
                    });
                }

                function runQuery(query) {
                    document.getElementById('sql-query').value = query;
                    executeQuery();
                }

                function clearQuery() {
                    document.getElementById('sql-query').value = '';
                    document.getElementById('query-result').innerHTML = '';
                }

                function saveQuery() {
                    const query = document.getElementById('sql-query').value;
                    if (query) {
                        localStorage.setItem('last_sql_query', query);
                        alert('Запрос сохранен в браузере');
                    }
                }

                // Загрузка при старте
                document.addEventListener('DOMContentLoaded', function() {
                    loadTables();
                    const saved = localStorage.getItem('last_sql_query');
                    if (saved) document.getElementById('sql-query').value = saved;
                });
            </script>
        </body>
        </html>
        '''

    def send_tables_json(self):
        try:
            conn = sqlite3.connect('data/database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'tables': tables}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def send_table_data(self, table_name, limit=100, offset=0):
        try:
            conn = sqlite3.connect('data/database.db')
            conn.row_factory = sqlite3.Row

            # Получить количество записей
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            count = cursor.fetchone()['count']

            # Получить данные
            cursor.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'count': count,
                'rows': rows
            }, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

    def send_schema_json(self):
        try:
            conn = sqlite3.connect('data/database.db')
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            schema = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                schema[table] = [
                    {
                        'name': col[1],
                        'type': col[2],
                        'notnull': bool(col[3]),
                        'dflt_value': col[4],
                        'pk': bool(col[5])
                    }
                    for col in columns
                ]

            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(schema).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def execute_query(self, query):
        try:
            conn = sqlite3.connect('data/database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query_lower = query.lower().strip()

            if query_lower.startswith('select'):
                cursor.execute(query)
                rows = cursor.fetchall()
                return {
                    'results': [dict(row) for row in rows],
                    'affected': len(rows)
                }
            else:
                cursor.execute(query)
                conn.commit()
                return {'affected': cursor.rowcount}

        except Exception as e:
            return {'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()


def main():
    # Проверяем наличие базы данных
    if not os.path.exists('data/database.db'):
        print("⚠️  База данных не найдена: data/database.db")
        print("Создаю структуру...")
        os.makedirs('data', exist_ok=True)
        conn = sqlite3.connect('data/database.db')

        # Создаем таблицы как в вашем проекте
        conn.execute('''
            CREATE TABLE IF NOT EXISTS batches (
                batch_id TEXT PRIMARY KEY,
                extraction_date DATE NOT NULL,
                sulfate_number INTEGER NOT NULL,
                sample_weight REAL NOT NULL,
                ni_percent REAL DEFAULT 0,
                cu_percent REAL DEFAULT 0,
                pt_percent REAL DEFAULT 0,
                pd_percent REAL DEFAULT 0,
                sio2_percent REAL DEFAULT 0,
                c_percent REAL DEFAULT 0,
                se_percent REAL DEFAULT 0,
                extraction_percent REAL NOT NULL,
                process_duration INTEGER,
                quality_rating INTEGER CHECK(quality_rating BETWEEN 1 AND 5),
                operator_id TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_good BOOLEAN DEFAULT 1
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS process_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                temperature_1 REAL,
                temperature_2 REAL,
                temperature_3 REAL,
                acid_flow REAL,
                current_value REAL,
                FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
            )
        ''')

        # Добавляем тестовые данные
        test_batch = {
            'batch_id': 'TEST-2024-001',
            'extraction_date': '2024-01-01',
            'sulfate_number': 3,
            'sample_weight': 1000.5,
            'ni_percent': 1.2,
            'cu_percent': 0.8,
            'pt_percent': 0.05,
            'pd_percent': 0.03,
            'sio2_percent': 15.0,
            'c_percent': 5.0,
            'se_percent': 0.1,
            'extraction_percent': 87.5,
            'operator_id': 'admin',
            'notes': 'Тестовая партия'
        }

        conn.execute('''
            INSERT OR IGNORE INTO batches 
            (batch_id, extraction_date, sulfate_number, sample_weight,
             ni_percent, cu_percent, pt_percent, pd_percent,
             sio2_percent, c_percent, se_percent, extraction_percent,
             operator_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tuple(test_batch.values()))

        conn.commit()
        conn.close()
        print("✅ База данных создана с тестовыми данными")

    # Запускаем сервер
    server_address = ('localhost', 8080)
    httpd = HTTPServer(server_address, SQLiteWebHandler)

    print("=" * 60)
    print("🌐 SQLite Web Browser запущен!")
    print("📁 База данных: data/database.db")
    print("🔗 Откройте в браузере: http://localhost:8080")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")


if __name__ == '__main__':
    main()