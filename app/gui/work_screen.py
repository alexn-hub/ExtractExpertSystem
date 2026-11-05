import pandas as pd
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QFrame, QComboBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from app.utils.config import config
from app.core.plc_client import RealtimePLCClient
from app.core.models import ProcessPredictor


class DashboardCards(QWidget):
    """Панель карточек параметров с отображением привязанных тегов ПЛК"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(8)
        self.value_labels = {}

    def setup_cards(self):
        for i in reversed(range(self.layout.count())):
            w = self.layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.value_labels.clear()

        for i, param in enumerate(config.hmi.trend_parameters):
            row, col = divmod(i, 2)

            card = QFrame()
            card.setObjectName("param_card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 6, 8, 6)
            card_layout.setSpacing(2)

            label_text = param.get('label', 'Параметр')
            plc_tag = str(param.get('plc_tag', '')).strip()
            title_text = f"{label_text} [{plc_tag}]" if plc_tag else label_text

            lbl_title = QLabel(title_text)
            lbl_title.setObjectName("lbl_card_title")
            lbl_title.setAlignment(Qt.AlignCenter)

            lbl_value = QLabel("0.00")
            lbl_value.setObjectName("lbl_card_value")
            lbl_value.setAlignment(Qt.AlignCenter)

            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_value)

            self.layout.addWidget(card, row, col)
            self.value_labels[param['key']] = lbl_value

    def update_values(self, data_dict):
        for key, lbl in self.value_labels.items():
            val = float(data_dict.get(key, 0.0))
            lbl.setText(f"{val:.2f}")


class AIWindow(QFrame):
    """Интеллектуальное окно ИИ-Советника с собственным стилизованным заголовком"""

    closed = pyqtSignal()

    def __init__(self, unit_name, on_algo_change_callback=None, parent=None):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.unit_name = unit_name
        self.on_algo_change_callback = on_algo_change_callback

        self.setMinimumWidth(440)
        self.setFixedWidth(450)
        self.setMinimumHeight(420)
        self.setObjectName("ai_popup_window")
        self.setStyleSheet("""
            QFrame#ai_popup_window {
                background-color: #212631;
                border: 2px solid #3A6D9E;
                border-radius: 4px;
            }
        """)

        self._drag_pos = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        # 1. Заголовок окна с кнопкой закрытия
        self.title_bar = QWidget(self)
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(0, 0, 0, 0)

        lbl_win_title = QLabel(f"ИИ-СОВЕТЧИК: {unit_name.upper()}", self.title_bar)
        lbl_win_title.setStyleSheet("font-weight: bold; font-size: 9.5pt; color: #BAC7D5; background: transparent;")
        lbl_win_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        title_bar_layout.addWidget(lbl_win_title)
        title_bar_layout.addStretch()

        btn_close = QPushButton("✕", self.title_bar)
        btn_close.setFixedSize(22, 22)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8A99AD;
                font-size: 11pt;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                color: #E57373;
                background-color: #331C1C;
                border-radius: 2px;
            }
        """)
        btn_close.clicked.connect(self.close_window)
        title_bar_layout.addWidget(btn_close)
        layout.addWidget(self.title_bar)

        # 2. Подзаголовок
        self.lbl_title = QLabel("ИНТЕЛЛЕКТУАЛЬНЫЙ ПРОГНОЗ (T+10 МИН)")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("font-weight: 700; color: #7EA6CD; font-size: 9pt; background: transparent;")
        self.lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_title)

        # 3. Выбор алгоритма
        algo_layout = QHBoxLayout()
        lbl_algo = QLabel("Метод ИИ:")
        lbl_algo.setStyleSheet("color: #8A99AD; font-weight: 600; background: transparent;")
        algo_layout.addWidget(lbl_algo)

        self.combo_algo = QComboBox()
        self.combo_algo.addItems(["RandomForest", "GradientBoosting", "Ridge"])
        if self.on_algo_change_callback:
            self.combo_algo.currentTextChanged.connect(self.on_algo_change_callback)
        algo_layout.addWidget(self.combo_algo, stretch=1)
        layout.addLayout(algo_layout)

        self.lbl_metrics = QLabel("Модель не обучена")
        self.lbl_metrics.setAlignment(Qt.AlignCenter)
        self.lbl_metrics.setStyleSheet("font-size: 8.5pt; color: #7A889B; background: transparent;")
        self.lbl_metrics.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_metrics)

        # 4. Прогноз целевого показателя
        self.lbl_prediction = QLabel("Процесс не запущен")
        self.lbl_prediction.setAlignment(Qt.AlignCenter)
        self.lbl_prediction.setWordWrap(True)
        self.lbl_prediction.setStyleSheet(
            "font-size: 9pt; color: #E0E6ED; font-weight: bold; background: #283344; "
            "padding: 6px; border-radius: 3px; border: 1px solid #3B4D66;"
        )
        self.lbl_prediction.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_prediction)

        # 5. Прогноз параметров T+10
        self.lbl_trends_t10 = QLabel("Нажмите «ЗАПУСК» для старта предиктивной аналитики.")
        self.lbl_trends_t10.setWordWrap(True)
        self.lbl_trends_t10.setStyleSheet(
            "font-size: 8.5pt; color: #C5D0DC; background: #181B22; "
            "padding: 6px; border-radius: 3px; border: 1px solid #262B36;"
        )
        self.lbl_trends_t10.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_trends_t10)

        # 6. Блок рекомендаций со скроллом
        self.advice_scroll = QScrollArea()
        self.advice_scroll.setWidgetResizable(True)
        self.advice_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.lbl_advice = QLabel("Рекомендации появятся после накопления 6 минут процесса.")
        self.lbl_advice.setWordWrap(True)
        self.lbl_advice.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_advice.setStyleSheet(
            "font-size: 8.5pt; color: #48BB78; background: #1B2E24; "
            "padding: 8px; border-radius: 3px; border: 1px solid #244732; font-weight: 500;"
        )
        self.lbl_advice.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.advice_scroll.setWidget(self.lbl_advice)
        layout.addWidget(self.advice_scroll, stretch=1)

    def close_window(self):
        self.hide()
        self.closed.emit()

    def reset_view(self, r2: float = 0.0, mae: float = 0.0, is_trained: bool = False):
        if is_trained:
            self.lbl_metrics.setText(f"Обучено на БЗ | Точность R²: {r2:.3f} | MAE: {mae:.2f}")
        else:
            self.lbl_metrics.setText("Ожидание обучения на архивных партиях")
        self.lbl_prediction.setText("Ожидание запуска процесса (00:00)...")
        self.lbl_trends_t10.setText("Прогноз параметров T+10 появится после старта.")
        self.lbl_advice.setStyleSheet(
            "font-size: 8.5pt; color: #48BB78; background: #1B2E24; "
            "padding: 8px; border-radius: 3px; border: 1px solid #244732; font-weight: 500;"
        )
        self.lbl_advice.setText("Нажмите «ЗАПУСК» для расчета рекомендаций.")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()


