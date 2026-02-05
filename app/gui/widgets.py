import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QFont


class SulfatizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(550, 500)
        self.angle = 0
        self.is_animating = False

        # Данные по умолчанию
        self.data = {
            "G": "0.0", "Ip": "0", "Tr": "0.0",
            "Tg": "0.0", "Lte": "0", "Ltr": "0"
        }

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

    def _update_frame(self):
        self.angle = (self.angle + 15) % 360
        self.update()

    def set_params(self, g, ip, tr, tg, lte, ltr):
        self.data = {
            "G": str(g), "Ip": str(ip), "Tr": str(tr),
            "Tg": str(tg), "Lte": str(lte), "Ltr": str(ltr)
        }
        self.update()

    def start_animation(self):
        self.is_animating = True
        self.timer.start(50)

    def stop_animation(self):
        self.is_animating = False
        self.timer.stop()
        self.update()

    def draw_indicator(self, painter, x, y, label, value, unit):
        """Рисует информационную плашку в стиле чертежа"""
        rect = QRectF(x, y, 120, 40)
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(Qt.white)
        painter.drawRect(rect)

        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        text = f"{label} {value} {unit}"
        painter.drawText(rect, Qt.AlignCenter, text)
        return rect

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Динамический центр для масштабируемости
        cx = self.width() / 2
        cy = self.height() / 2

        # Параметры основного бака
        tw, th = 240, 260
        tx = cx - tw / 2
        ty = cy - th / 2 + 30  # Сдвиг вниз для места под верхние приборы

        # 1. Отрисовка раствора (кофейный цвет)
        water_y = ty + 100
        painter.setBrush(QBrush(QColor(110, 90, 70, 220)))
        painter.setPen(Qt.NoPen)
        painter.drawRect(int(tx + 3), int(water_y), int(tw - 6), int(ty + th - water_y - 3))

        # 2. Корпус реактора
        painter.setPen(QPen(Qt.black, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(int(tx), int(ty), int(tx), int(ty + th))  # Левая стенка
        painter.drawLine(int(tx), int(ty + th), int(tx + tw), int(ty + th))  # Дно
        painter.drawLine(int(tx + tw), int(ty + th), int(tx + tw), int(ty))  # Правая стенка

        # 3. Индикаторы и Стрелка G
        # G поднята выше
        g_rect = self.draw_indicator(painter, tx - 150, ty - 60, "G,", self.data["G"], "кг")

        # Золотая стрелка от G внутрь бака (как цвет 'G к' на графике)
        arrow_color = QColor('#FFD740')
        painter.setPen(QPen(arrow_color, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        # Траектория стрелки: от правого края G до точки входа в бак
        start_arrow = QPointF(g_rect.right() + 5, g_rect.center().y())
        end_arrow = QPointF(tx + 30, ty + 40)

        # Рисуем Г-образную стрелку
        painter.drawLine(int(start_arrow.x()), int(start_arrow.y()), int(end_arrow.x()), int(start_arrow.y()))
        painter.drawLine(int(end_arrow.x()), int(start_arrow.y()), int(end_arrow.x()), int(end_arrow.y()))
        # Наконечник стрелки
        painter.drawLine(int(end_arrow.x()), int(end_arrow.y()), int(end_arrow.x() - 8), int(end_arrow.y() - 10))
        painter.drawLine(int(end_arrow.x()), int(end_arrow.y()), int(end_arrow.x() + 8), int(end_arrow.y() - 10))

        # Остальные индикаторы
        self.draw_indicator(painter, tx - 150, ty + 60, "I п", self.data["Ip"], "А")
        self.draw_indicator(painter, tx + tw + 30, ty - 20, "Тг", self.data["Tg"], "°C")
        self.draw_indicator(painter, tx + tw + 30, ty + 100, "Lt э", self.data["Lte"], "мм")
        self.draw_indicator(painter, tx + tw + 30, ty + 170, "Lt р", self.data["Ltr"], "мм")
        self.draw_indicator(painter, cx - 60, ty + th - 50, "Т р", self.data["Tr"], "°C")

        # 4. Электроды и Мешалка
        painter.setPen(QPen(Qt.black, 5))
        # Электроды выходят из трапеции
        painter.drawLine(int(cx - 65), int(ty - 10), int(cx - 65), int(ty + 110))
        painter.drawLine(int(cx + 65), int(ty - 10), int(cx + 65), int(ty + 110))

        # Мешалка (горизонтальное вращение)
        painter.setPen(QPen(Qt.black, 2))
        mixer_y = ty + th - 75
        painter.drawLine(int(cx), int(ty - 10), int(cx), int(mixer_y))  # Вал

        blade_w = 40 * math.cos(math.radians(self.angle))
        painter.setBrush(QBrush(QColor(40, 40, 40, 200)))
        painter.drawEllipse(QPointF(cx + blade_w, mixer_y), abs(blade_w), 10)
        painter.drawEllipse(QPointF(cx - blade_w, mixer_y), abs(blade_w), 10)

        # 5. Верхняя Трапеция и Подпись
        painter.setPen(QPen(Qt.black, 3))
        painter.setBrush(QBrush(QColor(220, 220, 220)))  # Серый цвет привода
        trap = QPolygonF([QPointF(cx - 50, ty - 40), QPointF(cx + 50, ty - 40),
                          QPointF(cx + 75, ty - 10), QPointF(cx - 75, ty - 10)])
        painter.drawPolygon(trap)

        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(QRectF(cx - 50, ty + th + 15, 100, 30), Qt.AlignCenter, "СФР-3")