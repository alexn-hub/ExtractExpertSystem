import os
from pathlib import Path
import yaml
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class HmiConfig:
    units: List[str] = field(default_factory=list)
    passport_fields: Dict[str, Any] = field(default_factory=dict)
    static_parameters: List[Dict[str, Any]] = field(default_factory=list)  # Свойства сырья
    target_parameter: Dict[str, Any] = field(default_factory=dict)
    trend_parameters: List[Dict[str, Any]] = field(default_factory=list)   # Показатели оборудования (+ plc_tag)


@dataclass
class DatabaseConfig:
    db_type: str = 'PostgreSQL'  # PostgreSQL, MSSQL, MySQL
    host: str = 'localhost'
    port: int = 5432
    database: str = 'production_db'
    username: str = 'operator'
    password: str = ''
    local_db_path: str = 'data/database.db'


@dataclass
class PlcConfig:
    protocol: str = 'Simulation'  # Simulation, OPC UA, Modbus TCP
    opc_url: str = 'opc.tcp://127.0.0.1:4840'
    opc_user: str = ''
    opc_password: str = ''
    modbus_host: str = '127.0.0.1'
    modbus_port: int = 502
    modbus_unit_id: int = 1
    polling_interval_ms: int = 1000


@dataclass
class ProcessConfig:
    sampling_interval: int = 60
    max_jump_delta: float = 50.0
    noise_filter_window: int = 3
    missing_data: str = "interpolate"


@dataclass
class ModelConfig:
    similarity_threshold: float = 0.75
    n_neighbors: int = 5
    random_state: int = 42


class Config:
    def __init__(self, config_path: Optional[Path] = None):
        self.base_dir = Path(__file__).parent.parent.parent
        self.config_path = config_path or self.base_dir / 'config.yaml'

        self.hmi = HmiConfig()
        self.db = DatabaseConfig()
        self.plc = PlcConfig()
        self.process = ProcessConfig()
        self.model = ModelConfig()
        self.load_from_file()

    def load_from_file(self):
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                if config_data:
                    self._update_from_dict(config_data)

    def _update_from_dict(self, config_dict: dict):
        if 'hmi' in config_dict and isinstance(config_dict['hmi'], dict):
            for key, value in config_dict['hmi'].items():
                if hasattr(self.hmi, key):
                    setattr(self.hmi, key, value)
        if 'database' in config_dict and isinstance(config_dict['database'], dict):
            for key, value in config_dict['database'].items():
                if hasattr(self.db, key):
                    setattr(self.db, key, str(value) if key == 'local_db_path' else value)
        if 'plc' in config_dict and isinstance(config_dict['plc'], dict):
            for key, value in config_dict['plc'].items():
                if hasattr(self.plc, key):
                    setattr(self.plc, key, value)
        if 'process' in config_dict and isinstance(config_dict['process'], dict):
            for key, value in config_dict['process'].items():
                if hasattr(self.process, key):
                    setattr(self.process, key, value)
        if 'model' in config_dict and isinstance(config_dict['model'], dict):
            for key, value in config_dict['model'].items():
                if hasattr(self.model, key):
                    setattr(self.model, key, value)

    def save_to_file(self):
        db_dict = self.db.__dict__.copy()
        db_dict['local_db_path'] = str(db_dict.get('local_db_path', 'data/database.db'))

        config_data = {
            'hmi': self.hmi.__dict__,
            'database': db_dict,
            'plc': self.plc.__dict__,
            'process': self.process.__dict__,
            'model': self.model.__dict__
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)


config = Config()