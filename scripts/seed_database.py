# scripts/seed_database.py
import sys
from pathlib import Path
import logging

# Добавляем корневую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import DatabaseManager
from app.utils.logger import logger


def seed_database():
    """Наполнение базы тестовыми данными"""
    logger.info("Начало наполнения базы данных...")

    db_manager = DatabaseManager()

    # Тестовые данные партий
    test_batches = [
        {
            'batch_id': 'P-2024-001',
            'extraction_date': '2024-10-04',
            'sulfate_number': 3,
            'sample_weight': 1042.08,
            'ni_percent': 1.57,
            'cu_percent': 1.58,
            'pt_percent': 8.37,
            'pd_percent': 33.62,
            'sio2_percent': 9.80,
            'c_percent': 9.86,
            'se_percent': 1.49,
            'extraction_percent': 93.08,
            'operator_id': 'Тестовый оператор 1',
            'is_good': True
        },
        {
            'batch_id': 'P-2024-002',
            'extraction_date': '2024-10-07',
            'sulfate_number': 3,
            'sample_weight': 1000.40,
            'ni_percent': 2.61,
            'cu_percent': 1.80,
            'pt_percent': 6.78,
            'pd_percent': 28.87,
            'sio2_percent': 11.24,
            'c_percent': 9.56,
            'se_percent': 1.13,
            'extraction_percent': 89.90,
            'operator_id': 'Тестовый оператор 1',
            'is_good': True
        },
        {
            'batch_id': 'P-2024-003',
            'extraction_date': '2024-10-15',
            'sulfate_number': 3,
            'sample_weight': 1159.45,
            'ni_percent': 2.69,
            'cu_percent': 1.74,
            'pt_percent': 4.69,
            'pd_percent': 20.74,
            'sio2_percent': 18.13,
            'c_percent': 17.50,
            'se_percent': 0.65,
            'extraction_percent': 81.80,
            'operator_id': 'Тестовый оператор 2',
            'is_good': False  # Низкое извлечение
        },
        {
            'batch_id': 'P-2024-004',
            'extraction_date': '2024-11-01',
            'sulfate_number': 4,
            'sample_weight': 1109.98,
            'ni_percent': 2.20,
            'cu_percent': 1.22,
            'pt_percent': 7.37,
            'pd_percent': 29.33,
            'sio2_percent': 11.70,
            'c_percent': 18.00,
            'se_percent': 0.82,
            'extraction_percent': 90.27,
            'operator_id': 'Тестовый оператор 2',
            'is_good': True
        },
        # Добавим еще несколько партий для разнообразия
        {
            'batch_id': 'P-2024-005',
            'extraction_date': '2024-11-10',
            'sulfate_number': 3,
            'sample_weight': 980.50,
            'ni_percent': 1.85,
            'cu_percent': 1.45,
            'pt_percent': 9.15,
            'pd_percent': 35.20,
            'sio2_percent': 8.90,
            'c_percent': 8.50,
            'se_percent': 1.25,
            'extraction_percent': 94.50,
            'operator_id': 'Тестовый оператор 1',
            'is_good': True
        },
        {
            'batch_id': 'P-2024-006',
            'extraction_date': '2024-11-15',
            'sulfate_number': 4,
            'sample_weight': 1050.75,
            'ni_percent': 2.10,
            'cu_percent': 1.65,
            'pt_percent': 5.80,
            'pd_percent': 25.40,
            'sio2_percent': 12.30,
            'c_percent': 10.20,
            'se_percent': 0.95,
            'extraction_percent': 87.30,
            'operator_id': 'Тестовый оператор 3',
            'is_good': False
        }
    ]

    added_count = 0
    for batch in test_batches:
        success = db_manager.add_batch(batch)
        if success:
            added_count += 1
            logger.info(f"Добавлена партия: {batch['batch_id']}")
        else:
            logger.error(f"Ошибка добавления партии: {batch['batch_id']}")

    logger.info(f"Добавлено {added_count} из {len(test_batches)} партий")

    # Проверим добавленные данные
    test_query = "SELECT batch_id, sample_weight, extraction_percent FROM batches ORDER BY batch_id"

    try:
        with db_manager.get_connection() as conn:
            import pandas as pd
            df = pd.read_sql_query(test_query, conn)

            print("\n" + "=" * 60)
            print("ТЕКУЩИЕ ДАННЫЕ В БАЗЕ:")
            print("=" * 60)
            print(df.to_string(index=False))
            print("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка чтения данных: {e}")

    db_manager.close()
    logger.info("Наполнение базы данных завершено")

    return added_count


if __name__ == "__main__":
    seed_database()