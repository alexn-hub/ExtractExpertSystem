# app/gui/config_screen.py
import yaml
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QGridLayout, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt
from app.utils.config import config


def generate_key_from_label(label: str) -> str:
    """Автоматическая генерация системного ключа из русской метки (транслитерация + snake_case)"""
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    label_lower = label.lower().strip()
    result = []
    for char in label_lower:
        if char in translit_map:
            result.append(translit_map[char])
        elif char.isalnum():
            result.append(char)
        elif char in (' ', '_', '-'):
            result.append('_')

    key = "".join(result)
    while '__' in key:
        key = key.replace('__', '_')
    key = key.strip('_')
    return key or "param"


class ConfigScreen(QWidget):
    """Экран встроенного конфигуратора технологического процесса"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title = QLabel("Конфигуратор технологического процесса (Инженерный модуль)")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1565C0;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        # --- 1. ОБЩИЕ НАСТРОЙКИ ---
        group_general = QGroupBox("1. Общие параметры процесса")
        grid_general = QGridLayout()

        self.edit_units = QLineEdit(", ".join(config.hmi.units))
        self.edit_main_label = QLineEdit(config.hmi.passport_fields.get('main_metric_label', 'Масса (кг)'))
        self.edit_target_label = QLineEdit(config.hmi.target_parameter.get('label', 'Извлечение (%)'))

        grid_general.addWidget(QLabel("Участки / Аппараты (через запятую):"), 0, 0)
        grid_general.addWidget(self.edit_units, 0, 1)
        grid_general.addWidget(QLabel("Название главного параметра (Паспорт):"), 1, 0)
        grid_general.addWidget(self.edit_main_label, 1, 1)
        grid_general.addWidget(QLabel("Целевой показатель (Оптимизация):"), 2, 0)
        grid_general.addWidget(self.edit_target_label, 2, 1)

        group_general.setLayout(grid_general)
        layout.addWidget(group_general)

        # --- 2. СТАТИЧЕСКИЕ ПАРАМЕТРЫ СЫРЬЯ (Для поиска эталона) ---
        group_static = QGroupBox("2. Параметры сырья (Ввод оператора / Статика)")
        self.layout_static = QVBoxLayout()
        self.static_widgets = []

        for param in config.hmi.static_parameters:
            self.add_static_row(param.get('key', ''), param.get('label', ''), param.get('default', 0.0))

        btn_add_static = QPushButton("＋ Добавить параметр сырья")
        btn_add_static.clicked.connect(lambda: self.add_static_row("", "", 0.0))

        self.layout_static.addWidget(btn_add_static)
        group_static.setLayout(self.layout_static)
        layout.addWidget(group_static)

        # --- 3. ДИНАМИЧЕСКИЕ ТРЕНДЫ (Датчики процесса) ---
        group_trends = QGroupBox("3. Параметры технологического процесса (Тренды датчиков)")
        self.layout_trends = QVBoxLayout()
        self.trend_widgets = []

        for param in config.hmi.trend_parameters:
            self.add_trend_row(param.get('key', ''), param.get('label', ''), param.get('color', '#000000'))

        btn_add_trend = QPushButton("＋ Добавить тренд датчика")
        btn_add_trend.clicked.connect(lambda: self.add_trend_row("", "", "#000000"))

        self.layout_trends.addWidget(btn_add_trend)
        group_trends.setLayout(self.layout_trends)
        layout.addWidget(group_trends)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Кнопка сохранения
        self.btn_save = QPushButton("💾 СОХРАНИТЬ КОНФИГУРАЦИЮ И ПЕРЕЗАГРУЗИТЬ")
        self.btn_save.setFixedHeight(50)
        self.btn_save.setStyleSheet(
            "background-color: #2E7D32; color: white; font-size: 11pt; font-weight: bold; border-radius: 5px;")
        self.btn_save.clicked.connect(self.save_config)
        main_layout.addWidget(self.btn_save)

    def add_static_row(self, key, label, default):
        h_layout = QHBoxLayout()

        e_label = QLineEdit(label)
        e_label.setPlaceholderText("Метка на экране (например Ni (%))")

        # Ключ генерируется автоматически и защищен от ручного изменения
        e_key = QLineEdit(key or generate_key_from_label(label))
        e_key.setReadOnly(True)
        e_key.setStyleSheet("background-color: #ECEFF1; color: #37474F;")
        e_key.setFixedWidth(120)

        # Динамическое обновление ключа при изменении метки
        e_label.textChanged.connect(lambda text: e_key.setText(generate_key_from_label(text)))

        e_def = QLineEdit(str(default))
        e_def.setPlaceholderText("Дефолт")
        e_def.setFixedWidth(80)

        btn_del = QPushButton("❌")
        btn_del.setFixedWidth(40)

        h_layout.addWidget(QLabel("Метка:"))
        h_layout.addWidget(e_label)
        h_layout.addWidget(QLabel("Ключ (авто):"))
        h_layout.addWidget(e_key)
        h_layout.addWidget(QLabel("Дефолт:"))
        h_layout.addWidget(e_def)
        h_layout.addWidget(btn_del)

        container = QWidget()
        container.setLayout(h_layout)
        self.static_widgets.append((container, e_key, e_label, e_def))

        def remove_row():
            container.setParent(None)
            self.static_widgets.remove((container, e_key, e_label, e_def))

        btn_del.clicked.connect(remove_row)

        self.layout_static.insertWidget(self.layout_static.count() - 1, container)

    def add_trend_row(self, key, label, color):
        h_layout = QHBoxLayout()

        e_label = QLineEdit(label)
        e_label.setPlaceholderText("Метка графика (Т раствора)")

        e_key = QLineEdit(key or generate_key_from_label(label))
        e_key.setReadOnly(True)
        e_key.setStyleSheet("background-color: #ECEFF1; color: #37474F;")
        e_key.setFixedWidth(120)

        e_label.textChanged.connect(lambda text: e_key.setText(generate_key_from_label(text)))

        e_color = QLineEdit(color)
        e_color.setPlaceholderText("Цвет (#FF5252)")
        e_color.setFixedWidth(90)

        btn_del = QPushButton("❌")
        btn_del.setFixedWidth(40)

        h_layout.addWidget(QLabel("Метка:"))
        h_layout.addWidget(e_label)
        h_layout.addWidget(QLabel("Ключ (авто):"))
        h_layout.addWidget(e_key)
        h_layout.addWidget(QLabel("Цвет:"))
        h_layout.addWidget(e_color)
        h_layout.addWidget(btn_del)

        container = QWidget()
        container.setLayout(h_layout)
        self.trend_widgets.append((container, e_key, e_label, e_color))

        def remove_row():
            container.setParent(None)
            self.trend_widgets.remove((container, e_key, e_label, e_color))

        btn_del.clicked.connect(remove_row)

        self.layout_trends.insertWidget(self.layout_trends.count() - 1, container)

    def save_config(self):
        try:
            units = [u.strip() for u in self.edit_units.text().split(',') if u.strip()]
            if not units: raise ValueError("Укажите хотя бы один аппарат/участок!")

            static_params = []
            for _, k, l, d in self.static_widgets:
                key_val = k.text().strip()
                label_val = l.text().strip()
                if not label_val: continue
                static_params.append({
                    'key': key_val or generate_key_from_label(label_val),
                    'label': label_val,
                    'default': float(d.text().replace(',', '.') or 0.0)
                })

            trend_params = []
            for _, k, l, c in self.trend_widgets:
                key_val = k.text().strip()
                label_val = l.text().strip()
                if not label_val: continue
                trend_params.append({
                    'key': key_val or generate_key_from_label(label_val),
                    'label': label_val,
                    'color': c.text().strip() or '#000000'
                })

            # Обновляем объект конфига
            config.hmi.units = units
            config.hmi.passport_fields['main_metric_label'] = self.edit_main_label.text().strip()
            config.hmi.target_parameter['label'] = self.edit_target_label.text().strip()
            config.hmi.static_parameters = static_params
            config.hmi.trend_parameters = trend_params

            # Сохраняем в файл config.yaml
            config.save_to_file()

            QMessageBox.information(self, "Успех",
                                    "Конфигурация успешно сохранена! Перезапустите приложение для применения изменений на всех вкладках.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))