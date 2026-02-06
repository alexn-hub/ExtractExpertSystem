import sys
from pathlib import Path

# Добавляем корневую директорию в путь Python, чтобы импорты app работали
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import pandas as pd

# Импортируем ваш класс
from app.core.database import DatabaseManager


class SimpleDBManager(QWidget):
    def __init__(self):
        super().__init__()
        # Используем ваш менеджер
        self.db_manager = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("SulfateDB Explorer (DatabaseManager Edition)")
        self.resize(1000, 700)

        layout = QVBoxLayout(self)

        # Поле ввода запроса
        layout.addWidget(QLabel("Введите SQL запрос (например, SELECT * FROM process_data):"))
        self.query_input = QTextEdit()
        self.query_input.setFont(QFont("Monospace", 11))
        # Запрос по умолчанию
        self.query_input.setText("SELECT * FROM process_data ORDER BY id DESC LIMIT 50")
        self.query_input.setMaximumHeight(150)
        layout.addWidget(self.query_input)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Выполнить запрос")
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #1976D2; 
                color: white; 
                font-weight: bold; 
                height: 40px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1565C0; }
        """)
        self.btn_run.clicked.connect(self.execute_query)

        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.clicked.connect(lambda: self.query_input.clear())

        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

        # Таблица результатов
        layout.addWidget(QLabel("Результаты:"))
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Статус-бар
        self.status_label = QLabel("Готов к работе")
        layout.addWidget(self.status_label)

    def execute_query(self):
        query = self.query_input.toPlainText().strip()
        if not query:
            return

        try:
            # Получаем соединение через ваш db_manager
            with self.db_manager.get_connection() as conn:
                # Используем pandas для загрузки данных
                df = pd.read_sql_query(query, conn)

                self.display_data(df)
                self.status_label.setText(f"Успешно: получено строк: {len(df)}")
                self.status_label.setStyleSheet("color: green")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка SQL", f"Произошла ошибка: {str(e)}")
            self.status_label.setText("Ошибка при выполнении")
            self.status_label.setStyleSheet("color: red")

    def display_data(self, df):
        # Очистка таблицы
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

        if df.empty:
            return

        self.table.setRowCount(df.shape[0])
        self.table.setColumnCount(df.shape[1])
        self.table.setHorizontalHeaderLabels(df.columns)

        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                val = str(df.iat[i, j])
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)  # Только для чтения
                self.table.setItem(i, j, item)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def closeEvent(self, event):
        # Закрываем менеджер при закрытии окна
        self.db_manager.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleDBManager()
    window.show()
    sys.exit(app.exec_())