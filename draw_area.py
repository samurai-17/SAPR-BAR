from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
from PyQt5.QtCore import Qt
import math
from validators import validate_data_on_save  # импортируем валидацию


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
        self.zoom_factor = 1.0  # масштаб
        self.zoom_center = None  # центр для зума
        self.pan_offset = [0.0, 0.0]  # смещение холста (для плавного центрирования)
        self.last_mouse_pos = None
        self.is_panning = False

    def mousePressEvent(self, event):
        """Начало панорамирования средней кнопкой мыши"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Перемещение сцены при зажатой средней кнопке"""
        if self.is_panning and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.pan_offset[0] += delta.x()
            self.pan_offset[1] += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Завершение панорамирования"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Сброс масштаба и смещения"""
        self.zoom_factor = 1.0
        self.pan_offset = [0.0, 0.0]
        self.update()

    def wheelEvent(self, event):
        """Масштабирование с фокусом на позиции курсора"""
        # Получаем позицию курсора в координатах виджета
        cursor_pos = event.position()
        delta = event.angleDelta().y()

        # Шаг изменения масштаба
        zoom_step = 0.1
        factor = 1 + zoom_step if delta > 0 else 1 - zoom_step
        new_zoom = self.zoom_factor * factor

        # Ограничения, чтобы не "улетать"
        if not (0.2 <= new_zoom <= 5.0):
            return

        # Переводим позицию курсора в координаты до масштабирования
        old_x = (cursor_pos.x() - self.pan_offset[0]) / self.zoom_factor
        old_y = (cursor_pos.y() - self.pan_offset[1]) / self.zoom_factor

        # Обновляем масштаб
        self.zoom_factor = new_zoom

        # После изменения масштаба пересчитаем сдвиг так,
        # чтобы курсор оставался на том же месте сцены
        new_x = old_x * self.zoom_factor + self.pan_offset[0]
        new_y = old_y * self.zoom_factor + self.pan_offset[1]
        dx = cursor_pos.x() - new_x
        dy = cursor_pos.y() - new_y

        self.pan_offset[0] += dx
        self.pan_offset[1] += dy

        self.update()


    def redraw_structure(self):
        """Считывает таблицы, валидирует и подготавливает данные для отрисовки"""
        w = self.parent_window

        # --- ВАЛИДАЦИЯ ---
        if not validate_data_on_save(w):
            QMessageBox.warning(self, "Ошибка", "Исправьте ошибки в таблицах перед построением конструкции.")
            self.structure_data = None
            self.update()
            return
        elif not w.table_1.table.is_table_filled():
            QMessageBox.warning(self, "Ошибка", "Таблица 'Стержни' заполнена не полностью!")
            return

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
        used_nodes = set()

        for row in range(w.table_3.table.rowCount()):
            node_item = w.table_3.table.item(row, 0)
            F_item = w.table_3.table.item(row, 1)
            node = safe_float(node_item.text() if node_item else "", None)
            F = safe_float(F_item.text() if F_item else "", None)

            if node is None or F is None:
                continue

            node_int = int(node)

            if node_int in used_nodes:
                QMessageBox.warning(
                    self, "Ошибка",
                    f"В таблице сосредоточенных нагрузок узел №{node_int} указан несколько раз.\n"
                    f"Допускается только одна нагрузка на узел."
                )
                return False

            used_nodes.add(node_int)
            concentrated.append((node_int, F))

        if not bars:
            QMessageBox.warning(self, "Ошибка", "Не заданы стержни для построения.")
            self.structure_data = None
        else:
            self.structure_data = {
                "bars": bars,
                "distributed": distributed,
                "concentrated": concentrated,
                "left_fixed": getattr(w, "left_fixed", False),
                "right_fixed": getattr(w, "right_fixed", False),
            }

        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.fillRect(self.rect(), QColor(255, 255, 255))
        qp.translate(self.pan_offset[0], self.pan_offset[1])
        qp.scale(self.zoom_factor, self.zoom_factor)

        data = self.structure_data
        if not data:
            qp.setPen(Qt.black)
            qp.drawText(10, 20, "Нажмите «Отрисовать конструкцию»")
            return

        bars = data["bars"]
        distributed = data["distributed"]
        concentrated = data["concentrated"]

        left_fixed = data.get("left_fixed", True)
        right_fixed = data.get("right_fixed", True)

        # размеры пространства для рисования
        left_margin = 60
        right_margin = 60
        top_margin = 30
        bottom_margin = 30
        avail_w = max(50, self.width() - left_margin - right_margin)
        avail_h = max(50, self.height() - top_margin - bottom_margin)

        # --- масштабирование с адаптацией ---
        total_L = sum(L for L, _ in bars)
        if total_L <= 0:
            qp.drawText(10, 20, "Нулевые длины стержней")
            return

        # параметры для масштабирования
        min_draw_w = 62      # минимальная длина стержня (в пикселях)
        min_draw_h = 15       # минимальная высота стержня (в пикселях)
        max_total_w = avail_w * 0.9
        max_total_h = avail_h * 0.3

        L_values = [L for L, _ in bars]
        A_values = [A for _, A in bars]

        L_min = min(L_values)
        L_max = max(L_values)
        A_min = min(A_values)
        A_max = max(A_values)

        # безопасное логарифмическое масштабирование
        def scaled_L_raw(L):
            return math.log10(max(L, 0.0) + 1.0)

        def scaled_A_raw(A):
            return math.log10(max(A, 0.0) + 1.0)

        denom_L = scaled_L_raw(L_max) if L_max > 0 else 1.0
        denom_A = scaled_A_raw(A_max) if A_max > 0 else 1.0

        prelim_widths = []
        prelim_heights = []

        for L in L_values:
            norm = (scaled_L_raw(L) / denom_L) if denom_L > 0 else 0.5
            w = min_draw_w + (max_total_w - len(bars) * min_draw_w) * norm
            prelim_widths.append(w)

        for A in A_values:
            norm = (scaled_A_raw(A) / denom_A) if denom_A > 0 else 0.5
            h = min_draw_h + (max_total_h - min_draw_h) * norm
            prelim_heights.append(h)

        total_prelim_w = sum(prelim_widths)
        max_allowed_w = avail_w * 0.95

        if total_prelim_w > max_allowed_w and total_prelim_w > 0:
            scale_factor = max_allowed_w / total_prelim_w
            scaled_widths = [max(min_draw_w, w * scale_factor) for w in prelim_widths]
            total_after = sum(scaled_widths)
            if total_after > max_allowed_w:
                extra_scale = max_allowed_w / total_after
                scaled_widths = [max(min_draw_w, w * extra_scale) for w in scaled_widths]
        else:
            scaled_widths = [max(min_draw_w, w) for w in prelim_widths]

        rect_widths = scaled_widths
        rect_heights = [max(min_draw_h, h) for h in prelim_heights]

        # --- отрисовка стержней ---
        x = left_margin
        center_y = top_margin + avail_h / 2
        node_positions = [x]

        for idx, (L, A) in enumerate(bars):
            rect_w = rect_widths[idx]
            rect_h = rect_heights[idx]
            rect_top = center_y - rect_h / 2
            qp.setPen(QPen(Qt.black, 1))
            qp.setBrush(QBrush(Qt.white))
            qp.drawRect(int(x), int(rect_top), int(rect_w), int(rect_h))
            x += rect_w
            node_positions.append(x)

        # --- ОТРИСОВКА ЗАДЕЛОК ---
        qp.setPen(QPen(Qt.black, 2))
        qp.setBrush(QBrush(QColor(180, 180, 180)))

        if left_fixed:
            self._draw_fixed_support(qp, node_positions[0], center_y, height=avail_h * 0.4, side="left")

        if right_fixed:
            self._draw_fixed_support(qp, node_positions[-1], center_y, height=avail_h * 0.4, side="right")

        # --- РАСПРЕДЕЛЕННЫЕ НАГРУЗКИ ---
        for bar_num, q in distributed:
            if bar_num < 1 or bar_num > len(bars):
                continue

            if q == 0:
                continue

            x1 = node_positions[bar_num - 1]
            x2 = node_positions[bar_num]
            rect_mid_y = center_y
            span = x2 - x1
            direction = 1 if q >= 0 else -1
            n = max(10, int(span // 12))
            step = span / (n - 1) if n > 1 else span
            offset = 0.4 * step

            pen_load = QPen(QColor(0, 150, 0), 2)
            brush_load = QBrush(QColor(0, 150, 0))
            qp.setPen(pen_load)
            qp.setBrush(brush_load)

            for i in range(n):
                px = x1 + i * step
                if direction > 0 and px + offset > x2-2:
                    continue
                if direction < 0 and px - offset < x1+2:
                    continue
                self._draw_horizontal_arrow(qp, px, rect_mid_y, q, size=11)

            qp.setPen(Qt.black)
            qp.drawText(int((x1 + x2) / 2) - 15, int(rect_mid_y - 10), f"q={q}")

        # --- СОСРЕДОТОЧЕННЫЕ НАГРУЗКИ ---
        for node, F in concentrated:
            if node < 1 or node > len(node_positions):
                continue

            if F == 0:
                continue

            px = node_positions[node - 1]
            py = center_y

            pen_force = QPen(QColor(200, 0, 0), 2)
            brush_force = QBrush(QColor(200, 0, 0))
            qp.setPen(pen_force)
            qp.setBrush(brush_force)

            self._draw_horizontal_arrow(qp, px, py, F, size=22)
            qp.setPen(Qt.black)
            qp.drawText(int(px + 5), int(py - 15), f"F={F}")

    # --- СЛУЖЕБНЫЕ МЕТОДЫ ---

    def _draw_horizontal_arrow(self, qp, x, y, value, size=11):
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

    def _draw_fixed_support(self, qp, x, y, height=80, side="left"):
        """Отрисовка заделки (вертикальная штриховка)"""
        half_h = height / 2
        top = y - half_h
        bottom = y + half_h

        if side == "left":
            qp.drawLine(int(x), int(top), int(x), int(bottom))
            step = 6
            for yy in range(int(top), int(bottom), step):
                qp.drawLine(int(x), yy, int(x - 10), yy + step)  # штрихи вниз-влево
        elif side == "right":
            qp.drawLine(int(x), int(top), int(x), int(bottom))
            step = 6
            for yy in range(int(top), int(bottom), step):
                qp.drawLine(int(x), yy, int(x + 10), yy - step)  # штрихи вверх-вправо
