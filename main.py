import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox, QTabWidget
from app.core.database import DatabaseManager
from app.core.recommender import ProcessRecommender
from app.gui.input_screen import InputScreen
from app.gui.work_screen import WorkScreen
from app.gui.sulfate_unit import SulfateUnit

# Добавляем путь к проекту в sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Extract Expert System")
        self.setMinimumSize(1200, 800)

        # Ресурсы
        self.db = DatabaseManager()
        self.recommender = ProcessRecommender(self.db)

        # Создаем виджет вкладок
        self.tabs = QTabWidget()

        # Создаем два независимых аппарата
        # У каждого будет свой стэк экранов, свой реактор и свои графики
        self.unit3 = SulfateUnit("СФР-3", self.recommender, self.db)
        self.unit4 = SulfateUnit("СФР-4", self.recommender, self.db)

        self.tabs.addTab(self.unit3, "СФР-3")
        self.tabs.addTab(self.unit4, "СФР-4")

        self.setCentralWidget(self.tabs)

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