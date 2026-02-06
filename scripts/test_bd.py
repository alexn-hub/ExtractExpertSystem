# scripts/update_electrodes.py
import sys
import random
from pathlib import Path

# Добавляем корневую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import DatabaseManager
from app.utils.logger import logger


def update_electrodes_position():
    """Обновление уровня электродов (electrodes_pos) во всей таблице process_data"""
    logger.info("Запуск обновления позиций электродов...")

    db_manager = DatabaseManager()

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Получаем список всех уникальных партий
            cursor.execute("SELECT DISTINCT batch_id FROM process_data")
            batches = [row[0] for row in cursor.fetchall()]

            if not batches:
                logger.warning("Записей в таблице process_data не обнаружено.")
                return

            logger.info(f"Найдено партий для обновления: {len(batches)}")

            total_rows_updated = 0
            for b_id in batches:
                # Генерируем значение 25.0 +/- 2.0
                new_pos = round(25.0 + random.uniform(-2.0, 2.0), 2)

                # Обновляем столбец electrodes_pos для конкретной партии
                cursor.execute(
                    "UPDATE process_data SET electrodes_pos = ? WHERE batch_id = ?",
                    (new_pos, b_id)
                )
                total_rows_updated += cursor.rowcount
                logger.info(f"Партия {b_id}: установлено значение {new_pos} (строк: {cursor.rowcount})")

            conn.commit()
            logger.info(f"Обновление завершено успешно. Всего затронуто строк: {total_rows_updated}")

            # 2. Контрольный вывод первых 10 строк для проверки
            import pandas as pd
            check_df = pd.read_sql_query(
                "SELECT batch_id, electrodes_pos, current_value FROM process_data LIMIT 10",
                conn
            )
            print("\n" + "=" * 60)
            print("ПРОВЕРКА ДАННЫХ (ПЕРВЫЕ 10 СТРОК):")
            print("=" * 60)
            print(check_df.to_string(index=False))
            print("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка при выполнении UPDATE: {e}")
    finally:
        db_manager.close()


if __name__ == "__main__":
    update_electrodes_position()