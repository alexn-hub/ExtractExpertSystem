import logging

# Настраиваем логгер для модуля
logger = logging.getLogger('expert_system.recommender')


class ProcessRecommender:
    def __init__(self, db_manager):
        self.db = db_manager

    def find_best_match(self, input_data):
        logger.info("--- Запуск поиска эталонной партии ---")
        logger.info(
            f"Входные данные: Масса={input_data['sample_weight']}кг, Ni={input_data['ni_percent']}%, Pd={input_data['pd_percent']}%")

        all_batches = self.db.get_all_batches()
        if not all_batches:
            logger.warning("База данных пуста. Поиск невозможен.")
            return None

        candidates = []
        features = ['ni_percent', 'cu_percent', 'pt_percent', 'pd_percent',
                    'sio2_percent', 'c_percent', 'se_percent']

        total_in_db = len(all_batches)
        rejected_by_mass = 0
        rejected_by_chemistry = 0

        for batch in all_batches:
            # 1. Проверка массы (5%)
            mass_base = batch['sample_weight']
            mass_input = input_data['sample_weight']
            mass_diff_pct = abs(mass_input - mass_base) / mass_base

            if mass_diff_pct > 0.05:
                rejected_by_mass += 1
                continue

            # 2. Проверка химии
            mismatches = 0
            mismatch_details = []

            for feat in features:
                val_base = batch.get(feat, 0)
                val_input = input_data.get(feat, 0)
                threshold = val_base * 0.05

                if abs(val_input - val_base) > threshold:
                    mismatches += 1
                    mismatch_details.append(feat)

            if mismatches <= 3:
                candidates.append(batch)
            else:
                rejected_by_chemistry += 1
                # Логируем только если партия была близка по массе, но завалила химию
                logger.debug(f"Партия {batch['batch_id']} отклонена: 4+ несовпадения ({', '.join(mismatch_details)})")

        # Итоговая статистика в лог
        logger.info(f"Всего в БД: {total_in_db}")
        logger.info(f"Отсеяно по массе (>5%): {rejected_by_mass}")
        logger.info(f"Отсеяно по химии (>3 элементов): {rejected_by_chemistry}")
        logger.info(f"Найдено подходящих кандидатов: {len(candidates)}")

        if not candidates:
            logger.error("Подходящих партий не обнаружено!")
            return None

        # 3. Выбор лучшего по извлечению
        best_match = max(candidates, key=lambda x: x['extraction_percent'])

        logger.info(
            f"ВЫБРАНА ЭТАЛОННАЯ ПАРТИЯ: {best_match['batch_id']} (Извлечение: {best_match['extraction_percent']}%)")
        logger.info("---------------------------------------")

        return best_match