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
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(12)

        title = QLabel(f"ВВОД ПАРАМЕТРОВ ПАРТИИ: {self.unit_name.upper()}")
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #7EA6CD;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 1. Общая информация
        form_group = QGroupBox("Общие параметры партии")
        form_layout = QGridLayout()
        form_layout.setSpacing(8)

        passport_cfg = config.hmi.passport_fields
        form_layout.addWidget(QLabel("ID Партии:"), 0, 0)
        self.edit_batch_id = QLineEdit(passport_cfg.get('id_placeholder', 'P-2026-001'))
        form_layout.addWidget(self.edit_batch_id, 0, 1)

        main_label = passport_cfg.get('main_metric_label', 'Масса (кг)')
        form_layout.addWidget(QLabel(f"{main_label}:"), 1, 0)
        self.edit_weight = QLineEdit(str(passport_cfg.get('default_main_metric', '1000.0')))
        form_layout.addWidget(self.edit_weight, 1, 1)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # 2. Динамические параметры сырья (из конфига)
        params_group = QGroupBox("Свойства сырья (Паспорт партии / Статика)")
        params_layout = QGridLayout()
        params_layout.setSpacing(8)
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

        # 3. Кнопка подтверждения (стили подтягиваются из styles.qss через btn_run)
        self.btn_start = QPushButton("ПОДТВЕРДИТЬ ДАННЫЕ ПАРТИИ")
        self.btn_start.setObjectName("btn_run")
        self.btn_start.setFixedHeight(40)
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
                raise ValueError("Поле главного показателя заполнено неверно!")

            batch_id = self.edit_batch_id.text().strip()
            if not batch_id:
                raise ValueError("Укажите ID партии!")

            data = {
                'unit_name': self.unit_name,
                'batch_id': batch_id,
                'sample_weight': weight,
            }

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