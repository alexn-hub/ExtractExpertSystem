from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLineEdit,
    QPushButton, QLabel, QComboBox, QGroupBox
)
from PyQt5.QtCore import Qt


class InputScreen(QWidget):
    def __init__(self, unit_name="", parent=None):
        super().__init__(parent)
        self.unit_name = unit_name
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

        form_layout.addWidget(QLabel("Номер партии:"), 1, 0)
        self.edit_batch_id = QLineEdit("P-2026-001")
        form_layout.addWidget(self.edit_batch_id, 1, 1)

        form_layout.addWidget(QLabel("Масса (кг):"), 2, 0)
        self.edit_weight = QLineEdit("1042.08")
        form_layout.addWidget(self.edit_weight, 2, 1)

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
        self.btn_start = QPushButton("Подтвердить данные партии")
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
        def clean_float(text):
            try:
                return float(text.replace(',', '.'))
            except ValueError:
                return None

        try:
            # 1. Проверка массы (Извлечение отсюда УДАЛИЛИ)
            weight = clean_float(self.edit_weight.text())

            if weight is None:
                raise ValueError("Поле 'Масса' заполнено неверно")

            # 2. Формируем словарь
            data = {
                'sulfate_number': int(self.unit_name.split('-')[-1]),
                'batch_id': self.edit_batch_id.text(),
                'sample_weight': weight,
            }

            # 3. Собираем химию
            for key, edit in self.inputs.items():
                val = clean_float(edit.text())
                if val is None:
                    element_name = next((e[0] for e in [
                        ("Ni", "ni_percent"), ("Cu", "cu_percent"), ("Pt", "pt_percent"),
                        ("Pd", "pd_percent"), ("SiO2", "sio2_percent"), ("C", "c_percent"),
                        ("Se", "se_percent")
                    ] if e[1] == key), key)
                    raise ValueError(f"Ошибка в поле химического состава: {element_name}")
                data[key] = val

            return data

        except ValueError as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка ввода", str(e))
            return None