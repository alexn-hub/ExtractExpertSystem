import pandas as pd
from datetime import datetime, timedelta
import random
from app.core.database import DatabaseManager


def fill_history_v3():
    db = DatabaseManager()

    # Получаем данные из первой таблицы
    batches = db.execute_query("SELECT batch_id, extraction_date, sulfate_number FROM batches")

    if batches.empty:
        print("❌ Партии не найдены в таблице batches")
        return

    all_process_data = []
    minutes_total = 30 * 60

    for _, row in batches.iterrows():
        batch_id = row['batch_id']
        s_num = row['sulfate_number']

        try:
            start_time = datetime.strptime(row['extraction_date'], '%Y-%m-%d')
        except:
            start_time = datetime.now()

        temp = 42.0
        cumulative_acid = 0.0
        current = 0.0

        for m in range(minutes_total):
            curr_time = start_time + timedelta(minutes=m)

            # Кислота
            acid_flow = 0.033 + random.uniform(-0.002, 0.002)
            if (m > 0) and (m % 360 < 5):
                acid_flow = 5.2 + random.uniform(-0.2, 0.2)
                temp -= 0.6

                # Физика температуры
            temp += (cumulative_acid * 0.0005) + (current * 0.001) - (temp - 30) * 0.001
            temp += random.uniform(-0.05, 0.05)

            # Ток
            if m < 100:
                current += 1.5
            elif m > 1600:
                current -= 0.5
            current = max(0, min(current, 160 + random.uniform(-2, 2)))

            cumulative_acid += acid_flow

            # Новые данные: пока нули или константы
            level_mixer = 0.0
            electrodes_pos = 0.0

            all_process_data.append({
                'batch_id': batch_id,
                'sulfate_number': s_num,
                'timestamp': curr_time.strftime('%Y-%m-%d %H:%M:%S'),
                'temperature_1': round(temp, 2),
                'temperature_2': round(temp - 1.5, 2),
                'temperature_3': round(temp + 1.2, 2),
                'acid_flow': round(acid_flow, 3),
                'current_value': round(current, 2),
                'level_mixer': level_mixer,  # НОВОЕ
                'electrodes_pos': electrodes_pos  # НОВОЕ
            })

        print(f"✅ Обработка {batch_id} (Сульфатизатор {s_num}) завершена")

    df_to_save = pd.DataFrame(all_process_data)

    try:
        with db.get_connection() as conn:
            conn.execute("DELETE FROM process_data")
            df_to_save.to_sql('process_data', conn, if_exists='append', index=False)
            print(f"\n🚀 БАЗА ОБНОВЛЕНА. Записано {len(df_to_save)} строк.")
            print("Параметры: Сульфатизатор, Температура, Кислота, Ток, Уровень, Электроды.")
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")


if __name__ == "__main__":
    fill_history_v3()