# app/core/database.py
import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from app.utils.config import config
from app.utils.logger import logger


class DatabaseManager:
    """Менеджер базы данных"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.base_dir / 'data' / 'database.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self._init_database()

    def _init_database(self):
        """Инициализация структуры базы данных"""
        try:
            with self.get_connection() as conn:
                # Таблица 1: Методические данные партий - ПОЛНАЯ СТРУКТУРА
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

                # Таблица 2: Процессные данные
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
                                    electrodes_pos REAL DEFAULT 0,
                                    level_mixer REAL DEFAULT 0,
                                    FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
                                )
                                ''')

                # Индексы для ускорения поиска
                conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_batch_composition 
                ON batches(ni_percent, cu_percent, pt_percent, pd_percent)
                ''')

                conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_process_batch_time 
                ON process_data(batch_id, timestamp)
                ''')

                logger.info("База данных инициализирована")

        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    def get_connection(self):
        """Получение соединения с БД"""
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            # Включение поддержки внешних ключей
            self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection

    def add_batch(self, batch_data: Dict):
        """Добавление информации о партии в таблицу batches"""
        try:
            with self.get_connection() as conn:
                query = '''
                INSERT OR REPLACE INTO batches (
                    batch_id, extraction_date, sulfate_number, sample_weight,
                    ni_percent, cu_percent, pt_percent, pd_percent,
                    sio2_percent, c_percent, se_percent, extraction_percent
                ) VALUES (
                    :batch_id, :extraction_date, :sulfate_number, :sample_weight,
                    :ni_percent, :cu_percent, :pt_percent, :pd_percent,
                    :sio2_percent, :c_percent, :se_percent, :extraction_percent
                )
                '''
                conn.execute(query, batch_data)
                conn.commit()
                logger.info(f"Партия {batch_data['batch_id']} успешно сохранена/обновлена.")
        except Exception as e:
            logger.error(f"Ошибка сохранения партии {batch_data.get('batch_id')}: {e}")
            raise

    def get_all_batches(self):
        """Возвращает список всех партий из базы для анализа рекомендателем"""
        query = "SELECT * FROM batches"
        try:
            import sqlite3
            # Если у тебя используется pandas для работы с БД:
            import pandas as pd
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn)
                return df.to_dict('records')  # Превращаем в список словарей
        except Exception as e:
            print(f"Ошибка при получении всех партий: {e}")
            return []

    def add_process_data(self, batch_id: str, process_records: List[Dict]) -> bool:
        """Добавление процессных данных для партии"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Добавляем колонки в SQL запрос
                sql = '''
                INSERT INTO process_data 
                (batch_id, timestamp, temperature_1, temperature_2, 
                 temperature_3, acid_flow, current_value, electrodes_pos, level_mixer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''

                for record in process_records:
                    # 2. Добавляем значения в параметры (используем .get() для безопасности)
                    params = (
                        batch_id,
                        record['timestamp'],
                        record.get('temperature_1'),
                        record.get('temperature_2'),
                        record.get('temperature_3'),
                        record.get('acid_flow'),
                        record.get('current_value'),
                        record.get('electrodes_pos', 0.0),  # Новое поле
                        record.get('level_mixer', 0.0)  # Новое поле
                    )
                    cursor.execute(sql, params)

                conn.commit()
                logger.info(f"Добавлено {len(process_records)} записей для партии {batch_id}")
                return True

        except Exception as e:
            logger.error(f"Ошибка добавления процессных данных: {e}")
            return False

    def find_similar_batches(self, sample_data: Dict[str, float],
                             limit: int = 10) -> pd.DataFrame:
        """Поиск похожих партий по составу"""
        try:
            with self.get_connection() as conn:
                query = '''
                SELECT * FROM batches 
                WHERE is_good = 1 
                AND sample_weight BETWEEN ? AND ?
                ORDER BY extraction_percent DESC
                LIMIT ?
                '''

                # Расчет диапазона веса (±15%)
                weight = sample_data.get('sample_weight', 100)
                min_weight = weight * 0.85
                max_weight = weight * 1.15

                df = pd.read_sql_query(
                    query,
                    conn,
                    params=[min_weight, max_weight, limit]
                )

                logger.info(f"Найдено {len(df)} похожих партий")
                return df

        except Exception as e:
            logger.error(f"Ошибка поиска похожих партий: {e}")
            return pd.DataFrame()

    def get_process_data(self, batch_id: str) -> pd.DataFrame:
        """Получение процессных данных по номеру партии"""
        try:
            with self.get_connection() as conn:
                query = '''
                SELECT * FROM process_data 
                WHERE batch_id = ? 
                ORDER BY timestamp
                '''

                df = pd.read_sql_query(query, conn, params=[batch_id])
                return df

        except Exception as e:
            logger.error(f"Ошибка получения процессных данных: {e}")
            return pd.DataFrame()

    def execute_query(self, query: str) -> Any:
        """Универсальное выполнение SQL запросов"""
        try:
            query_lower = query.strip().lower()
            with self.get_connection() as conn:
                if query_lower.startswith('select'):
                    return pd.read_sql_query(query, conn)
                else:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    conn.commit()
                    return cursor.rowcount  # Возвращаем кол-во измененных строк
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise

    def close(self):
        """Закрытие соединения с БД"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()