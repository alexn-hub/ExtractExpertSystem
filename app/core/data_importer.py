import json
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from typing import List, Dict, Optional
from app.core.database import DatabaseManager
from app.utils.config import config
from app.utils.logger import logger


class ExternalDBImporter:
    """Универсальный модуль импорта и экспорта данных для внешней производственной СУБД (PostgreSQL / MSSQL / MySQL)"""

    def __init__(self):
        self.external_engine = None
        self.local_db = DatabaseManager()

    def connect_from_config(self) -> bool:
        """Подключение к внешней БД с использованием настроек из Конфигуратора (config.db)"""
        return self.connect_external(
            db_type=getattr(config.db, 'db_type', 'PostgreSQL'),
            host=config.db.host,
            port=config.db.port,
            user=config.db.username,
            password=config.db.password,
            db_name=config.db.database
        )

    def connect_external(self, db_type: str, host: str, port: int, user: str, password: str, db_name: str) -> bool:
        """Создает подключение к внешней СУБД в зависимости от выбранного типа"""
        try:
            if db_type == "PostgreSQL":
                url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
            elif db_type == "MSSQL":
                url = f"mssql+pyodbc://{user}:{password}@{host}:{port}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server"
            elif db_type == "MySQL":
                url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
            else:
                raise ValueError(f"Тип СУБД {db_type} не поддерживается")

            self.external_engine = create_engine(url, connect_args={'connect_timeout': 5})

            with self.external_engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            logger.info(f"Успешное подключение к {db_type} ({host}:{port}/{db_name})")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к внешней БД ({db_type}): {e}")
            return False

    def get_tables_list(self) -> List[str]:
        """Возвращает список таблиц во внешней БД"""
        if not self.external_engine and not self.connect_from_config():
            return []
        try:
            inspector = inspect(self.external_engine)
            return inspector.get_table_names()
        except Exception as e:
            logger.error(f"Ошибка получения списка таблиц: {e}")
            return []

    def preview_columns(self, query_or_table: str, is_custom_query: bool = False) -> List[str]:
        """Считывает названия колонок из внешней таблицы или SQL-запроса (для маппинга)"""
        if not self.external_engine and not self.connect_from_config():
            raise ConnectionError("Не удалось подключиться к внешней БД. Проверьте настройки в Конфигураторе.")

        sql = query_or_table if is_custom_query else f"SELECT * FROM {query_or_table}"
        with self.external_engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
            return df.columns.tolist()

    def fetch_dataframe(self, query_or_table: str, is_custom_query: bool = False) -> pd.DataFrame:
        """Загружает DataFrame процессных данных из внешней БД"""
        if not self.external_engine and not self.connect_from_config():
            raise ConnectionError("Нет подключения к внешней БД.")

        sql = query_or_table if is_custom_query else f"SELECT * FROM {query_or_table}"
        with self.external_engine.connect() as conn:
            return pd.read_sql(text(sql), conn)

    def export_batch_to_sql(self, batch_info: Dict, process_df: pd.DataFrame, target_table_prefix: str = "ees_export") -> bool:
        """Экспортирует паспорт партии и процессные тренды во внешнюю SQL БД"""
        if not self.external_engine and not self.connect_from_config():
            raise ConnectionError("Не удалось подключиться к внешней SQL БД для экспорта.")

        try:
            # 1. Готовим плоскую строку паспорта партии (распаковываем JSON статики)
            passport_row = {
                'batch_id': batch_info.get('batch_id'),
                'extraction_date': batch_info.get('extraction_date'),
                'unit_name': batch_info.get('unit_name'),
                'sample_weight': batch_info.get('sample_weight'),
                'target_metric': batch_info.get('target_metric')
            }
            if batch_info.get('input_params'):
                try:
                    static_dict = json.loads(batch_info['input_params'])
                    passport_row.update(static_dict)
                except Exception:
                    pass

            df_passport = pd.DataFrame([passport_row])

            # 2. Готовим датафрейм процесса с привязкой к batch_id
            df_proc = process_df.copy()
            df_proc.insert(0, 'batch_id', batch_info.get('batch_id'))

            with self.external_engine.begin() as conn:
                df_passport.to_sql(f"{target_table_prefix}_batches", conn, if_exists='append', index=False)
                df_proc.to_sql(f"{target_table_prefix}_process", conn, if_exists='append', index=False)

            logger.info(f"Партия {batch_info.get('batch_id')} успешно экспортирована во внешнюю БД.")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта партии во внешнюю БД: {e}")
            raise