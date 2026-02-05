# app/gui/visualization_widget.py
import sys
import random
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QGridLayout,
    QHeaderView, QSpinBox, QDoubleSpinBox, QFrame,
    QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor, QPolygonF
import pyqtgraph as pg
import numpy as np
from pyqtgraph import mkPen, mkBrush


class SulfatizerWidget(QWidget):
    """Виджет сульфатизатора с анимацией"""

    def __init__(self):
        super().__init__()
        self.setFixedSize(400, 400)
        self.setStyleSheet("background-color: white; border: 2px solid gray;")

        # Параметры анимации
        self.electrode_offset = 0  # Смещение электродов (0-100)
        self.electrode_direction = 1  # Направление движения (1 вниз, -1 вверх)
        self.mixer_angle = 0  # Угол поворота мешалки
        self.is_animating = False

        # Таймер для анимации
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(50)  # Обновление каждые 50 мс

    def update_animation(self):
        """Обновление анимации"""
        if not self.is_animating:
            return

        # Анимация электродов (движение вверх-вниз)
        self.electrode_offset += self.electrode_direction * 2
        if self.electrode_offset >= 50 or self.electrode_offset <= 0:
            self.electrode_direction *= -1  # Меняем направление

        # Анимация мешалки (вращение)
        self.mixer_angle += 10
        if self.mixer_angle >= 360:
            self.mixer_angle = 0

        self.update()  # Перерисовка виджета

    def start_animation(self):
        """Запуск анимации"""
        self.is_animating = True

    def stop_animation(self):
        """Остановка анимации"""
        self.is_animating = False

    def paintEvent(self, event):
        """Отрисовка сульфатизатора с анимацией"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            # Основной бак (квадрат)
            painter.setPen(QPen(Qt.black, 3))
            painter.setBrush(QBrush(QColor(230, 240, 255)))
            painter.drawRect(50, 50, 300, 300)

            # Вал мешалки (НЕ вращается)
            painter.setPen(QPen(Qt.darkGray, 4))
            painter.drawLine(200, 50, 200, 150)

            # Труба от насоса (рисуем ДО вращения лопастей)
            painter.setPen(QPen(Qt.darkGreen, 4))
            painter.setBrush(QBrush(QColor(100, 200, 100)))
            painter.drawRect(180, 30, 40, 20)

            # Стрелка потока (анимированная)
            if self.is_animating:
                flow_color = QColor(100, 255, 100)
            else:
                flow_color = QColor(100, 200, 100)

            painter.setPen(QPen(Qt.darkGreen, 2))
            painter.setBrush(QBrush(flow_color))
            arrow = QPolygonF([
                QPointF(200, 10),
                QPointF(190, 30),
                QPointF(210, 30)
            ])
            painter.drawPolygon(arrow)

            # Лопасти мешалки (анимированные) - ТОЛЬКО лопасти вращаются
            painter.save()  # Сохраняем состояние painter

            # Центр вращения (центр диска лопастей)
            center_x = 200
            center_y = 170

            # Поворачиваем систему координат для лопастей
            painter.translate(center_x, center_y)
            painter.rotate(self.mixer_angle)
            painter.translate(-center_x, -center_y)

            # Диск лопастей
            painter.setPen(QPen(Qt.darkGray, 2))
            painter.setBrush(QBrush(QColor(180, 180, 180)))
            painter.drawEllipse(center_x - 20, 150, 40, 40)

            # Лопасти (4 штуки)
            blade_length = 30
            for i in range(4):
                angle = i * 90
                rad_angle = np.radians(angle)
                x1 = center_x + 20 * np.cos(rad_angle)
                y1 = center_y + 20 * np.sin(rad_angle)
                x2 = center_x + (20 + blade_length) * np.cos(rad_angle)
                y2 = center_y + (20 + blade_length) * np.sin(rad_angle)

                painter.setPen(QPen(QColor(100, 100, 100), 3))
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

                # Кончики лопастей
                painter.setBrush(QBrush(QColor(120, 120, 120)))
                painter.drawEllipse(int(x2) - 5, int(y2) - 5, 10, 10)

            painter.restore()  # Восстанавливаем состояние painter (отменяем вращение)

            # Электроды (анимированные - двигаются вверх-вниз)
            electrode_height = 200
            electrode_y_offset = self.electrode_offset

            # Левый электрод
            left_electrode_y = 100 + electrode_y_offset
            painter.setPen(QPen(Qt.darkBlue, 3))

            # Основной стержень
            painter.setBrush(QBrush(QColor(120, 120, 255, 200)))
            painter.drawRect(80, int(left_electrode_y), 20, electrode_height)

            # Верхняя часть электрода
            painter.setBrush(QBrush(QColor(80, 80, 255)))
            painter.drawEllipse(75, int(left_electrode_y) - 10, 30, 20)

            # Искры (если движется)
            if self.is_animating and abs(self.electrode_direction) > 0:
                painter.setPen(QPen(QColor(255, 255, 100), 1))
                for i in range(3):
                    spark_x = 90 + random.randint(-5, 5)
                    spark_y = int(left_electrode_y) + electrode_height + random.randint(0, 10)
                    painter.drawLine(spark_x, spark_y,
                                     spark_x + random.randint(-3, 3),
                                     spark_y + random.randint(5, 15))

            # Правый электрод
            right_electrode_y = 100 + (50 - electrode_y_offset)  # Противоположное движение
            painter.setPen(QPen(Qt.darkBlue, 3))
            painter.setBrush(QBrush(QColor(120, 120, 255, 200)))
            painter.drawRect(300, int(right_electrode_y), 20, electrode_height)

            # Верхняя часть электрода
            painter.setBrush(QBrush(QColor(80, 80, 255)))
            painter.drawEllipse(295, int(right_electrode_y) - 10, 30, 20)

            # Искры для правого электрода
            if self.is_animating and abs(self.electrode_direction) > 0:
                painter.setPen(QPen(QColor(255, 255, 100), 1))
                for i in range(3):
                    spark_x = 310 + random.randint(-5, 5)
                    spark_y = int(right_electrode_y) + electrode_height + random.randint(0, 10)
                    painter.drawLine(spark_x, spark_y,
                                     spark_x + random.randint(-3, 3),
                                     spark_y + random.randint(5, 15))

            # Соединение электродов (перевернутая трапеция)
            painter.setPen(QPen(Qt.darkRed, 2))
            painter.setBrush(QBrush(QColor(255, 200, 200, 180)))
            polygon = QPolygonF([
                QPointF(100, 150),
                QPointF(300, 150),
                QPointF(280, 200),
                QPointF(120, 200)
            ])
            painter.drawPolygon(polygon)

            # Стрелка тока
            arrow_length = 20 + abs(self.electrode_offset) / 5
            # Преобразовать float в int для координат
            end_y = int(250 + arrow_length)
            tip_y = int(250 + arrow_length - 10)

            painter.setPen(QPen(Qt.darkYellow, 2))
            painter.drawLine(200, 250, 200, end_y)
            painter.drawLine(200, end_y, 190, tip_y)
            painter.drawLine(200, end_y, 210, tip_y)

            # Подписи
            painter.setPen(Qt.black)
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)

            painter.drawText(150, 30, "Сульфатизатор")

            font.setPointSize(8)
            font.setBold(False)
            painter.setFont(font)

            # Анимированная надпись для мешалки
            if self.is_animating:
                mixer_text = "Мешалка (вращается)"
                mixer_color = Qt.darkGreen
            else:
                mixer_text = "Мешалка"
                mixer_color = Qt.black

            painter.setPen(mixer_color)
            painter.drawText(180, 210, mixer_text)

            painter.setPen(Qt.black)
            painter.drawText(170, 75, "Кислота")

            # Подписи электродов
            painter.setPen(Qt.blue)
            painter.drawText(60, 320, "Электрод -")
            painter.drawText(280, 320, "Электрод +")

            # Обозначение тока
            if self.is_animating:
                current_color = Qt.darkYellow
                current_text = "Ток ⚡"
            else:
                current_color = Qt.darkYellow
                current_text = "Ток"

            painter.setPen(current_color)
            painter.drawText(170, 280, current_text)

        except Exception as e:
            print(f"Ошибка отрисовки: {e}")
        finally:
            painter.end()  # Важно: завершаем работу с painter

class RecommendationTable(QTableWidget):
    """Таблица рекомендаций"""

    def __init__(self):
        super().__init__(18, 3)  # 18 строк, 3 столбца
        self.init_table()
        self.generate_test_data()

    def init_table(self):
        """Инициализация таблицы"""
        headers = ["Время (мин)", "Кислота (л/ч)", "Ток (А)"]
        self.setHorizontalHeaderLabels(headers)

        # Настройка внешнего вида
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
               QTableWidget {
                   background-color: #f8f8f8;
                   gridline-color: #cccccc;
                   border: none;
               }
               QTableWidget::item {
                   padding: 8px;
                   font-size: 11px;
               }
               QHeaderView::section {
                   background-color: #4a86e8;
                   color: white;
                   padding: 10px;
                   border: 1px solid #cccccc;
                   font-weight: bold;
                   font-size: 12px;
               }
               QTableWidget::item:selected {
                   background-color: #d4e6ff;
               }
               QScrollBar:vertical {
                   width: 12px;
                   background-color: #f0f0f0;
               }
               QScrollBar::handle:vertical {
                   background-color: #aaaaaa;
                   border-radius: 6px;
                   min-height: 20px;
               }
               QScrollBar::handle:vertical:hover {
                   background-color: #888888;
               }
           """)

        # Автоматическое растягивание столбцов на всю ширину
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Фиксированная высота строк
        self.verticalHeader().setDefaultSectionSize(35)

        # Скрыть вертикальный заголовок
        self.verticalHeader().setVisible(False)

        # Отключить редактирование
        self.setEditTriggers(self.NoEditTriggers)

        # Отключить выделение по ячейкам, только по строкам
        self.setSelectionBehavior(QTableWidget.SelectRows)

        # Отключить горизонтальную прокрутку, ВКЛЮЧИТЬ вертикальную
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Вертикальная прокрутка по необходимости

    def generate_test_data(self):
        """Генерация тестовых данных для таблицы"""
        time = 0
        acid_accumulated = 0

        for row in range(18):
            # Время с накоплением
            time_item = QTableWidgetItem(f"{time:3d} мин")
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setBackground(QColor(245, 245, 245))
            self.setItem(row, 0, time_item)

            # Кислота с накоплением (от 0 до 30)
            acid_increment = random.uniform(0.5, 2.5)
            acid_accumulated += acid_increment
            if acid_accumulated > 30:
                acid_accumulated = 30

            acid_item = QTableWidgetItem(f"{acid_accumulated:5.1f} л/ч")
            acid_item.setTextAlignment(Qt.AlignCenter)
            if acid_accumulated > 25:
                acid_item.setBackground(QColor(255, 200, 200))  # Красный при высоком значении
                acid_item.setForeground(QBrush(QColor(139, 0, 0)))  # Темно-красный текст
            elif acid_accumulated > 15:
                acid_item.setBackground(QColor(255, 255, 200))  # Желтый при среднем
                acid_item.setForeground(QBrush(QColor(153, 153, 0)))  # Темно-желтый текст
            else:
                acid_item.setBackground(QColor(200, 255, 200))  # Зеленый при низком
                acid_item.setForeground(QBrush(QColor(0, 100, 0)))  # Темно-зеленый текст
            self.setItem(row, 1, acid_item)

            # Ток без накопления (от 0 до 10)
            current = random.uniform(0, 10)
            current_item = QTableWidgetItem(f"{current:5.1f} А")
            current_item.setTextAlignment(Qt.AlignCenter)
            if current > 8:
                current_item.setBackground(QColor(255, 200, 200))
                current_item.setForeground(QBrush(QColor(139, 0, 0)))
            elif current > 5:
                current_item.setBackground(QColor(255, 255, 200))
                current_item.setForeground(QBrush(QColor(153, 153, 0)))
            else:
                current_item.setBackground(QColor(200, 255, 200))
                current_item.setForeground(QBrush(QColor(0, 100, 0)))
            self.setItem(row, 2, current_item)

            # Увеличиваем время для следующей строки
            time += 5  # 5 минут между шагами

    def update_recommendations(self, time_index: int, acid: float, current: float):
        """Обновление рекомендаций для конкретного времени"""
        if time_index < self.rowCount():
            acid_item = QTableWidgetItem(f"{acid:5.1f} л/ч")
            acid_item.setTextAlignment(Qt.AlignCenter)

            current_item = QTableWidgetItem(f"{current:5.1f} А")
            current_item.setTextAlignment(Qt.AlignCenter)

            # Цветовая индикация
            if acid > 25:
                acid_item.setBackground(QColor(255, 200, 200))
                acid_item.setForeground(QBrush(QColor(139, 0, 0)))
            elif acid > 15:
                acid_item.setBackground(QColor(255, 255, 200))
                acid_item.setForeground(QBrush(QColor(153, 153, 0)))
            else:
                acid_item.setBackground(QColor(200, 255, 200))
                acid_item.setForeground(QBrush(QColor(0, 100, 0)))

            if current > 8:
                current_item.setBackground(QColor(255, 200, 200))
                current_item.setForeground(QBrush(QColor(139, 0, 0)))
            elif current > 5:
                current_item.setBackground(QColor(255, 255, 200))
                current_item.setForeground(QBrush(QColor(153, 153, 0)))
            else:
                current_item.setBackground(QColor(200, 255, 200))
                current_item.setForeground(QBrush(QColor(0, 100, 0)))

            self.setItem(time_index, 1, acid_item)
            self.setItem(time_index, 2, current_item)

