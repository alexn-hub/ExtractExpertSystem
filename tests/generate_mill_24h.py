import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from app.core.database import DatabaseManager
from app.utils.config import config


def simulate_mill_curve(
    total_points: int = 360,
    step_minutes: int = 4,
    ore_hardness: float = 12.0,
    fraction_size: float = 30.0,
    mode: str = "optimal",
    seed: int = 42
) -> pd.DataFrame:
    """
    Генерирует суточный цикл мельницы (360 точек по 4 мин = 24 часа, либо 360 минут на таймере)
    с 5 выраженными технологическими фазами (перегибами) и физической связью параметров:
      - Управляющие параметры: mill_rpm (Обороты), water_flow (Вода), rfr (Расход реагента)
      - Параметры состояния (инерционный отклик): power_kw (Мощность), as (Плотность пульпы)
    """
    rng = np.random.default_rng(seed)
    start_time = datetime(2026, 10, 21, 0, 0, 0)
    timestamps = [
        (start_time + timedelta(minutes=i * step_minutes)).strftime('%Y-%m-%d %H:%M:%S')
        for i in range(total_points)
    ]

    # Коэффициент тяжести сырья (зависит от статики: твердости и крупности)
    hardness_factor = (ore_hardness / 12.0) * 0.7 + (fraction_size / 30.0) * 0.3

    mill_rpm = np.zeros(total_points)
    water_flow = np.zeros(total_points)
    rfr_reagent = np.zeros(total_points)
    power_kw = np.zeros(total_points)
    as_density = np.zeros(total_points)

    # Задаем профиль управляющих воздействий с 5 перегибами
    for i in range(total_points):
        if i < 40:
            # Фаза 1: Разгон мельницы
            progress = i / 40.0
            rpm_sp = 45.0 + 25.0 * progress
            water_sp = 10.0 + 6.0 * progress
            rfr_sp = 20.0 + 15.0 * progress
        elif i < 120:
            # Фаза 2: Стабильное плато №1
            rpm_sp = 70.0
            water_sp = 16.0
            rfr_sp = 35.0
        elif i < 200:
            # Фаза 3: ПЕРЕГИБ ВВЕРХ — пошла тяжелая руда (форсированный режим)
            rpm_sp = 82.0
            water_sp = 21.0
            rfr_sp = 48.0
        elif i < 260:
            # Фаза 4: ПЕРЕГИБ ВНИЗ — профилактическая разгрузка и промывка барабана
            rpm_sp = 58.0
            water_sp = 25.0
            rfr_sp = 25.0
        else:
            # Фаза 5: Выход на финальное оптимальное плато
            rpm_sp = 74.0
            water_sp = 17.5
            rfr_sp = 38.0

        # Если генерируем партию с ошибками оператора ("deviated"), вносим просадку на Фазе 3
        if mode == "deviated" and 130 <= i <= 190:
            rpm_sp -= 12.0   # Оператор недодал обороты
            water_sp -= 4.5  # Зажал воду

        mill_rpm[i] = rpm_sp + rng.normal(0, 0.6)
        water_flow[i] = water_sp + rng.normal(0, 0.25)
        rfr_reagent[i] = rfr_sp + rng.normal(0, 0.4)

    # Рассчитываем инерционный отклик Мощности (power_kw) и Плотности пульпы (as)
    # Мощность зависит от оборотов, твердости руды и воды с тепловой/механической инерцией
    power_state = 35.0
    density_state = 45.0

    for i in range(total_points):
        target_power = (
            12.0
            + 0.72 * mill_rpm[i] * hardness_factor
            - 0.45 * water_flow[i]
            + 0.15 * rfr_reagent[i]
        )
        # Инерционный фильтр 1-го порядка (эффект запаздывания на 6-10 шагов!)
        power_state = 0.82 * power_state + 0.18 * target_power
        power_kw[i] = round(power_state + rng.normal(0, 0.7), 2)

        target_density = 65.0 + 0.25 * mill_rpm[i] - 1.1 * water_flow[i]
        density_state = 0.85 * density_state + 0.15 * target_density
        as_density[i] = round(density_state + rng.normal(0, 0.4), 2)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'mill_rpm': np.round(mill_rpm, 2),
        'water_flow': np.round(water_flow, 2),
        'power_kw': np.round(power_kw, 2),
        'rfr': np.round(rfr_reagent, 2),
        'as': np.round(as_density, 2),
        'zhopa': np.round(as_density * 0.1, 2)  # На случай если ключ zhopa остался в конфиге
    })
    return df


