import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QFont

import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QFont


class SulfatizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.unit_label = ""
        self.setMinimumSize(550, 500)
        self.angle = 0
        self.is_animating = False
        self.current_lte = 0.0
        self.target_lte = 0.0

        self.data = {
            "G": "0.0", "Ip": "0", "Tr": "0.0",
            "Tg": "0.0", "Lte": "0", "Ltr": "0"
        }

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

    def _update_frame(self):
        self.angle = (self.angle + 5) % 360
        diff = self.target_lte - self.current_lte
        if abs(diff) > 0.1:
            self.current_lte += diff * 0.1
        else:
            self.current_lte = self.target_lte

        self.update()

    def set_params(self, g, ip, tr, tg, lte, ltr):
        # Преобразуем входящее значение в float для анимации
        try:
            self.target_lte = float(lte)
        except:
            self.target_lte = 0.0

        self.data = {
            "G": str(g), "Ip": str(ip), "Tr": str(tr),
            "Tg": str(tg), "Lte": str(lte), "Ltr": str(ltr)
        }

        # Если анимация не запущена, обновляем позицию мгновенно
        if not self.is_animating:
            self.current_lte = self.target_lte

        self.update()

    def start_animation(self):
        self.is_animating = True
        self.timer.start(50)

    def stop_animation(self):
        self.is_animating = False
        self.timer.stop()
        self.update()

    def draw_indicator(self, painter, x, y, label, value, unit):
        # 1. Форматирование числа (0.00 с принудительной точкой)
        try:
            val_float = float(value)
            # Форматируем через f-строку
            display_text = f"{val_float:.2f}"
        except:
            display_text = str(value)

        # 2. Геометрия
        label_w = 45
        rect_w = 80
        rect_h = 25
        val_rect = QRectF(x + label_w, y, rect_w, rect_h)

        painter.setRenderHint(QPainter.Antialiasing)

        # 3. Наименование (Графитовый серый)
        painter.setPen(QColor(0, 0, 0)) #(64, 64, 64))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(QRectF(x, y, label_w - 5, rect_h), Qt.AlignRight | Qt.AlignVCenter, label)

        # 4. Рамка значения
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.setBrush(QBrush(Qt.white))
        painter.drawRoundedRect(val_rect, 3, 3)

        # 5. Текст значения
        painter.setPen(Qt.black)
        painter.setFont(QFont("Verdana", 10))
        text_padding = 6
        inner_rect = val_rect.adjusted(0, 0, -text_padding, 0)
        painter.drawText(inner_rect, Qt.AlignRight | Qt.AlignVCenter, display_text)

        # 6. Единицы измерения
        painter.setPen(QColor(0, 0, 0)) #(80, 80, 80))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(int(x + label_w + rect_w + 5), int(y + rect_h / 2 + 5), unit)

        return val_rect

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2

        tw, th = 240, 260
        tx = cx - tw / 2
        ty = cy - th / 2 + 30

        # 1. Отрисовка раствора
        water_y = ty + 100
        painter.setBrush(QBrush(QColor(110, 90, 70, 220)))
        painter.setPen(Qt.NoPen)
        painter.drawRect(int(tx + 3), int(water_y), int(tw - 6), int(ty + th - water_y - 3))

        # 2. КОРПУС РЕАКТОРА (Оставляем толстым - 4px)
        painter.setPen(QPen(Qt.black, 4))
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(int(tx), int(ty), int(tx), int(ty + th))
        painter.drawLine(int(tx), int(ty + th), int(tx + tw), int(ty + th))
        painter.drawLine(int(tx + tw), int(ty + th), int(tx + tw), int(ty))

        self.draw_indicator(painter, tx - 190, ty + 60, "Iп:", self.data["Ip"], "А")
        self.draw_indicator(painter, tx + tw + 15, ty - 20, "Тг:", self.data["Tg"], "°C")
        self.draw_indicator(painter, tx + tw + 15, ty + 100, "H э:", self.data["Lte"], "мм")
        self.draw_indicator(painter, tx + tw + 15, ty + 180, "H м:", self.data["Ltr"], "мм")
        self.draw_indicator(painter, cx - 85, ty + th - 35, "Тр:", self.data["Tr"], "°C")

        # 4. Электроды
        electrode_width = 15
        visual_multiplier = 2.0
        total_h = 80 + (self.current_lte * visual_multiplier)
        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(QBrush(QColor(45, 45, 45)))
        painter.drawRect(int(cx - 70), int(ty - 10), electrode_width, int(total_h))
        painter.drawRect(int(cx + 70 - electrode_width), int(ty - 10), electrode_width, int(total_h))

        # 5. МЕШАЛКА С ЭФФЕКТАМИ ОБЪЕМА
        mixer_y = ty + th - 75

        # вал
        painter.setPen(QPen(Qt.black, 4))
        painter.drawLine(int(cx), int(ty - 10), int(cx), int(mixer_y))

        # Расчет параметров
        rad = math.radians(self.angle)
        cos_val = math.cos(rad)
        sin_val = math.sin(rad)

        max_w = 25
        current_w = max_w * cos_val

        # Базовый тон (графитовый)
        base_grey = 50

        # Рассчитываем динамическую яркость.
        # Когда sin_val = 1 (лопасть максимально впереди), она самая светлая.
        # Когда sin_val = -1 (лопасть за валом), она самая темная.
        def get_dynamic_color(s_val, is_left=False):
            # Для левой лопасти инвертируем синус, так как она в противофазе
            val = -s_val if is_left else s_val
            brightness_mod = int(val * 40)  # Амплитуда изменения цвета (+-40)
            c = max(0, min(255, base_grey + brightness_mod))
            return QColor(c, c, c, 220)

        painter.setPen(QPen(Qt.black, 1.5))

        # Рисуем лопасти. Чтобы одна перекрывала другую правильно,
        # сначала рисуем ту, что "дальше" (sin < 0), потом ту, что "ближе".

        parts = [
            {'w': current_w, 'is_left': False, 'sin': sin_val},  # Правая
            {'w': -current_w, 'is_left': True, 'sin': -sin_val}  # Левая
        ]

        # Сортируем по значению синуса (сначала задние, потом передние)
        parts.sort(key=lambda p: p['sin'])

        for part in parts:
            painter.setBrush(QBrush(get_dynamic_color(sin_val, part['is_left'])))
            painter.drawEllipse(QPointF(cx + part['w'], mixer_y), abs(part['w']), 8)

        # 6. ВЕРХНЯЯ ТРАПЕЦИЯ И ГАЗООТВОД (Тонкие линии - 1.5px)
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(QBrush(QColor(240, 240, 240)))  # Цвет чуть светлее
        trap = QPolygonF([QPointF(cx - 50, ty - 40), QPointF(cx + 50, ty - 40),
                          QPointF(cx + 75, ty - 10), QPointF(cx - 75, ty - 10)])
        painter.drawPolygon(trap)

        # Тонкие линии газоотвода/кабелей сверху
        painter.setPen(QPen(Qt.black, 1.5))
        # Линия 1
        painter.drawLine(int(cx - 20), int(ty - 40), int(cx - 20), int(ty - 70))
        painter.drawLine(int(cx - 20), int(ty - 70), int(cx + 150), int(ty - 70))
        # Линия 2
        painter.drawLine(int(cx + 15), int(ty - 40), int(cx + 15), int(ty - 55))
        painter.drawLine(int(cx + 15), int(ty - 55), int(cx + 150), int(ty - 55))

        # Подпись внизу
        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(QRectF(cx - 50, ty + th + 15, 100, 30), Qt.AlignCenter, self.unit_label)