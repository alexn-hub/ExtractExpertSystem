# app/gui/main_window.py - в начале файла
import sys
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QFormLayout, QMessageBox, QTextEdit, QSplitter,
    QHeaderView, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont

from app.core.database import DatabaseManager
from app.utils.logger import logger

# Эти импорты должны быть ТОЛЬКО здесь:
from app.gui.process_monitor_widget import ProcessMonitorWidget
from app.gui.visualization_widget import ProcessVisualizationWidget

class BatchInputWidget(QWidget):
    """Виджет для ввода данных партии"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Ввод данных новой пробы")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Группа основных данных
        basic_group = QGroupBox("Основные данные")
        basic_layout = QFormLayout()

        self.batch_id_input = QLineEdit()
        self.batch_id_input.setPlaceholderText("Например: P-2024-001")
        basic_layout.addRow("Номер партии:", self.batch_id_input)

        self.sulfate_number_input = QSpinBox()
        self.sulfate_number_input.setRange(1, 10)
        self.sulfate_number_input.setValue(3)
        basic_layout.addRow("Номер сульфатизатора:", self.sulfate_number_input)

        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        basic_layout.addRow("Дата начала:", self.date_input)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0, 10000)
        self.weight_input.setDecimals(2)
        self.weight_input.setValue(1000.0)
        basic_layout.addRow("Масса (сух.), кг:", self.weight_input)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Группа химического состава
        chem_group = QGroupBox("Химический состав (%)")
        chem_layout = QFormLayout()

        self.ni_input = QDoubleSpinBox()
        self.ni_input.setRange(0, 100)
        self.ni_input.setDecimals(2)
        self.ni_input.setValue(0.0)
        chem_layout.addRow("Ni:", self.ni_input)

        self.cu_input = QDoubleSpinBox()
        self.cu_input.setRange(0, 100)
        self.cu_input.setDecimals(2)
        self.cu_input.setValue(0.0)
        chem_layout.addRow("Cu:", self.cu_input)

        self.pt_input = QDoubleSpinBox()
        self.pt_input.setRange(0, 100)
        self.pt_input.setDecimals(2)
        self.pt_input.setValue(0.0)
        chem_layout.addRow("Pt:", self.pt_input)

        self.pd_input = QDoubleSpinBox()
        self.pd_input.setRange(0, 100)
        self.pd_input.setDecimals(2)
        self.pd_input.setValue(0.0)
        chem_layout.addRow("Pd:", self.pd_input)

        self.sio2_input = QDoubleSpinBox()
        self.sio2_input.setRange(0, 100)
        self.sio2_input.setDecimals(2)
        self.sio2_input.setValue(0.0)
        chem_layout.addRow("SiO₂:", self.sio2_input)

        self.c_input = QDoubleSpinBox()
        self.c_input.setRange(0, 100)
        self.c_input.setDecimals(2)
        self.c_input.setValue(0.0)
        chem_layout.addRow("C:", self.c_input)

        self.se_input = QDoubleSpinBox()
        self.se_input.setRange(0, 100)
        self.se_input.setDecimals(2)
        self.se_input.setValue(0.0)
        chem_layout.addRow("Se:", self.se_input)

        chem_group.setLayout(chem_layout)
        layout.addWidget(chem_group)

        # Группа результатов
        result_group = QGroupBox("Результаты")
        result_layout = QFormLayout()

        self.extraction_input = QDoubleSpinBox()
        self.extraction_input.setRange(0, 100)
        self.extraction_input.setDecimals(2)
        self.extraction_input.setValue(0.0)
        result_layout.addRow("Извлечение, %:", self.extraction_input)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # Кнопки
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_form)

        self.save_btn = QPushButton("Сохранить в БД")
        self.save_btn.clicked.connect(self.save_batch)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white;")

        self.find_similar_btn = QPushButton("Найти похожие")
        self.find_similar_btn.clicked.connect(self.find_similar)
        self.find_similar_btn.setStyleSheet("background-color: #2196F3; color: white;")

        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.find_similar_btn)

        layout.addLayout(button_layout)

        # Область результатов поиска
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        self.setLayout(layout)



    def clear_form(self):
        """Очистка формы"""
        self.batch_id_input.clear()
        self.sulfate_number_input.setValue(3)
        self.date_input.setDate(QDate.currentDate())
        self.weight_input.setValue(0.0)
        self.ni_input.setValue(0.0)
        self.cu_input.setValue(0.0)
        self.pt_input.setValue(0.0)
        self.pd_input.setValue(0.0)
        self.sio2_input.setValue(0.0)
        self.c_input.setValue(0.0)
        self.se_input.setValue(0.0)
        self.extraction_input.setValue(0.0)
        self.result_label.setText("")

    def save_batch(self):
        """Сохранение партии в БД"""
        try:
            batch_data = self.get_batch_data()

            if not batch_data['batch_id']:
                QMessageBox.warning(self, "Ошибка", "Введите номер партии")
                return

            success = self.db_manager.add_batch(batch_data)

            if success:
                QMessageBox.information(self, "Успех", f"Партия {batch_data['batch_id']} сохранена!")
                self.clear_form()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось сохранить партию")

        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {str(e)}")

    def find_similar(self):
        """Поиск похожих партий"""
        try:
            sample_data = {
                'sample_weight': self.weight_input.value(),
                'ni_percent': self.ni_input.value(),
                'cu_percent': self.cu_input.value(),
                'pt_percent': self.pt_input.value(),
                'pd_percent': self.pd_input.value()
            }

            similar = self.db_manager.find_similar_batches(sample_data)

            if len(similar) > 0:
                best_match = similar.iloc[0]
                result_text = f"""
                <h3>Найдено {len(similar)} похожих партий</h3>
                <b>Лучшее соответствие:</b> Партия {best_match['batch_id']}<br>
                <b>Извлечение:</b> {best_match['extraction_percent']}%<br>
                <b>Масса:</b> {best_match['sample_weight']} кг<br>
                <b>Состав:</b> Ni={best_match['ni_percent']}%, Cu={best_match['cu_percent']}%, 
                Pt={best_match['pt_percent']}%, Pd={best_match['pd_percent']}%<br>
                <br>
                <i>Рекомендуется использовать параметры этой партии как эталон.</i>
                """
                self.result_label.setText(result_text)
            else:
                self.result_label.setText("<span style='color: red'>Похожих партий не найдено</span>")

        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            self.result_label.setText(f"<span style='color: red'>Ошибка поиска: {str(e)}</span>")

    def get_batch_data(self):
        """Получение данных из формы"""
        return {
            'batch_id': self.batch_id_input.text().strip(),
            'extraction_date': self.date_input.date().toString("yyyy-MM-dd"),
            'sulfate_number': self.sulfate_number_input.value(),
            'sample_weight': self.weight_input.value(),
            'ni_percent': self.ni_input.value(),
            'cu_percent': self.cu_input.value(),
            'pt_percent': self.pt_input.value(),
            'pd_percent': self.pd_input.value(),
            'sio2_percent': self.sio2_input.value(),
            'c_percent': self.c_input.value(),
            'se_percent': self.se_input.value(),
            'extraction_percent': self.extraction_input.value(),
            'operator_id': 'GUI_OPERATOR'
        }


class DatabaseQueryWidget(QWidget):
    """Виджет для SQL запросов к БД"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Менеджер базы данных (только SELECT)")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Поле ввода SQL
        sql_group = QGroupBox("SQL запрос")
        sql_layout = QVBoxLayout()

        self.sql_input = QTextEdit()
        self.sql_input.setPlaceholderText("Введите SELECT запрос...\nНапример: SELECT * FROM batches LIMIT 10")
        self.sql_input.setMaximumHeight(100)
        sql_layout.addWidget(self.sql_input)

        # Кнопки запросов
        button_layout = QHBoxLayout()

        self.execute_btn = QPushButton("Выполнить")
        self.execute_btn.clicked.connect(self.execute_query)
        self.execute_btn.setStyleSheet("background-color: #2196F3; color: white;")

        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_query)

        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.clear_btn)

        sql_layout.addLayout(button_layout)
        sql_group.setLayout(sql_layout)
        layout.addWidget(sql_group)

        # Таблица результатов
        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        layout.addWidget(self.result_table)

        # Статус
        self.status_label = QLabel("Готово")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def execute_query(self):
        """Выполнение SQL запроса"""
        query = self.sql_input.toPlainText().strip()

        if not query:
            QMessageBox.warning(self, "Ошибка", "Введите SQL запрос")
            return

        # Проверка, что это SELECT запрос
        if not query.lower().strip().startswith('select'):
            QMessageBox.warning(self, "Ошибка", "Разрешены только SELECT запросы")
            return

        try:
            # Выполняем запрос
            df = self.db_manager.execute_query(query)

            if df.empty:
                self.result_table.setRowCount(0)
                self.result_table.setColumnCount(0)
                self.status_label.setText("Запрос выполнен, но данных не найдено")
                return

            # Отображаем результат в таблице
            self.display_dataframe(df)
            self.status_label.setText(f"Найдено {len(df)} записей")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения запроса:\n{str(e)}")
            self.status_label.setText(f"Ошибка: {str(e)}")

    def display_dataframe(self, df):
        """Отображение DataFrame в таблице"""
        rows, cols = df.shape

        self.result_table.setRowCount(rows)
        self.result_table.setColumnCount(cols)
        self.result_table.setHorizontalHeaderLabels(df.columns)

        for i in range(rows):
            for j in range(cols):
                value = df.iloc[i, j]
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)  # Не редактируемый
                self.result_table.setItem(i, j, item)

        # Автоматическая ширина столбцов
        self.result_table.resizeColumnsToContents()
        self.result_table.horizontalHeader().setStretchLastSection(True)

    def clear_query(self):
        """Очистка запроса и результатов"""
        self.sql_input.clear()
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self.status_label.setText("Готово")


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Экспертная система извлечения драгметаллов")
        self.setGeometry(100, 100, 1200, 800)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)

        # Верхняя панель
        top_layout = QHBoxLayout()

        title = QLabel("🏭 Экспертная система управления процессом сульфатизации")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)

        top_layout.addWidget(title)
        top_layout.addStretch()

        self.status_label = QLabel("✅ База данных подключена")
        top_layout.addWidget(self.status_label)

        main_layout.addLayout(top_layout)

        # Tab widget
        self.tabs = QTabWidget()

        # Вкладка 1: Ввод данных
        self.input_widget = BatchInputWidget(self.db_manager)
        self.tabs.addTab(self.input_widget, "📝 Ввод новой пробы")

        # Вкладка 2: Поиск в БД
        self.query_widget = DatabaseQueryWidget(self.db_manager)
        self.tabs.addTab(self.query_widget, "🔍 Поиск в БД")

        # Вкладка 3: Мониторинг процесса
        self.monitor_widget = ProcessMonitorWidget(self.db_manager)
        self.tabs.addTab(self.monitor_widget, "📊 Мониторинг процесса")

        # Вкладка 4: Визуализация процесса (НОВАЯ)
        self.visualization_widget = ProcessVisualizationWidget()
        self.tabs.addTab(self.visualization_widget, "🏭 Визуализация")

        main_layout.addWidget(self.tabs)

        # Нижняя панель
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.quit_btn = QPushButton("Выход")
        self.quit_btn.clicked.connect(self.close)
        self.quit_btn.setStyleSheet("background-color: #f44336; color: white;")

        bottom_layout.addWidget(self.quit_btn)
        main_layout.addLayout(bottom_layout)

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        reply = QMessageBox.question(
            self, 'Подтверждение',
            'Вы уверены, что хотите выйти?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.db_manager.close()
            event.accept()
        else:
            event.ignore()


def run_gui():
    """Запуск GUI приложения"""
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern style

    window = MainWindow()
    window.show()

    return app.exec_()