class WorkScreen(QWidget):
    """Главный рабочий экран мониторинга и предиктивного управления процессом"""

    def __init__(self, unit_name, parent=None):
        super().__init__(parent)
        self.unit_name = unit_name
        self.history_data = None
        self.batch_info = {}
        self.current_minute = 0
        self.plc_client = RealtimePLCClient()
        self.predictor = ProcessPredictor(algorithm="RandomForest")

        self.live_x = []
        self.live_y = {p['key']: [] for p in config.hmi.trend_parameters}
        self.live_records = []

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)

        self.init_ui()
        self.btn_run.clicked.connect(self.start_simulation)
        self.btn_stop.clicked.connect(self.stop_simulation)
        self.btn_new_batch.clicked.connect(self.request_new_batch)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 10)
        self.main_layout.setSpacing(6)

        self.ai_window = AIWindow(
            unit_name=self.unit_name,
            on_algo_change_callback=self.on_ai_algorithm_changed,
            parent=self
        )
        self.ai_window.closed.connect(self._on_ai_window_closed)

        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"РАБОЧАЯ ПАНЕЛЬ: {self.unit_name.upper()}")
        self.title_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #7EA6CD;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.lbl_plc_status = QLabel("Режим: Архивные данные")
        self.lbl_plc_status.setStyleSheet("font-size: 8.5pt; color: #8A99AD; font-weight: bold;")
        header_layout.addWidget(self.lbl_plc_status)
        self.main_layout.addLayout(header_layout)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # 1. Дашборд параметров оборудования
        self.left_group = QGroupBox("Текущие показатели оборудования")
        left_vbox = QVBoxLayout(self.left_group)
        left_vbox.setContentsMargins(4, 4, 4, 4)
        self.dashboard = DashboardCards()
        self.dashboard.setup_cards()
        left_vbox.addWidget(self.dashboard)

        # 2. Панель управления процессом
        self.right_group = QGroupBox("Управление процессом")
        self.right_group.setFixedWidth(410)
        right_vbox = QVBoxLayout(self.right_group)
        right_vbox.setContentsMargins(10, 8, 10, 10)
        right_vbox.setSpacing(8)

        mode_layout = QHBoxLayout()
        lbl_mode = QLabel("Режим работы:")
        lbl_mode.setStyleSheet("font-weight: bold; color: #BAC7D5;")
        mode_layout.addWidget(lbl_mode)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "Архивные данные",
            f"Онлайн-опрос ({getattr(config.plc, 'protocol', 'Simulation')})"
        ])
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.combo_mode, stretch=1)
        right_vbox.addLayout(mode_layout)

        self.lbl_process_time = QLabel("00:00")
        self.lbl_process_time.setObjectName("lbl_process_time")
        self.lbl_process_time.setAlignment(Qt.AlignCenter)
        self.lbl_process_time.setFixedHeight(48)
        right_vbox.addWidget(self.lbl_process_time)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        self.btn_run = QPushButton("ЗАПУСК")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setFixedHeight(30)

        self.btn_stop = QPushButton("СБРОС")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedHeight(30)

        self.btn_new_batch = QPushButton("НОВАЯ")
        self.btn_new_batch.setObjectName("btn_new_batch")
        self.btn_new_batch.setFixedHeight(30)

        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_new_batch)
        right_vbox.addLayout(btn_layout)

        self.val_extraction = QLabel("Прогноз: Ожидание...")
        self.val_extraction.setObjectName("val_extraction")
        self.val_extraction.setAlignment(Qt.AlignCenter)
        right_vbox.addWidget(self.val_extraction)

        self.btn_toggle_ai = QPushButton("ИИ-СОВЕТЧИК")
        self.btn_toggle_ai.setObjectName("btn_toggle_ai")
        self.btn_toggle_ai.setCheckable(True)
        self.btn_toggle_ai.setFixedHeight(30)
        self.btn_toggle_ai.clicked.connect(self.toggle_ai_window)
        right_vbox.addWidget(self.btn_toggle_ai)

        top_layout.addWidget(self.left_group, stretch=2)
        top_layout.addWidget(self.right_group, stretch=1)

        # 3. Графики трендов (ISA-101 Dark)
        self.graph_group = QGroupBox("Универсальный профиль процесса")
        graph_vbox = QVBoxLayout(self.graph_group)
        graph_vbox.setContentsMargins(6, 6, 6, 6)

        self.plot_widget = pg.PlotWidget(background='#181B22')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen('#3F4756'))
        self.plot_widget.getAxis('left').setPen(pg.mkPen('#3F4756'))
        self.plot_widget.addLegend(offset=(10, 10))
        graph_vbox.addWidget(self.plot_widget)

        self.ref_curves = {}
        self.live_curves = {}
        for param in config.hmi.trend_parameters:
            key = param['key']
            color = param.get('color', '#448AFF')
            label = param.get('label', key)

            self.ref_curves[key] = self.plot_widget.plot(
                pen=pg.mkPen(color, width=1.5), name=f"{label} (Эталон)", antialias=True
            )
            self.live_curves[key] = self.plot_widget.plot(
                pen=pg.mkPen(color, width=2.5), name=f"{label} (ПЛК)", antialias=True
            )

        self.v_line = pg.InfiniteLine(pos=0, angle=90, movable=False, pen=pg.mkPen('#8A99AD', width=1.5, style=Qt.DashLine))
        self.plot_widget.addItem(self.v_line)

        self.main_layout.addLayout(top_layout, 4)
        self.main_layout.addWidget(self.graph_group, 6)

    def on_ai_algorithm_changed(self, algo_name: str):
        """Переключение математической модели на лету"""
        self.predictor = ProcessPredictor(algorithm=algo_name)
        trained = self.predictor.train(unit_name=self.unit_name)
        if not trained:
            trained = self.predictor.train()
        self.ai_window.lbl_metrics.setText(
            f"Метод: {algo_name} | R²: {self.predictor.last_r2:.3f} | MAE: {self.predictor.last_mae:.2f}"
            if trained else f"Метод: {algo_name} | Недостаточно данных"
        )

    def is_realtime_mode(self) -> bool:
        return self.combo_mode.currentIndex() == 1

    def on_mode_changed(self):
        if self.timer.isActive():
            self.stop_simulation()
        self.combo_mode.setItemText(1, f"Онлайн-опрос ({config.plc.protocol})")
        self._redraw_reference_curves()

    def _redraw_reference_curves(self):
        if self.history_data is None or self.history_data.empty:
            return

        x = list(range(len(self.history_data)))
        realtime = self.is_realtime_mode()

        for param in config.hmi.trend_parameters:
            key = param['key']
            color = param.get('color', '#448AFF')
            ref_curve = self.ref_curves.get(key)
            live_curve = self.live_curves.get(key)
            if not ref_curve or not live_curve:
                continue

            if realtime:
                ref_curve.setPen(pg.mkPen(color, width=1.5, style=Qt.DotLine))
                self.lbl_plc_status.setText(f"Онлайн ({config.plc.protocol}): Готов к опросу")
            else:
                ref_curve.setPen(pg.mkPen(color, width=2.0, style=Qt.SolidLine))
                live_curve.setData([], [])
                self.lbl_plc_status.setText("Режим: Архивные данные")

            if key in self.history_data.columns:
                ref_curve.setData(x, self.history_data[key].values)
            else:
                ref_curve.setData(x, [0] * len(x))

    def _on_ai_window_closed(self):
        """Сбрасывает флаг кнопки на панели при закрытии окна через крестик"""
        self.btn_toggle_ai.setChecked(False)

    def toggle_ai_window(self):
        if self.btn_toggle_ai.isChecked():
            rect = self.right_group.geometry()
            pos = self.mapToGlobal(rect.bottomRight())
            self.ai_window.move(pos.x() - self.ai_window.width() - 10, pos.y() + 40)
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
        self.live_records.clear()

        self.dashboard.setup_cards()
        target_lbl = config.hmi.target_parameter.get('label', 'Целевой показатель')
        self.val_extraction.setText(
            f"Эталон: {batch_info.get('batch_id')} | {target_lbl} = {batch_info.get('target_metric', 0.0):.1f}%"
        )

        trained = self.predictor.train(unit_name=self.unit_name)
        if not trained:
            trained = self.predictor.train()

        self.ai_window.reset_view(
            r2=self.predictor.last_r2,
            mae=self.predictor.last_mae,
            is_trained=trained
        )

        self._redraw_reference_curves()
        self.v_line.setValue(0)
        if not history_df.empty:
            self.dashboard.update_values(history_df.iloc[0].to_dict())

    def start_simulation(self):
        if self.history_data is None or self.history_data.empty:
            return

        self.live_x.clear()
        self.live_y = {p['key']: [] for p in config.hmi.trend_parameters}
        self.live_records.clear()

        if self.is_realtime_mode():
            self.plc_client.connect()
            self.lbl_plc_status.setText(self.plc_client.last_status_msg)
            interval = getattr(config.plc, 'polling_interval_ms', 1000)
        else:
            interval = 1000

        self.timer.start(interval)
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.combo_mode.setEnabled(False)

    def update_simulation(self):
        if self.is_realtime_mode():
            self._step_realtime()
        else:
            self._step_retrospective()

    def _step_retrospective(self):
        if self.current_minute >= len(self.history_data):
            self.stop_simulation()
            return

        h, m = divmod(self.current_minute, 60)
        self.lbl_process_time.setText(f"{h:02d}:{m:02d}")
        self.v_line.setValue(self.current_minute)

        row = self.history_data.iloc[self.current_minute].to_dict()
        self.dashboard.update_values(row)
        self.live_records.append(row)

        self._update_ai_advisor()
        self.current_minute += 1

    def _step_realtime(self):
        ref_row = {}
        if self.history_data is not None and not self.history_data.empty:
            idx = min(self.current_minute, len(self.history_data) - 1)
            ref_row = self.history_data.iloc[idx].to_dict()

        live_row = self.plc_client.read_trends(reference_row=ref_row)
        self.lbl_plc_status.setText(self.plc_client.last_status_msg)

        h, m = divmod(self.current_minute, 60)
        self.lbl_process_time.setText(f"{h:02d}:{m:02d}")
        self.v_line.setValue(self.current_minute)

        self.dashboard.update_values(live_row)
        self.live_records.append(live_row)

        self.live_x.append(self.current_minute)
        for param in config.hmi.trend_parameters:
            key = param['key']
            if key in self.live_y and key in self.live_curves:
                self.live_y[key].append(live_row.get(key, 0.0))
                self.live_curves[key].setData(self.live_x, self.live_y[key])

        self._update_ai_advisor()
        self.current_minute += 1

    def _update_ai_advisor(self):
        """Вызов предиктивной модели ProcessPredictor и обновление советов"""
        recent_df = pd.DataFrame(self.live_records)
        base_target = float(self.batch_info.get('target_metric', 90.0))
        target_lbl = config.hmi.target_parameter.get('label', 'Извлечение (%)')

        res = self.predictor.predict_and_advise(
            recent_live_df=recent_df,
            reference_df=self.history_data,
            current_minute=self.current_minute,
            base_target_metric=base_target
        )

        if not res.get("ready"):
            self.ai_window.lbl_prediction.setText(res.get("status", "Ожидание..."))
            return

        # 1. Ожидаемый целевой показатель
        est_target = res['estimated_target']
        self.ai_window.lbl_prediction.setText(
            f"Ожидаемое «{target_lbl}»: {est_target:.1f}% (Эталон: {base_target:.1f}%)"
        )

        # 2. Прогноз параметров T+10
        preds = res['predictions_t10']
        refs = res['ref_t10']
        lines = ["<b>Прогноз параметров через 10 мин (T+10):</b>"]
        for p in config.hmi.trend_parameters:
            k = p['key']
            lbl = p.get('label', k)
            p_val = preds.get(k, 0.0)
            r_val = float(refs.get(k, 0.0))
            if abs(p_val) > 1e-3 or abs(r_val) > 1e-3:
                lines.append(f"• {lbl}: <b>{p_val:.1f}</b> <i>(эталон: {r_val:.1f})</i>")

        self.ai_window.lbl_trends_t10.setText("<br>".join(lines))

        # 3. Советы оператору
        advices = res['advices']
        if advices:
            self.ai_window.lbl_advice.setStyleSheet(
                "font-size: 8.5pt; color: #E57373; background: #331C1C; "
                "padding: 8px; border-radius: 3px; border: 1px solid #5C2626; font-weight: 500;"
            )
            self.ai_window.lbl_advice.setText("<b>КОРРЕКТИРОВКА РЕЖИМА:</b><br>" + "<br>".join(advices))
        else:
            self.ai_window.lbl_advice.setStyleSheet(
                "font-size: 8.5pt; color: #48BB78; background: #1B2E24; "
                "padding: 8px; border-radius: 3px; border: 1px solid #244732; font-weight: 500;"
            )
            self.ai_window.lbl_advice.setText("Параметры находятся в пределах эталонного коридора.")

    def stop_simulation(self):
        self.timer.stop()
        if self.is_realtime_mode():
            self.plc_client.disconnect()
        self.current_minute = 0
        self.v_line.setValue(0)
        self.lbl_process_time.setText("00:00")
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.combo_mode.setEnabled(True)
        self.ai_window.reset_view(
            r2=self.predictor.last_r2,
            mae=self.predictor.last_mae,
            is_trained=self.predictor.is_trained
        )