import logging

# Настраиваем логгер для модуля
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

        candidates = []
        features = ['ni_percent', 'cu_percent', 'pt_percent', 'pd_percent',
                    'sio2_percent', 'c_percent', 'se_percent']

        for batch in all_batches:
            # 1. Проверка массы (строго 5%)
            mass_base = batch['sample_weight']
            mass_input = input_data['sample_weight']
            mass_diff_pct = abs(mass_input - mass_base) / mass_base

            if mass_diff_pct > 0.05:
                continue

            # 2. Проверка химии (отклонение не более 5% по каждому элементу)
            mismatches = 0
            for feat in features:
                val_base = batch.get(feat, 0)
                val_input = input_data.get(feat, 0)
                threshold = val_base * 0.05
                if abs(val_input - val_base) > threshold:
                    mismatches += 1

            # Если совпало по большинству элементов (не более 3 ошибок)
            if mismatches <= 3:
                candidates.append(batch)

        # 3. Выбор лучшего среди найденных
        if not candidates:
            logger.error("Подходящих партий по заданным критериям не обнаружено!")
            return None

        # Если нашли несколько, выбираем ту, где МАКСИМАЛЬНОЕ извлечение
        best_match = max(candidates, key=lambda x: x['extraction_percent'])

        logger.info(f"Найдено подходящих кандидатов: {len(candidates)}")
        logger.info(f"ВЫБРАНА ЛУЧШАЯ ПАРТИЯ: {best_match['batch_id']} (Извлечение: {best_match['extraction_percent']}%)")
        logger.info("---------------------------------------")

        return best_match