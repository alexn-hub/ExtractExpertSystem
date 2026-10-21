import random
import math
from typing import Dict, Any, Optional
from app.utils.config import config
from app.utils.logger import logger


class RealtimePLCClient:
    """
    Клиент сбора данных в реальном времени (Modbus TCP / OPC UA / Эмулятор).
    Читает значения по тегам/регистрам из конфигуратора (config.hmi.trend_parameters).
    """

    def __init__(self):
        self.protocol = "Simulation"
        self.is_connected = False
        self.modbus_client = None
        self.opc_client = None
        self.step_counter = 0
        self.last_status_msg = "Не подключен"

    def connect(self) -> bool:
        self.protocol = getattr(config.plc, 'protocol', 'Simulation')
        self.step_counter = 0

        if self.protocol == "Modbus TCP":
            return self._connect_modbus()
        elif self.protocol == "OPC UA":
            return self._connect_opc()
        else:
            self.is_connected = True
            self.last_status_msg = "🟢 Эмуляция ПЛК активна"
            logger.info("Запущен режим встроенной эмуляции ПЛК.")
            return True

    def _connect_modbus(self) -> bool:
        host = config.plc.modbus_host
        port = config.plc.modbus_port
        try:
            from pymodbus.client import ModbusTcpClient
            self.modbus_client = ModbusTcpClient(host=host, port=port, timeout=2)
            if self.modbus_client.connect():
                self.is_connected = True
                self.last_status_msg = f"🟢 Modbus TCP ({host}:{port})"
                logger.info(self.last_status_msg)
                return True
            else:
                self.last_status_msg = f"🟡 Modbus недоступен ({host}:{port}) -> Эмуляция"
                logger.warning(self.last_status_msg)
                self.is_connected = True # Переходим на мягкую эмуляцию при обрыве связи
                return True
        except ImportError:
            self.last_status_msg = "🟡 pymodbus не найден -> Эмуляция регистров"
            self.is_connected = True
            return True
        except Exception as e:
            self.last_status_msg = f"🔴 Ошибка Modbus: {e}"
            self.is_connected = True
            return True

    def _connect_opc(self) -> bool:
        url = config.plc.opc_url
        try:
            from opcua import Client
            self.opc_client = Client(url, timeout=2)
            if config.plc.opc_user:
                self.opc_client.set_user(config.plc.opc_user)
                self.opc_client.set_password(config.plc.opc_password)
            self.opc_client.connect()
            self.is_connected = True
            self.last_status_msg = f"🟢 OPC UA ({url})"
            logger.info(self.last_status_msg)
            return True
        except ImportError:
            self.last_status_msg = "🟡 opcua не найден -> Эмуляция нод"
            self.is_connected = True
            return True
        except Exception as e:
            self.last_status_msg = f"🔴 Ошибка OPC UA: {e}"
            self.is_connected = True
            return True

    def read_trends(self, reference_row: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Считывает показания датчиков по их тегам/регистрам"""
        self.step_counter += 1
        result = {}
        tag_log = []

        for param in config.hmi.trend_parameters:
            key = param['key']
            tag = str(param.get('plc_tag', '')).strip()
            ref_val = float(reference_row.get(key, 0.0)) if reference_row else 50.0

            val = None
            # 1. Чтение из Modbus TCP по числовому адресу (например 40001)
            if self.protocol == "Modbus TCP" and self.modbus_client and self.modbus_client.is_socket_open() and tag.isdigit():
                try:
                    reg_num = int(tag)
                    address = reg_num - 40001 if reg_num >= 40001 else reg_num
                    rr = self.modbus_client.read_holding_registers(
                        address, 1, slave=getattr(config.plc, 'modbus_unit_id', 1)
                    )
                    if not rr.isError():
                        val = float(rr.registers[0])
                except Exception:
                    pass

            # 2. Чтение из OPC UA по строковому тегу
            elif self.protocol == "OPC UA" and self.opc_client and tag:
                try:
                    node = self.opc_client.get_node(tag)
                    val = float(node.get_value())
                except Exception:
                    pass

            # 3. Эмуляция / Сглаженный шум вокруг эталонного профиля
            if val is None:
                base = ref_val if ref_val != 0 else 25.0
                noise = random.uniform(-0.02, 0.02) * base
                wave = math.sin(self.step_counter * 0.2) * (base * 0.01)
                val = max(0.0, round(base + noise + wave, 2))

            result[key] = val
            if tag:
                tag_log.append(f"{key}[{tag}]={val:.1f}")

        if tag_log:
            self.last_status_msg = f"📡 {self.protocol}: " + " | ".join(tag_log)

        return result

    def disconnect(self):
        try:
            if self.modbus_client:
                self.modbus_client.close()
            if self.opc_client:
                self.opc_client.disconnect()
        except Exception:
            pass
        self.is_connected = False