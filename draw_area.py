from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
from PyQt5.QtCore import Qt
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
        # elif not w.table_2.table.is_table_filled():
        #     QMessageBox.warning(self, "Ошибка", "Таблица 'Распределенные нагрузки' заполнена не полностью!")
        #     return
        # elif not w.table_3.table.is_table_filled():
        #     QMessageBox.warning(self, "Ошибка", "Таблица 'Сосредоточенные нагрузки' заполнена не полностью!")
        #     return

        # --- ЧТЕНИЕ ТАБЛИЦ ---
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
        #
        # try:
        #     n_bars = len(bars)
        #     n_nodes = n_bars + 1
        #
        #     # Читаем состояние чекбоксов
        #     left_is_fixed = getattr(w, "chk_left_fixed", None)
        #     left_is_fixed = left_is_fixed.isChecked() if left_is_fixed else getattr(w, "left_fixed", False)
        #
        #     right_is_fixed = getattr(w, "chk_right_fixed", None)
        #     right_is_fixed = right_is_fixed.isChecked() if right_is_fixed else getattr(w, "right_fixed", False)
        #
        #     # Обновляем список сосредоточенных сил
        #     new_conc = []
        #     for node, F in concentrated:
        #         if (left_is_fixed and node == 1 and F != 0) or (right_is_fixed and node == n_nodes and F != 0):
        #             QMessageBox.warning(
        #                 w, "Ошибка",
        #                 f"В узле с заделкой не может быть сосредоточенной силы! Она была заменена на 0"
        #             )
        #             new_conc.append((node, 0.0))
        #         else:
        #             new_conc.append((node, F))
        #     concentrated = new_conc
        #
        #     # Также обновим таблицу, чтобы пользователь видел "0"
        #     from PyQt5.QtWidgets import QTableWidgetItem
        #     table3 = w.table_3.table
        #     for row in range(table3.rowCount()):
        #         item_node = table3.item(row, 0)
        #         if not item_node:
        #             continue
        #         try:
        #             node_num = int(item_node.text())
        #         except Exception:
        #             continue
        #         if (left_is_fixed and node_num == 1) or (right_is_fixed and node_num == n_nodes):
        #             table3.setItem(row, 1, QTableWidgetItem("0"))
        # except Exception as e:
        #     print(f"[DEBUG] Ошибка при проверке заделок: {e}")

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

        # --- ОТРИСОВКА СТЕРЖНЕЙ ---
        for (L, A) in bars:
            rect_w = L * scale_x
            rect_h = max(4, A * scale_y)
            rect_top = center_y - rect_h / 2
            qp.setPen(QPen(Qt.black, 1))
            qp.setBrush(QBrush(Qt.white))
            qp.drawRect(int(x), int(rect_top), int(rect_w), int(rect_h))
            x += rect_w
            node_positions.append(x)

        # --- ОТРИСОВКА ЗАДЕЛОК ---
        qp.setPen(QPen(Qt.black, 2))
        qp.setBrush(QBrush(QColor(180, 180, 180)))

        # Левая заделка
        if left_fixed:
            self._draw_fixed_support(qp, node_positions[0], center_y, height=avail_h * 0.4, side="left")

        # Правая заделка
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

            self._draw_horizontal_arrow(qp, px, py, F, size=28)
            qp.setPen(Qt.black)
            qp.drawText(int(px+5), int(py - 15), f"F={F}")

    # --- СЛУЖЕБНЫЕ МЕТОДЫ ---

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

    def _draw_fixed_support(self, qp, x, y, height=80, side="left"):
        """Отрисовка заделки (вертикальная штриховка)"""
        half_h = height / 2
        top = y - half_h
        bottom = y + half_h

        if side == "left":
            qp.drawLine(int(x), int(top), int(x), int(bottom))
            # диагональная штриховка
            step = 6
            for yy in range(int(top), int(bottom), step):
                qp.drawLine(int(x), yy, int(x - 10), yy + step)
        elif side == "right":
            qp.drawLine(int(x), int(top), int(x), int(bottom))
            step = 6
            for yy in range(int(top), int(bottom), step):
                qp.drawLine(int(x), yy, int(x + 10), yy + step)
