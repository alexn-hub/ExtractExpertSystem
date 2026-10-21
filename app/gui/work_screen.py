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
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)
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
            card.setStyleSheet("QFrame { background-color: #F5F7FA; border: 1px solid #CFD8DC; border-radius: 8px; }")
            card_layout = QVBoxLayout(card)

            label_text = param.get('label', 'Параметр')
            plc_tag = str(param.get('plc_tag', '')).strip()
            title_html = f"{label_text} <span style='color:#1565C0; font-size:8pt;'>[{plc_tag}]</span>" if plc_tag else label_text

            lbl_title = QLabel(title_html)
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
        for key, lbl in self.value_labels.items():
            val = float(data_dict.get(key, 0.0))
            lbl.setText(f"{val:.2f}")


class AIWindow(QFrame):
    """Интеллектуальное окно ИИ-Советника с выбором математической модели и прогнозом по всем трендам"""

    def __init__(self, unit_name, on_algo_change_callback=None, parent=None):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.unit_name = unit_name
        self.on_algo_change_callback = on_algo_change_callback
        self.setWindowTitle(f"ИИ-Советчик: {unit_name}")
        self.setFixedSize(390, 340)
        self.setStyleSheet(
            "QFrame { background-color: #F8F9FA; border: 2px solid #1565C0; border-radius: 10px; } "
            "QLabel { border: none; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.lbl_title = QLabel("<b>ИНТЕЛЛЕКТУАЛЬНЫЙ ПРОГНОЗ (T+10 МИН)</b>")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_title)

        # Выбор метода моделирования (по запросу заказчика)
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(QLabel("Метод ИИ:"))
        self.combo_algo = QComboBox()
        self.combo_algo.addItems(["RandomForest", "GradientBoosting", "Ridge"])
        if self.on_algo_change_callback:
            self.combo_algo.currentTextChanged.connect(self.on_algo_change_callback)
        algo_layout.addWidget(self.combo_algo, stretch=1)
        layout.addLayout(algo_layout)

        self.lbl_metrics = QLabel("Модель не обучена")
        self.lbl_metrics.setAlignment(Qt.AlignCenter)
        self.lbl_metrics.setStyleSheet("font-size: 8.5pt; color: #546E7A;")
        layout.addWidget(self.lbl_metrics)

        self.lbl_prediction = QLabel("Процесс не запущен")
        self.lbl_prediction.setAlignment(Qt.AlignCenter)
        self.lbl_prediction.setWordWrap(True)
        self.lbl_prediction.setStyleSheet(
            "font-size: 10pt; color: #0D47A1; font-weight: bold; background: #E3F2FD; padding: 6px; border-radius: 5px;"
        )
        layout.addWidget(self.lbl_prediction)

        self.lbl_trends_t10 = QLabel("Нажмите «ЗАПУСК» для старта предиктивной аналитики.")
        self.lbl_trends_t10.setWordWrap(True)
        self.lbl_trends_t10.setStyleSheet("font-size: 9pt; color: #263238; background: white; padding: 6px; border-radius: 5px;")
        layout.addWidget(self.lbl_trends_t10)

        self.lbl_advice = QLabel("Рекомендации появятся после накопления 6 минут процесса.")
        self.lbl_advice.setWordWrap(True)
        self.lbl_advice.setAlignment(Qt.AlignCenter)
        self.lbl_advice.setStyleSheet(
            "font-size: 9.5pt; color: #1B5E20; background: #E8F5E9; padding: 6px; border-radius: 5px; font-weight: bold;"
        )
        layout.addWidget(self.lbl_advice)
        layout.addStretch()

    def reset_view(self, r2: float = 0.0, mae: float = 0.0, is_trained: bool = False):
        if is_trained:
            self.lbl_metrics.setText(f"Обучено на БЗ | Точность R²: {r2:.3f} | MAE: {mae:.2f}")
        else:
            self.lbl_metrics.setText("Ожидание обучения на архивных партиях")
        self.lbl_prediction.setText("Ожидание запуска процесса (00:00)...")
        self.lbl_trends_t10.setText("Прогноз параметров T+10 появится после старта.")
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
        self.live_records = []  # Накопленные строки текущего прогона для подачи в ML-модель

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

        self.ai_window = AIWindow(
            unit_name=self.unit_name,
            on_algo_change_callback=self.on_ai_algorithm_changed,
            parent=self
        )

        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"Рабочая панель: {self.unit_name}")
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #263238;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.lbl_plc_status = QLabel("Режим: Архивные данные")
        self.lbl_plc_status.setStyleSheet("font-size: 10pt; color: #37474F; font-weight: bold;")
        header_layout.addWidget(self.lbl_plc_status)
        self.main_layout.addLayout(header_layout)

        group_style = (
            "QGroupBox { font-size: 11pt; font-weight: bold; border: 2px solid #CFD8DC; "
            "border-radius: 8px; margin-top: 12px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }"
        )

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
        self.right_group.setFixedWidth(440)
        right_vbox = QVBoxLayout(self.right_group)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Режим работы:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "📁 Архивные данные",
            f"⚡ Онлайн-опрос ({getattr(config.plc, 'protocol', 'Simulation')})"
        ])
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.combo_mode, stretch=1)
        right_vbox.addLayout(mode_layout)

        self.lbl_process_time = QLabel("00:00")
        self.lbl_process_time.setAlignment(Qt.AlignCenter)
        self.lbl_process_time.setFixedHeight(55)
        self.lbl_process_time.setStyleSheet(
            "font-size: 30pt; color: #1B5E20; background: #E8F5E9; border: 1px solid #C8E6C9; border-radius: 5px; font-weight: bold;"
        )
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
            "font-weight: bold; color: #0D47A1; font-size: 11pt; padding: 5px; background-color: #E3F2FD;"
        )
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

        self.ref_curves = {}
        self.live_curves = {}
        for param in config.hmi.trend_parameters:
            key = param['key']
            color = param.get('color', '#000000')
            label = param.get('label', key)

            self.ref_curves[key] = self.plot_widget.plot(
                pen=pg.mkPen(color, width=2.0), name=f"{label} (Эталон)", antialias=True
            )
            self.live_curves[key] = self.plot_widget.plot(
                pen=pg.mkPen(color, width=3.5), name=f"{label} (ПЛК)", antialias=True
            )

        self.v_line = pg.InfiniteLine(pos=0, angle=90, movable=False, pen=pg.mkPen('gray', width=2, style=Qt.DashLine))
        self.plot_widget.addItem(self.v_line)

        self.main_layout.addLayout(top_layout, 4)
        self.main_layout.addWidget(self.graph_group, 6)

    def on_ai_algorithm_changed(self, algo_name: str):
        """Переключение математической модели (RandomForest / GradientBoosting / Ridge) на лету"""
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
        self.combo_mode.setItemText(1, f"⚡ Онлайн-опрос ({config.plc.protocol})")
        self._redraw_reference_curves()

    def _redraw_reference_curves(self):
        if self.history_data is None or self.history_data.empty:
            return

        x = list(range(len(self.history_data)))
        realtime = self.is_realtime_mode()

        for param in config.hmi.trend_parameters:
            key = param['key']
            color = param.get('color', '#000000')
            ref_curve = self.ref_curves.get(key)
            live_curve = self.live_curves.get(key)
            if not ref_curve or not live_curve:
                continue

            if realtime:
                ref_curve.setPen(pg.mkPen(color, width=1.5, style=Qt.DotLine))
                self.lbl_plc_status.setText(f"Онлайн ({config.plc.protocol}): Готов")
            else:
                ref_curve.setPen(pg.mkPen(color, width=2.5, style=Qt.SolidLine))
                live_curve.setData([], [])
                self.lbl_plc_status.setText("Режим: Архивные данные")

            if key in self.history_data.columns:
                ref_curve.setData(x, self.history_data[key].values)
            else:
                ref_curve.setData(x, [0] * len(x))

    def toggle_ai_window(self):
        if self.btn_toggle_ai.isChecked():
            rect = self.right_group.geometry()
            pos = self.mapToGlobal(rect.bottomRight())
            self.ai_window.move(pos.x() - self.ai_window.width(), pos.y() + 50)
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

        # Обучаем реальную ML-модель на партиях текущего участка
        trained = self.predictor.train(unit_name=self.unit_name)
        if not trained:
            trained = self.predictor.train()

        # Сбрасываем окно ИИ (чтобы на 00:00 не висел старый прогноз!)
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
        """Вызов реальной многомерной ML-модели ProcessPredictor"""
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

        # 1. Выводим ожидаемый Целевой показатель (Извлечение / Качество)
        est_target = res['estimated_target']
        self.ai_window.lbl_prediction.setText(
            f"Ожидаемое «{target_lbl}»: {est_target:.1f}% (Эталон: {base_target:.1f}%)"
        )

        # 2. Выводим ML-прогноз T+10 по КАЖДОМУ ненулевому параметру
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

        # 3. Выводим управляющие советы оператору
        advices = res['advices']
        if advices:
            self.ai_window.lbl_advice.setStyleSheet(
                "font-size: 9pt; color: #B71C1C; background: #FFEBEE; padding: 6px; border-radius: 5px;"
            )
            self.ai_window.lbl_advice.setText("<b>⚠️ КОРРЕКТИРОВКА РЕЖИМА:</b><br>" + "<br>".join(advices))
        else:
            self.ai_window.lbl_advice.setStyleSheet(
                "font-size: 9.5pt; color: #1B5E20; background: #E8F5E9; padding: 6px; border-radius: 5px; font-weight: bold;"
            )
            self.ai_window.lbl_advice.setText("✅ Все параметры идут по эталонному коридору.")

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