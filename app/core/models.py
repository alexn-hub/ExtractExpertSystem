import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')

from app.core.database import DatabaseManager
from app.utils.config import config
from app.utils.logger import logger


class ProcessPredictor:
    def __init__(self, algorithm: str = "RandomForest"):
        self.algorithm = algorithm
        self.horizon = 10
        self.window_size = 6
        self.scaler = StandardScaler()
        self.is_trained = False
        self.trained_keys: List[str] = []
        self.last_mae = 0.0
        self.last_r2 = 0.0

        self.model = self._build_model(algorithm)
        self.model_path = config.base_dir / 'data' / 'models' / 'process_model.pkl'
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

    def _build_model(self, algorithm: str):
        if algorithm == "GradientBoosting":
            base = GradientBoostingRegressor(n_estimators=80, max_depth=5, random_state=42)
            return MultiOutputRegressor(base)
        elif algorithm == "Ridge":
            return Ridge(alpha=1.0)
        else:
            return RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)

    def prepare_training_data(self, unit_name: Optional[str] = None) -> Tuple[
        Optional[np.ndarray], Optional[np.ndarray]]:
        db = DatabaseManager()
        all_batches = db.get_all_batches()
        if not all_batches:
            return None, None

        trend_keys = [p['key'] for p in config.hmi.trend_parameters]
        if not trend_keys:
            return None, None

        self.trained_keys = trend_keys
        features, targets = [], []

        for b in all_batches:
            if unit_name and b.get('unit_name') != unit_name:
                continue

            df = db.get_process_data(b['batch_id'])
            if df.empty or len(df) <= self.window_size + self.horizon:
                continue

            for k in trend_keys:
                if k not in df.columns:
                    df[k] = 0.0

            values_matrix = df[trend_keys].fillna(0.0).astype(float).values

            for i in range(self.window_size - 1, len(values_matrix) - self.horizon):
                window = values_matrix[i - self.window_size + 1: i + 1]
                diffs = window[-1] - window[0]
                feature_vec = np.concatenate([window.flatten(), diffs])
                target_vec = values_matrix[i + self.horizon]

                features.append(feature_vec)
                targets.append(target_vec)

        if not features:
            return None, None

        return np.array(features), np.array(targets)

    def train(self, unit_name: Optional[str] = None) -> bool:
        try:
            X, y = self.prepare_training_data(unit_name=unit_name)
            if X is None or len(X) < 10:
                return False

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            self.model.fit(X_train_scaled, y_train)
            y_pred = self.model.predict(X_test_scaled)

            self.last_mae = float(mean_absolute_error(y_test, y_pred))
            self.last_r2 = float(r2_score(y_test, y_pred))
            self.is_trained = True

            self.save_model()
            return True
        except Exception as e:
            logger.error(f"Ошибка при обучении ML-модели: {e}")
            return False

    def predict_and_advise(
            self,
            recent_live_df: pd.DataFrame,
            reference_df: pd.DataFrame,
            current_minute: int,
            base_target_metric: float
    ) -> Dict:
        trend_params = config.hmi.trend_parameters
        trend_keys = [p['key'] for p in trend_params]
        key_to_label = {p['key']: p.get('label', p['key']) for p in trend_params}
        param_roles = {p['key']: p.get('role', 'state') for p in trend_params}

        if len(recent_live_df) < self.window_size:
            return {"ready": False, "status": f"Накопление данных ({len(recent_live_df)}/{self.window_size})..."}

        if not self.is_trained or self.trained_keys != trend_keys:
            if not self.load_model() or self.trained_keys != trend_keys:
                self.train()

        if not self.is_trained:
            return {"ready": False, "status": "Недостаточно данных для ИИ."}

        tail_df = recent_live_df.tail(self.window_size).copy()
        for k in trend_keys:
            if k not in tail_df.columns:
                tail_df[k] = 0.0

        window = tail_df[trend_keys].fillna(0.0).astype(float).values
        diffs = window[-1] - window[0]
        feature_vec = np.concatenate([window.flatten(), diffs])

        X_scaled = self.scaler.transform([feature_vec])
        pred_vec = self.model.predict(X_scaled)[0]
        predictions_t10 = {k: float(val) for k, val in zip(trend_keys, pred_vec)}

        ref_idx = min(current_minute + self.horizon, len(reference_df) - 1)
        ref_row_t10 = reference_df.iloc[ref_idx].to_dict() if not reference_df.empty else {}

        ref_curr_idx = min(current_minute, len(reference_df) - 1)
        ref_curr_row = reference_df.iloc[ref_curr_idx].to_dict() if not reference_df.empty else {}

        advices = []
        total_rel_deviation = 0.0
        active_trends_count = 0

        for k in trend_keys:
            pred_val = predictions_t10[k]
            ref_val = float(ref_row_t10.get(k, 0.0))
            ref_curr_val = float(ref_curr_row.get(k, 0.0))
            role = param_roles.get(k, 'state')

            if abs(ref_val) < 1e-4 and abs(pred_val) < 1e-4:
                continue

            active_trends_count += 1
            diff = pred_val - ref_val
            rel_dev = abs(diff) / (abs(ref_val) if abs(ref_val) > 1.0 else 1.0)
            total_rel_deviation += rel_dev

            step_change = ref_val - ref_curr_val
            is_upcoming_step = abs(step_change) > 2.0

            # Советы генерируем только для управляющих параметров (control)
            if role == 'control':
                if is_upcoming_step:
                    action = "УВЕЛИЧИТЬ" if step_change > 0 else "СНИЗИТЬ"
                    advices.append(
                        f"• <b>[ПЛАНОВО] {key_to_label[k]}</b>: смена режима → {action} до <b>{ref_val:.1f}</b>")
                elif rel_dev > 0.06 and abs(diff) > 1.0:
                    action = "снизить" if diff > 0 else "увеличить"
                    advices.append(
                        f"• <b>[УПРАВЛЕНИЕ] {key_to_label[k]}</b>: прогноз {pred_val:.1f} → {action.upper()}!")

        avg_dev = (total_rel_deviation / active_trends_count) if active_trends_count > 0 else 0.0
        penalty = min(20.0, avg_dev * 25.0)
        estimated_target = max(0.0, base_target_metric - penalty)

        return {
            "ready": True,
            "predictions_t10": predictions_t10,
            "ref_t10": ref_row_t10,
            "estimated_target": estimated_target,
            "base_target": base_target_metric,
            "advices": advices,
            "r2": self.last_r2,
            "mae": self.last_mae,
            "algorithm": self.algorithm
        }

    def save_model(self):
        try:
            joblib.dump({
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained,
                'trained_keys': self.trained_keys,
                'last_mae': self.last_mae,
                'last_r2': self.last_r2,
                'algorithm': self.algorithm
            }, self.model_path)
        except Exception as e:
            logger.error(f"Ошибка сохранения модели: {e}")

    def load_model(self) -> bool:
        try:
            if self.model_path.exists():
                data = joblib.load(self.model_path)
                self.model = data['model']
                self.scaler = data['scaler']
                self.is_trained = data['is_trained']
                self.trained_keys = data.get('trained_keys', [])
                self.last_mae = data.get('last_mae', 0.0)
                self.last_r2 = data.get('last_r2', 0.0)
                self.algorithm = data.get('algorithm', 'RandomForest')
                return True
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
        return False