# app/gui/input_screen.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLineEdit,
    QPushButton, QLabel, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt
from app.utils.config import config


class InputScreen(QWidget):
    """Динамический экран ввода параметров сырья на основе конфигурации"""

    def __init__(self, unit_name, parent=None):
        super().__init__(parent)
        self.unit_name = unit_name
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)

        title = QLabel(f"Ввод параметров партии: {self.unit_name}")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #263238;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Общая информация
        form_group = QGroupBox("Общие параметры")
        form_layout = QGridLayout()

        passport_cfg = config.hmi.passport_fields
        form_layout.addWidget(QLabel("ID Партии:"), 0, 0)
        self.edit_batch_id = QLineEdit(passport_cfg.get('id_placeholder', 'P-2026-001'))
        form_layout.addWidget(self.edit_batch_id, 0, 1)

        form_layout.addWidget(QLabel(passport_cfg.get('main_metric_label', 'Масса (кг):')), 1, 0)
        self.edit_weight = QLineEdit(str(passport_cfg.get('default_main_metric', '1000.0')))
        form_layout.addWidget(self.edit_weight, 1, 1)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Динамические параметры сырья (из конфига)
        params_group = QGroupBox("Свойства сырья / Химический состав")
        params_layout = QGridLayout()
        self.dynamic_inputs = {}

        for i, param in enumerate(config.hmi.static_parameters):
            row, col = divmod(i, 2)
            label_text = param.get('label', param['key'])
            default_val = str(param.get('default', 0.0))

            params_layout.addWidget(QLabel(f"{label_text}:"), row, col * 2)
            edit = QLineEdit(default_val)
            params_layout.addWidget(edit, row, col * 2 + 1)
            self.dynamic_inputs[param['key']] = edit

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Кнопка подтверждения
        self.btn_start = QPushButton("Подтвердить данные партии")
        self.btn_start.setMinimumHeight(55)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                font-size: 13pt;
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
            weight = clean_float(self.edit_weight.text())
            if weight is None:
                raise ValueError("Поле главного параметра (массы) заполнено неверно!")

            batch_id = self.edit_batch_id.text().strip()
            if not batch_id:
                raise ValueError("Укажите ID партии!")

            data = {
                'unit_name': self.unit_name,
                'batch_id': batch_id,
                'sample_weight': weight,
            }

            # Считываем статические параметры из динамических полей ввода
            for param in config.hmi.static_parameters:
                key = param['key']
                val = clean_float(self.dynamic_inputs[key].text())
                if val is None:
                    raise ValueError(f"Ошибка ввода в поле: {param['label']}")
                data[key] = val

            return data
        except ValueError as e:
            QMessageBox.critical(self, "Ошибка ввода", str(e))
            return None