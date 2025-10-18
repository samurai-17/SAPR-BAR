# draw_area.py
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
from PyQt5.QtCore import Qt


def safe_float(text, default=None):
    try:
        if text is None:
            return default
        s = str(text).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


class DrawArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.structure_data = None

    def redraw_structure(self):
        """Считывает таблицы и подготавливает данные для отрисовки"""
        w = self.parent_window
        bars = []
        for row in range(w.table_1.table.rowCount()):
            L = safe_float(w.table_1.table.item(row, 0).text() if w.table_1.table.item(row, 0) else "", None)
            A = safe_float(w.table_1.table.item(row, 1).text() if w.table_1.table.item(row, 1) else "", None)
            if L is None or A is None:
                continue
            bars.append((L, A))

        distributed = []
        for row in range(w.table_2.table.rowCount()):
            bar_num = safe_float(w.table_2.table.item(row, 0).text() if w.table_2.table.item(row, 0) else "", None)
            q = safe_float(w.table_2.table.item(row, 1).text() if w.table_2.table.item(row, 1) else "", None)
            if bar_num is None or q is None:
                continue
            distributed.append((int(bar_num), q))

        concentrated = []
        for row in range(w.table_3.table.rowCount()):
            node = safe_float(w.table_3.table.item(row, 0).text() if w.table_3.table.item(row, 0) else "", None)
            F = safe_float(w.table_3.table.item(row, 1).text() if w.table_3.table.item(row, 1) else "", None)
            if node is None or F is None:
                continue
            concentrated.append((int(node), F))

        if not bars:
            self.structure_data = None
        else:
            self.structure_data = {
                "bars": bars,
                "distributed": distributed,
                "concentrated": concentrated
            }
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.fillRect(self.rect(), QColor(255, 255, 255))

        data = self.structure_data
        if not data:
            qp.setPen(Qt.black)
            qp.drawText(10, 20, "Нажмите «Отрисовать конструкцию»")
            return

        bars = data["bars"]
        distributed = data["distributed"]
        concentrated = data["concentrated"]

        # размеры пространства для рисования
        left_margin = 20
        right_margin = 20
        top_margin = 30
        bottom_margin = 30
        avail_w = max(50, self.width() - left_margin - right_margin)
        avail_h = max(50, self.height() - top_margin - bottom_margin)

        # масштабирование длины и высоты
        total_L = sum(L for L, _ in bars)
        if total_L <= 0:
            qp.drawText(10, 20, "Нулевые длины стержней")
            return
        scale_x = (avail_w / total_L) * 0.85
        max_A = max(A for _, A in bars)
        max_draw_h = avail_h * 0.3
        scale_y = (max_draw_h / max_A) if max_A > 0 else 1.0

        x = left_margin
        center_y = top_margin + avail_h / 2
        node_positions = [x]

        # рисуем стержни
        for (L, A) in bars:
            rect_w = L * scale_x
            rect_h = max(4, A * scale_y)
            rect_top = center_y - rect_h / 2
            qp.setPen(QPen(Qt.black, 1))
            qp.setBrush(QBrush(Qt.white))
            qp.drawRect(int(x), int(rect_top), int(rect_w), int(rect_h))
            x += rect_w
            node_positions.append(x)

        # распределённые нагрузки — горизонтальные зелёные стрелки вдоль стержня
        for bar_num, q in distributed:
            if bar_num < 1 or bar_num > len(bars):
                continue

            x1 = node_positions[bar_num - 1]
            x2 = node_positions[bar_num]
            rect_mid_y = center_y
            span = x2 - x1
            direction = 1 if q >= 0 else -1
            n = max(8, int(span // 15))
            step = span / (n - 1) if n > 1 else span
            offset = 0.5 * step

            pen_load = QPen(QColor(0, 150, 0), 2)
            brush_load = QBrush(QColor(0, 150, 0))
            qp.setPen(pen_load)
            qp.setBrush(brush_load)

            for i in range(n):
                px = x1 + i * step
                if direction > 0 and px + offset > x2:
                    continue
                if direction < 0 and px - offset < x1:
                    continue
                self._draw_horizontal_arrow(qp, px, rect_mid_y, q, size=14)

            # подпись нагрузки
            qp.setPen(Qt.black)
            qp.drawText(int((x1 + x2) / 2) - 15, int(rect_mid_y - 10), f"q={q}")

        # сосредоточенные нагрузки — горизонтальные красные стрелки из узлов
        for node, F in concentrated:
            if node < 1 or node > len(node_positions):
                continue

            px = node_positions[node - 1]
            py = center_y
            pen_force = QPen(QColor(200, 0, 0), 2)
            brush_force = QBrush(QColor(200, 0, 0))
            qp.setPen(pen_force)
            qp.setBrush(brush_force)

            self._draw_horizontal_arrow(qp, px, py, F, size=25)

            qp.setPen(Qt.black)
            qp.drawText(int(px), int(py - 15), f"F={F}")

    def _draw_horizontal_arrow(self, qp, x, y, value, size=20):
        """Горизонтальная стрелка (вправо если >0, влево если <0)"""
        direction = 1 if value >= 0 else -1
        line_x1 = x
        line_x2 = x + direction * size

        qp.drawLine(int(line_x1), int(y), int(line_x2), int(y))

        if direction >= 0:
            qp.drawLine(int(line_x2), int(y), int(line_x2 - 6), int(y - 4))
            qp.drawLine(int(line_x2), int(y), int(line_x2 - 6), int(y + 4))
        else:
            qp.drawLine(int(line_x2), int(y), int(line_x2 + 6), int(y - 4))
            qp.drawLine(int(line_x2), int(y), int(line_x2 + 6), int(y + 4))
