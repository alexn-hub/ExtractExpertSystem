import pandas as pd
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLineEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox, QHBoxLayout, QComboBox, QScrollArea, QWidget,
    QTabWidget, QApplication
)
from PyQt5.QtCore import Qt
from app.core.data_importer import ExternalDBImporter


class ImportDataDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.sql_importer = ExternalDBImporter()
        self.filepath = ""
        self.setWindowTitle("Импорт новой партии в БЗ")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)

        # Создаем вкладки
        self.tabs = QTabWidget()

        # Вкладка 1: Ручной импорт / Excel
        self.excel_tab = QWidget()
        self.setup_excel_ui()

        # Вкладка 2: Импорт из SQL БД
        self.sql_tab = QWidget()
        self.setup_sql_ui()

        self.tabs.addTab(self.excel_tab, "Файлы")
        self.tabs.addTab(self.sql_tab, "БД (SQL)")

        self.main_layout.addWidget(self.tabs)

    def setup_excel_ui(self):
        """Твой существующий интерфейс для Excel/Ручного ввода"""
        layout = QVBoxLayout(self.excel_tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll_layout = QVBoxLayout(content_widget)

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
        scroll_layout.addWidget(batch_group)

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
        scroll_layout.addWidget(chem_group)

        # --- 3. Файл ---
        file_group = QGroupBox("Файл данных")
        file_layout = QHBoxLayout()
        self.lbl_file = QLabel("Файл не выбран")
        btn_select = QPushButton("📁 Выбрать Excel/CSV")
        btn_select.clicked.connect(self.select_file)
        file_layout.addWidget(self.lbl_file)
        file_layout.addWidget(btn_select)
        file_group.setLayout(file_layout)
        scroll_layout.addWidget(file_group)

        # --- 4. МАППИНГ (С ТАЙМСТЕМПОМ) ---
        self.mapping_group = QGroupBox("Сопоставление столбцов процесса")
        self.mapping_grid = QGridLayout()
        self.mapping_group.setLayout(self.mapping_grid)
        self.mapping_group.hide()
        scroll_layout.addWidget(self.mapping_group)
        # Прижимаем всё содержимое вверх, чтобы не расползалось
        scroll_layout.addStretch()
        scroll.setWidget(content_widget)

        layout.addWidget(scroll)

        self.btn_save = QPushButton("✅ ЗАГРУЗИТЬ В БАЗУ")
        self.btn_save.setFixedHeight(45)
        self.btn_save.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_data)
        self.btn_save.setEnabled(False)
        layout.addWidget(self.btn_save)

        # Список полей для процесса
        self.required_fields = {
            "timestamp": "Дата и время (Timestamp)",
            "temperature_1": "Т раствора 1 (°C)",
            "temperature_2": "Т раствора 2 (°C)",
            "temperature_3": "Т газа (°C)",
            "current_value": "Ток (А)",
            "acid_flow": "Расход кислоты (т)",
            "level_mixer": "Уровень миксера",
            "electrodes_pos": "Позиция электрода",  # Исправлено
            "optimal_temp": "Опт. температура"
        }
        self.combos = {}

    def run_sql_sync(self):
        """Логика подключения и импорта из SQL"""
        self.btn_run_sql.setEnabled(False)
        self.btn_run_sql.setText("Подключение...")
        QApplication.processEvents()

        success = self.sql_importer.connect_external(
            self.db_type.currentText(),
            self.db_host.text(),
            self.db_port.text(),
            self.db_user.text(),
            self.db_pass.text(),
            self.db_name.text()
        )

        if not success:
            QMessageBox.critical(self, "Ошибка связи", "Не удалось установить соединение с сервером БД.")
            self.btn_run_sql.setEnabled(True)
            self.btn_run_sql.setText("ЗАПУСТИТЬ СИНХРОНИЗАЦИЮ")
            return

        self.btn_run_sql.setText("Загрузка данных...")
        QApplication.processEvents()

        count = self.sql_importer.import_good_batches(days_back=30)

        if count > 0:
            QMessageBox.information(self, "Успех", f"Синхронизация завершена!\nИмпортировано партий: {count}")
            self.accept()
        else:
            QMessageBox.warning(self, "Результат", "Новых данных для импорта не обнаружено.")
            self.btn_run_sql.setEnabled(True)
            self.btn_run_sql.setText("ЗАПУСТИТЬ СИНХРОНИЗАЦИЮ")

    def setup_sql_ui(self):
        """Новый интерфейс для подключения к SQL"""
        layout = QVBoxLayout(self.sql_tab)

        conn_group = QGroupBox("Параметры подключения к внешней БД")
        grid = QGridLayout()

        self.db_type = QComboBox()
        self.db_type.addItems(["PostgreSQL", "MSSQL"])

        self.db_host = QLineEdit("localhost")
        self.db_port = QLineEdit("5432")
        self.db_user = QLineEdit("postgres")
        self.db_pass = QLineEdit()
        self.db_pass.setEchoMode(QLineEdit.Password)
        self.db_name = QLineEdit("factory_db")

        grid.addWidget(QLabel("Тип БД:"), 0, 0);
        grid.addWidget(self.db_type, 0, 1)
        grid.addWidget(QLabel("Хост:"), 1, 0);
        grid.addWidget(self.db_host, 1, 1)
        grid.addWidget(QLabel("Порт:"), 2, 0);
        grid.addWidget(self.db_port, 2, 1)
        grid.addWidget(QLabel("Пользователь:"), 3, 0);
        grid.addWidget(self.db_user, 3, 1)
        grid.addWidget(QLabel("Пароль:"), 4, 0);
        grid.addWidget(self.db_pass, 4, 1)
        grid.addWidget(QLabel("Имя БД:"), 5, 0);
        grid.addWidget(self.db_name, 5, 1)

        conn_group.setLayout(grid)
        layout.addWidget(conn_group)

        info_label = QLabel("Будут загружены только успешные партии за последние 30 дней\n"
                            "(Извлечение > 85%, оценка качества >= 4)")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)

        self.btn_run_sql = QPushButton("ЗАПУСТИТЬ СИНХРОНИЗАЦИЮ")
        self.btn_run_sql.setFixedHeight(50)
        self.btn_run_sql.setStyleSheet("background-color: #E3F2FD; font-weight: bold;")
        self.btn_run_sql.clicked.connect(self.run_sql_sync)
        layout.addWidget(self.btn_run_sql)
        layout.addStretch()

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

            # --- Вспомогательная функция для валидации ---
            def clean_and_validate(widget, name, is_percent=True):
                val_str = widget.text().replace(',', '.')
                if not val_str: return 0.0
                val = float(val_str)
                if is_percent and not (0 <= val <= 100):
                    raise ValueError(f"Поле '{name}' должно быть в диапазоне от 0 до 100!")
                return val

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
            process_df['timestamp'] = process_df['timestamp'].astype(str).str.strip()
            excel_time_col_name = self.combos['timestamp'].currentText().strip()

            process_df = process_df[
                (process_df['timestamp'] != excel_time_col_name) &
                (process_df['timestamp'].str.lower() != "время")
                ]
            process_df = process_df.dropna(subset=['timestamp'])
            process_df = process_df[process_df['timestamp'] != "nan"]

            # РАСШИРЕННЫЙ СПИСОК СТОЛБЦОВ: добавили level_mixer, electrode_pos, optimal_temp
            float_cols = [
                'temperature_1', 'temperature_2', 'temperature_3',
                'current_value', 'acid_flow',
                'level_mixer', 'electrodes_pos', 'optimal_temp'  # Исправлено
            ]

            for col in float_cols:
                if col in process_df.columns:
                    process_df[col] = pd.to_numeric(process_df[col], errors='coerce').fillna(0.0)
                else:
                    process_df[col] = 0.0
            # --- КОНЕЦ ОЧИСТКИ ---

            # 3. Сохранение партии (batches) с проверками
            sfr_val = self.edit_sfr.text().strip()
            if sfr_val not in ['3', '4']:
                raise ValueError("Номер СФР должен быть только 3 или 4!")

            sfr_int = int(sfr_val)

            batch_data = {
                'batch_id': batch_id,
                'extraction_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                'sulfate_number': sfr_int,
                'sample_weight': clean_and_validate(self.edit_mass, "Масса", is_percent=False),
                'extraction_percent': clean_and_validate(self.edit_ext, "Извлечение")
            }

            # Добавляем химию с проверкой на 0-100%
            if hasattr(self, 'chem_inputs'):
                chem_names = {'ni_percent': 'Ni', 'cu_percent': 'Cu', 'pt_percent': 'Pt',
                              'pd_percent': 'Pd', 'sio2_percent': 'SiO2', 'c_percent': 'C', 'se_percent': 'Se'}
                for key, edit in self.chem_inputs.items():
                    batch_data[key] = clean_and_validate(edit, chem_names.get(key, key))

            self.db.add_batch(batch_data)

            # 4. Сохранение процесса (process_data)
            process_df['timestamp'] = process_df['timestamp'].astype(str)
            records = process_df.to_dict('records')

            # ПЕРЕДАЕМ sfr_int вторым аргументом, как обновили в database.py
            self.db.add_process_data(batch_id, sfr_int, records)

            QMessageBox.information(self, "Готово", f"Успешно загружено {len(records)} строк для СФР-{sfr_int}")
            self.accept()

        except ValueError as ve:
            QMessageBox.warning(self, "Ошибка в данных", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Детали: {e}")