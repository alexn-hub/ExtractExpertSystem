import pandas as pd
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QFrame, QComboBox
)
from PyQt5.QtCore import Qt, QTimer

from app.utils.config import config
from app.core.plc_client import RealtimePLCClient
from app.core.models import ProcessPredictor


class DashboardCards(QWidget):
    """Панель карточек параметров с отображением привязанных тегов ПЛК"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)
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
            card_layout.setContentsMargins(8, 8, 8, 8)
            card_layout.setSpacing(4)

            label_text = param.get('label', 'Параметр')
            plc_tag = str(param.get('plc_tag', '')).strip()
            title_html = f"{label_text} <span style='color:#7EA6CD; font-size:8pt;'>[{plc_tag}]</span>" if plc_tag else label_text

            lbl_title = QLabel(title_html)
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
    """Интеллектуальное окно ИИ-Советника с выбором математической модели и прогнозом по всем трендам"""

    def __init__(self, unit_name, on_algo_change_callback=None, parent=None):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.unit_name = unit_name
        self.on_algo_change_callback = on_algo_change_callback
        self.setWindowTitle(f"ИИ-СОВЕТЧИК: {unit_name.upper()}")
        self.setFixedSize(410, 350)
        self.setObjectName("ai_popup_window")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self.lbl_title = QLabel("ИНТЕЛЛЕКТУАЛЬНЫЙ ПРОГНОЗ (T+10 МИН)")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("font-weight: 700; color: #7EA6CD; letter-spacing: 0.5px;")
        layout.addWidget(self.lbl_title)

        algo_layout = QHBoxLayout()
        lbl_algo = QLabel("Метод ИИ:")
        lbl_algo.setStyleSheet("color: #8A99AD; font-weight: 600;")
        algo_layout.addWidget(lbl_algo)

        self.combo_algo = QComboBox()
        self.combo_algo.addItems(["RandomForest", "GradientBoosting", "Ridge"])
        if self.on_algo_change_callback:
            self.combo_algo.currentTextChanged.connect(self.on_algo_change_callback)
        algo_layout.addWidget(self.combo_algo, stretch=1)
        layout.addLayout(algo_layout)

        self.lbl_metrics = QLabel("Модель не обучена")
        self.lbl_metrics.setAlignment(Qt.AlignCenter)
        self.lbl_metrics.setStyleSheet("font-size: 8.5pt; color: #7A889B;")
        layout.addWidget(self.lbl_metrics)

        self.lbl_prediction = QLabel("Процесс не запущен")
        self.lbl_prediction.setAlignment(Qt.AlignCenter)
        self.lbl_prediction.setWordWrap(True)
        self.lbl_prediction.setStyleSheet(
            "font-size: 10pt; color: #E0E6ED; font-weight: bold; background: #283344; "
            "padding: 8px; border-radius: 4px; border: 1px solid #3B4D66;"
        )
        layout.addWidget(self.lbl_prediction)

        self.lbl_trends_t10 = QLabel("Нажмите «ЗАПУСК» для старта предиктивной аналитики.")
        self.lbl_trends_t10.setWordWrap(True)
        self.lbl_trends_t10.setStyleSheet(
            "font-size: 9pt; color: #C5D0DC; background: #181B22; "
            "padding: 8px; border-radius: 4px; border: 1px solid #262B36;"
        )
        layout.addWidget(self.lbl_trends_t10)

        self.lbl_advice = QLabel("Рекомендации появятся после накопления 6 минут процесса.")
        self.lbl_advice.setWordWrap(True)
        self.lbl_advice.setAlignment(Qt.AlignCenter)
        self.lbl_advice.setStyleSheet(
            "font-size: 9.5pt; color: #48BB78; background: #1B2E24; "
            "padding: 8px; border-radius: 4px; border: 1px solid #244732; font-weight: 600;"
        )
        layout.addWidget(self.lbl_advice)
        layout.addStretch()

    def reset_view(self, r2: float = 0.0, mae: float = 0.0, is_trained: bool = False):
        if is_trained:
            self.lbl_metrics.setText(f"Обучено на БЗ | Точность R2: {r2:.3f} | MAE: {mae:.2f}")
        else:
            self.lbl_metrics.setText("Ожидание обучения на архивных партиях")
        self.lbl_prediction.setText("Ожидание запуска процесса (00:00)...")
        self.lbl_trends_t10.setText("Прогноз параметров T+10 появится после старта.")
        self.lbl_advice.setStyleSheet(
            "font-size: 9.5pt; color: #48BB78; background: #1B2E24; "
            "padding: 8px; border-radius: 4px; border: 1px solid #244732; font-weight: 600;"
        )
        self.lbl_advice.setText("Нажмите «ЗАПУСК» для расчета рекомендаций.")

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
        self.main_layout.setContentsMargins(12, 10, 12, 12)
        self.main_layout.setSpacing(10)

        self.ai_window = AIWindow(
            unit_name=self.unit_name,
            on_algo_change_callback=self.on_ai_algorithm_changed,
            parent=self
        )

        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"РАБОЧАЯ ПАНЕЛЬ: {self.unit_name.upper()}")
        self.title_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #E0E6ED; letter-spacing: 0.5px;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.lbl_plc_status = QLabel("РЕЖИМ: АРХИВНЫЕ ДАННЫЕ")
        self.lbl_plc_status.setStyleSheet("font-size: 9.5pt; color: #7A889B; font-weight: 600;")
        header_layout.addWidget(self.lbl_plc_status)
        self.main_layout.addLayout(header_layout)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        # 1. ДАШБОРД ТЕЛЕМЕТРИИ
        self.left_group = QGroupBox("Текущие показатели оборудования")
        left_vbox = QVBoxLayout(self.left_group)
        self.dashboard = DashboardCards()
        self.dashboard.setup_cards()
        left_vbox.addWidget(self.dashboard)

        # 2. ПАНЕЛЬ УПРАВЛЕНИЯ
        self.right_group = QGroupBox("Управление процессом")
        self.right_group.setFixedWidth(430)
        right_vbox = QVBoxLayout(self.right_group)
        right_vbox.setSpacing(8)

        mode_layout = QHBoxLayout()
        lbl_mode = QLabel("Режим работы:")
        lbl_mode.setStyleSheet("color: #8A99AD; font-weight: 600;")
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
        self.lbl_process_time.setFixedHeight(54)
        right_vbox.addWidget(self.lbl_process_time)

        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("ЗАПУСК")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setProperty("role", "run")

        self.btn_stop = QPushButton("СБРОС")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setProperty("role", "stop")

        self.btn_new_batch = QPushButton("НОВАЯ")
        self.btn_new_batch.setObjectName("btn_new_batch")
        self.btn_new_batch.setProperty("role", "action")

        for btn in (self.btn_run, self.btn_stop, self.btn_new_batch):
            btn.setFixedHeight(34)
            btn_layout.addWidget(btn)
        right_vbox.addLayout(btn_layout)

        self.val_extraction = QLabel("Прогноз: Ожидание...")
        self.val_extraction.setObjectName("val_extraction")
        self.val_extraction.setAlignment(Qt.AlignCenter)
        right_vbox.addWidget(self.val_extraction)

        self.btn_toggle_ai = QPushButton("ИИ-СОВЕТЧИК")
        self.btn_toggle_ai.setObjectName("btn_toggle_ai")
        self.btn_toggle_ai.setCheckable(True)
        self.btn_toggle_ai.setFixedHeight(34)
        self.btn_toggle_ai.clicked.connect(self.toggle_ai_window)
        right_vbox.addWidget(self.btn_toggle_ai)

        top_layout.addWidget(self.left_group, stretch=2)
        top_layout.addWidget(self.right_group, stretch=1)

        # 3. ГРАФИКИ
        self.graph_group = QGroupBox("Универсальный профиль процесса")
        graph_vbox = QVBoxLayout(self.graph_group)
        graph_vbox.setContentsMargins(6, 12, 6, 6)

        # Настройка PyQtGraph под тему Slate Dark
        pg.setConfigOption('background', '#181B22')
        pg.setConfigOption('foreground', '#8A99AD')
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen('#2D333F', width=1))
        self.plot_widget.getAxis('left').setPen(pg.mkPen('#2D333F', width=1))
        self.plot_widget.addLegend(offset=(10, 10))
        graph_vbox.addWidget(self.plot_widget)

        self.ref_curves = {}
        self.live_curves = {}
        for param in config.hmi.trend_parameters:
            key = param['key']
            color = param.get('color', '#448AFF')
            label = param.get('label', key)

            self.ref_curves[key] = self.plot_widget.plot(
                pen=pg.mkPen(color, width=1.8), name=f"{label} (Эталон)", antialias=True
            )
            self.live_curves[key] = self.plot_widget.plot(
                pen=pg.mkPen(color, width=3.2), name=f"{label} (ПЛК)", antialias=True
            )

        self.v_line = pg.InfiniteLine(pos=0, angle=90, movable=False, pen=pg.mkPen('#7A889B', width=1.5, style=Qt.DashLine))
        self.plot_widget.addItem(self.v_line)

        self.main_layout.addLayout(top_layout, 4)
        self.main_layout.addWidget(self.graph_group, 6)

    def on_ai_algorithm_changed(self, algo_name: str):
        self.predictor = ProcessPredictor(algorithm=algo_name)
        trained = self.predictor.train(unit_name=self.unit_name)
        if not trained:
            trained = self.predictor.train()
        self.ai_window.lbl_metrics.setText(
            f"Метод: {algo_name} | R2: {self.predictor.last_r2:.3f} | MAE: {self.predictor.last_mae:.2f}"
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
                self.lbl_plc_status.setText(f"ОНЛАЙН ({config.plc.protocol}): ГОТОВ")
            else:
                ref_curve.setPen(pg.mkPen(color, width=2.2, style=Qt.SolidLine))
                live_curve.setData([], [])
                self.lbl_plc_status.setText("РЕЖИМ: АРХИВНЫЕ ДАННЫЕ")

            if key in self.history_data.columns:
                ref_curve.setData(x, self.history_data[key].values)
            else:
                ref_curve.setData(x, [0] * len(x))

    def toggle_ai_window(self):
        if self.btn_toggle_ai.isChecked():
            rect = self.right_group.geometry()
            pos = self.mapToGlobal(rect.bottomRight())
            self.ai_window.move(pos.x() - self.ai_window.width(), pos.y() + 45)
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
            f"Эталон: {batch_info.get('batch_id')} | {target_lbl} = {batch_info.get('target_metric', 0.0)} %"
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
            self.lbl_plc_status.setText(self.plc_client.last_status_msg.upper())
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
        self.lbl_plc_status.setText(self.plc_client.last_status_msg.upper())

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

        est_target = res['estimated_target']
        self.ai_window.lbl_prediction.setText(
            f"Ожидаемое «{target_lbl}»: {est_target:.1f}% (Эталон: {base_target:.1f}%)"
        )

        preds = res['predictions_t10']
        refs = res['ref_t10']
        lines = ["<b>Прогноз параметров через 10 мин (T+10):</b>"]
        for p in config.hmi.trend_parameters:
            k = p['key']
            lbl = p.get('label', k)
            p_val = preds.get(k, 0.0)
            r_val = float(refs.get(k, 0.0))
            if abs(p_val) > 1e-3 or abs(r_val) > 1e-3:
                lines.append(f"— {lbl}: <b>{p_val:.1f}</b> <i>(эталон: {r_val:.1f})</i>")

        self.ai_window.lbl_trends_t10.setText("<br>".join(lines))

        advices = res['advices']
        if advices:
            self.ai_window.lbl_advice.setStyleSheet(
                "font-size: 9pt; color: #E57373; background: #331C1C; "
                "padding: 8px; border-radius: 4px; border: 1px solid #5C2B2B;"
            )
            self.ai_window.lbl_advice.setText("<b>КОРРЕКТИРОВКА РЕЖИМА:</b><br>" + "<br>".join(advices))
        else:
            self.ai_window.lbl_advice.setStyleSheet(
                "font-size: 9.5pt; color: #48BB78; background: #1B2E24; "
                "padding: 8px; border-radius: 4px; border: 1px solid #244732; font-weight: 600;"
            )
            self.ai_window.lbl_advice.setText("Все параметры идут по эталонному коридору.")

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