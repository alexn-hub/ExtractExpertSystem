# app/core/database.py
import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import logging
from app.utils.config import config
from app.utils.logger import logger


class DatabaseManager:
    """Универсальный менеджер базы данных с поддержкой динамических конфигураций"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.base_dir / 'data' / 'database.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self._init_database()

    def get_connection(self):
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection

    def _init_database(self):
        try:
            with self.get_connection() as conn:
                # Таблица 1: Паспорт партии (статика сырья хранится в JSON)
                conn.execute('''
                CREATE TABLE IF NOT EXISTS batches (
                    batch_id TEXT PRIMARY KEY,
                    extraction_date DATE NOT NULL,
                    unit_name TEXT NOT NULL,
                    sample_weight REAL NOT NULL,
                    input_params TEXT,               -- JSON со всеми статическими параметрами сырья
                    target_metric REAL NOT NULL,     -- Целевой показатель (извлечение/качество)
                    process_duration INTEGER,
                    quality_rating INTEGER CHECK(quality_rating BETWEEN 1 AND 5),
                    operator_id TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_good BOOLEAN DEFAULT 1
                )
                ''')

                # Таблица 2: Процессные данные (динамические тренды хранятся в JSON)
                conn.execute('''
                CREATE TABLE IF NOT EXISTS process_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    process_metrics TEXT,            -- JSON со всеми показателями датчиков за минуту
                    FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
                )
                ''')

                conn.execute('CREATE INDEX IF NOT EXISTS idx_process_batch_time ON process_data(batch_id, timestamp)')
                logger.info("Универсальная база данных инициализирована.")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    def add_batch(self, batch_data: Dict):
        """Добавление партии с упаковкой статических параметров в JSON"""
        try:
            input_params_dict = {}
            # Собираем все статические параметры, определенные в конфиге
            for param in config.hmi.static_parameters:
                key = param['key']
                if key in batch_data:
                    input_params_dict[key] = batch_data[key]

            clean_data = {
                'batch_id': batch_data.get('batch_id'),
                'extraction_date': batch_data.get('extraction_date', datetime.now().strftime('%Y-%m-%d')),
                'unit_name': batch_data.get('unit_name', 'Участок-1'),
                'sample_weight': batch_data.get('sample_weight', 0.0),
                'input_params': json.dumps(input_params_dict),
                'target_metric': batch_data.get('target_metric', batch_data.get('extraction_percent', 0.0))
            }

            with self.get_connection() as conn:
                query = '''
                INSERT OR REPLACE INTO batches (
                    batch_id, extraction_date, unit_name, sample_weight,
                    input_params, target_metric
                ) VALUES (
                    :batch_id, :extraction_date, :unit_name, :sample_weight,
                    :input_params, :target_metric
                )
                '''
                conn.execute(query, clean_data)
                conn.commit()
                logger.info(f"Партия {clean_data['batch_id']} успешно сохранена.")
        except Exception as e:
            logger.error(f"Ошибка сохранения партии: {e}")
            raise

    def get_all_batches(self) -> List[Dict]:
        """Получение всех партий из базы"""
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM batches"
                df = pd.read_sql_query(query, conn)
                return df.to_dict('records')
        except Exception as e:
            logger.error(f"Ошибка при получении всех партий: {e}")
            return []

    def add_process_data(self, batch_id: str, process_records: List[Dict]) -> bool:
        """Добавление процессных данных с упаковкой в JSON"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = 'INSERT INTO process_data (batch_id, timestamp, process_metrics) VALUES (?, ?, ?)'

                for record in process_records:
                    timestamp = record.get('timestamp')
                    # Сохраняем все метрики датчиков, кроме служебных полей
                    metrics = {k: v for k, v in record.items() if k not in ['timestamp', 'batch_id', 'unit_name']}
                    cursor.execute(sql, (batch_id, str(timestamp), json.dumps(metrics)))

                conn.commit()
                logger.info(f"Добавлено {len(process_records)} записей процесса для партии {batch_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления процессных данных для {batch_id}: {e}")
            return False

    def get_process_data(self, batch_id: str) -> pd.DataFrame:
        """Получение процессных данных и распаковка из JSON в DataFrame"""
        try:
            with self.get_connection() as conn:
                query = 'SELECT timestamp, process_metrics FROM process_data WHERE batch_id = ? ORDER BY timestamp'
                df_raw = pd.read_sql_query(query, conn, params=[batch_id])

                if df_raw.empty:
                    return pd.DataFrame()

                records = []
                for _, row in df_raw.iterrows():
                    metrics = json.loads(row['process_metrics']) if row['process_metrics'] else {}
                    metrics['timestamp'] = row['timestamp']
                    records.append(metrics)

                return pd.DataFrame(records)
        except Exception as e:
            logger.error(f"Ошибка получения процессных данных: {e}")
            return pd.DataFrame()

    def delete_batch(self, batch_id: str):
        """Удаление партии и связанных с ней процессных данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM process_data WHERE batch_id = ?", (batch_id,))
                cursor.execute("DELETE FROM batches WHERE batch_id = ?", (batch_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении партии {batch_id}: {e}")
            return False

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None