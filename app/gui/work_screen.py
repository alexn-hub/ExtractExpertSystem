import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QPushButton, QGridLayout, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.gui.widgets import SulfatizerWidget


class WorkScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Основной вертикальный контейнер
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # --- 1. ВЕРХНЯЯ ПАНЕЛЬ (Заголовок и управление) ---
        header_layout = QHBoxLayout()

        title_label = QLabel("Система Советчика")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Кнопки аппаратов (как на эскизе)
        self.btn_sfr3 = QPushButton("СФР-3")
        self.btn_sfr4 = QPushButton("СФР-4")
        for btn in [self.btn_sfr3, self.btn_sfr4]:
            btn.setFixedSize(100, 35)
            btn.setStyleSheet("font-weight: bold; background-color: #f0f0f0; border: 1px solid black;")

        # Кнопка останова
        self.btn_stop = QPushButton("ОСТАНОВ")
        self.btn_stop.setFixedSize(100, 35)
        self.btn_stop.setStyleSheet(
            "background-color: #ffcdd2; color: #b71c1c; font-weight: bold; border: 1px solid #b71c1c;")

        header_layout.addWidget(self.btn_sfr3)
        header_layout.addWidget(self.btn_sfr4)
        header_layout.addWidget(self.btn_stop)

        self.main_layout.addLayout(header_layout)

        # --- 2. СРЕДНЯЯ СЕКЦИЯ (Реактор + Рекомендации) ---
        mid_layout = QHBoxLayout()

        # ЛЕВО: Прогнозируемые параметры (Мнемосхема)
        self.left_group = QGroupBox("Прогнозируемые параметры процесса сульфатизации")
        self.left_group.setFont(QFont("Arial", 10))
        left_vbox = QVBoxLayout()

        # Наш анимированный виджет реактора
        self.sulfatizer = SulfatizerWidget()
        self.sulfatizer.setMinimumSize(450, 400)

        left_vbox.addWidget(self.sulfatizer)
        self.left_group.setLayout(left_vbox)
        mid_layout.addWidget(self.left_group, 3)

        # ПРАВО: Рекомендации по загрузке
        self.right_group = QGroupBox("Рекомендации по загрузке кислоты")
        right_vbox = QVBoxLayout()

        self.rec_table = QTableWidget(0, 2)
        self.rec_table.setHorizontalHeaderLabels(["Время", "G к, т"])
        self.rec_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rec_table.setAlternatingRowColors(True)
        self.rec_table.setStyleSheet("""
            QTableWidget { 
                background-color: white; 
                border: 1px solid #ccc;
            }
            QHeaderView::section { 
                background-color: #455A64; 
                color: white; 
                padding: 4px; 
            }
        """)

        right_vbox.addWidget(self.rec_table)

        # Прогноз извлечения
        predict_layout = QHBoxLayout()
        predict_layout.addWidget(QLabel("Прогнозируемое\nизвлечение Rh"))
        self.val_extraction = QLabel("0.0")
        self.val_extraction.setFixedSize(100, 40)
        self.val_extraction.setAlignment(Qt.AlignCenter)
        self.val_extraction.setStyleSheet(
            "font-size: 18pt; border: 2px solid black; background: white; font-weight: bold;")
        predict_layout.addWidget(self.val_extraction)
        predict_layout.addWidget(QLabel("%"))

        right_vbox.addLayout(predict_layout)
        self.right_group.setLayout(right_vbox)
        mid_layout.addWidget(self.right_group, 2)

        self.main_layout.addLayout(mid_layout)

        # --- 3. НИЖНЯЯ СЕКЦИЯ (График) ---
        self.graph_group = QGroupBox("Прогнозируемый график выполнения процесса сульфатизации")
        graph_vbox = QVBoxLayout()

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')  # Глубокий темный фон
        self.plot_widget.getAxis('left').setPen('w')
        self.plot_widget.getAxis('bottom').setPen('w')

        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend(offset=(10, 10))

        # Инициализация кривых
        self.curve_tp1 = self.plot_widget.plot(pen=pg.mkPen('r', width=2), name="Тр1")
        self.curve_tp2 = self.plot_widget.plot(pen=pg.mkPen('g', width=2), name="Тр2")
        self.curve_tg = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name="Тг")
        self.curve_gk = self.plot_widget.plot(pen=pg.mkPen('#FFD740', width=3), name="G к")
        self.curve_ip = self.plot_widget.plot(pen=pg.mkPen(color=(150, 150, 150), width=1), name="I п")

        graph_vbox.addWidget(self.plot_widget)
        self.graph_group.setLayout(graph_vbox)
        self.main_layout.addWidget(self.graph_group, 2)

    def create_overlay_label(self, parent, text, y, x):
        lbl = QLabel(text, parent)
        lbl.move(x, y)
        lbl.setFixedSize(110, 40)
        lbl.setAlignment(Qt.AlignCenter)
        # Стиль: Белый фон, жирная черная рамка
        lbl.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 3px solid black;
                color: black;
                font-weight: bold;
                font-size: 11pt;
            }
        """)
        return lbl

    def init_overlay_indicators(self, parent_widget):
        # Создаем индикаторы как в эскизе, привязывая их к родителю-реактору
        self.val_mass = self.create_label(parent_widget, "G, 5.11 т", 10, 10)
        self.val_tg = self.create_label(parent_widget, "Тг 25.0 °C", 10, 170)
        self.val_tp = self.create_label(parent_widget, "Т р 10.0 °C", 180, 80)
        # И так далее...

    def create_label(self, parent, text, y, x):
        lbl = QLabel(text, parent)
        lbl.move(x, y)
        lbl.setStyleSheet("background: white; border: 1px solid black; padding: 2px; font-weight: bold;")
        return lbl

    def init_reactor_map(self):
        """Размещение цифровых индикаторов поверх схемы реактора"""
        # В реальном приложении здесь можно использовать QLabel с картинкой на фоне
        layout = QGridLayout(self.reactor_frame)

        # Создаем индикаторы как атрибуты класса для обновления
        self.val_mass = self.create_indicator(layout, "G, т", 0, 0)
        self.val_tg = self.create_indicator(layout, "Тг, °C", 0, 2)
        self.val_current = self.create_indicator(layout, "I п, А", 1, 0)
        self.val_level_1 = self.create_indicator(layout, "Lt, мм", 1, 2)
        self.val_level_2 = self.create_indicator(layout, "Lt, мм", 2, 2)
        self.val_temp_reactor = self.create_indicator(layout, "Т р, °C", 3, 1)

        layout.addWidget(QLabel("СФР-3"), 4, 1, alignment=Qt.AlignCenter)

    def create_indicator(self, layout, label_text, row, col):
        frame = QFrame()
        vbox = QVBoxLayout(frame)
        lbl = QLabel(label_text)
        val = QLabel("0.0")
        val.setFont(QFont("Monospace", 12, QFont.Bold))
        vbox.addWidget(lbl)
        vbox.addWidget(val)
        layout.addWidget(frame, row, col)
        return val

    def init_reactor_map(self):
        layout = QGridLayout(self.reactor_frame)

        # Сетка 5x5 для точного позиционирования
        # Левая колонка
        self.val_mass = self.create_indicator(layout, "G, т", 0, 0)
        self.val_current = self.create_indicator(layout, "I п, А", 2, 0)

        # Правая колонка
        self.val_tg = self.create_indicator(layout, "Тг, °C", 0, 4)
        self.val_level_1 = self.create_indicator(layout, "Lt, мм", 1, 4)
        self.val_level_2 = self.create_indicator(layout, "Lt, мм", 2, 4)

        # Низ (центр)
        self.val_temp_reactor = self.create_indicator(layout, "Т р, °C", 4, 2)

        # Центр - рисуем «кастрюлю»
        self.body_draw = QFrame()
        self.body_draw.setStyleSheet("border: 3px solid black; border-top: none; background: white;")
        layout.addWidget(self.body_draw, 1, 1, 3, 3)  # Занимает центр сетки

    def update_data(self, batch_info, history_df):
        """Обновление данных: усреднение для таблицы + лестница для графика"""
        last_row = history_df.iloc[-1]

        # --- НОВАЯ СТРОКА: Пробрасываем прогноз извлечения Rh ---
        # Мы берем значение 'extraction_percent' из словаря batch_info,
        # который прилетел из рекомендации
        self.val_extraction.setText(str(batch_info.get('extraction_percent', 0.0)))

        # 1. Передаем всё сразу в виджет реактора
        self.sulfatizer.set_params(
            g=batch_info['sample_weight'],
            ip=int(last_row['current_value']),
            tr=last_row['temperature_1'],
            tg=last_row['temperature_3'],
            lte=0,
            ltr=0
        )
        self.sulfatizer.start_animation()

        # 2. ТАБЛИЦА: Усредненные значения
        pulse_starts = history_df[
            (history_df['acid_flow'] > 1.0) &
            (history_df['acid_flow'].shift(1, fill_value=0) < 1.0)
            ].index

        self.rec_table.setRowCount(len(pulse_starts))
        for i, start_idx in enumerate(pulse_starts):
            window = history_df.iloc[start_idx: start_idx + 5]
            avg_flow = round(window['acid_flow'].mean(), 3)
            self.rec_table.setItem(i, 0, QTableWidgetItem(f"{start_idx} мин"))
            self.rec_table.setItem(i, 1, QTableWidgetItem(str(avg_flow)))

        # 3. ГРАФИК: Накопительная сумма
        x = list(range(len(history_df)))
        cumulative_acid = history_df['acid_flow'].cumsum()

        self.curve_tp1.setData(x, history_df['temperature_1'].values)
        self.curve_tp2.setData(x, history_df['temperature_2'].values)
        self.curve_tg.setData(x, history_df['temperature_3'].values)
        self.curve_gk.setData(x, cumulative_acid.values)
        self.curve_ip.setData(x, history_df['current_value'].values)