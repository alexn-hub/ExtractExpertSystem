# app/gui/process_monitor_widget.py
import sys
from datetime import datetime
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QGridLayout,
    QSplitter, QTabWidget, QTextEdit, QSpinBox, QDoubleSpinBox,
    QComboBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import pyqtgraph as pg
import numpy as np

from app.core.recommender import ProcessRecommender
from app.core.models import TemperaturePredictor
from app.core.database import DatabaseManager


class ProcessMonitorWidget(QWidget):
    """Виджет мониторинга и рекомендаций процесса"""

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.recommender = ProcessRecommender(db_manager)
        self.predictor = TemperaturePredictor()
        self.current_batch_id = None
        self.process_data = None

        self.init_ui()
        self.init_graphs()

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("📊 Мониторинг процесса и рекомендации")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Верхняя панель с выбором партии
        top_panel = QHBoxLayout()

        self.batch_label = QLabel("Партия для анализа:")
        top_panel.addWidget(self.batch_label)

        self.batch_combo = QComboBox()
        self.batch_combo.currentTextChanged.connect(self.load_batch_data)
        top_panel.addWidget(self.batch_combo)

        self.refresh_btn = QPushButton("Обновить список")
        self.refresh_btn.clicked.connect(self.refresh_batch_list)
        top_panel.addWidget(self.refresh_btn)

        self.train_model_btn = QPushButton("Обучить модель")
        self.train_model_btn.clicked.connect(self.train_prediction_model)
        top_panel.addWidget(self.train_model_btn)

        top_panel.addStretch()
        layout.addLayout(top_panel)

        # Splitter для графиков и таблиц
        splitter = QSplitter(Qt.Vertical)

        # Графики
        graph_widget = QWidget()
        graph_layout = QHBoxLayout(graph_widget)

        self.temp_plot = pg.PlotWidget(title="Температура")
        self.temp_plot.showGrid(x=True, y=True)
        self.temp_plot.setLabel('left', 'Температура', '°C')
        self.temp_plot.setLabel('bottom', 'Время', 'мин')
        graph_layout.addWidget(self.temp_plot)

        self.acid_plot = pg.PlotWidget(title="Подача кислоты")
        self.acid_plot.showGrid(x=True, y=True)
        self.acid_plot.setLabel('left', 'Расход', 'л/ч')
        self.acid_plot.setLabel('bottom', 'Время', 'мин')
        graph_layout.addWidget(self.acid_plot)

        splitter.addWidget(graph_widget)

        # Таблицы с рекомендациями
        table_widget = QTabWidget()

        # Таблица графика кислоты
        self.acid_table = QTableWidget()
        self.acid_table.setColumnCount(5)
        self.acid_table.setHorizontalHeaderLabels(['Время (мин)', 'Момент', 'Расход', 'Температура', 'Ток'])
        table_widget.addTab(self.acid_table, "📅 График подачи кислоты")

        # Таблица событий
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(4)
        self.events_table.setHorizontalHeaderLabels(['Время', 'Тип события', 'Параметр', 'Изменение'])
        table_widget.addTab(self.events_table, "⚠️ Ключевые события")

        # Прогноз температуры
        self.prediction_text = QTextEdit()
        self.prediction_text.setReadOnly(True)
        table_widget.addTab(self.prediction_text, "🔮 Прогноз температуры")

        splitter.addWidget(table_widget)
        splitter.setSizes([400, 300])

        layout.addWidget(splitter)

        # Статусная строка
        self.status_label = QLabel("Готов к работе")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        # Таймер для автообновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(30000)  # 30 секунд

        # Загрузка начальных данных
        self.refresh_batch_list()

    def init_graphs(self):
        """Инициализация графиков"""
        # Температура
        self.temp_curve_1 = self.temp_plot.plot(pen=pg.mkPen(color='r', width=2), name='Темп. 1')
        self.temp_curve_2 = self.temp_plot.plot(pen=pg.mkPen(color='g', width=2), name='Темп. 2')
        self.temp_curve_3 = self.temp_plot.plot(pen=pg.mkPen(color='b', width=2), name='Темп. 3')

        # Подача кислоты
        self.acid_curve = self.acid_plot.plot(pen=pg.mkPen(color='m', width=2), name='Кислота')

        # Ток
        self.current_curve = self.acid_plot.plot(pen=pg.mkPen(color='y', width=2), name='Ток')

        # Легенда
        self.temp_plot.addLegend()
        self.acid_plot.addLegend()

    def refresh_batch_list(self):
        """Обновление списка партий"""
        try:
            query = """
            SELECT batch_id, extraction_date, extraction_percent 
            FROM batches 
            WHERE is_good = 1 
            ORDER BY extraction_date DESC 
            LIMIT 50
            """

            df = self.db.execute_query(query)

            self.batch_combo.clear()
            for _, row in df.iterrows():
                display_text = f"{row['batch_id']} ({row['extraction_date']}) - {row['extraction_percent']}%"
                self.batch_combo.addItem(display_text, row['batch_id'])

            if self.batch_combo.count() > 0:
                self.batch_combo.setCurrentIndex(0)
                self.load_batch_data()

        except Exception as e:
            self.status_label.setText(f"Ошибка загрузки списка: {str(e)}")

    def load_batch_data(self):
        """Загрузка данных выбранной партии"""
        if self.batch_combo.count() == 0:
            return

        batch_id = self.batch_combo.currentData()
        self.current_batch_id = batch_id

        try:
            # Загрузка процессных данных
            self.process_data = self.db.get_process_data(batch_id)

            if not self.process_data.empty:
                self.update_graphs()
                self.generate_recommendations()
                self.update_prediction()
                self.status_label.setText(f"Данные партии {batch_id} загружены")
            else:
                self.status_label.setText(f"Нет процессных данных для {batch_id}")

        except Exception as e:
            self.status_label.setText(f"Ошибка загрузки: {str(e)}")

    def update_graphs(self):
        """Обновление графиков"""
        if self.process_data is None or self.process_data.empty:
            return

        # Подготовка данных
        time_idx = np.arange(len(self.process_data))

        # Температура
        if 'temperature_1' in self.process_data.columns:
            temp1 = self.process_data['temperature_1'].fillna(0).values
            self.temp_curve_1.setData(time_idx, temp1)

        if 'temperature_2' in self.process_data.columns:
            temp2 = self.process_data['temperature_2'].fillna(0).values
            self.temp_curve_2.setData(time_idx, temp2)

        if 'temperature_3' in self.process_data.columns:
            temp3 = self.process_data['temperature_3'].fillna(0).values
            self.temp_curve_3.setData(time_idx, temp3)

        # Подача кислоты и ток
        if 'acid_flow' in self.process_data.columns:
            acid = self.process_data['acid_flow'].fillna(0).values
            self.acid_curve.setData(time_idx, acid)

        if 'current_value' in self.process_data.columns:
            current = self.process_data['current_value'].fillna(0).values
            self.current_curve.setData(time_idx, current)

    def generate_recommendations(self):
        """Генерация рекомендаций"""
        if self.current_batch_id is None:
            return

        try:
            # Получение рекомендаций
            batch_info = self.db.execute_query(
                f"SELECT * FROM batches WHERE batch_id = '{self.current_batch_id}'"
            ).iloc[0].to_dict()

            recommendations = self.recommender.generate_recommendation(self.current_batch_id)

            # Заполнение таблицы графика кислоты
            acid_schedule = recommendations.get('acid_schedule', [])
            self.acid_table.setRowCount(len(acid_schedule))

            for i, event in enumerate(acid_schedule):
                self.acid_table.setItem(i, 0, QTableWidgetItem(str(event.get('time_minute', ''))))
                self.acid_table.setItem(i, 1, QTableWidgetItem(str(event.get('timestamp', ''))))
                self.acid_table.setItem(i, 2, QTableWidgetItem(str(event.get('acid_flow', ''))))
                self.acid_table.setItem(i, 3, QTableWidgetItem(str(event.get('temperature_1', ''))))
                self.acid_table.setItem(i, 4, QTableWidgetItem(str(event.get('current', ''))))

            # Заполнение таблицы событий
            key_events = recommendations.get('key_events', [])
            self.events_table.setRowCount(len(key_events))

            for i, event in enumerate(key_events):
                self.events_table.setItem(i, 0, QTableWidgetItem(str(event.get('time_minute', ''))))
                self.events_table.setItem(i, 1, QTableWidgetItem(event.get('type', '')))
                self.events_table.setItem(i, 2, QTableWidgetItem(event.get('parameter', '')))
                self.events_table.setItem(i, 3, QTableWidgetItem(str(event.get('change', ''))))

        except Exception as e:
            self.status_label.setText(f"Ошибка генерации рекомендаций: {str(e)}")

    def update_prediction(self):
        """Обновление прогноза температуры"""
        if self.process_data is None or len(self.process_data) < 10:
            return

        try:
            prediction = self.predictor.predict_temperature(self.process_data)

            text = "<h3>Прогноз температуры</h3>"

            if 'error' in prediction:
                text += f"<span style='color: red'>Ошибка: {prediction['error']}</span>"
            else:
                text += f"""
                <p><b>Прогнозируемая температура:</b> {prediction['predicted_temperature']:.1f}°C</p>
                <p><b>Доверительный интервал (95%):</b> {prediction['confidence_interval'][0]:.1f} - {prediction['confidence_interval'][1]:.1f}°C</p>
                <p><b>Рекомендация:</b> {prediction['recommendation']}</p>
                <p><b>Время прогноза:</b> {prediction['timestamp']}</p>
                """

            self.prediction_text.setHtml(text)

        except Exception as e:
            self.prediction_text.setHtml(f"<span style='color: red'>Ошибка прогноза: {str(e)}</span>")

    def train_prediction_model(self):
        """Обучение модели прогнозирования"""
        try:
            self.status_label.setText("Обучение модели...")

            success = self.predictor.train()

            if success:
                self.status_label.setText("Модель успешно обучена")
            else:
                self.status_label.setText("Ошибка обучения модели")

            # Обновление прогноза после обучения
            self.update_prediction()

        except Exception as e:
            self.status_label.setText(f"Ошибка обучения: {str(e)}")

    def update_display(self):
        """Автообновление дисплея"""
        if self.current_batch_id:
            self.load_batch_data()