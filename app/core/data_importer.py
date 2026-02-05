# app/core/data_importer.py
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from app.core.database import DatabaseManager
from app.utils.config import config
from app.utils.logger import logger


class ExternalDBImporter:
    """Импорт данных из внешней производственной БД"""

    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string
        self.external_engine = None
        self.local_db = DatabaseManager()

    def connect_external(self, connection_string: str):
        """Подключение к внешней БД"""
        try:
            self.external_engine = create_engine(connection_string)
            logger.info(f"Подключение к внешней БД: {connection_string}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к внешней БД: {e}")
            return False

    def import_good_batches(self, days_back: int = 30, min_extraction: float = 85.0):
        """Импорт успешных партий за указанный период"""
        try:
            if not self.external_engine:
                raise ValueError("Нет подключения к внешней БД")

            # Запрос к внешней БД для получения успешных партий
            query = text(f"""
                SELECT 
                    batch_id,
                    extraction_date,
                    sulfate_number,
                    sample_weight,
                    ni_percent,
                    cu_percent,
                    pt_percent,
                    pd_percent,
                    sio2_percent,
                    c_percent,
                    se_percent,
                    extraction_percent,
                    process_duration,
                    quality_rating,
                    operator_id,
                    notes
                FROM production_batches
                WHERE extraction_date >= DATE_SUB(NOW(), INTERVAL {days_back} DAY)
                AND extraction_percent >= {min_extraction}
                AND quality_rating >= 4
                ORDER BY extraction_date DESC
            """)

            with self.external_engine.connect() as conn:
                batches_df = pd.read_sql(query, conn)

            logger.info(f"Найдено {len(batches_df)} успешных партий для импорта")

            # Импорт в локальную БД
            imported_count = 0
            for _, row in batches_df.iterrows():
                batch_data = row.to_dict()
                batch_data['is_good'] = True

                # Импорт основной информации о партии
                if self.local_db.add_batch(batch_data):
                    # Импорт процессных данных
                    self.import_process_data(batch_data['batch_id'])
                    imported_count += 1

            logger.info(f"Импортировано {imported_count} партий")
            return imported_count

        except Exception as e:
            logger.error(f"Ошибка импорта партий: {e}")
            return 0

    def import_process_data(self, batch_id: str):
        """Импорт процессных данных для конкретной партии"""
        try:
            query = text("""
                SELECT 
                    timestamp,
                    temperature_1,
                    temperature_2,
                    temperature_3,
                    acid_flow,
                    current_value
                FROM process_history
                WHERE batch_id = :batch_id
                ORDER BY timestamp
            """)

            with self.external_engine.connect() as conn:
                params = {'batch_id': batch_id}
                process_df = pd.read_sql(query, conn, params=params)

            # Преобразование данных
            process_records = []
            for _, row in process_df.iterrows():
                record = {
                    'timestamp': row['timestamp'],
                    'temperature_1': float(row['temperature_1']) if pd.notna(row['temperature_1']) else None,
                    'temperature_2': float(row['temperature_2']) if pd.notna(row['temperature_2']) else None,
                    'temperature_3': float(row['temperature_3']) if pd.notna(row['temperature_3']) else None,
                    'acid_flow': float(row['acid_flow']) if pd.notna(row['acid_flow']) else None,
                    'current_value': float(row['current_value']) if pd.notna(row['current_value']) else None
                }
                process_records.append(record)

            # Сохранение в локальную БД
            self.local_db.add_process_data(batch_id, process_records)
            logger.info(f"Импортировано {len(process_records)} записей для партии {batch_id}")

        except Exception as e:
            logger.error(f"Ошибка импорта процессных данных для {batch_id}: {e}")

    def sync_daily(self):
        """Ежедневная синхронизация"""
        logger.info("Начало ежедневной синхронизации")
        imported = self.import_good_batches(days_back=1)
        logger.info(f"Ежедневная синхронизация завершена. Импортировано: {imported}")
        return imported