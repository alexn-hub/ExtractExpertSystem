# app/utils/logger.py
import logging
import sys
from pathlib import Path
from datetime import datetime
from app.utils.config import config


def setup_logger(name: str = 'expert_system'):
    """Настройка системы логирования"""

    # Создаем логгер
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Файловый обработчик
    log_dir = config.base_dir / 'logs'
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f'expert_system_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Добавляем обработчики
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Глобальный логгер
logger = setup_logger()