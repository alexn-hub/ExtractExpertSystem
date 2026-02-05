from PyQt5.QtWidgets import QWidget, QStackedWidget, QVBoxLayout
from app.gui.input_screen import InputScreen
from app.gui.work_screen import WorkScreen


class SulfateUnit(QWidget):
    """
    Этот класс управляет состоянием одного аппарата.
    Он содержит внутри себя 'бутерброд' из двух экранов.
    """

    def __init__(self, unit_name, recommender, db, parent=None):
        super().__init__(parent)
        self.unit_name = unit_name
        self.recommender = recommender
        self.db = db

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Стэк — это как колода карт, видна только верхняя
        self.stack = QStackedWidget()

        # 1. Создаем экран ввода
        self.input_page = InputScreen()
        self.input_page.combo_sfr.setCurrentText(unit_name)
        self.input_page.combo_sfr.setEnabled(False)  # Чтобы нельзя было поменять СФР во вкладке

        # 2. Создаем экран работы
        self.work_page = WorkScreen()

        # Добавляем их в стэк
        self.stack.addWidget(self.input_page)  # индекс 0
        self.stack.addWidget(self.work_page)  # индекс 1

        layout.addWidget(self.stack)

        # При нажатии "ОК" на экране ввода — запускаем расчет
        self.input_page.btn_start.clicked.connect(self.process_start_request)

        self.work_page.btn_stop.clicked.connect(self.return_to_input)

    def return_to_input(self):
        self.work_page.stop_simulation()  # Обязательно гасим таймер
        self.stack.setCurrentIndex(0)

    def process_start_request(self):
        """Логика перехода от ввода к работе"""
        raw_data = self.input_page.get_data()
        best_match = self.recommender.find_best_match(raw_data)

        if best_match:
            # Получаем историю из БД
            history_df = self.db.get_process_data(best_match['batch_id'])

            # Обновляем экран работы данными
            self.work_page.update_data(best_match, history_df)

            # ПЕРЕКЛЮЧАЕМ ЭКРАН на работу внутри этой вкладки
            self.stack.setCurrentWidget(self.work_page)
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Поиск", "Похожих партий не найдено.")