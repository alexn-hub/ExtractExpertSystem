import json
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QLineEdit, QLabel, QComboBox, QPushButton,
    QFrame, QMessageBox, QFileDialog, QInputDialog
)
from PyQt5.QtCore import Qt
from app.utils.config import config


class KnowledgeBaseScreen(QWidget):
    """Динамический экран Базы Знаний с поддержкой импорта и экспорта (Файл / SQL)"""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Фильтры и кнопки управления архивом
        filter_group = QGroupBox("Параметры поиска и архив")
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(8, 8, 8, 8)
        filter_layout.setSpacing(8)

        self.filter_unit = QComboBox()
        self.filter_unit.addItem("Все участки")
        self.filter_unit.addItems(config.hmi.units)
        self.filter_unit.setFixedHeight(28)

        self.filter_mass_min = QLineEdit()
        self.filter_mass_min.setPlaceholderText("Мин. масса")
        self.filter_mass_min.setFixedWidth(110)
        self.filter_mass_min.setFixedHeight(28)

        self.btn_search = QPushButton("ОБНОВИТЬ")
        self.btn_search.setObjectName("btn_search")
        self.btn_search.setFixedHeight(28)
        self.btn_search.clicked.connect(self.load_batches)

        self.btn_import = QPushButton("ИМПОРТ")
        self.btn_import.setObjectName("btn_import")
        self.btn_import.setFixedHeight(28)
        self.btn_import.clicked.connect(self.open_import_dialog)

        self.btn_export = QPushButton("ЭКСПОРТ")
        self.btn_export.setObjectName("btn_export")
        self.btn_export.setFixedHeight(28)
        self.btn_export.clicked.connect(self.export_selected_batch)

        self.btn_delete = QPushButton("УДАЛИТЬ")
        self.btn_delete.setObjectName("btn_delete")
        self.btn_delete.setFixedHeight(28)
        self.btn_delete.clicked.connect(self.delete_selected_batch)

        filter_layout.addWidget(QLabel("Участок:"))
        filter_layout.addWidget(self.filter_unit)
        filter_layout.addWidget(QLabel("Масса от:"))
        filter_layout.addWidget(self.filter_mass_min)
        filter_layout.addStretch()
        filter_layout.addWidget(self.btn_search)
        filter_layout.addWidget(self.btn_import)
        filter_layout.addWidget(self.btn_export)
        filter_layout.addWidget(self.btn_delete)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # 2. Верхняя таблица (Реестр партий)
        lbl_batches = QLabel("РЕЕСТР ПАРТИЙ И ТЕХНОЛОГИЧЕСКИХ ПРОЦЕССОВ:")
        lbl_batches.setStyleSheet("font-weight: bold; color: #8A99AD; font-size: 9pt;")
        layout.addWidget(lbl_batches)

        self.table_batches = QTableWidget()
        self.table_batches.verticalHeader().setDefaultSectionSize(24)
        self.table_batches.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_batches.horizontalHeader().setStretchLastSection(False)
        self.table_batches.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_batches.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_batches.itemSelectionChanged.connect(self.on_batch_selected)
        layout.addWidget(self.table_batches, stretch=4)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #2D333F;")
        layout.addWidget(line)

        # 3. Нижняя таблица (Параметры процесса)
        self.lbl_process_title = QLabel("ПОДРОБНЫЕ ПАРАМЕТРЫ ПРОЦЕССА:")
        self.lbl_process_title.setStyleSheet("font-weight: bold; color: #8A99AD; font-size: 9pt;")
        layout.addWidget(self.lbl_process_title)

        self.table_process = QTableWidget()
        self.table_process.verticalHeader().setVisible(False)
        self.table_process.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_process.horizontalHeader().setStretchLastSection(False)
        self.table_process.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table_process, stretch=5)

        self.load_batches()

    def load_batches(self):
        """Динамическое построение шапки таблицы и загрузка партий"""
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
                except Exception:
                    pass

            for col_idx, key in enumerate(static_keys, start=5):
                val = input_params.get(key, 0.0)
                self.table_batches.setItem(row_idx, col_idx, QTableWidgetItem(f"{float(val):.2f}"))

            row_idx += 1

        # Выравниваем колонки верхней таблицы с минимальным лимитом ширины
        self.table_batches.resizeColumnsToContents()
        for c in range(self.table_batches.columnCount()):
            current_w = self.table_batches.columnWidth(c)
            self.table_batches.setColumnWidth(c, max(current_w + 16, 90))

    def on_batch_selected(self):
        """Динамическая отрисовка нижней таблицы процесса с русскими метками"""
        selected = self.table_batches.selectedItems()
        if not selected:
            return

        batch_id = self.table_batches.item(selected[0].row(), 0).text()
        self.lbl_process_title.setText(f"ПОДРОБНЫЕ ПАРАМЕТРЫ ПРОЦЕССА (ПАРТИЯ: {batch_id}):")

        df = self.db.get_process_data(batch_id)
        self.table_process.setRowCount(0)

        if df.empty:
            self.table_process.setColumnCount(0)
            return

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

                # 1. Форматирование времени
                if col == 'timestamp':
                    t_str = str(val).strip()
                    try:
                        numeric_val = float(t_str)
                        if numeric_val < 100000:
                            total_min = int(numeric_val)
                            h, m = divmod(total_min, 60)
                            val = f"{h:02d}:{m:02d}"
                        else:
                            val = pd.to_datetime(numeric_val, unit='s').strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            dt = pd.to_datetime(t_str)
                            val = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception:
                            if '.' in t_str and len(t_str) > 12:
                                val = t_str.split('.')[0]
                            elif '+' in t_str:
                                val = t_str.split('+')[0]
                            else:
                                val = t_str

                # 2. Форматирование числовых показателей процесса
                elif isinstance(val, (int, float)):
                    val = f"{float(val):.2f}"
                else:
                    try:
                        val = f"{float(str(val).replace(',', '.')):.2f}"
                    except (ValueError, TypeError):
                        val = str(val)

                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.table_process.setItem(i, j, item)

        # Выравниваем каждую колонку строго ПОСЛЕ полного заполнения таблицы
        self.table_process.resizeColumnsToContents()
        for c in range(self.table_process.columnCount()):
            current_w = self.table_process.columnWidth(c)
            self.table_process.setColumnWidth(c, max(current_w + 16, 85))

    def export_selected_batch(self):
        """Экспорт выбранной партии в файл или во внешнюю SQL БД"""
        selected = self.table_batches.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Сначала выберите партию в верхней таблице для экспорта!")
            return

        batch_id = self.table_batches.item(selected[0].row(), 0).text()
        all_batches = self.db.get_all_batches()
        batch_info = next((b for b in all_batches if str(b.get('batch_id')) == batch_id), None)
        process_df = self.db.get_process_data(batch_id)

        if not batch_info or process_df.empty:
            QMessageBox.warning(self, "Нет данных", f"У партии {batch_id} отсутствуют процессные данные для выгрузки.")
            return

        choices = [
            "Выгрузить в файл (Excel .xlsx / .csv)",
            f"Выгрузить во внешнюю SQL БД ({getattr(config.db, 'db_type', 'SQL')}: {config.db.host})"
        ]
        choice, ok = QInputDialog.getItem(
            self, "Экспорт партии", f"Куда экспортировать партию '{batch_id}'?", choices, 0, False
        )
        if not ok:
            return

        if choice.startswith("Выгрузить в файл"):
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить процессные данные партии", f"batch_{batch_id}.xlsx",
                "Excel (*.xlsx);;CSV (*.csv)"
            )
            if file_path:
                try:
                    if file_path.endswith('.csv'):
                        process_df.to_csv(file_path, index=False, encoding='utf-8-sig')
                    else:
                        process_df.to_excel(file_path, index=False)
                    QMessageBox.information(self, "Экспорт завершен", f"Партия '{batch_id}' успешно сохранена:\n{file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка сохранения файла", str(e))
        else:
            from app.core.data_importer import ExternalDBImporter
            importer = ExternalDBImporter()
            try:
                importer.export_batch_to_sql(batch_info, process_df)
                QMessageBox.information(
                    self, "Экспорт в SQL завершен",
                    f"Партия '{batch_id}' успешно выгружена во внешнюю БД ({config.db.database}) "
                    f"в таблицы ees_export_batches и ees_export_process!"
                )
            except Exception as e:
                QMessageBox.critical(self, "Ошибка SQL экспорта", str(e))

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