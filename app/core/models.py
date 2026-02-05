# app/core/models.py
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')

from app.core.database import DatabaseManager
from app.utils.config import config
from app.utils.logger import logger


class TemperaturePredictor:
    """Модель для прогнозирования температурного режима"""

    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = config.base_dir / 'data' / 'models' / 'temperature_model.pkl'
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

    def prepare_training_data(self, batch_id: str = None) -> Tuple[np.ndarray, np.ndarray]:
        """Подготовка данных для обучения"""
        db = DatabaseManager()

        if batch_id:
            # Данные конкретной партии
            query = f"""
            SELECT * FROM process_data 
            WHERE batch_id = '{batch_id}'
            ORDER BY timestamp
            """
        else:
            # Все успешные партии
            query = """
            SELECT p.* FROM process_data p
            JOIN batches b ON p.batch_id = b.batch_id
            WHERE b.is_good = 1 AND b.extraction_percent >= 85
            ORDER BY p.timestamp
            LIMIT 10000
            """

        df = db.execute_query(query)

        if df.empty:
            logger.warning("Нет данных для обучения")
            return None, None

        # Признаки: предыдущие значения температуры, подача кислоты, ток
        features = []
        targets = []

        for i in range(6, len(df)):
            # Целевая переменная - температура в следующий момент времени
            if i + 1 < len(df):
                target = df.iloc[i + 1]['temperature_1']
                if pd.isna(target):
                    continue

                # Признаки: последние 6 значений
                window = df.iloc[i - 5:i + 1]
                feature_row = []

                for col in ['temperature_1', 'temperature_2', 'temperature_3', 'acid_flow', 'current_value']:
                    if col in window.columns:
                        feature_row.extend(window[col].fillna(0).values)
                    else:
                        feature_row.extend([0] * 6)

                features.append(feature_row)
                targets.append(target)

        X = np.array(features)
        y = np.array(targets)

        logger.info(f"Подготовлено {len(X)} образцов для обучения")
        return X, y

    def train(self, batch_id: str = None):
        """Обучение модели"""
        try:
            X, y = self.prepare_training_data(batch_id)

            if X is None or len(X) < 100:
                logger.warning("Недостаточно данных для обучения")
                return False

            # Разделение на train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Масштабирование
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Обучение
            self.model.fit(X_train_scaled, y_train)

            # Оценка
            y_pred = self.model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            logger.info(f"Модель обучена. MAE: {mae:.2f}, R²: {r2:.3f}")

            # Сохранение модели
            self.save_model()
            self.is_trained = True

            return True

        except Exception as e:
            logger.error(f"Ошибка обучения модели: {e}")
            return False

    def predict_temperature(self, recent_data: pd.DataFrame) -> Dict:
        """Прогноз температуры на следующий шаг"""
        try:
            if not self.is_trained:
                self.load_model()
                if not self.is_trained:
                    return {"error": "Модель не обучена"}

            # Подготовка последних 6 записей
            if len(recent_data) < 6:
                return {"error": "Недостаточно данных для прогноза"}

            recent_data = recent_data.tail(6).reset_index(drop=True)

            # Формирование признаков
            feature_row = []
            for col in ['temperature_1', 'temperature_2', 'temperature_3', 'acid_flow', 'current_value']:
                if col in recent_data.columns:
                    feature_row.extend(recent_data[col].fillna(0).values)
                else:
                    feature_row.extend([0] * 6)

            X = np.array([feature_row])
            X_scaled = self.scaler.transform(X)

            # Прогноз
            prediction = self.model.predict(X_scaled)[0]

            # Доверительный интервал (упрощенно)
            std_dev = np.std([tree.predict(X_scaled)[0] for tree in self.model.estimators_])

            return {
                'predicted_temperature': float(prediction),
                'confidence_interval': [
                    float(prediction - 1.96 * std_dev),
                    float(prediction + 1.96 * std_dev)
                ],
                'timestamp': datetime.now().isoformat(),
                'recommendation': self.generate_temperature_recommendation(prediction)
            }

        except Exception as e:
            logger.error(f"Ошибка прогнозирования: {e}")
            return {"error": str(e)}

    def generate_temperature_recommendation(self, predicted_temp: float) -> str:
        """Генерация рекомендации по температуре"""
        optimal_range = (85.0, 95.0)  # Оптимальный диапазон

        if predicted_temp < optimal_range[0]:
            return f"Температура низкая ({predicted_temp:.1f}°C). Рекомендуется увеличить нагрев."
        elif predicted_temp > optimal_range[1]:
            return f"Температура высокая ({predicted_temp:.1f}°C). Рекомендуется снизить нагрев."
        else:
            return f"Температура в оптимальном диапазоне ({predicted_temp:.1f}°C). Продолжайте текущий режим."

    def save_model(self):
        """Сохранение модели в файл"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained
            }
            joblib.dump(model_data, self.model_path)
            logger.info(f"Модель сохранена: {self.model_path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения модели: {e}")

    def load_model(self):
        """Загрузка модели из файла"""
        try:
            if self.model_path.exists():
                model_data = joblib.load(self.model_path)
                self.model = model_data['model']
                self.scaler = model_data['scaler']
                self.is_trained = model_data['is_trained']
                logger.info(f"Модель загружена: {self.model_path}")
                return True
            else:
                logger.warning("Файл модели не найден")
                return False
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            return False