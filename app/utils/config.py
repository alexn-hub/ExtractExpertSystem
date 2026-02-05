# app/utils/config.py
import os
from pathlib import Path
import yaml
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    host: str = 'localhost'
    port: int = 3306
    database: str = 'production_db'
    username: str = 'operator'
    password: str = ''
    local_db_path: Path = Path('data/database.db')


@dataclass
class ProcessConfig:
    """Конфигурация процесса"""
    temperature_threshold: float = 120.0
    min_acid_flow: float = 0.5
    max_current: float = 200.0
    sampling_interval: int = 60


@dataclass
class ModelConfig:
    """Конфигурация ML моделей"""
    similarity_threshold: float = 0.75
    n_neighbors: int = 5
    random_state: int = 42


class Config:
    """Главный класс конфигурации"""

    def __init__(self, config_path: Optional[Path] = None):
        self.base_dir = Path(__file__).parent.parent.parent
        self.config_path = config_path or self.base_dir / 'config.yaml'

        # Инициализация конфигураций
        self.db = DatabaseConfig()
        self.process = ProcessConfig()
        self.model = ModelConfig()

        # Загрузка из файла если существует
        self.load_from_file()

    def load_from_file(self):
        """Загрузка конфигурации из YAML файла"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                self._update_from_dict(config_data)

    def _update_from_dict(self, config_dict: dict):
        """Обновление конфигурации из словаря"""
        if 'database' in config_dict:
            for key, value in config_dict['database'].items():
                if hasattr(self.db, key):
                    setattr(self.db, key, value)  # ← ИСПРАВЛЕНО

        if 'process' in config_dict:
            for key, value in config_dict['process'].items():
                if hasattr(self.process, key):
                    setattr(self.process, key, value)  # ← ИСПРАВЛЕНО

        if 'model' in config_dict:
            for key, value in config_dict['model'].items():
                if hasattr(self.model, key):
                    setattr(self.model, key, value)  # ← ИСПРАВЛЕНО

    def save_to_file(self):
        """Сохранение конфигурации в файл"""
        config_data = {
            'database': self.db.__dict__,
            'process': self.process.__dict__,
            'model': self.model.__dict__
        }

        # Создаем директорию если не существует
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)


# Глобальный экземпляр конфигурации
config = Config()