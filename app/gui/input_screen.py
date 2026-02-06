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
        self.edit_weight = QLineEdit("1042.08")
        form_layout.addWidget(self.edit_weight, 2, 1)


        form_layout.addWidget(QLabel("Извлечение (%):"), 3, 0)
        self.edit_extraction = QLineEdit("93.08")
        form_layout.addWidget(self.edit_extraction, 3, 1)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Сетка для химического состава
        # Создаем словарь соответствия ключей и тестовых значений
        test_values = {
            "ni_percent": "1.57",
            "cu_percent": "1.58",
            "pt_percent": "8.37",
            "pd_percent": "33.62",
            "sio2_percent": "9.80",
            "c_percent": "9.86",
            "se_percent": "1.49"
        }

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

            val = test_values.get(key, "0")
            edit = QLineEdit(val)
            chem_layout.addWidget(edit, row, col * 2 + 1)
            self.inputs[key] = edit

        chem_group.setLayout(chem_layout)
        layout.addWidget(chem_group)


        # Кнопка ОК
        self.btn_start = QPushButton("Запустить расчет")
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
        """Метод для сбора данных из всех полей для Recommender с проверкой ошибок"""
        from PyQt5.QtWidgets import QMessageBox

        def clean_float(text):
            """Заменяет запятую на точку и пробует превратить в число"""
            try:
                # 1. Меняем запятую на точку, если она есть
                sanitized_text = text.replace(',', '.')
                return float(sanitized_text)
            except ValueError:
                return None

        try:
            # Проверка основных полей
            weight = clean_float(self.edit_weight.text())
            extraction = clean_float(self.edit_extraction.text())

            if weight is None or extraction is None:
                raise ValueError("Поля 'Масса' или 'Извлечение' заполнены неверно")

            data = {
                'sulfate_number': int(self.combo_sfr.currentText().split('-')[-1]),
                'batch_id': self.edit_batch_id.text(),
                'sample_weight': weight,
                'extraction_percent': extraction
            }

            # Собираем и проверяем химию
            for key, edit in self.inputs.items():
                val = clean_float(edit.text())
                if val is None:
                    # Ищем красивое имя элемента для сообщения об ошибке
                    element_name = next((e[0] for e in [
                        ("Ni", "ni_percent"), ("Cu", "cu_percent"), ("Pt", "pt_percent"),
                        ("Pd", "pd_percent"), ("SiO2", "sio2_percent"), ("C", "c_percent"),
                        ("Se", "se_percent")
                    ] if e[1] == key), key)
                    raise ValueError(f"Ошибка в поле химического состава: {element_name}")
                data[key] = val

            return data

        except ValueError as e:
            # Вывод ошибки пользователю
            QMessageBox.critical(self, "Ошибка ввода", str(e))
            return None