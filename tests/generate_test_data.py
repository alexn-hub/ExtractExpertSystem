import pandas as pd
import numpy as np

# Генерируем 60 минут процесса (1 час)
minutes = 60
time_stamps = pd.date_range(start="2026-10-21 08:00:00", periods=minutes, freq="min")

np.random.seed(42)
data = {
    'timestamp': [t.strftime('%Y-%m-%d %H:%M:%S') for t in time_stamps],
    'mill_rpm': np.linspace(10, 80, minutes) + np.random.normal(0, 1.5, minutes),
    'water_flow': np.full(minutes, 12.5) + np.random.normal(0, 0.2, minutes),
    'power_kw': np.linspace(40, 70, minutes) + np.random.normal(0, 2.0, minutes),
    'zhopa': np.zeros(minutes) # Соответствует ключам из вашего config.yaml
}

df = pd.DataFrame(data)
file_path = "test_batch_data.xlsx"
df.to_excel(file_path, index=False)

print(f"✅ Тестовый файл успешно создан: {file_path}")
print("Вы можете импортировать его через интерфейс приложения (вкладка БАЗА ЗНАНИЙ -> Импорт данных).")