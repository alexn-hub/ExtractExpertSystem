import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_normal_mill_dataset(filename="mill_normal_24h.xlsx", total_points=360, step_minutes=4):
    """
    Генерирует суточный технологический цикл работы мельницы (24 часа, шаги по 4 минуты = 360 точек).
    Включает плавные переходы, технологические перегибы и реальную тепловую/механическую инерцию.
    """
    rng = np.random.default_rng(42)
    start_time = datetime(2026, 10, 21, 0, 0, 0)
    timestamps = [
        (start_time + timedelta(minutes=i * step_minutes)).strftime('%Y-%m-%d %H:%M:%S')
        for i in range(total_points)
    ]

    mill_rpm = np.zeros(total_points)      # Управляющий: Обороты
    water_flow = np.zeros(total_points)    # Управляющий: Расход воды
    reagent_flow = np.zeros(total_points)  # Управляющий: Расход реагента
    power_kw = np.zeros(total_points)      # Контролируемый: Мощность
    pulp_density = np.zeros(total_points)  # Контролируемый: Плотность пульпы
    temperature = np.zeros(total_points)   # Контролируемый: Температура

    # 1. Задаем профиль управляющих воздействий с 4 фазами (перегибами)
    for i in range(total_points):
        if i < 45:
            # Фаза 1: Плавный пуск и набор оборотов
            progress = i / 45.0
            rpm_sp = 40.0 + 30.0 * progress
            water_sp = 12.0 + 4.0 * progress
            reag_sp = 15.0 + 10.0 * progress
        elif i < 150:
            # Фаза 2: Номинальный режим работы
            rpm_sp = 72.0
            water_sp = 16.5
            reag_sp = 25.0
        elif i < 230:
            # Фаза 3: Перегиб — поступает более плотная руда, форсируем нагрузку
            rpm_sp = 82.0
            water_sp = 20.0
            reag_sp = 32.0
        elif i < 290:
            # Фаза 4: Разгрузка / промывка барабана
            rpm_sp = 55.0
            water_sp = 24.0
            reag_sp = 18.0
        else:
            # Фаза 5: Возврат на стабильное плато
            rpm_sp = 75.0
            water_sp = 17.0
            reag_sp = 26.0

        mill_rpm[i] = rpm_sp + rng.normal(0, 0.4)
        water_flow[i] = water_sp + rng.normal(0, 0.15)
        reagent_flow[i] = reag_sp + rng.normal(0, 0.3)

    # 2. Моделируем инерционный отклик контролируемых параметров
    power_state = 30.0
    density_state = 50.0
    temp_state = 35.0

    for i in range(total_points):
        # Мощность зависит от оборотов с запаздыванием (инерцией)
        target_power = 15.0 + 0.75 * mill_rpm[i] - 0.3 * water_flow[i]
        power_state = 0.85 * power_state + 0.15 * target_power
        power_kw[i] = round(power_state + rng.normal(0, 0.5), 2)

        # Плотность пульпы
        target_density = 68.0 + 0.2 * mill_rpm[i] - 1.2 * water_flow[i]
        density_state = 0.88 * density_state + 0.12 * target_density
        pulp_density[i] = round(density_state + rng.normal(0, 0.3), 2)

        # Температура (тепловая инерция от мощности и реагента)
        target_temp = 25.0 + 0.5 * power_kw[i] + 0.3 * reagent_flow[i]
        temp_state = 0.92 * temp_state + 0.08 * target_temp
        temperature[i] = round(temp_state + rng.normal(0, 0.2), 2)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'mill_rpm': np.round(mill_rpm, 2),
        'water_flow': np.round(water_flow, 2),
        'reagent_flow': np.round(reagent_flow, 2),
        'power_kw': np.round(power_kw, 2),
        'pulp_density': np.round(pulp_density, 2),
        'temperature': np.round(temperature, 2)
    })

    df.to_excel(filename, index=False)
    print(f"✅ Успешно создан файл с нормальными параметрами мельницы: {filename}")

if __name__ == "__main__":
    generate_normal_mill_dataset()