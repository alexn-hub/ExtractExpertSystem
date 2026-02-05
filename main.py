import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from app.core.database import DatabaseManager
from app.core.recommender import ProcessRecommender
from app.gui.input_screen import InputScreen
from app.gui.work_screen import WorkScreen

# Добавляем путь к проекту в sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ExtractExpertSystem")
        self.resize(1280, 900)

        self.db = DatabaseManager()
        self.recommender = ProcessRecommender(self.db)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.input_screen = InputScreen()
        self.work_screen = WorkScreen()

        self.stacked_widget.addWidget(self.input_screen)
        self.stacked_widget.addWidget(self.work_screen)

        self.work_screen.btn_sfr3.clicked.connect(self.switch_to_sfr)
        self.work_screen.btn_sfr4.clicked.connect(self.switch_to_sfr)
        self.work_screen.btn_stop.clicked.connect(self.stop_process)

        self.input_screen.btn_start.clicked.connect(self.handle_start_process)

    def switch_to_sfr(self):
        sender = self.sender()
        # Устанавливаем выбор в комбобоксе на экране ввода
        self.input_screen.combo_sfr.setCurrentText(sender.text())
        # Возвращаемся на экран ввода
        self.stacked_widget.setCurrentIndex(0)

    def stop_process(self):
        # Логика сброса текущей работы
        self.stacked_widget.setCurrentIndex(0)

    def handle_start_process(self):
        raw_data = self.input_screen.get_data()
        best_match = self.recommender.find_best_match(raw_data)

        if best_match:
            batch_id = best_match['batch_id']
            history_df = self.db.get_process_data(batch_id)

            if not history_df.empty:
                self.work_screen.update_data(best_match, history_df)
                self.stacked_widget.setCurrentIndex(1)
            else:
                QMessageBox.warning(self, "Ошибка", f"Данные процесса для партии {batch_id} не найдены.")
        else:
            QMessageBox.information(self, "Поиск", "В базе знаний не найдено похожих партий для сравнения.")


if __name__ == "__main__":
    # 1. Создаем экземпляр приложения
    app = QApplication(sys.argv)

    # 2. Создаем и показываем главное окно
    window = MainWindow()
    window.show()
    # 3. Запускаем цикл обработки событий
    sys.exit(app.exec_())