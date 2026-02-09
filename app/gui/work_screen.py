import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from app.gui.widgets import SulfatizerWidget

class WorkScreen(QWidget):
    def __init__(self, unit_name="Неизвестно", parent=None):
        super().__init__(parent)
        self.unit_name = unit_name
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.current_minute = 0
        self.history_data = None
        self.batch_info = None
        self.active_pulses = []
        self.init_ui()

        self.btn_run.clicked.connect(self.start_simulation)
        self.btn_stop.clicked.connect(self.stop_simulation)
        self.btn_new_batch.clicked.connect(self.request_new_batch)

    def init_ui(self):
        # 1. Главный контейнер
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 5, 10, 10)
        self.main_layout.setSpacing(5)

        # Создаем окно ИИ (пока скрытое)
        self.ai_window = AIWindow(unit_name=self.unit_name, parent=self)

        # --- ВЕРХНЯЯ ПАНЕЛЬ (Заголовок слева) ---
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 5, 0, 5)

        self.title_label = QLabel("Система Советчика")
        self.title_label.setStyleSheet("""
            font-size: 16pt; 
            font-weight: bold; 
            color: #263238;
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()  # Прижимает заголовок влево

        self.main_layout.addWidget(header_widget)

        # Стиль GroupBox (Рамки)
        group_style = """
            QGroupBox { 
                font-size: 11pt; font-weight: bold; color: #37474F; 
                border: 2px solid #CFD8DC; border-radius: 8px; margin-top: 12px; 
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
        """

        # --- ВЕРХНЯЯ СЕКЦИЯ (40%) ---
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        # ЛЕВО: Параметры
        self.left_group = QGroupBox("Прогнозируемые параметры сульфатизации")
        self.left_group.setStyleSheet(group_style)
        left_vbox = QVBoxLayout(self.left_group)
        left_vbox.setContentsMargins(5, 20, 5, 5)
        self.sulfatizer = SulfatizerWidget()
        self.sulfatizer.setMinimumHeight(400)
        left_vbox.addWidget(self.sulfatizer)

        # ПРАВО: Управление
        self.right_group = QGroupBox("Рекомендации по расходу кислоты")
        self.right_group.setStyleSheet(group_style)
        self.right_group.setFixedWidth(420)
        right_vbox = QVBoxLayout(self.right_group)
        right_vbox.setContentsMargins(10, 25, 10, 10)
        right_vbox.setSpacing(8)

        # Время
        self.lbl_process_time = QLabel("00:00")
        self.lbl_process_time.setAlignment(Qt.AlignCenter)
        self.lbl_process_time.setFixedHeight(60)
        self.lbl_process_time.setStyleSheet("""
            font-size: 32pt; color: #1B5E20; background: #E8F5E9; 
            border: 1px solid #C8E6C9; border-radius: 5px; font-weight: bold;
        """)
        right_vbox.addWidget(self.lbl_process_time)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("ЗАПУСК")
        self.btn_stop = QPushButton("СБРОС")
        self.btn_new_batch = QPushButton("НОВАЯ")
        for btn, color in [(self.btn_run, "#2E7D32"), (self.btn_stop, "#C62828"), (self.btn_new_batch, "#1976D2")]:
            btn.setFixedHeight(35)
            btn.setStyleSheet(
                f"background-color: {color}; color: white; font-weight: bold; border-radius: 4px; font-size: 8pt;")
            btn_layout.addWidget(btn)
        right_vbox.addLayout(btn_layout)

        # Таблица
        self.rec_table = QTableWidget(0, 3)
        self.rec_table.setHorizontalHeaderLabels(["Начало", "Расход, т", "Длит-ть"])
        self.rec_table.verticalHeader().setVisible(False)
        self.rec_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rec_table.setStyleSheet("font-size: 10pt; background: white;")
        self.rec_table.setMaximumHeight(400)  # Ограничиваем, чтобы не теснила график
        right_vbox.addWidget(self.rec_table)


        # Прогноз извлечения (Крупно)
        self.val_extraction = QLabel("Прогноз извлечения Rh: 0.0 %")
        self.val_extraction.setAlignment(Qt.AlignCenter)
        self.val_extraction.setStyleSheet("""
            font-weight: bold; color: #0D47A1; font-size: 15pt; 
            padding: 8px; background-color: #E3F2FD; border-radius: 4px;
        """)
        right_vbox.addWidget(self.val_extraction)

        # НОВАЯ КНОПКА МОДЕЛИ
        self.btn_toggle_ai = QPushButton("📊 МОДЕЛЬ ИИ")
        self.btn_toggle_ai.setCheckable(True)  # <--- ДОБАВЬ ЭТУ СТРОКУ
        self.btn_toggle_ai.setStyleSheet(
            "background-color: #455A64; color: white; font-weight: bold; height: 35px; border-radius: 4px;")
        self.btn_toggle_ai.clicked.connect(self.toggle_ai_window)
        right_vbox.addWidget(self.btn_toggle_ai)

        top_layout.addWidget(self.left_group, stretch=2)
        top_layout.addWidget(self.right_group, stretch=1)

        # --- НИЖНЯЯ СЕКЦИЯ (60%) ---
        self.graph_group = QGroupBox("Прогнозируемый график процесса сульфатизации")
        self.graph_group.setStyleSheet(group_style)
        graph_vbox = QVBoxLayout(self.graph_group)
        graph_vbox.setContentsMargins(5, 25, 5, 5)

        self.plot_widget = pg.PlotWidget(background='k')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # ЛЕГЕНДА СЛЕВА
        self.plot_widget.addLegend(offset=(10, 10))

        graph_vbox.addWidget(self.plot_widget)

        # Финальное размещение
        self.main_layout.addWidget(top_container, 4)
        self.main_layout.addWidget(self.graph_group, 6)

        # Кривые
        self.curve_tp1 = self.plot_widget.plot(pen=pg.mkPen('#FF5252', width=2), name="T1", antialias=True)
        self.curve_tp2 = self.plot_widget.plot(pen=pg.mkPen('#69F0AE', width=2), name="T2", antialias=True)
        self.curve_tg = self.plot_widget.plot(pen=pg.mkPen('#FFD740', width=2), name="T газа", antialias=True)
        self.curve_opt_temp = self.plot_widget.plot(
            pen=pg.mkPen(color='#2E7D32', width=2),
            name="T регламент",
            antialias=True
        )
        self.curve_ip = self.plot_widget.plot(pen=pg.mkPen('#448AFF', width=2), name="Ток", antialias=True)
        self.curve_gk = self.plot_widget.plot(pen=pg.mkPen('#FFAB40', width=3), name="Расход", antialias=True)

        self.v_line = pg.InfiniteLine(pos=0, angle=90, movable=False, pen=pg.mkPen('y', width=2, style=Qt.DashLine))
        self.plot_widget.addItem(self.v_line)

    def toggle_ai_window(self):
        """Метод для кнопки: открываем окно под таблицей поверх графика"""
        if self.btn_toggle_ai.isChecked():
            # 1. Получаем геометрию правой панели (где таблица и кнопка)
            rect = self.right_group.geometry()

            # 2. Определяем глобальную позицию правого нижнего угла этой панели
            # Это как раз точка, где заканчивается таблица и начинается график
            pos = self.mapToGlobal(rect.bottomRight())

            # 3. Сдвигаем окно:
            # x: вычитаем ширину окна, чтобы оно не ушло за край экрана
            # y: вычитаем небольшое значение (например, 20-40 пикселей),
            # чтобы оно слегка "заползло" под таблицу или прижалось к ней
            x_coord = pos.x() - self.ai_window.width()
            y_coord = pos.y() + 80 # Небольшой отступ вниз от границы группы

            self.ai_window.move(x_coord, y_coord)
            self.ai_window.show()
            self.ai_window.raise_()  # Поверх всех слоев (графика в том числе)
        else:
            self.ai_window.hide()

    # Добавь эти методы в любое место внутри класса WorkScreen
    def showEvent(self, event):
        super().showEvent(event)
        # Показываем только если кнопка ВКЛЮЧЕНА
        if hasattr(self, 'btn_toggle_ai') and self.btn_toggle_ai.isChecked():
            self.ai_window.show()
        else:
            self.ai_window.hide()

    def hideEvent(self, event):
        """Вызывается автоматически, когда пользователь уходит на другую вкладку"""
        super().hideEvent(event)
        # Скрываем окно, но НЕ выключаем кнопку (чтобы оно вернулось при возврате)
        if hasattr(self, 'ai_window'):
            self.ai_window.hide()

    def request_new_batch(self):
        self.stop_simulation()
        if hasattr(self, 'parent_unit'):
            self.parent_unit.return_to_input()

    def update_data(self, batch_info, history_df):
        self.batch_info = batch_info
        self.history_data = history_df
        self.current_minute = 0
        self.active_pulses = []
        self.val_extraction.setText(f"Прогноз извлечения Rh: {batch_info.get('extraction_percent', 0.0)} %")
        x = list(range(len(history_df)))
        self.curve_tp1.setData(x, history_df['temperature_1'].values)
        self.curve_tp2.setData(x, history_df['temperature_2'].values)
        self.curve_tg.setData(x, history_df['temperature_3'].values)
        self.curve_ip.setData(x, history_df['current_value'].values)
        self.curve_gk.setData(x, history_df['acid_flow'].cumsum().values)
        if 'optimal_temp' in history_df.columns:
            # Используем x (ось времени) и .values (массив данных)
            self.curve_opt_temp.setData(x, history_df['optimal_temp'].values)

        self.v_line.setValue(0)
        pulse_starts = history_df[(history_df['acid_flow'] > 1.0) & (history_df['acid_flow'].shift(1, fill_value=0) < 1.0)].index
        self.rec_table.setRowCount(len(pulse_starts))
        for i, start_idx in enumerate(pulse_starts):
            duration = 0
            curr = start_idx
            while curr < len(history_df) and history_df.iloc[curr]['acid_flow'] > 1.0:
                duration += 1
                curr += 1
            avg_flow = round(history_df.iloc[start_idx : start_idx + duration]['acid_flow'].mean(), 2)
            self.active_pulses.append({'start': start_idx, 'end': start_idx + duration, 'row': i})
            self.rec_table.setItem(i, 0, QTableWidgetItem(f"{start_idx} мин"))
            self.rec_table.setItem(i, 1, QTableWidgetItem(str(avg_flow)))
            self.rec_table.setItem(i, 2, QTableWidgetItem(f"{duration} мин"))
            for col in range(3):
                self.rec_table.item(i, col).setTextAlignment(Qt.AlignCenter)

            self.sulfatizer.set_params(0, 0, 0, 0, 0, 0)
            self.lbl_process_time.setText("00:00")

    def start_simulation(self):
        if self.history_data is not None:
            self.current_minute = 0

            # СНАЧАЛА включаем анимацию
            self.sulfatizer.start_animation()
            # ТЕПЕРЬ передаем данные
            self.update_ui_elements(0)
            self.timer.start(1000)  # В продакт нужно указать 600000, чтобы была настоящая минута
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
        for pulse in self.active_pulses:
            row_idx = pulse['row']
            is_active = pulse['start'] <= self.current_minute < pulse['end']
            bg_color = QColor("#C8E6C9") if is_active else QColor("white")
            for col in range(3):
                if self.rec_table.item(row_idx, col):
                    self.rec_table.item(row_idx, col).setBackground(bg_color)
        self.update_ui_elements(self.current_minute)

    def update_ui_elements(self, minute):
        if minute < len(self.history_data):
            row = self.history_data.iloc[minute]
            self.sulfatizer.set_params(
                g=round(row.get('acid_flow', 0.0), 3),
                ip=int(row.get('current_value', 0)),
                tr=row.get('temperature_1', 0.0),
                tg=row.get('temperature_3', 0.0),
                lte=row.get('electrodes_pos', 0.0),
                ltr=row.get('level_mixer', 0.0)
            )

            # --- ЛОГИКА СОВЕТНИКА ---
            future_idx = minute + 10
            if future_idx < len(self.history_data):
                future_row = self.history_data.iloc[future_idx]
                future_t = future_row.get('temperature_1', 0.0)
                future_opt = future_row.get('optimal_temp', 0.0)  # Это наша "min T протек. опер."

                future_delta = future_t - future_opt
                self.ai_window.lbl_prediction.setText(f"T+10 мин: {future_t:.1f} °C")

                if future_delta < -2.0:
                    # Температура в будущем упадет ниже технологического минимума
                    status = "НИЖЕ РЕГЛАМЕНТА"
                    color = "#1565C0"
                    advice = f"<b>СОВЕТ:</b> Прогноз Т ниже минимума на {abs(future_delta):.1f}°C. Подайте 5т кислоты сейчас для компенсации падения."

                elif future_delta > 7.0:
                    # Ожидается чрезмерный перегрев
                    status = "РИСК ПЕРЕГРЕВА"
                    color = "#B71C1C"
                    advice = "<b>СОВЕТ:</b> Ожидается резкий рост Т. Приостановите подачу кислоты и проверьте ток на электродах."

                else:
                    status = "В НОРМЕ"
                    color = "#2E7D32"
                    advice = "Температурный тренд соответствует оптимальному графику. Продолжайте текущий режим."

                self.ai_window.lbl_title.setText(f"<b>{status}</b>")
                self.ai_window.lbl_title.setStyleSheet(f"color: {color}; border: none;")
                self.ai_window.lbl_advice.setText(advice)

    def stop_simulation(self):
        self.timer.stop()
        self.sulfatizer.stop_animation()
        self.current_minute = 0
        self.v_line.setValue(0)
        self.lbl_process_time.setText("00:00")

        # Сброс всех параметров мнемосхемы в ноль
        self.sulfatizer.set_params(0, 0, 0, 0, 0, 0)

        # Сброс подсветки таблицы (если есть)
        for i in range(self.rec_table.rowCount()):
            for j in range(self.rec_table.columnCount()):
                item = self.rec_table.item(i, j)
                if item:
                    item.setBackground(QColor("white"))
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)


class AIWindow(QFrame):
    """Всплывающее окно ИИ-Советника"""

    def __init__(self, unit_name, parent=None):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.unit_name = unit_name
        self.setWindowTitle(f"ИИ-Модель: {unit_name}")  # Теперь в заголовке будет СФР-3 или СФР-4
        self.setFixedSize(240, 200)
        self.setStyleSheet("""
            QFrame { 
                background-color: #F8F9FA; 
                border: 2px solid #1565C0; 
                border-radius: 10px; 
            }
            QLabel { border: none; }
        """)

        layout = QVBoxLayout(self)
        self.lbl_title = QLabel("<b>ПРОГНОЗ МОДЕЛИ</b>")
        self.lbl_title.setAlignment(Qt.AlignCenter)

        self.lbl_prediction = QLabel("Ожидание данных...")
        self.lbl_prediction.setAlignment(Qt.AlignCenter)
        self.lbl_prediction.setStyleSheet("font-size: 11pt; color: #1565C0;")

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

    def closeEvent(self, event):
        """Сообщаем родителю, что окно закрыто крестиком"""
        if hasattr(self.parent(), 'btn_toggle_ai'):
            self.parent().btn_toggle_ai.setChecked(False)
        event.accept()