class ProcessVisualizationWidget(QWidget):
    """Виджет визуализации процесса сульфатизации"""

    def __init__(self):
        super().__init__()
        self.time_data = []
        self.temperature_data = []
        self.acid_data = []
        self.current_data = []

        self.init_ui()
        self.init_graph()
        self.generate_test_process()

    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("🏭 Визуализация процесса сульфатизации")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("padding: 10px; background-color: #e0e0e0; border-radius: 5px;")
        layout.addWidget(title)

        # Верхняя часть: сульфатизатор и таблица
        top_layout = QHBoxLayout()

        # Сульфатизатор
        sulf_group = QGroupBox("Сульфатизатор")
        sulf_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #aaaaaa;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        sulf_layout = QVBoxLayout()
        self.sulfatizer = SulfatizerWidget()
        sulf_layout.addWidget(self.sulfatizer, alignment=Qt.AlignCenter)

        # Кнопки управления анимацией
        anim_btn_layout = QHBoxLayout()
        self.start_anim_btn = QPushButton("▶ Анимация")
        self.start_anim_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.start_anim_btn.clicked.connect(self.start_animation)

        self.stop_anim_btn = QPushButton("⏹ Стоп")
        self.stop_anim_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        self.stop_anim_btn.clicked.connect(self.stop_animation)
        self.stop_anim_btn.setEnabled(False)

        anim_btn_layout.addWidget(self.start_anim_btn)
        anim_btn_layout.addWidget(self.stop_anim_btn)
        anim_btn_layout.addStretch()

        sulf_layout.addLayout(anim_btn_layout)
        sulf_group.setLayout(sulf_layout)
        top_layout.addWidget(sulf_group, 1)  # Коэффициент растяжения 1

        # Таблица рекомендаций
        table_group = QGroupBox("Рекомендации по процессу")
        table_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #aaaaaa;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        table_layout = QVBoxLayout()
        self.recommendation_table = RecommendationTable()

        # Вместо этого установите политику размера:
        self.recommendation_table.setSizePolicy(
            QSizePolicy.Expanding,  # Горизонтальная
            QSizePolicy.Expanding  # Вертикальная
        )

        table_layout.addWidget(self.recommendation_table)

        # Кнопки управления
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Запуск процесса")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.start_btn.clicked.connect(self.start_process)

        self.pause_btn = QPushButton("⏸ Пауза")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #e68a00;
            }
            QPushButton:pressed {
                background-color: #cc7a00;
            }
        """)
        self.pause_btn.clicked.connect(self.pause_process)
        self.pause_btn.setEnabled(False)

        self.reset_btn = QPushButton("↺ Сброс")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c00;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_process)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.pause_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()

        table_layout.addLayout(button_layout)
        table_group.setLayout(table_layout)
        top_layout.addWidget(table_group, 2)  # Коэффициент растяжения 2

        layout.addLayout(top_layout)

        # ГРАФИК - теперь в отдельном Splitter для контроля размера
        splitter = QSplitter(Qt.Vertical)

        # Контейнер для графика
        graph_container = QWidget()
        graph_container_layout = QVBoxLayout(graph_container)

        graph_group = QGroupBox("График температуры и параметров процесса")
        graph_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #aaaaaa;
                border-radius: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        graph_layout = QVBoxLayout()

        # Настройка графика
        self.temp_plot = pg.PlotWidget()

        # Увеличим минимальную высоту графика
        self.temp_plot.setMinimumHeight(350)

        # Темный фон графика
        self.temp_plot.setBackground('#2b2b2b')  # Темно-серый

        # Стиль сетки
        self.temp_plot.showGrid(x=True, y=True, alpha=0.5)

        # Цвета осей и текста
        self.temp_plot.setLabel('left', 'Температура', units='°C', color='white')
        self.temp_plot.setLabel('bottom', 'Время', units='ч', color='white')
        self.temp_plot.getAxis('left').setPen(pg.mkPen(color='white', width=1))
        self.temp_plot.getAxis('bottom').setPen(pg.mkPen(color='white', width=1))
        self.temp_plot.getAxis('left').setTextPen(pg.mkPen(color='white'))
        self.temp_plot.getAxis('bottom').setTextPen(pg.mkPen(color='white'))

        self.temp_plot.setYRange(0, 300)
        self.temp_plot.setXRange(0, 25)

        # Панель инструментов для графика
        toolbar_layout = QHBoxLayout()

        zoom_in_btn = QPushButton("🔍 +")
        zoom_in_btn.setToolTip("Увеличить")
        zoom_in_btn.setFixedSize(40, 30)
        zoom_in_btn.clicked.connect(lambda: self.temp_plot.getViewBox().scaleBy((0.9, 0.9)))

        zoom_out_btn = QPushButton("🔍 -")
        zoom_out_btn.setToolTip("Уменьшить")
        zoom_out_btn.setFixedSize(40, 30)
        zoom_out_btn.clicked.connect(lambda: self.temp_plot.getViewBox().scaleBy((1.1, 1.1)))

        reset_view_btn = QPushButton("↺")
        reset_view_btn.setToolTip("Сбросить вид")
        reset_view_btn.setFixedSize(40, 30)
        reset_view_btn.clicked.connect(self.reset_graph_view)

        auto_range_btn = QPushButton("🔄")
        auto_range_btn.setToolTip("Автоподбор масштаба")
        auto_range_btn.setFixedSize(40, 30)
        auto_range_btn.clicked.connect(self.temp_plot.autoRange)

        toolbar_layout.addWidget(QLabel("Масштаб:"))
        toolbar_layout.addWidget(zoom_in_btn)
        toolbar_layout.addWidget(zoom_out_btn)
        toolbar_layout.addWidget(reset_view_btn)
        toolbar_layout.addWidget(auto_range_btn)
        toolbar_layout.addStretch()

        graph_layout.addLayout(toolbar_layout)
        graph_layout.addWidget(self.temp_plot)
        graph_group.setLayout(graph_layout)

        graph_container_layout.addWidget(graph_group)
        splitter.addWidget(graph_container)

        # Контейнер для статуса (нижняя часть)
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)

        # Статус
        self.status_label = QLabel("Готов к запуску процесса")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 12px;
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                margin: 5px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)

        splitter.addWidget(status_container)

        # Установим размеры splitter (график - 70%, статус - 30%)
        splitter.setSizes([700, 300])

        layout.addWidget(splitter, 1)  # Коэффициент растяжения 1

        self.setLayout(layout)

        # Таймер для имитации процесса
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self.update_process)
        self.current_time = 0
        self.is_running = False

    def start_animation(self):
        """Запуск анимации сульфатизатора"""
        self.sulfatizer.start_animation()
        self.start_anim_btn.setEnabled(False)
        self.stop_anim_btn.setEnabled(True)

    def stop_animation(self):
        """Остановка анимации сульфатизатора"""
        self.sulfatizer.stop_animation()
        self.start_anim_btn.setEnabled(True)
        self.stop_anim_btn.setEnabled(False)

    # В методе start_process можно добавить автоматический запуск анимации:
    def start_process(self):
        """Запуск процесса"""
        if not self.is_running:
            self.is_running = True
            self.process_timer.start(200)
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)

            # Автоматически запускаем анимацию
            self.start_animation()

            self.status_label.setText("Процесс запущен...")
            self.status_label.setStyleSheet("""
                   QLabel {
                       padding: 10px;
                       background-color: #d4edda;
                       color: #155724;
                       border: 1px solid #c3e6cb;
                       border-radius: 4px;
                       font-weight: bold;
                   }
               """)

    def pause_process(self):
        """Пауза процесса"""
        if self.is_running:
            self.is_running = False
            self.process_timer.stop()
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)

            # Останавливаем анимацию при паузе
            self.stop_animation()

            self.status_label.setText("Процесс на паузе")
            self.status_label.setStyleSheet("""
                   QLabel {
                       padding: 10px;
                       background-color: #fff3cd;
                       color: #856404;
                       border: 1px solid #ffeaa7;
                       border-radius: 4px;
                       font-weight: bold;
                   }
               """)

    def reset_graph_view(self):
        """Сброс вида графика к исходным настройкам"""
        self.temp_plot.setYRange(0, 300)
        self.temp_plot.setXRange(0, 25)

    def init_graph(self):
        """Инициализация графиков"""
        # Температура (пилообразный сигнал) - красный
        self.temp_curve = self.temp_plot.plot(
            pen=pg.mkPen(color='#ff3333', width=3),
            name='Температура'
        )

        # Кислота (ступенчатый график) - зеленый, БЕЗ stepMode
        self.acid_curve = self.temp_plot.plot(
            pen=pg.mkPen(color='#33ff33', width=3),
            name='Кислота'
            # Убрали stepMode='center'
        )

        # Ток (пилообразный) - желтый
        self.current_curve = self.temp_plot.plot(
            pen=pg.mkPen(color='#ffff33', width=2),
            name='Ток'
        )

        # Легенда
        self.temp_plot.addLegend(offset=(-10, 10))

    def generate_test_process(self):
        """Генерация тестовых данных процесса"""
        self.time_data = []
        self.temperature_data = []
        self.acid_data = []
        self.current_data = []

        # Генерация ступенчатой кислоты
        acid_steps = []
        current_acid = 0
        step_points = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25]

        # Генерируем значения кислоты для каждой точки
        for i, t in enumerate(step_points):
            if i == 0:
                acid_steps.append((t, 0))  # Начало: 0
            elif i == len(step_points) - 1:
                acid_steps.append((t, 25.6))  # Конец: 25.6
            else:
                # Рандомное увеличение, но гарантируем рост
                increment = random.uniform(1.5, 4.0)
                current_acid += increment
                if current_acid > 25:
                    current_acid = 25
                acid_steps.append((t, current_acid))

        # Генерация данных для 25 часов процесса
        for t in np.linspace(0, 25, 500):  # 500 точек для более гладкого графика
            self.time_data.append(t)

            # Определяем значение кислоты для текущего времени (ступенчатая функция)
            acid_value = 0
            for i in range(len(acid_steps) - 1):
                t_start, acid_start = acid_steps[i]
                t_end, acid_end = acid_steps[i + 1]

                if t_start <= t < t_end:
                    # Линейная интерполяция между ступенями
                    if t_end - t_start > 0:
                        progress = (t - t_start) / (t_end - t_start)
                        acid_value = acid_start + (acid_end - acid_start) * progress
                    else:
                        acid_value = acid_start
                    break
                elif t >= acid_steps[-1][0]:  # Последняя ступень
                    acid_value = acid_steps[-1][1]

            self.acid_data.append(acid_value)

            # Температура: пилообразный сигнал, зависящий от подачи кислоты
            # Базовый уровень температуры увеличивается с увеличением кислоты
            base_temp = 80 + acid_value * 2  # Температура растет с кислотой

            # Пилообразный компонент
            sawtooth = 40 * ((t * 3) % 1)  # Более частые пилы

            # Случайные колебания
            noise = random.uniform(-5, 5)

            # Зависимость от времени (постепенный рост)
            time_growth = t * 0.8

            temp = base_temp + sawtooth + time_growth + noise

            # Ограничения
            if temp > 280:  # Максимальная температура ниже 300
                temp = 280 - random.uniform(0, 10)
            if temp < 50:
                temp = 50 + random.uniform(0, 10)

            self.temperature_data.append(temp)

            # Ток: также зависит от кислоты и имеет пилообразную форму
            # Базовый ток растет с кислотя
            base_current = 2 + acid_value * 0.2

            # Пилообразный компонент для тока (с другой частотой)
            current_sawtooth = 3 * ((t * 2.5) % 1)

            # Случайные скачки тока при увеличении кислоты
            current_jump = 0
            for acid_step in acid_steps:
                if abs(t - acid_step[0]) < 0.1:  # В моменты ступеней кислоты
                    current_jump = random.uniform(1, 3)
                    break

            # Случайные колебания
            current_noise = random.uniform(-0.5, 0.5)

            current = base_current + current_sawtooth + current_jump + current_noise

            # Ограничения тока
            if current > 12:
                current = 12 - random.uniform(0, 2)
            if current < 0.5:
                current = 0.5 + random.uniform(0, 1)

            self.current_data.append(current)

        # Обновление графика
        self.update_graph()

    def update_graph(self):
        """Обновление графика"""
        if not self.time_data:
            return

        # Температура
        self.temp_curve.setData(self.time_data, self.temperature_data)

        # Кислота (ступенчатый график)
        self.acid_curve.setData(self.time_data, self.acid_data)

        # Ток (масштабированный для видимости)
        scaled_current = [c * 15 for c in self.current_data]
        self.current_curve.setData(self.time_data, scaled_current)

    def start_process(self):
        """Запуск процесса"""
        if not self.is_running:
            self.is_running = True
            self.process_timer.start(200)  # Обновление каждые 200 мс
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.status_label.setText("Процесс запущен...")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #d4edda;
                    color: #155724;
                    border: 1px solid #c3e6cb;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)

    def pause_process(self):
        """Пауза процесса"""
        if self.is_running:
            self.is_running = False
            self.process_timer.stop()
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.status_label.setText("Процесс на паузе")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #fff3cd;
                    color: #856404;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)

    def reset_process(self):
        """Сброс процесса"""
        self.is_running = False
        self.process_timer.stop()
        self.current_time = 0
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.generate_test_process()
        self.status_label.setText("Процесс сброшен")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f8f9fa;
                color: #6c757d;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                font-weight: bold;
            }
        """)

    def update_process(self):
        """Обновление процесса (вызывается таймером)"""
        if self.current_time >= len(self.time_data) - 1:
            self.pause_process()
            self.status_label.setText("Процесс завершен")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #d1ecf1;
                    color: #0c5460;
                    border: 1px solid #bee5eb;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
            return

        # Увеличиваем время
        self.current_time += 2  # Ускорим для демонстрации

        # Обновляем график для текущего времени
        time_window = 8  # Показываем последние 8 часов
        start_idx = max(0, self.current_time - int(time_window * 20))  # 20 точек на час

        # Обрезаем данные для отображения окна
        display_time = self.time_data[start_idx:self.current_time + 1]
        display_temp = self.temperature_data[start_idx:self.current_time + 1]
        display_acid = self.acid_data[start_idx:self.current_time + 1]
        display_current = self.current_data[start_idx:self.current_time + 1]

        # Обновление графика
        self.temp_curve.setData(display_time, display_temp)
        self.acid_curve.setData(display_time, display_acid)

        # Ток (масштабированный)
        scaled_current = [c * 15 for c in display_current]
        self.current_curve.setData(display_time, scaled_current)

        # Обновление статуса
        current_temp = self.temperature_data[min(self.current_time, len(self.temperature_data) - 1)]
        current_acid = self.acid_data[min(self.current_time, len(self.acid_data) - 1)]
        current_current = self.current_data[min(self.current_time, len(self.current_data) - 1)]

        self.status_label.setText(
            f"Время: {display_time[-1]:.1f} ч | "
            f"Температура: {current_temp:.1f}°C | "
            f"Кислота: {current_acid:.1f} л/ч | "
            f"Ток: {current_current:.1f} А"
        )

        # Обновление таблицы рекомендаций (каждые 30 минут реального времени)
        if self.current_time % 100 == 0:  # Примерно каждые 30 минут на графике
            table_row = min(self.current_time // 100, 17)  # Не более 18 строк
            if table_row < 18:
                self.recommendation_table.update_recommendations(
                    table_row,
                    current_acid,
                    current_current
                )