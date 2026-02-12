import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.core.database import DatabaseManager
from app.utils.config import config
from app.utils.logger import logger


class ExternalDBImporter:
    """Импорт данных из внешней производственной БД (PostgreSQL / MSSQL)"""

    def __init__(self):
        self.external_engine = None
        self.local_db = DatabaseManager()

    def connect_external(self, db_type, host, port, user, password, db_name):
        """Создает подключение к БД в зависимости от типа"""
        try:
            if db_type == "PostgreSQL":
                # Нужен: pip install psycopg2-binary
                url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
            elif db_type == "MSSQL":
                # Нужен: pip install pyodbc (и установленный ODBC Driver 17 на Windows)
                url = f"mssql+pyodbc://{user}:{password}@{host}:{port}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server"
            else:
                raise ValueError(f"Тип БД {db_type} не поддерживается")

            self.external_engine = create_engine(url)

            # Тестовое подключение
            with self.external_engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            logger.info(f"Успешное подключение к {db_type} на {host}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к внешней БД: {e}")
            return False

    def import_good_batches(self, days_back: int = 30, min_extraction: float = 85.0):
        """Импорт успешных партий. SQL адаптирован под универсальность"""
        try:
            if not self.external_engine:
                raise ValueError("Нет подключения к внешней БД")

            # Вычисляем дату в Python, чтобы SQL запрос был одинаковым для всех БД
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

            query = text(f"""
                SELECT * FROM production_batches
                WHERE extraction_date >= :start_date
                AND extraction_percent >= :min_ext
                ORDER BY extraction_date DESC
            """)

            with self.external_engine.connect() as conn:
                batches_df = pd.read_sql(query, conn, params={
                    "start_date": start_date,
                    "min_ext": min_extraction
                })

            logger.info(f"Найдено {len(batches_df)} партий во внешней БД")

            imported_count = 0
            for _, row in batches_df.iterrows():
                batch_data = row.to_dict()

                # Добавляем в локальную SQLite (DatabaseManager)
                if self.local_db.add_batch(batch_data):
                    # Сразу тянем процессные данные (графики) для этой партии
                    self.import_process_data(batch_data['batch_id'])
                    imported_count += 1

            return imported_count
        except Exception as e:
            logger.error(f"Ошибка импорта партий: {e}")
            return 0

    def import_process_data(self, batch_id: str):
        """Метод остается почти как был, но с защитой от пустых данных"""
        try:
            query = text("SELECT * FROM process_history WHERE batch_id = :batch_id")

            with self.external_engine.connect() as conn:
                df = pd.read_sql(query, conn, params={"batch_id": batch_id})

            if df.empty:
                return

            # Преобразуем в список словарей для DatabaseManager.add_process_data
            records = df.to_dict('records')

            # Извлекаем номер аппарата из ID партии или данных (для корректной вставки)
            # Предположим, номер аппарата есть в колонке sulfate_number
            sfr_num = int(df['sulfate_number'].iloc[0]) if 'sulfate_number' in df.columns else 3

            self.local_db.add_process_data(batch_id, sfr_num, records)

        except Exception as e:
            logger.error(f"Ошибка импорта графиков для {batch_id}: {e}")