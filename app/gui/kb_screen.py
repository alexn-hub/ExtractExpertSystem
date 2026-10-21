import json
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QLineEdit, QLabel, QComboBox, QPushButton, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt
from app.utils.config import config

class KnowledgeBaseScreen(QWidget):
    """Динамический экран Базы Знаний, адаптирующийся под конфигурацию"""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        filter_group = QGroupBox("Параметры поиска")
        filter_layout = QHBoxLayout()

        self.filter_unit = QComboBox()
        self.filter_unit.addItem("Все участки")
        self.filter_unit.addItems(config.hmi.units)

        self.filter_mass_min = QLineEdit()
        self.filter_mass_min.setPlaceholderText("Мин. масса")

        btn_width, btn_height = 160, 40

        self.btn_search = QPushButton("🔍 ОБНОВИТЬ")
        self.btn_search.setFixedSize(btn_width, btn_height)
        self.btn_search.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        self.btn_search.clicked.connect(self.load_batches)

        self.btn_import = QPushButton("➕ ИМПОРТ ДАННЫХ")
        self.btn_import.setFixedSize(btn_width, btn_height)
        self.btn_import.setStyleSheet("background-color: #1565C0; color: white; font-weight: bold;")
        self.btn_import.clicked.connect(self.open_import_dialog)

        self.btn_delete = QPushButton("УДАЛИТЬ ПАРТИЮ")
        self.btn_delete.setFixedSize(btn_width, btn_height)
        self.btn_delete.setStyleSheet("background-color: #C62828; color: white; font-weight: bold;")
        self.btn_delete.clicked.connect(self.delete_selected_batch)

        filter_layout.addWidget(QLabel("Участок:"))
        filter_layout.addWidget(self.filter_unit)
        filter_layout.addWidget(QLabel("Масса от:"))
        filter_layout.addWidget(self.filter_mass_min)
        filter_layout.addStretch()
        filter_layout.addWidget(self.btn_search)
        filter_layout.addWidget(self.btn_import)
        filter_layout.addWidget(self.btn_delete)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        layout.addWidget(QLabel("<b>Реестр партий / процессов:</b>"))
        self.table_batches = QTableWidget()
        self.table_batches.verticalHeader().setDefaultSectionSize(25)
        self.table_batches.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_batches.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_batches.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_batches.itemSelectionChanged.connect(self.on_batch_selected)
        layout.addWidget(self.table_batches)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)

        self.lbl_process_title = QLabel("<b>Подробные параметры тех. процесса:</b>")
        layout.addWidget(self.lbl_process_title)

        self.table_process = QTableWidget()
        self.table_process.verticalHeader().setVisible(False)
        self.table_process.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_process.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table_process)

        self.load_batches()

    def load_batches(self):
        all_batches = self.db.get_all_batches()
        base_headers = [
            "ID Партии", "Дата", "Участок",
            config.hmi.passport_fields.get('main_metric_label', 'Масса'),
            config.hmi.target_parameter.get('label', 'Целевой')
        ]

        static_keys = [p['key'] for p in config.hmi.static_parameters]
        static_labels = [p['label'] for p in config.hmi.static_parameters]

        all_headers = base_headers + static_labels
        self.table_batches.setColumnCount(len(all_headers))
        self.table_batches.setHorizontalHeaderLabels(all_headers)
        self.table_batches.setRowCount(0)

        unit_filter = self.filter_unit.currentText()
        try:
            min_mass = float(self.filter_mass_min.text()) if self.filter_mass_min.text() else 0.0
        except ValueError:
            min_mass = 0.0

        row_idx = 0
        for b in all_batches:
            if unit_filter != "Все участки" and b.get('unit_name') != unit_filter:
                continue
            if b.get('sample_weight', 0.0) < min_mass:
                continue

            self.table_batches.insertRow(row_idx)
            self.table_batches.setItem(row_idx, 0, QTableWidgetItem(str(b.get('batch_id', ''))))
            self.table_batches.setItem(row_idx, 1, QTableWidgetItem(str(b.get('extraction_date', ''))))
            self.table_batches.setItem(row_idx, 2, QTableWidgetItem(str(b.get('unit_name', ''))))
            self.table_batches.setItem(row_idx, 3, QTableWidgetItem(f"{b.get('sample_weight', 0):.1f}"))
            self.table_batches.setItem(row_idx, 4, QTableWidgetItem(f"{b.get('target_metric', 0):.2f}"))

            input_params = {}
            if b.get('input_params'):
                try:
                    input_params = json.loads(b['input_params'])
                except:
                    pass

            for col_idx, key in enumerate(static_keys, start=5):
                val = input_params.get(key, 0.0)
                self.table_batches.setItem(row_idx, col_idx, QTableWidgetItem(f"{float(val):.2f}"))

            row_idx += 1

    def on_batch_selected(self):
        selected = self.table_batches.selectedItems()
        if not selected:
            return

        batch_id = self.table_batches.item(selected[0].row(), 0).text()
        self.lbl_process_title.setText(f"<b>Подробные параметры тех. процесса (Партия: {batch_id}):</b>")

        df = self.db.get_process_data(batch_id)
        self.table_process.setRowCount(0)

        if df.empty:
            self.table_process.setColumnCount(0)
            return

        # Маппинг ключей в русские метки из конфигуратора
        trend_configs = config.hmi.trend_parameters
        key_to_label = {p['key']: p.get('label', p['key']) for p in trend_configs}

        data_cols = [col for col in df.columns if col != 'timestamp']
        headers = ["Время"] + [key_to_label.get(col, col) for col in data_cols]
        cols_order = ['timestamp'] + data_cols

        self.table_process.setColumnCount(len(cols_order))
        self.table_process.setHorizontalHeaderLabels(headers)

        for i, row in df.iterrows():
            self.table_process.insertRow(i)
            for j, col in enumerate(cols_order):
                val = row.get(col, '')
                if isinstance(val, (int, float)):
                    val = f"{val:.2f}"
                self.table_process.setItem(i, j, QTableWidgetItem(str(val)))

    def delete_selected_batch(self):
        selected = self.table_batches.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Сначала выберите партию в таблице!")
            return

        batch_id = self.table_batches.item(selected[0].row(), 0).text()
        reply = QMessageBox.question(
            self, 'Подтверждение', f"Удалить партию {batch_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.db.delete_batch(batch_id):
                QMessageBox.information(self, "Успех", f"Партия {batch_id} удалена.")
                self.load_batches()
                self.table_process.setRowCount(0)
                self.table_process.setColumnCount(0)

    def open_import_dialog(self):
        from app.gui.import_dialog import ImportDataDialog
        dialog = ImportDataDialog(self.db, self)
        if dialog.exec_():
            self.load_batches()