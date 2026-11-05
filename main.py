# app/main.py
import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget

# Импорты модулей
from app.core.database import DatabaseManager
from app.core.recommender import ProcessRecommender
from app.gui.sulfate_unit import SulfateUnit
from app.gui.kb_screen import KnowledgeBaseScreen
from app.utils.config import config
from app.gui.config_screen import ConfigScreen
from app.utils.logger import logger


def load_stylesheet(app: QApplication):
    """Поиск и применение QSS стилей темы Slate Dark"""
    root_dir = Path(__file__).resolve().parent

    candidates = [
        root_dir / 'app' / 'gui' / 'styles.qss',  # Точный путь для запуска из корня проекта
        root_dir / 'gui' / 'styles.qss',  # Если main.py переместят в папку app
        root_dir / 'styles.qss'
    ]

    loaded = False
    for qss_path in candidates:
        if qss_path.is_file():
            try:
                with open(qss_path, 'r', encoding='utf-8') as f:
                    app.setStyleSheet(f.read())
                print(f"[OK] Тема Slate Dark успешно загружена из: {qss_path}")
                loaded = True
                break
            except Exception as e:
                print(f"[ERROR] Ошибка чтения {qss_path}: {e}")

    if not loaded:
        print(f"[WARNING] Файл styles.qss не найден! Искали в: {[str(p) for p in candidates]}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ИСППР СИСТЕМА СОВЕТЧИКА")
        self.resize(1400, 900)

        # Инициализация ядра
        self.db = DatabaseManager()
        self.recommender = ProcessRecommender(self.db)

        # Создаем виджет вкладок
        self.tabs = QTabWidget()
        self.tabs.setObjectName("main_tabs")
        self.tabs.setUsesScrollButtons(True)

        # Динамическая генерация технологических вкладок
        self.units = []
        for unit_name in config.hmi.units:
            unit_widget = SulfateUnit(unit_name, self.recommender, self.db)
            self.units.append(unit_widget)
            self.tabs.addTab(unit_widget, unit_name.upper())

        # Экран Базы Знаний
        self.kb_screen = KnowledgeBaseScreen(self.db)
        self.tabs.addTab(self.kb_screen, "БАЗА ЗНАНИЙ")

        # Экран Конфигуратора (чистый текст без эмодзи)
        self.config_screen = ConfigScreen()
        self.tabs.addTab(self.config_screen, "КОНФИГУРАТОР")

        self.setCentralWidget(self.tabs)

        # Обновление БЗ при переключении
        self.tabs.currentChanged.connect(self.handle_tab_change)

    def handle_tab_change(self, index):
        # Если переключились на вкладку БЗ (предпоследняя вкладка)
        if index == len(self.units):
            self.kb_screen.load_batches()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_stylesheet(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())