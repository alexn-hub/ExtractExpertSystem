# app/gui/work_screen.py
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QHeaderView, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from app.utils.config import config


class DashboardCards(QWidget):
    """Универсальная панель карточек текущих параметров процесса"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)
        self.value_labels = {}

    def setup_cards(self):
        # Очистка старых карточек
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)

        self.value_labels.clear()

        # БЕРЕМ ДАННЫЕ ИЗ ТРЕНДОВ (Динамика оборудования)
        for i, param in enumerate(config.hmi.trend_parameters):
            row, col = divmod(i, 2)

            card = QFrame()
            card.setStyleSheet("QFrame { background-color: #F5F7FA; border: 1px solid #CFD8DC; border-radius: 8px; }")
            card_layout = QVBoxLayout(card)

            lbl_title = QLabel(param.get('label', 'Параметр'))
            lbl_title.setStyleSheet("color: #546E7A; font-weight: bold; font-size: 10pt; border: none;")
            lbl_title.setAlignment(Qt.AlignCenter)

            lbl_value = QLabel("0.00")
            lbl_value.setStyleSheet("color: #263238; font-weight: bold; font-size: 16pt; border: none;")
            lbl_value.setAlignment(Qt.AlignCenter)

            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_value)

            self.layout.addWidget(card, row, col)
            self.value_labels[param['key']] = lbl_value

    def update_values(self, data_dict):
        """Обновление значений на карточках каждую минуту"""
        for key, lbl in self.value_labels.items():
            val = data_dict.get(key, 0.0)
            lbl.setText(f"{val:.2f}")


class AIWindow(QFrame):
    """Всплывающее окно ИИ-Советника"""

    def __init__(self, unit_name, parent=None):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.unit_name = unit_name
        self.setWindowTitle(f"ИИ-Модель: {unit_name}")
        self.setFixedSize(260, 200)
        self.setStyleSheet(
            "QFrame { background-color: #F8F9FA; border: 2px solid #1565C0; border-radius: 10px; } QLabel { border: none; }")

        layout = QVBoxLayout(self)
        self.lbl_title = QLabel("<b>ПРОГНОЗ ИИ</b>")
        self.lbl_title.setAlignment(Qt.AlignCenter)

        self.lbl_prediction = QLabel("Ожидание данных...")
        self.lbl_prediction.setAlignment(Qt.AlignCenter)
        self.lbl_prediction.setStyleSheet("font-size: 11pt; color: #1565C0; font-weight: bold;")

        self.lbl_advice = QLabel("Запустите процесс для анализа")
        self.lbl_advice.setWordWrap(True)
        self.lbl_advice.setAlignment(Qt.AlignCenter)
        self.lbl_advice.setStyleSheet("background: white; padding: 5px; border-radius: 5px;")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_prediction)
        layout.addWidget(self.lbl_advice)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()


class WorkScreen(QWidget):
    def __init__(self, unit_name, parent=None):
        super().__init__(parent)
        self.unit_name = unit_name
        self.history_data = None
        self.current_minute = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)

        self.init_ui()
        self.btn_run.clicked.connect(self.start_simulation)
        self.btn_stop.clicked.connect(self.stop_simulation)
        self.btn_new_batch.clicked.connect(self.request_new_batch)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 5, 10, 10)
        self.main_layout.setSpacing(5)

        self.ai_window = AIWindow(unit_name=self.unit_name, parent=self)

        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"Рабочая панель: {self.unit_name}")
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #263238;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

        group_style = "QGroupBox { font-size: 11pt; font-weight: bold; border: 2px solid #CFD8DC; border-radius: 8px; margin-top: 12px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }"

        top_layout = QHBoxLayout()

        # ДАШБОРД
        self.left_group = QGroupBox("Текущие показатели оборудования")
        self.left_group.setStyleSheet(group_style)
        left_vbox = QVBoxLayout(self.left_group)
        self.dashboard = DashboardCards()
        self.dashboard.setup_cards()
        left_vbox.addWidget(self.dashboard)

        # УПРАВЛЕНИЕ
        self.right_group = QGroupBox("Управление процессом")
        self.right_group.setStyleSheet(group_style)
        self.right_group.setFixedWidth(420)
        right_vbox = QVBoxLayout(self.right_group)

        self.lbl_process_time = QLabel("00:00")
        self.lbl_process_time.setAlignment(Qt.AlignCenter)
        self.lbl_process_time.setFixedHeight(60)
        self.lbl_process_time.setStyleSheet(
            "font-size: 32pt; color: #1B5E20; background: #E8F5E9; border: 1px solid #C8E6C9; border-radius: 5px; font-weight: bold;")
        right_vbox.addWidget(self.lbl_process_time)

        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("ЗАПУСК")
        self.btn_stop = QPushButton("СБРОС")
        self.btn_new_batch = QPushButton("НОВАЯ")
        for btn, color in [(self.btn_run, "#2E7D32"), (self.btn_stop, "#C62828"), (self.btn_new_batch, "#1976D2")]:
            btn.setFixedHeight(35)
            btn.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; border-radius: 4px;")
            btn_layout.addWidget(btn)
        right_vbox.addLayout(btn_layout)

        self.val_extraction = QLabel("Прогноз: Ожидание...")
        self.val_extraction.setAlignment(Qt.AlignCenter)
        self.val_extraction.setStyleSheet(
            "font-weight: bold; color: #0D47A1; font-size: 14pt; padding: 5px; background-color: #E3F2FD;")
        right_vbox.addWidget(self.val_extraction)

        self.btn_toggle_ai = QPushButton("📊 ИИ-СОВЕТЧИК")
        self.btn_toggle_ai.setCheckable(True)
        self.btn_toggle_ai.setStyleSheet("background-color: #455A64; color: white; font-weight: bold; height: 35px;")
        self.btn_toggle_ai.clicked.connect(self.toggle_ai_window)
        right_vbox.addWidget(self.btn_toggle_ai)

        top_layout.addWidget(self.left_group, stretch=2)
        top_layout.addWidget(self.right_group, stretch=1)

        # ГРАФИКИ
        self.graph_group = QGroupBox("Универсальный профиль процесса")
        self.graph_group.setStyleSheet(group_style)
        graph_vbox = QVBoxLayout(self.graph_group)

        self.plot_widget = pg.PlotWidget(background='w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend(offset=(10, 10))
        graph_vbox.addWidget(self.plot_widget)

        # Рисуем кривые на основе trend_parameters!
        self.curves = {}
        for param in config.hmi.trend_parameters:
            key = param['key']
            color = param.get('color', '#000000')
            self.curves[key] = self.plot_widget.plot(pen=pg.mkPen(color, width=2.5), name=param.get('label', key),
                                                     antialias=True)

        self.v_line = pg.InfiniteLine(pos=0, angle=90, movable=False, pen=pg.mkPen('gray', width=2, style=Qt.DashLine))
        self.plot_widget.addItem(self.v_line)

        self.main_layout.addLayout(top_layout, 4)
        self.main_layout.addWidget(self.graph_group, 6)

    def toggle_ai_window(self):
        if self.btn_toggle_ai.isChecked():
            rect = self.right_group.geometry()
            pos = self.mapToGlobal(rect.bottomRight())
            self.ai_window.move(pos.x() - self.ai_window.width(), pos.y() + 80)
            self.ai_window.show()
            self.ai_window.raise_()
        else:
            self.ai_window.hide()

    def request_new_batch(self):
        self.stop_simulation()
        if hasattr(self, 'parent_unit'):
            self.parent_unit.return_to_input()

    def update_data(self, batch_info, history_df):
        self.batch_info = batch_info
        self.history_data = history_df
        self.current_minute = 0

        target_lbl = config.hmi.target_parameter.get('label', 'Целевой показатель')
        self.val_extraction.setText(f"Прогноз: {target_lbl} = {batch_info.get('target_metric', 0.0)} %")

        x = list(range(len(history_df)))

        # Обновляем графики из DataFrame
        for key, curve in self.curves.items():
            if key in history_df.columns:
                curve.setData(x, history_df[key].values)
            else:
                curve.setData(x, [0] * len(x))

        self.v_line.setValue(0)
        if not history_df.empty:
            self.dashboard.update_values(history_df.iloc[0].to_dict())

    def start_simulation(self):
        if self.history_data is not None and not self.history_data.empty:
            self.timer.start(1000)
            self.btn_run.setEnabled(False)
            self.btn_stop.setEnabled(True)

    def update_simulation(self):
        self.current_minute += 1
        if self.current_minute >= len(self.history_data):
            self.stop_simulation()
            return

        h, m = divmod(self.current_minute, 60)
        self.lbl_process_time.setText(f"{h:02d}:{m:02d}")
        self.v_line.setValue(self.current_minute)

        # Обновляем дашборд
        row = self.history_data.iloc[self.current_minute].to_dict()
        self.dashboard.update_values(row)

        # Заглушка ИИ-Советника
        future_idx = self.current_minute + 10
        if future_idx < len(self.history_data):
            future_row = self.history_data.iloc[future_idx].to_dict()
            target_key = config.hmi.trend_parameters[0]['key'] if config.hmi.trend_parameters else None

            if target_key and target_key in future_row:
                future_val = future_row[target_key]
                self.ai_window.lbl_prediction.setText(f"Т+10: {future_val:.1f}")
                self.ai_window.lbl_title.setText("<b>АНАЛИЗ</b>")
                self.ai_window.lbl_advice.setText("Модель собирает данные...")

    def stop_simulation(self):
        self.timer.stop()
        self.current_minute = 0
        self.v_line.setValue(0)
        self.lbl_process_time.setText("00:00")
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)