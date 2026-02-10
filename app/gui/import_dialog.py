import pandas as pd
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLineEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox, QHBoxLayout, QComboBox, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt


class ImportDataDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.filepath = ""
        self.setWindowTitle("Импорт новой партии в БЗ")
        self.setMinimumWidth(750)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        # --- 1. Основные параметры ---
        batch_group = QGroupBox("Параметры партии")
        grid_main = QGridLayout()
        self.edit_id = QLineEdit();
        self.edit_id.setPlaceholderText("P-2026-XXX")
        self.edit_mass = QLineEdit();
        self.edit_mass.setPlaceholderText("кг")
        self.edit_ext = QLineEdit();
        self.edit_ext.setPlaceholderText("%")
        self.edit_sfr = QLineEdit();
        self.edit_sfr.setPlaceholderText("3 или 4")
        grid_main.addWidget(QLabel("ID Партии:"), 0, 0);
        grid_main.addWidget(self.edit_id, 0, 1)
        grid_main.addWidget(QLabel("СФР:"), 1, 0);
        grid_main.addWidget(self.edit_sfr, 1, 1)
        grid_main.addWidget(QLabel("Масса:"), 0, 2);
        grid_main.addWidget(self.edit_mass, 0, 3)
        grid_main.addWidget(QLabel("Извлечение:"), 1, 2);
        grid_main.addWidget(self.edit_ext, 1, 3)
        batch_group.setLayout(grid_main)
        layout.addWidget(batch_group)

        # --- 2. Химический состав ---
        chem_group = QGroupBox("Химический состав (%)")
        grid_chem = QGridLayout()
        self.chem_inputs = {
            'ni_percent': QLineEdit("0.0"), 'cu_percent': QLineEdit("0.0"),
            'pt_percent': QLineEdit("0.0"), 'pd_percent': QLineEdit("0.0"),
            'sio2_percent': QLineEdit("0.0"), 'c_percent': QLineEdit("0.0"),
            'se_percent': QLineEdit("0.0")
        }
        names = [("Ni", "ni_percent"), ("Cu", "cu_percent"), ("Pt", "pt_percent"),
                 ("Pd", "pd_percent"), ("SiO2", "sio2_percent"), ("C", "c_percent"), ("Se", "se_percent")]
        for i, (label, key) in enumerate(names):
            grid_chem.addWidget(QLabel(f"{label}:"), i // 2, (i % 2) * 2)
            grid_chem.addWidget(self.chem_inputs[key], i // 2, (i % 2) * 2 + 1)
        chem_group.setLayout(grid_chem)
        layout.addWidget(chem_group)

        # --- 3. Файл ---
        file_group = QGroupBox("Файл данных")
        file_layout = QHBoxLayout()
        self.lbl_file = QLabel("Файл не выбран")
        btn_select = QPushButton("📁 Выбрать Excel/CSV")
        btn_select.clicked.connect(self.select_file)
        file_layout.addWidget(self.lbl_file)
        file_layout.addWidget(btn_select)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # --- 4. МАППИНГ (С ТАЙМСТЕМПОМ) ---
        self.mapping_group = QGroupBox("Сопоставление столбцов процесса")
        self.mapping_grid = QGridLayout()
        self.mapping_group.setLayout(self.mapping_grid)
        self.mapping_group.setVisible(False)
        layout.addWidget(self.mapping_group)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self.btn_save = QPushButton("✅ ЗАГРУЗИТЬ ВСЁ В БАЗУ")
        self.btn_save.setFixedHeight(45)
        self.btn_save.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_data)
        self.btn_save.setEnabled(False)
        main_layout.addWidget(self.btn_save)

        # Список полей для процесса
        self.required_fields = {
            "timestamp": "Дата и время (Timestamp)",
            "temperature_1": "Т раствора 1 (°C)",
            "temperature_2": "Т раствора 2 (°C)",
            "temperature_3": "Т газа (°C)",
            "current_value": "Ток (А)",
            "acid_flow": "Расход кислоты (л/мин)"
        }
        self.combos = {}

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Выбор", "", "Data (*.xlsx *.csv)")
        if file:
            try:
                self.filepath = file
                self.lbl_file.setText(file.split("/")[-1])
                df = pd.read_csv(file, nrows=1) if file.endswith('.csv') else pd.read_excel(file, nrows=1)
                self.setup_mapping_ui(df.columns.tolist())
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Файл не читается: {e}")

    def setup_mapping_ui(self, columns):
        for i in reversed(range(self.mapping_grid.count())):
            self.mapping_grid.itemAt(i).widget().setParent(None)

        cols_with_skip = ["-- Пропустить --"] + columns
        for i, (key, label) in enumerate(self.required_fields.items()):
            combo = QComboBox()
            combo.addItems(cols_with_skip)

            # Авто-поиск
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
            if not batch_id: raise ValueError("Укажите ID партии!")

            # 1. Чтение данных
            df = pd.read_csv(self.filepath) if self.filepath.endswith('.csv') else pd.read_excel(self.filepath)

            # 2. Формируем маппинг из комбобоксов
            rename_map = {}
            for internal_name, combo in self.combos.items():
                excel_col_name = combo.currentText()
                if excel_col_name != "-- Пропустить --":
                    rename_map[excel_col_name] = internal_name

            if 'timestamp' not in rename_map.values():
                raise ValueError("Поле Timestamp обязательно!")

            # Создаем рабочий DataFrame
            process_df = df[list(rename_map.keys())].rename(columns=rename_map)

            # --- ЖЕСТКАЯ ОЧИСТКА ДАННЫХ ---

            # 1. Сначала превращаем всё в строки и убираем лишние пробелы по краям
            process_df['timestamp'] = process_df['timestamp'].astype(str).str.strip()

            # 2. Получаем имя колонки, которое пользователь выбрал в интерфейсе
            excel_time_col_name = self.combos['timestamp'].currentText().strip()

            # 3. УДАЛЯЕМ СТРОКУ-ДУБЛИКАТ:
            # Оставляем только те строки, где значение НЕ совпадает с заголовком
            # Добавляем проверку на "название колонки" и на само слово "время" (на всякий случай)
            process_df = process_df[
                (process_df['timestamp'] != excel_time_col_name) &
                (process_df['timestamp'].str.lower() != "время")
                ]

            # 4. Удаляем пустые строки, если они есть
            process_df = process_df.dropna(subset=['timestamp'])
            process_df = process_df[process_df['timestamp'] != "nan"]  # Pandas при astype(str) превращает null в "nan"

            # 5. Числовые данные: теперь, когда мусорный заголовок удален,
            # приводим всё к float. Всё, что не число (вдруг там еще какой текст), станет 0.0
            float_cols = ['temperature_1', 'temperature_2', 'temperature_3', 'current_value', 'acid_flow']
            for col in float_cols:
                if col in process_df.columns:
                    process_df[col] = pd.to_numeric(process_df[col], errors='coerce').fillna(0.0)
                else:
                    process_df[col] = 0.0

            # --- КОНЕЦ ОЧИСТКИ ---

            # 3. Сохранение партии (batches)
            batch_data = {
                'batch_id': batch_id,
                'extraction_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                'sulfate_number': int(self.edit_sfr.text() or 3),
                'sample_weight': float(self.edit_mass.text() or 0),
                'extraction_percent': float(self.edit_ext.text() or 0)
            }
            # Добавляем химию (если поля созданы)
            if hasattr(self, 'chem_inputs'):
                for key, edit in self.chem_inputs.items():
                    batch_data[key] = float(edit.text() or 0)

            self.db.add_batch(batch_data)

            # 4. Сохранение процесса (process_data)
            # Переводим timestamp в строку "как есть", чтобы не терять дату
            process_df['timestamp'] = process_df['timestamp'].astype(str)

            records = process_df.to_dict('records')
            self.db.add_process_data(batch_id, records)

            QMessageBox.information(self, "Готово", f"Успешно загружено {len(records)} строк")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Детали: {e}")