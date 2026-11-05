import socket
from urllib.parse import urlparse
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QGridLayout, QMessageBox, QScrollArea,
    QTabWidget, QComboBox, QColorDialog
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from app.utils.config import config


def generate_key_from_label(label: str) -> str:
    """Генерация системного ключа из русской метки под капотом"""
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
        'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
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
    """Экран инженерной конфигурации технологического процесса и сетевых подключений"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        title = QLabel("ИНЖЕНЕРНЫЙ КОНФИГУРАТОР ТЕХНОЛОГИЧЕСКОГО ПРОЦЕССА")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #7EA6CD;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Двухвкладочная структура без длинных технических названий
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setObjectName("config_sub_tabs")
        self.sub_tabs.addTab(self._create_process_tab(), "ТЕХПРОЦЕСС И ТРЕНДЫ")
        self.sub_tabs.addTab(self._create_integration_tab(), "СЕТЕВЫЕ ПОДКЛЮЧЕНИЯ (SQL / ПЛК)")
        main_layout.addWidget(self.sub_tabs)

        # Единая кнопка сохранения без упоминания внутренних файлов
        self.btn_save = QPushButton("СОХРАНИТЬ КОНФИГУРАЦИЮ")
        self.btn_save.setObjectName("btn_save")
        self.btn_save.setFixedHeight(38)
        self.btn_save.clicked.connect(self.save_config)
        main_layout.addWidget(self.btn_save)

    # =========================================================================
    # ВКЛАДКА 1: ТЕХНОЛОГИЧЕСКИЙ ПРОЦЕСС
    # =========================================================================
    def _create_process_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # 1. Общие параметры
        group_general = QGroupBox("1. Общие параметры процесса")
        grid_general = QGridLayout()
        grid_general.setSpacing(6)

        self.edit_units = QLineEdit(", ".join(config.hmi.units))
        self.edit_main_label = QLineEdit(config.hmi.passport_fields.get('main_metric_label', 'Масса (кг)'))
        self.edit_target_label = QLineEdit(config.hmi.target_parameter.get('label', 'Извлечение (%)'))

        grid_general.addWidget(QLabel("Участки / Аппараты (через запятую):"), 0, 0)
        grid_general.addWidget(self.edit_units, 0, 1)
        grid_general.addWidget(QLabel("Название главного показателя сырья:"), 1, 0)
        grid_general.addWidget(self.edit_main_label, 1, 1)
        grid_general.addWidget(QLabel("Целевой показатель оптимизации:"), 2, 0)
        grid_general.addWidget(self.edit_target_label, 2, 1)

        group_general.setLayout(grid_general)
        layout.addWidget(group_general)

        # 2. Параметры сырья (Статика)
        group_static = QGroupBox("2. Параметры сырья (Паспорт партии / Статика)")
        self.layout_static = QVBoxLayout()
        self.layout_static.setSpacing(6)
        self.static_widgets = []

        for param in config.hmi.static_parameters:
            self.add_static_row(
                param.get('key', ''),
                param.get('label', ''),
                param.get('default', 0.0)
            )

        btn_add_static = QPushButton("ДОБАВИТЬ ПАРАМЕТР СЫРЬЯ")
        btn_add_static.setObjectName("btn_new_batch")
        btn_add_static.setFixedHeight(28)
        btn_add_static.clicked.connect(lambda: self.add_static_row("", "", 0.0))
        self.layout_static.addWidget(btn_add_static)
        group_static.setLayout(self.layout_static)
        layout.addWidget(group_static)

        # 3. Тренды датчиков (Динамика)
        group_trends = QGroupBox("3. Параметры технологического процесса (Тренды оборудования)")
        self.layout_trends = QVBoxLayout()
        self.layout_trends.setSpacing(6)
        self.trend_widgets = []

        for param in config.hmi.trend_parameters:
            self.add_trend_row(
                param.get('key', ''),
                param.get('label', ''),
                param.get('color', '#448AFF'),
                param.get('role', 'control'),
                param.get('plc_tag', '')
            )

        btn_add_trend = QPushButton("ДОБАВИТЬ ТРЕНД")
        btn_add_trend.setObjectName("btn_new_batch")
        btn_add_trend.setFixedHeight(28)
        btn_add_trend.clicked.connect(lambda: self.add_trend_row("", "", "#448AFF", "control", ""))
        self.layout_trends.addWidget(btn_add_trend)
        group_trends.setLayout(self.layout_trends)
        layout.addWidget(group_trends)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # =========================================================================
    # ВКЛАДКА 2: СЕТЕВЫЕ ПОДКЛЮЧЕНИЯ (SQL И ПЛК)
    # =========================================================================
    def _create_integration_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # Блок 1: Внешняя БД
        group_sql = QGroupBox("1. Внешняя производственная база данных (SQL)")
        grid_sql = QGridLayout()
        grid_sql.setSpacing(6)

        self.combo_db_type = QComboBox()
        self.combo_db_type.addItems(["PostgreSQL", "MSSQL", "MySQL"])
        saved_db_type = getattr(config.db, 'db_type', 'PostgreSQL')
        if saved_db_type in ["PostgreSQL", "MSSQL", "MySQL"]:
            self.combo_db_type.setCurrentText(saved_db_type)
        self.combo_db_type.currentTextChanged.connect(self._on_db_type_changed)

        self.edit_db_host = QLineEdit(str(getattr(config.db, 'host', 'localhost')))
        self.edit_db_port = QLineEdit(str(getattr(config.db, 'port', 5432)))
        self.edit_db_name = QLineEdit(str(getattr(config.db, 'database', 'acdb')))
        self.edit_db_user = QLineEdit(str(getattr(config.db, 'username', 'postgres')))
        self.edit_db_pass = QLineEdit(str(getattr(config.db, 'password', '')))
        self.edit_db_pass.setEchoMode(QLineEdit.Password)

        btn_test_sql = QPushButton("ПРОВЕРИТЬ СОЕДИНЕНИЕ С СУБД")
        btn_test_sql.setObjectName("btn_import")
        btn_test_sql.setFixedHeight(28)
        btn_test_sql.clicked.connect(self.test_sql_connection)

        grid_sql.addWidget(QLabel("Тип СУБД:"), 0, 0)
        grid_sql.addWidget(self.combo_db_type, 0, 1)
        grid_sql.addWidget(QLabel("Хост / IP:"), 0, 2)
        grid_sql.addWidget(self.edit_db_host, 0, 3)

        grid_sql.addWidget(QLabel("Порт:"), 1, 0)
        grid_sql.addWidget(self.edit_db_port, 1, 1)
        grid_sql.addWidget(QLabel("База данных:"), 1, 2)
        grid_sql.addWidget(self.edit_db_name, 1, 3)

        grid_sql.addWidget(QLabel("Пользователь:"), 2, 0)
        grid_sql.addWidget(self.edit_db_user, 2, 1)
        grid_sql.addWidget(QLabel("Пароль:"), 2, 2)
        grid_sql.addWidget(self.edit_db_pass, 2, 3)

        grid_sql.addWidget(btn_test_sql, 3, 0, 1, 4)
        group_sql.setLayout(grid_sql)
        layout.addWidget(group_sql)

        # Блок 2: ПЛК
        group_plc = QGroupBox("2. Сбор данных в реальном времени (ПЛК / Эмуляция)")
        grid_plc = QGridLayout()
        grid_plc.setSpacing(6)

        self.combo_plc_protocol = QComboBox()
        self.combo_plc_protocol.addItems(["Simulation", "Modbus TCP", "OPC UA"])
        saved_proto = getattr(config.plc, 'protocol', 'Simulation')
        idx = self.combo_plc_protocol.findText(saved_proto)
        if idx >= 0:
            self.combo_plc_protocol.setCurrentIndex(idx)

        self.edit_poll_interval = QLineEdit(str(getattr(config.plc, 'polling_interval_ms', 1000)))

        self.edit_mb_host = QLineEdit(str(getattr(config.plc, 'modbus_host', '127.0.0.1')))
        self.edit_mb_port = QLineEdit(str(getattr(config.plc, 'modbus_port', 502)))
        self.edit_mb_unit = QLineEdit(str(getattr(config.plc, 'modbus_unit_id', 1)))

        self.edit_opc_url = QLineEdit(str(getattr(config.plc, 'opc_url', 'opc.tcp://127.0.0.1:4840')))
        self.edit_opc_user = QLineEdit(str(getattr(config.plc, 'opc_user', '')))
        self.edit_opc_pass = QLineEdit(str(getattr(config.plc, 'opc_password', '')))
        self.edit_opc_pass.setEchoMode(QLineEdit.Password)

        btn_test_plc = QPushButton("ПРОВЕРИТЬ ДОСТУПНОСТЬ УЗЛА ПЛК (TCP)")
        btn_test_plc.setObjectName("btn_import")
        btn_test_plc.setFixedHeight(28)
        btn_test_plc.clicked.connect(self.test_plc_connection)

        grid_plc.addWidget(QLabel("Активный протокол опроса:"), 0, 0)
        grid_plc.addWidget(self.combo_plc_protocol, 0, 1)
        grid_plc.addWidget(QLabel("Период опроса (мс):"), 0, 2)
        grid_plc.addWidget(self.edit_poll_interval, 0, 3)

        lbl_mb = QLabel("Параметры Modbus TCP:")
        lbl_mb.setStyleSheet("font-weight: bold; color: #8A99AD;")
        grid_plc.addWidget(lbl_mb, 1, 0, 1, 4)
        grid_plc.addWidget(QLabel("IP-адрес ПЛК:"), 2, 0)
        grid_plc.addWidget(self.edit_mb_host, 2, 1)
        grid_plc.addWidget(QLabel("Порт:"), 2, 2)
        grid_plc.addWidget(self.edit_mb_port, 2, 3)
        grid_plc.addWidget(QLabel("Slave (Unit) ID:"), 3, 0)
        grid_plc.addWidget(self.edit_mb_unit, 3, 1)

        lbl_opc = QLabel("Параметры OPC UA:")
        lbl_opc.setStyleSheet("font-weight: bold; color: #8A99AD;")
        grid_plc.addWidget(lbl_opc, 4, 0, 1, 4)
        grid_plc.addWidget(QLabel("URL конечной точки:"), 5, 0)
        grid_plc.addWidget(self.edit_opc_url, 5, 1, 1, 3)
        grid_plc.addWidget(QLabel("OPC Логин:"), 6, 0)
        grid_plc.addWidget(self.edit_opc_user, 6, 1)
        grid_plc.addWidget(QLabel("OPC Пароль:"), 6, 2)
        grid_plc.addWidget(self.edit_opc_pass, 6, 3)

        grid_plc.addWidget(btn_test_plc, 7, 0, 1, 4)
        group_plc.setLayout(grid_plc)
        layout.addWidget(group_plc)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _on_db_type_changed(self, db_type: str):
        default_ports = {"PostgreSQL": "5432", "MSSQL": "1433", "MySQL": "3306"}
        if db_type in default_ports:
            self.edit_db_port.setText(default_ports[db_type])

    # =========================================================================
    # РАБОТА СО СТРОКАМИ ПАРАМЕТРОВ (КЛЮЧ СПРЯТАН, ВЫБОР ЦВЕТА КНОПКОЙ)
    # =========================================================================
    def add_static_row(self, key, label, default):
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(6)

        e_label = QLineEdit(label)
        e_label.setPlaceholderText("Название параметра сырья")

        # Системный ключ скрыт от оператора, но хранится и обновляется динамически
        internal_key = key or generate_key_from_label(label)
        key_storage = {'key': internal_key}
        e_label.textChanged.connect(lambda text: key_storage.update({'key': generate_key_from_label(text)}))

        e_def = QLineEdit(str(default))
        e_def.setPlaceholderText("Значение по умолчанию")
        e_def.setFixedWidth(120)

        btn_del = QPushButton("x")
        btn_del.setObjectName("btn_delete")
        btn_del.setFixedWidth(50)
        btn_del.setFixedHeight(26)

        h_layout.addWidget(QLabel("Параметр:"))
        h_layout.addWidget(e_label, stretch=2)
        h_layout.addWidget(QLabel("Дефолт:"))
        h_layout.addWidget(e_def)
        h_layout.addWidget(btn_del)

        container = QWidget()
        container.setLayout(h_layout)
        self.static_widgets.append((container, key_storage, e_label, e_def))

        def remove_row():
            container.setParent(None)
            self.static_widgets.remove((container, key_storage, e_label, e_def))

        btn_del.clicked.connect(remove_row)
        self.layout_static.insertWidget(self.layout_static.count() - 1, container)

    def add_trend_row(self, key, label, color, role="control", plc_tag=""):
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(6)

        e_label = QLineEdit(label)
        e_label.setPlaceholderText("Название показателя")

        internal_key = key or generate_key_from_label(label)
        key_storage = {'key': internal_key}
        e_label.textChanged.connect(lambda text: key_storage.update({'key': generate_key_from_label(text)}))

        # Интерактивная плашка выбора цвета
        current_color = color if color else "#448AFF"
        btn_color = QPushButton()
        btn_color.setFixedWidth(40)
        btn_color.setFixedHeight(24)
        btn_color.setStyleSheet(f"background-color: {current_color}; border: 1px solid #5C6A7D; border-radius: 2px;")
        color_storage = {'color': current_color}

        def pick_color():
            dlg = QColorDialog(QColor(color_storage['color']), self)
            if dlg.exec_():
                col = dlg.selectedColor()
                hex_str = col.name().upper()
                color_storage['color'] = hex_str
                btn_color.setStyleSheet(f"background-color: {hex_str}; border: 1px solid #5C6A7D; border-radius: 2px;")

        btn_color.clicked.connect(pick_color)

        combo_role = QComboBox()
        combo_role.addItems(["control", "state"])
        combo_role.setCurrentText(role if role in ["control", "state"] else "control")
        combo_role.setFixedWidth(85)
        combo_role.setFixedHeight(26)

        e_tag = QLineEdit(str(plc_tag))
        e_tag.setPlaceholderText("Тег / Регистр")
        e_tag.setFixedWidth(130)

        btn_del = QPushButton("x")
        btn_del.setObjectName("btn_delete")
        btn_del.setFixedWidth(50)
        btn_del.setFixedHeight(26)

        h_layout.addWidget(QLabel("Показатель:"))
        h_layout.addWidget(e_label, stretch=2)
        h_layout.addWidget(QLabel("Цвет:"))
        h_layout.addWidget(btn_color)
        h_layout.addWidget(QLabel("Роль:"))
        h_layout.addWidget(combo_role)
        h_layout.addWidget(QLabel("ПЛК:"))
        h_layout.addWidget(e_tag)
        h_layout.addWidget(btn_del)

        container = QWidget()
        container.setLayout(h_layout)
        self.trend_widgets.append((container, key_storage, e_label, color_storage, combo_role, e_tag))

        def remove_row():
            container.setParent(None)
            self.trend_widgets.remove((container, key_storage, e_label, color_storage, combo_role, e_tag))

        btn_del.clicked.connect(remove_row)
        self.layout_trends.insertWidget(self.layout_trends.count() - 1, container)

    # =========================================================================
    # ПРОВЕРКА СОЕДИНЕНИЙ И СОХРАНЕНИЕ
    # =========================================================================
    def test_sql_connection(self):
        try:
            from app.core.data_importer import ExternalDBImporter
            importer = ExternalDBImporter()
            port = int(self.edit_db_port.text().strip() or 5432)
            ok = importer.connect_external(
                db_type=self.combo_db_type.currentText(),
                host=self.edit_db_host.text().strip(),
                port=port,
                user=self.edit_db_user.text().strip(),
                password=self.edit_db_pass.text(),
                db_name=self.edit_db_name.text().strip()
            )
            if ok:
                QMessageBox.information(self, "Успех", "Подключение к внешней производственной базе установлено успешно!")
            else:
                QMessageBox.critical(self, "Ошибка подключения", "Не удалось установить соединение с внешней СУБД.")
        except Exception as e:
            QMessageBox.critical(self, "Исключение", f"Ошибка проверки подключения к БД:\n{e}")

    def test_plc_connection(self):
        protocol = self.combo_plc_protocol.currentText()
        if protocol == "Simulation":
            QMessageBox.information(
                self, "Режим имитации",
                "Выбран режим имитации (Simulation). Внешний сетевой опрос отключен."
            )
            return

        try:
            if protocol == "OPC UA":
                url = self.edit_opc_url.text().strip()
                parsed = urlparse(url)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or 4840
            else:
                host = self.edit_mb_host.text().strip()
                port = int(self.edit_mb_port.text().strip() or 502)

            with socket.create_connection((host, port), timeout=2.5):
                pass
            QMessageBox.information(self, "Узел доступен", f"TCP-сокет контроллера {host}:{port} открыт и отвечает.")
        except Exception as e:
            QMessageBox.critical(self, "Узел недоступен", f"Не удалось подключиться к {host}:{port}:\n{e}")

    def save_config(self):
        try:
            # 1. Валидация и ограничение названий участков/аппаратов
            raw_units = [u.strip() for u in self.edit_units.text().split(',') if u.strip()]
            if not raw_units:
                raise ValueError("Необходимо указать хотя бы один участок/аппарат!")

            if len(raw_units) > 8:
                raise ValueError("Максимальное количество участков — не более 8 (для сохранения читаемости HMI).")

            units = []
            for unit in raw_units:
                if len(unit) > 22:
                    raise ValueError(f"Название участка «{unit}» слишком длинное ({len(unit)} симв.)! Лимит — 22 символа.")
                units.append(unit)

            # 2. Сбор статических параметров сырья (ключ хранится в k_store)
            static_params = []
            for _, k_store, l, d in self.static_widgets:
                label_val = l.text().strip()
                if not label_val:
                    continue
                static_params.append({
                    'key': k_store['key'] or generate_key_from_label(label_val),
                    'label': label_val,
                    'default': float(d.text().replace(',', '.') or 0.0)
                })

            # 3. Сбор трендов датчиков (ключ из k_store, цвет из col_store, роль control/state, тег ПЛК)
            trend_params = []
            for _, k_store, l, col_store, r, tag in self.trend_widgets:
                label_val = l.text().strip()
                if not label_val:
                    continue
                trend_params.append({
                    'key': k_store['key'] or generate_key_from_label(label_val),
                    'label': label_val,
                    'color': col_store['color'],
                    'role': r.currentText(),
                    'plc_tag': tag.text().strip()
                })

            # 4. Запись параметров интерфейса (HMI)
            config.hmi.units = units
            config.hmi.passport_fields['main_metric_label'] = self.edit_main_label.text().strip()
            config.hmi.target_parameter['label'] = self.edit_target_label.text().strip()
            config.hmi.static_parameters = static_params
            config.hmi.trend_parameters = trend_params

            # 5. Запись сетевых настроек СУБД
            config.db.db_type = self.combo_db_type.currentText()
            config.db.host = self.edit_db_host.text().strip()
            config.db.port = int(self.edit_db_port.text().strip() or 5432)
            config.db.database = self.edit_db_name.text().strip()
            config.db.username = self.edit_db_user.text().strip()
            config.db.password = self.edit_db_pass.text()

            # 6. Запись параметров опроса ПЛК
            config.plc.protocol = self.combo_plc_protocol.currentText()
            config.plc.polling_interval_ms = int(self.edit_poll_interval.text().strip() or 1000)
            config.plc.modbus_host = self.edit_mb_host.text().strip()
            config.plc.modbus_port = int(self.edit_mb_port.text().strip() or 502)
            config.plc.modbus_unit_id = int(self.edit_mb_unit.text().strip() or 1)
            config.plc.opc_url = self.edit_opc_url.text().strip()
            config.plc.opc_user = self.edit_opc_user.text().strip()
            config.plc.opc_password = self.edit_opc_pass.text()

            # Сохранение конфигурации в файл
            config.save_to_file()

            QMessageBox.information(
                self, "Успех",
                "Конфигурация технологического процесса успешно сохранена!\n"
                "Если изменялся состав участков или параметров, перезапустите приложение."
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))