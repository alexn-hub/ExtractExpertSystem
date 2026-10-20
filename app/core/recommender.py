# app/core/recommender.py
import json
import logging
from app.utils.config import config

logger = logging.getLogger('expert_system.recommender')


class ProcessRecommender:
    def __init__(self, db_manager):
        self.db = db_manager

    def find_best_match(self, input_data):
        logger.info("--- Запуск поиска эталонной партии ---")

        all_batches = self.db.get_all_batches()
        if not all_batches:
            logger.warning("База данных пуста. Поиск невозможен.")
            return None

        # Получаем название текущего участка/аппарата из входных данных
        target_unit = input_data.get('unit_name')

        candidates = []
        # БЕРЕМ КЛЮЧИ ТОЛЬКО ИЗ СТАТИКИ
        static_keys = [p['key'] for p in config.hmi.static_parameters]

        for batch in all_batches:
            # ЖЕСТКАЯ ПРИВЯЗКА К УЧАСТКУ: пропускаем партии с других участков
            if target_unit and batch.get('unit_name') != target_unit:
                continue

            mass_base = batch.get('sample_weight', 0.0)
            mass_input = input_data.get('sample_weight', 0.0)

            if mass_base == 0: continue
            mass_diff_pct = abs(mass_input - mass_base) / mass_base
            if mass_diff_pct > 0.05: continue

            batch_params = {}
            if batch.get('input_params'):
                try:
                    batch_params = json.loads(batch['input_params'])
                except:
                    pass

            mismatches = 0
            for key in static_keys:
                val_base = float(batch_params.get(key, 0.0))
                val_input = float(input_data.get(key, 0.0))

                threshold = val_base * 0.05
                if abs(val_input - val_base) > threshold:
                    mismatches += 1

            allowed_mismatches = max(1, len(static_keys) // 2)
            if mismatches <= allowed_mismatches:
                candidates.append(batch)

        if not candidates:
            logger.error(f"Подходящих партий для участка '{target_unit}' не обнаружено!")
            return None

        best_match = max(candidates, key=lambda x: x.get('target_metric', 0.0))

        logger.info(f"Найдено подходящих кандидатов для {target_unit}: {len(candidates)}")
        logger.info(f"ВЫБРАНА ЛУЧШАЯ ПАРТИЯ: {best_match['batch_id']} (Участок: {best_match.get('unit_name')})")
        return best_match