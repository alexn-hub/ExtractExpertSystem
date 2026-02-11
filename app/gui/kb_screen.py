from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QLineEdit,
    QLabel, QComboBox, QPushButton, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt
from app.gui.import_dialog import ImportDataDialog

class KnowledgeBaseScreen(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # --- ОБЛАСТЬ 1: ФИЛЬТРЫ ---
        filter_group = QGroupBox("Параметры поиска")
        filter_layout = QHBoxLayout()

        self.filter_sfr = QComboBox()
        self.filter_sfr.addItems(["Все аппараты", "3", "4"])

        self.filter_mass_min = QLineEdit()
        self.filter_mass_min.setPlaceholderText("Мин. масса (кг)")

        self.filter_extract = QComboBox()
        self.filter_extract.addItems(["Любое извлечение", "> 90%", "> 95%", "> 98%"])

        # Фиксированная ширина для кнопок, чтобы они были одинаковыми
        btn_width = 170
        btn_height = 40

        #Кнопка выгрузки данных из БЗ
        self.btn_search = QPushButton("🔍 ОБНОВИТЬ")
        self.btn_search.setFixedWidth(btn_width)
        self.btn_search.setFixedHeight(btn_height)
        self.btn_search.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; padding: 5px 15px;")
        self.btn_search.clicked.connect(self.load_batches)

        # Кнопка Импорт данных
        self.btn_import = QPushButton("➕ ИМПОРТ ДАННЫХ")
        self.btn_import.setFixedWidth(btn_width)
        self.btn_import.setFixedHeight(btn_height)
        self.btn_import.setStyleSheet("background-color: #1565C0; color: white; font-weight: bold; padding: 5px 15px;")
        self.btn_import.clicked.connect(self.open_import_dialog)

        # Кнопка Удалить ---
        self.btn_delete = QPushButton("УДАЛИТЬ ПАРТИЮ")
        self.btn_delete.setFixedWidth(btn_width)
        self.btn_delete.setFixedHeight(btn_height)
        self.btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #C62828; 
                    color: white; 
                    font-weight: bold; 
                    padding: 5px 15px;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                }
            """)
        self.btn_delete.clicked.connect(self.delete_selected_batch)

        filter_layout.addWidget(QLabel("Аппарат:"))
        filter_layout.addWidget(self.filter_sfr)
        filter_layout.addWidget(QLabel("Масса от:"))
        filter_layout.addWidget(self.filter_mass_min)
        filter_layout.addWidget(QLabel("Эффективность:"))
        filter_layout.addWidget(self.filter_extract)
        filter_layout.addStretch()
        filter_layout.addWidget(self.btn_search)
        filter_layout.addWidget(self.btn_import)
        filter_layout.addWidget(self.btn_delete)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # --- ОБЛАСТЬ 2: ТАБЛИЦА BATCHES (ВЕРХНЯЯ) ---
        layout.addWidget(QLabel("<b>Реестр успешных партий (batches):</b>"))
        self.table_batches = QTableWidget()
        # Включаем стандартную нумерацию строк слева
        self.table_batches.verticalHeader().setVisible(True)
        self.table_batches.verticalHeader().setDefaultSectionSize(25)

        self.table_batches.setColumnCount(12)
        self.table_batches.setHorizontalHeaderLabels([
            "ID Партии", "Дата", "СФР", "Масса, кг", "Извлеч. %",
            "Ni %", "Cu %", "Pt %", "Pd %", "SiO2 %", "C %", "Se %"
        ])

        self.table_batches.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_batches.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_batches.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_batches.itemSelectionChanged.connect(self.on_batch_selected)
        layout.addWidget(self.table_batches)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # --- ОБЛАСТЬ 3: ТАБЛИЦА PROCESS_DATA (НИЖНЯЯ) ---
        layout.addWidget(QLabel("<b>Подробные параметры тех. процесса (process_data):</b>"))
        self.table_process = QTableWidget()
        self.table_process.verticalHeader().setVisible(False)

        # Увеличиваем количество колонок до 9 (или 10, если хочешь видеть СФР и там)
        self.table_process.setColumnCount(9)
        self.table_process.setHorizontalHeaderLabels([
            "Время", "Т раст. 1", "Т раст. 2", "Т газа", "Ток", "Расход кисл.",
            "Уров. микс.", "Полож. электр.", "Опт. темп."
        ])

        self.table_process.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_process.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table_process)

        # Чтобы левые края колонок совпадали, установим одинаковую ширину отступа (Vertical Header Width)
        # В верхней таблице он есть, в нижней его нет. Мы можем сделать фиктивный отступ.
        self.table_batches.verticalHeader().setFixedWidth(40)

        self.load_batches()

    def load_batches(self):
        """Загрузка данных с фильтрацией"""
        all_batches = self.db.get_all_batches()
        sfr_filter = self.filter_sfr.currentText()
        extract_filter = self.filter_extract.currentText()

        # 1. Парсинг фильтра по массе
        try:
            min_mass = float(self.filter_mass_min.text()) if self.filter_mass_min.text() else 0
        except ValueError:
            min_mass = 0

        # 2. Парсинг фильтра по извлечению (например из "> 90%" достаем 90)
        min_extract = 0
        if "%" in extract_filter:
            try:
                min_extract = float(extract_filter.replace(">", "").replace("%", "").strip())
            except:
                min_extract = 0

        self.table_batches.setRowCount(0)
        row_idx = 0
        for b in all_batches:
            # Фильтр СФР
            if sfr_filter != "Все аппараты" and str(b['sulfate_number']) != sfr_filter:
                continue

            # Фильтр Масса
            if b['sample_weight'] < min_mass:
                continue

            # Фильтр Извлечение (ИСПРАВЛЕНО)
            if b['extraction_percent'] < min_extract:
                continue

            self.table_batches.insertRow(row_idx)
            # Ставим данные
            self.table_batches.setItem(row_idx, 0, QTableWidgetItem(str(b['batch_id'])))
            self.table_batches.setItem(row_idx, 1, QTableWidgetItem(str(b['extraction_date'])))
            self.table_batches.setItem(row_idx, 2, QTableWidgetItem(f"СФР-{b['sulfate_number']}"))
            self.table_batches.setItem(row_idx, 3, QTableWidgetItem(f"{b['sample_weight']:.1f}"))
            self.table_batches.setItem(row_idx, 4, QTableWidgetItem(f"{b['extraction_percent']}%"))

            # Химия
            fields = ['ni_percent', 'cu_percent', 'pt_percent', 'pd_percent', 'sio2_percent', 'c_percent', 'se_percent']
            for col, field in enumerate(fields, start=5):
                val = b.get(field, 0)
                self.table_batches.setItem(row_idx, col, QTableWidgetItem(f"{val:.2f}"))

            row_idx += 1

    def open_import_dialog(self):
        from app.gui.import_dialog import ImportDataDialog  # Импорт внутри метода, чтобы избежать циклов
        dialog = ImportDataDialog(self.db, self)
        if dialog.exec_():
            self.load_batches()  # Обновляем таблицу после добавления

    def on_batch_selected(self):
        selected = self.table_batches.selectedItems()
        if not selected:
            return

        # batch_id берем из 0-й колонки (ID Партии)
        batch_id = self.table_batches.item(selected[0].row(), 0).text()
        df = self.db.get_process_data(batch_id)

        self.table_process.setRowCount(0)
        for i, row in df.iterrows():
            self.table_process.insertRow(i)

            # 1-6 колонки (базовые)
            self.table_process.setItem(i, 0, QTableWidgetItem(str(row.get('timestamp', ''))))
            self.table_process.setItem(i, 1, QTableWidgetItem(f"{row.get('temperature_1', 0):.1f}"))
            self.table_process.setItem(i, 2, QTableWidgetItem(f"{row.get('temperature_2', 0):.1f}"))
            self.table_process.setItem(i, 3, QTableWidgetItem(f"{row.get('temperature_3', 0):.1f}"))
            self.table_process.setItem(i, 4, QTableWidgetItem(f"{row.get('current_value', 0):.3f}"))
            self.table_process.setItem(i, 5, QTableWidgetItem(f"{row.get('acid_flow', 0):.2f}"))

            # 7-9 колонки (новые параметры)
            self.table_process.setItem(i, 6, QTableWidgetItem(f"{row.get('level_mixer', 0):.1f}"))
            self.table_process.setItem(i, 7, QTableWidgetItem(f"{row.get('electrodes_pos', 0):.1f}"))
            self.table_process.setItem(i, 8, QTableWidgetItem(f"{row.get('optimal_temp', 0):.1f}"))

    def delete_selected_batch(self):
        selected = self.table_batches.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Сначала выберите партию в таблице!")
            return

        # Берем ID партии из первой колонки выделенной строки
        row = selected[0].row()
        batch_id = self.table_batches.item(row, 0).text()

        # Спрашиваем подтверждение (важно, чтобы не удалить случайно!)
        reply = QMessageBox.question(
            self, 'Подтверждение',
            f"Вы уверены, что хотите полностью удалить партию {batch_id}?\nЭто действие нельзя отменить.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.db.delete_batch(batch_id):
                QMessageBox.information(self, "Успех", f"Партия {batch_id} удалена.")
                self.load_batches()  # Обновляем список партий
                self.table_process.setRowCount(0)  # Очищаем нижнюю таблицу
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить данные из базы.")