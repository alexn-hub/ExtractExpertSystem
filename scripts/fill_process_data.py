import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from app.core.database import DatabaseManager
from app.utils.logger import logger


def fill_history():
    db = DatabaseManager()

    # 1. Получаем список всех партий, которые уже есть в базе
    batches = db.execute_query("SELECT batch_id, extraction_date FROM batches")

    if batches.empty:
        print("❌ В таблице batches пусто. Сначала добавь партии через GUI или SQL.")
        return

    print(f"Найдено партий: {len(batches)}. Генерируем процессные данные...")

    all_process_data = []
    minutes_total = 30 * 60  # 30 часов

    for _, row in batches.iterrows():
        batch_id = row['batch_id']
        # Пробуем распарсить дату
        try:
            start_time = datetime.strptime(row['extraction_date'], '%Y-%m-%d')
        except:
            start_time = datetime.now()

        temp = 40.0  # Начальная температура в реакторе
        cumulative_acid = 0.0
        current = 0.0

        for m in range(minutes_total):
            curr_time = start_time + timedelta(minutes=m)

            # Базовый расход кислоты (шум датчика)
            acid_flow = 0.033 + random.uniform(-0.002, 0.002)

            # Имитация впрыска кислоты (каждые 6 часов на 5 минут)
            if (m > 0) and (m % 360 < 5):
                acid_flow = 5.2 + random.uniform(-0.2, 0.2)
                temp -= 0.6  # Та самая "пила" (охлаждение при впрыске)

            # Физика: температура растет от кислоты и тока, но остывает сама
            temp += (cumulative_acid * 0.0005) + (current * 0.001) - (temp - 30) * 0.001
            temp += random.uniform(-0.05, 0.05)

            # Ток (плавный выход на 150А и спад в конце)
            if m < 100:
                current += 1.5
            elif m > 1600:
                current -= 0.5
            current = max(0, min(current, 160 + random.uniform(-2, 2)))

            cumulative_acid += acid_flow

            all_process_data.append({
                'batch_id': batch_id,
                'timestamp': curr_time.strftime('%Y-%m-%d %H:%M:%S'),
                'temperature_1': round(temp, 2),
                'temperature_2': round(temp - 1.5, 2),
                'temperature_3': round(temp + 1.2, 2),
                'acid_flow': round(acid_flow, 3),
                'current_value': round(current, 2)
            })

        print(f"✅ Подготовлены данные для {batch_id}")

    # Превращаем в DataFrame и сохраняем в БД одним махом
    df_to_save = pd.DataFrame(all_process_data)

    try:
        with db.get_connection() as conn:
            # Очищаем старые данные, чтобы не дублировать
            conn.execute("DELETE FROM process_data")
            # Записываем новые
            df_to_save.to_sql('process_data', conn, if_exists='append', index=False)
            print(f"\n🚀 Успешно записано {len(df_to_save)} строк в таблицу process_data!")
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")


if __name__ == "__main__":
    fill_history()