def main():
    db = DatabaseManager()
    unit_name = config.hmi.units[0] if config.hmi.units else "Участок измельчения 1"

    # 1. Сохраняем 2 Excel-файла в корень проекта для ручного импорта и экспериментов
    df_ref = simulate_mill_curve(ore_hardness=12.0, fraction_size=30.0, mode="optimal", seed=101)
    df_dev = simulate_mill_curve(ore_hardness=12.0, fraction_size=30.0, mode="deviated", seed=202)

    df_ref.to_excel("mill_24h_reference_94pct.xlsx", index=False)
    df_dev.to_excel("mill_24h_deviated_test.xlsx", index=False)
    print("📁 Созданы Excel-файлы в корне проекта:")
    print("   1) mill_24h_reference_94pct.xlsx (Эталонный суточный цикл с 5 перегибами)")
    print("   2) mill_24h_deviated_test.xlsx   (Цикл с ошибками режима на 130-190 шаге)")

    # 2. Автоматически загружаем в БД серию из 4 партий для качественного обучения ИИ!
    scenarios = [
        {
            "batch_id": "MILL-24H-ETALON-01",
            "sample_weight": 500.0,
            "ore_hardness": 12.0,
            "fraction_size": 30.0,
            "target_metric": 94.5,
            "mode": "optimal",
            "seed": 101
        },
        {
            "batch_id": "MILL-24H-NORM-02",
            "sample_weight": 505.0,
            "ore_hardness": 12.2,
            "fraction_size": 29.5,
            "target_metric": 91.0,
            "mode": "optimal",
            "seed": 102
        },
        {
            "batch_id": "MILL-24H-HARD-03",
            "sample_weight": 600.0,
            "ore_hardness": 15.0,
            "fraction_size": 35.0,
            "target_metric": 92.8,
            "mode": "optimal",
            "seed": 103
        },
        {
            "batch_id": "MILL-24H-BAD-04",
            "sample_weight": 495.0,
            "ore_hardness": 11.8,
            "fraction_size": 30.5,
            "target_metric": 82.0,
            "mode": "deviated",
            "seed": 202
        }
    ]

    for sc in scenarios:
        df_proc = simulate_mill_curve(
            ore_hardness=sc["ore_hardness"],
            fraction_size=sc["fraction_size"],
            mode=sc["mode"],
            seed=sc["seed"]
        )
        batch_data = {
            "batch_id": sc["batch_id"],
            "extraction_date": "2026-10-21",
            "unit_name": unit_name,
            "sample_weight": sc["sample_weight"],
            "target_metric": sc["target_metric"],
            "ore_hardness": sc["ore_hardness"],
            "fraction_size": sc["fraction_size"]
        }
        # Поддержка любых пользовательских ключей статики из config.yaml
        for p in config.hmi.static_parameters:
            k = p['key']
            if k not in batch_data:
                batch_data[k] = float(p.get('default', 10.0))

        db.add_batch(batch_data)
        db.add_process_data(sc["batch_id"], df_proc.to_dict('records'))

    print(f"✅ В базу данных для участка '{unit_name}' успешно загружено 4 суточные партии!")
    print("Теперь ML-модель обучится на 1400+ точках с реальными перегибами и инерцией.")


if __name__ == "__main__":
    main()