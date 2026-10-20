# app/main.py
import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget

# Импорты ваших модулей
from app.core.database import DatabaseManager
from app.core.recommender import ProcessRecommender
from app.gui.sulfate_unit import SulfateUnit  # Класс оставляем, но теперь он универсален!
from app.gui.kb_screen import KnowledgeBaseScreen
from app.utils.config import config  # Наш новый конфигуратор
from app.gui.config_screen import ConfigScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ИСППР Система Советчика (Универсальная)")
        self.resize(1400, 900)

        # Инициализация ядра
        self.db = DatabaseManager()
        self.recommender = ProcessRecommender(self.db)

        # Создаем виджет вкладок
        self.tabs = QTabWidget()

        # --- ДИНАМИЧЕСКАЯ ГЕНЕРАЦИЯ ВКЛАДОК ИЗ CONFIG.YAML ---
        self.units = []
        for unit_name in config.hmi.units:
            # Создаем вкладку с именем из конфига (например, "Участок измельчения 1")
            unit_widget = SulfateUnit(unit_name, self.recommender, self.db)
            self.units.append(unit_widget)
            self.tabs.addTab(unit_widget, unit_name)

        # Создаем экран Базы Знаний
        self.kb_screen = KnowledgeBaseScreen(self.db)
        self.tabs.addTab(self.kb_screen, "БАЗА ЗНАНИЙ")

        self.config_screen = ConfigScreen()
        self.tabs.addTab(self.config_screen, "⚙️ КОНФИГУРАТОР")


        self.setCentralWidget(self.tabs)

        # Обновляем БЗ при переключении
        self.tabs.currentChanged.connect(self.handle_tab_change)

    def handle_tab_change(self, index):
        # Если переключились на последнюю вкладку (БЗ) — обновляем таблицу
        if index == self.tabs.count() - 1:
            self.kb_screen.load_batches()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())