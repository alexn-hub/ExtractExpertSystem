# app/gui/import_dialog.py
import pandas as pd
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QLabel,
    QFileDialog, QMessageBox, QGroupBox, QHBoxLayout, QComboBox, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt
from app.utils.config import config


class ImportDataDialog(QDialog):
    """Диалог импорта данных с жестким маппингом по конфигуратору трендов"""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.filepath = ""
        self.combos = {}
        self.setWindowTitle("Импорт новой партии в Базу Знаний")
        self.setMinimumWidth(850)
        self.setMinimumHeight(650)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll_layout = QVBoxLayout(content_widget)

        # 1. Паспорт партии (Общие данные)
        batch_group = QGroupBox("Параметры партии (Паспорт)")
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
        chem_group = QGroupBox("Свойства сырья (Статика)")
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

        # 3. Выбор файла
        file_group = QGroupBox("Файл процессных данных (Архив трендов)")
        file_layout = QHBoxLayout()
        self.lbl_file = QLabel("Файл не выбран")
        btn_select = QPushButton("📁 Выбрать Excel / CSV")
        btn_select.clicked.connect(self.select_file)
        file_layout.addWidget(self.lbl_file)
        file_layout.addWidget(btn_select)
        file_group.setLayout(file_layout)
        scroll_layout.addWidget(file_group)

        # 4. Ручной маппинг колонок (Динамически из trend_parameters)
        self.mapping_group = QGroupBox("Сопоставление колонок техпроцесса (из Конфигуратора)")
        self.mapping_grid = QGridLayout()
        self.mapping_group.setLayout(self.mapping_grid)
        self.mapping_group.hide()
        scroll_layout.addWidget(self.mapping_group)

        scroll_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Кнопка сохранения
        self.btn_save = QPushButton("✅ ЗАГРУЗИТЬ В БАЗУ")
        self.btn_save.setFixedHeight(50)
        self.btn_save.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; font-size: 11pt;")
        self.btn_save.clicked.connect(self.save_data)
        self.btn_save.setEnabled(False)
        layout.addWidget(self.btn_save)

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Выбор файла", "", "Data (*.xlsx *.csv)")
        if file:
            try:
                self.filepath = file
                self.lbl_file.setText(file.split("/")[-1])
                df = pd.read_csv(file, nrows=1) if file.endswith('.csv') else pd.read_excel(file, nrows=1)
                self.setup_mapping_ui(df.columns.tolist())
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Файл не читается: {e}")

    def setup_mapping_ui(self, columns):
        """Динамическое построение полей маппинга строго под тренды из конфигуратора"""
        for i in reversed(range(self.mapping_grid.count())):
            item = self.mapping_grid.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        self.combos.clear()
        cols_with_skip = ["-- Пропустить --"] + columns

        # Сначала обязательное поле времени
        required_fields = {"timestamp": "Дата и время (Timestamp / Время)"}
        # Затем добавляем ВСЕ тренды, которые инженер настроил в Конфигураторе
        for param in config.hmi.trend_parameters:
            required_fields[param['key']] = param.get('label', param['key'])

        for i, (key, label) in enumerate(required_fields.items()):
            combo = QComboBox()
            combo.addItems(cols_with_skip)

            # Автоматический подбор похожего названия колонки в файле
            for col in columns:
                if key.lower() in col.lower() or label.split(' ')[0].lower() in col.lower():
                    combo.setCurrentText(col)
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

            def clean_float(text, name, is_percent=False):
                val_str = text.replace(',', '.')
                if not val_str:
                    return 0.0
                val = float(val_str)
                if is_percent and not (0 <= val <= 100):
                    raise ValueError(f"Поле '{name}' должно быть в диапазоне от 0 до 100!")
                return val

            # Читаем исходный файл
            df = pd.read_csv(self.filepath) if self.filepath.endswith('.csv') else pd.read_excel(self.filepath)

            # Проверяем маппинг времени
            time_combo = self.combos.get('timestamp')
            if not time_combo or time_combo.currentText() == "-- Пропустить --":
                raise ValueError("Поле 'Дата и время (Timestamp)' обязательно для сопоставления!")

            excel_time_col = time_combo.currentText()

            # Готовим чистый датафрейм процесса
            process_records = []

            # Собираем список всех ключей трендов из конфигуратора, которые нужно вытащить
            trend_keys = [param['key'] for param in config.hmi.trend_parameters]

            for _, row in df.iterrows():
                # Пропускаем строки-заголовки, если они попали в данные
                t_val = str(row.get(excel_time_col, '')).strip()
                if t_val in ["", "nan", "None", excel_time_col.lower(), "время", "timestamp"]:
                    continue

                record = {'timestamp': t_val}

                # Для каждого тренда из конфигуратора проверяем, сопоставил ли его пользователь
                for key in trend_keys:
                    combo = self.combos.get(key)
                    if combo and combo.currentText() != "-- Пропустить --":
                        excel_col = combo.currentText()
                        val = row.get(excel_col, 0.0)
                        try:
                            record[key] = float(str(val).replace(',', '.'))
                        except (ValueError, TypeError):
                            record[key] = 0.0
                    else:
                        # Если колонка пропущена, ставим 0.0
                        record[key] = 0.0

                process_records.append(record)

            if not process_records:
                raise ValueError("Не удалось извлечь ни одной валидной строки процессных данных из файла!")

            # Собираем данные паспорта партии
            batch_data = {
                'batch_id': batch_id,
                'extraction_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                'unit_name': self.edit_unit.currentText(),
                'sample_weight': clean_float(self.edit_mass.text(), "Масса", is_percent=False),
                'target_metric': clean_float(self.edit_ext.text(),
                                             config.hmi.target_parameter.get('label', 'Целевой показатель'),
                                             is_percent=True)
            }

            # Добираем статические параметры сырья из конфига
            for key, edit in self.chem_inputs.items():
                batch_data[key] = clean_float(edit.text(), key, is_percent=False)

            # Сохраняем в БД
            self.db.add_batch(batch_data)
            self.db.add_process_data(batch_id, process_records)

            QMessageBox.information(self, "Готово",
                                    f"Успешно загружено {len(process_records)} строк процессных данных строго по конфигурации!")
            self.accept()

        except ValueError as ve:
            QMessageBox.warning(self, "Ошибка в данных", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Детали: {e}")