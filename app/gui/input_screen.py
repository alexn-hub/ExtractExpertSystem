from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLineEdit,
    QPushButton, QLabel, QComboBox, QGroupBox
)
from PyQt5.QtCore import Qt


class InputScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel("Ввод данных новой партии")
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Основная форма
        form_group = QGroupBox("Общая информация")
        form_layout = QGridLayout()

        form_layout.addWidget(QLabel("Сульфатизатор:"), 0, 0)
        self.combo_sfr = QComboBox()
        self.combo_sfr.addItems(["СФР-3", "СФР-4"])
        form_layout.addWidget(self.combo_sfr, 0, 1)

        form_layout.addWidget(QLabel("Номер партии:"), 1, 0)
        self.edit_batch_id = QLineEdit("P-2026-001")
        form_layout.addWidget(self.edit_batch_id, 1, 1)

        form_layout.addWidget(QLabel("Масса (кг):"), 2, 0)
        self.edit_weight = QLineEdit("0")
        form_layout.addWidget(self.edit_weight, 2, 1)


        form_layout.addWidget(QLabel("Извлечение (%):"), 3, 0)
        self.edit_extraction = QLineEdit("0.0")
        form_layout.addWidget(self.edit_extraction, 3, 1)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Сетка для химического состава
        chem_group = QGroupBox("Химический состав (%)")
        chem_layout = QGridLayout()

        self.inputs = {}
        elements = [
            ("Ni", "ni_percent"), ("Cu", "cu_percent"),
            ("Pt", "pt_percent"), ("Pd", "pd_percent"),
            ("SiO2", "sio2_percent"), ("C", "c_percent"), ("Se", "se_percent")
        ]

        for i, (name, key) in enumerate(elements):
            row, col = divmod(i, 2)
            chem_layout.addWidget(QLabel(f"{name}:"), row, col * 2)
            edit = QLineEdit("0")  # Значение по умолчанию
            chem_layout.addWidget(edit, row, col * 2 + 1)
            self.inputs[key] = edit

        chem_group.setLayout(chem_layout)
        layout.addWidget(chem_group)


        # Кнопка ОК
        self.btn_start = QPushButton("ОК (Запустить расчет)")
        self.btn_start.setMinimumHeight(60)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        layout.addWidget(self.btn_start)
        layout.addStretch()

    def get_data(self):
        """Метод для сбора данных из всех полей для Recommender"""
        data = {
            'sulfate_number': int(self.combo_sfr.currentText().split('-')[-1]),
            'batch_id': self.edit_batch_id.text(),
            'sample_weight': float(self.edit_weight.text() or 0),
            'extraction_percent': float(self.edit_extraction.text() or 0)
        }
        # Собираем химию
        for key, edit in self.inputs.items():
            data[key] = float(edit.text() or 0)
        return data