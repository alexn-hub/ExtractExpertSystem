import pandas as pd
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLineEdit, QPushButton,
    QLabel, QFileDialog, QMessageBox, QGroupBox, QHBoxLayout,
    QComboBox, QScrollArea, QWidget, QRadioButton, QStackedWidget
)
from PyQt5.QtCore import Qt
from app.utils.config import config
from app.core.data_importer import ExternalDBImporter


class ImportDataDialog(QDialog):
    """Универсальный диалог импорта партии: из файла (Excel/CSV) или из внешней СУБД (SQL)"""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.sql_importer = ExternalDBImporter()
        self.filepath = ""
        self.loaded_df = None
        self.combos = {}
        self.setWindowTitle("Импорт новой партии в Базу Знаний")
        self.setMinimumWidth(880)
        self.setMinimumHeight(700)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll_layout = QVBoxLayout(content_widget)

        # 1. Паспорт партии (Общие данные)
        batch_group = QGroupBox("1. Параметры партии (Паспорт)")
        grid_main = QGridLayout()

        self.edit_id = QLineEdit()
        self.edit_id.setPlaceholderText(config.hmi.passport_fields.get('id_placeholder', 'P-2026-001'))

        self.edit_mass = QLineEdit()
        self.edit_mass.setPlaceholderText(config.hmi.passport_fields.get('main_metric_label', 'Масса'))

        self.edit_ext = QLineEdit()
        self.edit_ext.setPlaceholderText("0-100%")

        self.edit_unit = QComboBox()
        self.edit_unit.addItems(config.hmi.units)

        grid_main.addWidget(QLabel("ID Партии:"), 0, 0)
        grid_main.addWidget(self.edit_id, 0, 1)
        grid_main.addWidget(QLabel("Участок / Аппарат:"), 0, 2)
        grid_main.addWidget(self.edit_unit, 0, 3)

        grid_main.addWidget(QLabel(config.hmi.passport_fields.get('main_metric_label', 'Масса:')), 1, 0)
        grid_main.addWidget(self.edit_mass, 1, 1)
        grid_main.addWidget(QLabel(config.hmi.target_parameter.get('label', 'Целевой показатель (%):')), 1, 2)
        grid_main.addWidget(self.edit_ext, 1, 3)

        batch_group.setLayout(grid_main)
        scroll_layout.addWidget(batch_group)

        # 2. Статические параметры сырья (из конфигуратора)
        chem_group = QGroupBox("2. Свойства сырья (Статика)")
        grid_chem = QGridLayout()
        self.chem_inputs = {}

        for i, param in enumerate(config.hmi.static_parameters):
            row, col = divmod(i, 2)
            label_text = param.get('label', param['key'])
            default_val = str(param.get('default', 0.0))

            grid_chem.addWidget(QLabel(f"{label_text}:"), row, col * 2)
            edit = QLineEdit(default_val)
            grid_chem.addWidget(edit, row, col * 2 + 1)
            self.chem_inputs[param['key']] = edit

        chem_group.setLayout(grid_chem)
        scroll_layout.addWidget(chem_group)

        # 3. Выбор источника процессных данных (Файл или Внешняя SQL БД)
        source_group = QGroupBox("3. Источник процессных данных (Архив трендов)")
        source_vbox = QVBoxLayout()

        radio_layout = QHBoxLayout()
        self.rb_file = QRadioButton("📁 Из файла (Excel / CSV)")
        self.rb_sql = QRadioButton(f"🗄️ Из внешней СУБД ({getattr(config.db, 'db_type', 'SQL')}: {config.db.host})")
        self.rb_file.setChecked(True)
        self.rb_file.toggled.connect(self.on_source_toggled)
        radio_layout.addWidget(self.rb_file)
        radio_layout.addWidget(self.rb_sql)
        radio_layout.addStretch()
        source_vbox.addLayout(radio_layout)

        self.source_stack = QStackedWidget()

        # Страница 0: Файловый импорт
        page_file = QWidget()
        file_layout = QHBoxLayout(page_file)
        file_layout.setContentsMargins(0, 5, 0, 0)
        self.lbl_file = QLabel("Файл не выбран")
        btn_select = QPushButton("📁 Выбрать Excel / CSV")
        btn_select.clicked.connect(self.select_file)
        file_layout.addWidget(self.lbl_file)
        file_layout.addWidget(btn_select)
        self.source_stack.addWidget(page_file)

        # Страница 1: SQL импорт
        page_sql = QWidget()
        sql_grid = QGridLayout(page_sql)
        sql_grid.setContentsMargins(0, 5, 0, 0)

        self.combo_sql_tables = QComboBox()
        self.combo_sql_tables.setEditable(True)
        self.combo_sql_tables.setPlaceholderText("Имя таблицы (например process_history)")

        btn_fetch_tables = QPushButton("🔄 Список таблиц из БД")
        btn_fetch_tables.clicked.connect(self.load_sql_tables)

        self.edit_sql_query = QLineEdit()
        self.edit_sql_query.setPlaceholderText(
            "Или введите свой SQL-запрос (например: SELECT * FROM process_history WHERE batch_id = '101')"
        )

        btn_load_sql_cols = QPushButton("📥 Загрузить данные и колонки из SQL")
        btn_load_sql_cols.setStyleSheet("background-color: #1565C0; color: white; font-weight: bold; padding: 6px;")
        btn_load_sql_cols.clicked.connect(self.load_from_sql)

        sql_grid.addWidget(QLabel("Таблица в БД:"), 0, 0)
        sql_grid.addWidget(self.combo_sql_tables, 0, 1)
        sql_grid.addWidget(btn_fetch_tables, 0, 2)
        sql_grid.addWidget(QLabel("SQL-запрос (опц.):"), 1, 0)
        sql_grid.addWidget(self.edit_sql_query, 1, 1, 1, 2)
        sql_grid.addWidget(btn_load_sql_cols, 2, 0, 1, 3)

        self.source_stack.addWidget(page_sql)
        source_vbox.addWidget(self.source_stack)
        source_group.setLayout(source_vbox)
        scroll_layout.addWidget(source_group)

        # 4. Маппинг колонок (единый и для файла, и для SQL)
        self.mapping_group = QGroupBox("4. Сопоставление колонок техпроцесса (из Конфигуратора)")
        self.mapping_grid = QGridLayout()
        self.mapping_group.setLayout(self.mapping_grid)
        self.mapping_group.hide()
        scroll_layout.addWidget(self.mapping_group)

        scroll_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Кнопка сохранения
        self.btn_save = QPushButton("✅ ЗАГРУЗИТЬ ПАРТИЮ В ЛОКАЛЬНУЮ БАЗУ ЗНАНИЙ")
        self.btn_save.setFixedHeight(50)
        self.btn_save.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; font-size: 11pt;")
        self.btn_save.clicked.connect(self.save_data)
        self.btn_save.setEnabled(False)
        layout.addWidget(self.btn_save)

    def on_source_toggled(self):
        self.mapping_group.setVisible(False)
        self.btn_save.setEnabled(False)
        self.loaded_df = None
        if self.rb_file.isChecked():
            self.source_stack.setCurrentIndex(0)
        else:
            self.source_stack.setCurrentIndex(1)

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Выбор файла", "", "Data (*.xlsx *.csv)")
        if file:
            try:
                self.filepath = file
                self.lbl_file.setText(file.split("/")[-1])
                self.loaded_df = pd.read_csv(file) if file.endswith('.csv') else pd.read_excel(file)
                self.setup_mapping_ui(self.loaded_df.columns.tolist())
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Файл не читается: {e}")

    def load_sql_tables(self):
        tables = self.sql_importer.get_tables_list()
        if tables:
            self.combo_sql_tables.clear()
            self.combo_sql_tables.addItems(tables)
            QMessageBox.information(self, "Таблицы получены", f"Найдено таблиц во внешней БД: {len(tables)}")
        else:
            QMessageBox.warning(
                self, "Нет связи с БД",
                "Не удалось получить список таблиц.\nПроверьте настройки подключения во вкладке КОНФИГУРАТОР -> Сетевые подключения."
            )

    def load_from_sql(self):
        custom_query = self.edit_sql_query.text().strip()
        table_name = self.combo_sql_tables.currentText().strip()

        if not custom_query and not table_name:
            QMessageBox.warning(self, "Внимание", "Выберите таблицу или введите SQL-запрос!")
            return

        try:
            if custom_query:
                self.loaded_df = self.sql_importer.fetch_dataframe(custom_query, is_custom_query=True)
            else:
                self.loaded_df = self.sql_importer.fetch_dataframe(table_name, is_custom_query=False)

            if self.loaded_df.empty:
                QMessageBox.warning(self, "Пустой результат", "Запрос выполнился успешно, но вернул 0 строк.")
                return

            self.setup_mapping_ui(self.loaded_df.columns.tolist())
            QMessageBox.information(
                self, "Данные получены",
                f"Из внешней СУБД загружено {len(self.loaded_df)} строк.\nСопоставьте колонки ниже и нажмите 'Загрузить'."
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка SQL", f"Не удалось загрузить данные из внешней БД:\n{e}")

    def setup_mapping_ui(self, columns):
        """Динамическое построение полей маппинга строго под тренды из конфигуратора"""
        for i in reversed(range(self.mapping_grid.count())):
            item = self.mapping_grid.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        self.combos.clear()
        cols_with_skip = ["-- Пропустить --"] + [str(c) for c in columns]

        required_fields = {"timestamp": "Дата и время (Timestamp / Время)"}
        for param in config.hmi.trend_parameters:
            required_fields[param['key']] = param.get('label', param['key'])

        for i, (key, label) in enumerate(required_fields.items()):
            combo = QComboBox()
            combo.addItems(cols_with_skip)

            for col in columns:
                col_str = str(col)
                if key.lower() in col_str.lower() or label.split(' ')[0].lower() in col_str.lower():
                    combo.setCurrentText(col_str)
                    break

            self.mapping_grid.addWidget(QLabel(f"<b>{label}</b>:"), i, 0)
            self.mapping_grid.addWidget(combo, i, 1)
            self.combos[key] = combo

        self.mapping_group.setVisible(True)
        self.btn_save.setEnabled(True)

    def save_data(self):
        try:
            batch_id = self.edit_id.text().strip()
            if not batch_id:
                raise ValueError("Укажите ID партии!")

            if self.loaded_df is None or self.loaded_df.empty:
                raise ValueError("Сначала загрузите данные из файла или SQL!")

            def clean_float(text, name, is_percent=False):
                val_str = text.replace(',', '.')
                if not val_str:
                    return 0.0
                val = float(val_str)
                if is_percent and not (0 <= val <= 100):
                    raise ValueError(f"Поле '{name}' должно быть в диапазоне от 0 до 100!")
                return val

            df = self.loaded_df

            time_combo = self.combos.get('timestamp')
            if not time_combo or time_combo.currentText() == "-- Пропустить --":
                raise ValueError("Поле 'Дата и время (Timestamp)' обязательно для сопоставления!")

            src_time_col = time_combo.currentText()
            process_records = []
            trend_keys = [param['key'] for param in config.hmi.trend_parameters]

            for _, row in df.iterrows():
                t_val = str(row.get(src_time_col, '')).strip()
                if t_val in ["", "nan", "None", src_time_col.lower(), "время", "timestamp"]:
                    continue

                record = {'timestamp': t_val}

                for key in trend_keys:
                    combo = self.combos.get(key)
                    if combo and combo.currentText() != "-- Пропустить --":
                        src_col = combo.currentText()
                        val = row.get(src_col, 0.0)
                        try:
                            record[key] = float(str(val).replace(',', '.'))
                        except (ValueError, TypeError):
                            record[key] = 0.0
                    else:
                        record[key] = 0.0

                process_records.append(record)

            if not process_records:
                raise ValueError("Не удалось извлечь ни одной валидной строки процессных данных!")

            batch_data = {
                'batch_id': batch_id,
                'extraction_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                'unit_name': self.edit_unit.currentText(),
                'sample_weight': clean_float(self.edit_mass.text(), "Масса", is_percent=False),
                'target_metric': clean_float(
                    self.edit_ext.text(),
                    config.hmi.target_parameter.get('label', 'Целевой показатель'),
                    is_percent=True
                )
            }

            for key, edit in self.chem_inputs.items():
                batch_data[key] = clean_float(edit.text(), key, is_percent=False)

            self.db.add_batch(batch_data)
            self.db.add_process_data(batch_id, process_records)

            QMessageBox.information(
                self, "Готово",
                f"Успешно импортировано {len(process_records)} строк процессных данных в локальную Базу Знаний!"
            )
            self.accept()

        except ValueError as ve:
            QMessageBox.warning(self, "Ошибка в данных", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Детали: {e}")