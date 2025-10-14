import json
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QTableWidget, QHeaderView, QFileDialog, QMessageBox, QTableWidgetItem
)
from tables_delegate import TablesDelegate


class Table(QTableWidget):
    def __init__(self, parent_window, title, col_c, row_c, hor_lab, ver_lab):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.create_table(title, col_c, row_c, hor_lab, ver_lab)

    def create_table(self, title, col_c, row_c, hor_lab, ver_lab):
        self.setRowCount(row_c)
        self.setColumnCount(col_c)
        self.setHorizontalHeaderLabels(hor_lab)
        self.setVerticalHeaderLabels(ver_lab)
        header_h = self.horizontalHeader()
        header_h.setSectionResizeMode(QHeaderView.Stretch)
        # header_v = self.verticalHeader()
        # header_v.setSectionResizeMode(QHeaderView.Stretch)

        if title == "Стержни":
            self.setItemDelegate(TablesDelegate(self, is_int=False, is_positive=True))
        elif title == "Распределенные нагрузки":
            self.setItemDelegateForColumn(0, TablesDelegate(self, is_int=True, is_positive=True))
            self.setItemDelegateForColumn(1, TablesDelegate(self, is_int=False, is_positive=True))
        else:
            self.setItemDelegateForColumn(0, TablesDelegate(self, is_int=True, is_positive=True))
            self.setItemDelegateForColumn(1, TablesDelegate(self, is_int=False, is_positive=True))

    def add_row(self):
        cur_row = self.currentRow()
        if cur_row == -1:
            self.insertRow(self.rowCount())
        else:
            self.insertRow(cur_row + 1)
        self.clearSelection()
        self.setCurrentCell(-1, -1)

    def del_row(self):
        cur_row = self.currentRow()
        if self.rowCount() > 0:
            if cur_row == -1:
                self.removeRow(self.rowCount() - 1)
            else:
                self.removeRow(cur_row)
        self.clearSelection()
        self.setCurrentCell(-1, -1)

    def table_to_dicts(self, keys):
        """
        Преобразует таблицу в список словарей по заданным ключам.
        Поддерживает случаи, когда keys содержит дополнительные "авто"-ключи
        (например "bar_number"), которые не соответствуют колонкам таблицы.
        """
        auto_keys = {"bar_number"}  # ключи, для которых ставим номер строки
        data = []

        # Определяем, на сколько ключей больше, чем фактических столбцов (смещение)
        offset = len(keys) - self.columnCount()
        if offset < 0:
            offset = 0  # если ключей меньше, чем столбцов, не делаем отрицательное смещение

        for row in range(self.rowCount()):
            row_dict = {}
            for col_index, key in enumerate(keys):
                # Если ключ — авто-ключ, подставляем номер строки
                if key in auto_keys:
                    row_dict[key] = str(row + 1)
                    continue

                # Для остальных ключей вычисляем соответствующий индекс столбца в таблице
                data_col = col_index - offset

                # Если data_col выходит за границы таблицы, записываем пустую строку
                if data_col < 0 or data_col >= self.columnCount():
                    row_dict[key] = ""
                else:
                    item = self.item(row, data_col)
                    row_dict[key] = item.text() if item else ""

            data.append(row_dict)

        return data

    def is_table_filled(self):
        """Проверяет, что все ячейки таблицы заполнены"""
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item is None or item.text().strip() == "":
                    return False
        return True

    def save_all_tables(self):
        """Сохраняет все таблицы в один JSON (метод внутри Table)"""
        w = self.parent_window

        # Проверка заполнения
        if not w.table_1.table.is_table_filled():
            QMessageBox.warning(self, "Ошибка", "Таблица 'Стержни' заполнена не полностью!")
            return
        if not w.table_2.table.is_table_filled():
            QMessageBox.warning(self, "Ошибка", "Таблица 'Распределенные нагрузки' заполнена не полностью!")
            return
        if not w.table_3.table.is_table_filled():
            QMessageBox.warning(self, "Ошибка", "Таблица 'Сосредоточенные нагрузки' заполнена не полностью!")
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Сохранить все таблицы", "", "JSON Files (*.json)", options=options
        )
        if not file_name:
            return

        sterzhni_values = w.table_1.table.table_to_dicts(
            ["bar_number", "bar_length", "bar_cross_section", "bar_modulus_elasticity", "bar_tension"]
        )
        raspr_values = w.table_2.table.table_to_dicts(["bar_number_raspr", "q_value"])
        sosred_values = w.table_3.table.table_to_dicts(["node_number", "f_value"])

        all_data = {
            "Tables": [
                {
                    "table": "Стержни",
                    "values": sterzhni_values,
                    "table_raspr": "Распределенные нагрузки",
                    "values_raspr": raspr_values,
                    "table_sosred": "Сосредоточенные нагрузки",
                    "value_sosred": sosred_values
                }
            ]
        }

        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)

        QMessageBox.information(self, "Сохранение", f"✅ Таблицы сохранены в:\n{file_name}")

    def load_all_tables(self):
        """Загружает таблицы из JSON (в соответствии с новой структурой)"""
        w = self.parent_window
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть JSON файл", "", "JSON Files (*.json)", options=options
        )
        if not file_name:
            return

        try:
            with open(file_name, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить JSON:\n{e}")
            return

        try:
            table_data = data["Tables"][0]

            # Стержни
            sterzhni_values = table_data.get("values", [])
            self.fill_table_from_dicts(
                w.table_1.table, sterzhni_values, skip_auto_keys={"bar_number"})

            # Распределённые
            raspr_values = table_data.get("values_raspr", [])
            self.fill_table_from_dicts(
                w.table_2.table, raspr_values)

            # Сосредоточенные
            sosred_values = table_data.get("value_sosred", [])
            self.fill_table_from_dicts(
                w.table_3.table, sosred_values)

            QMessageBox.information(self, "Загрузка", f" Таблицы успешно загружены из:\n{file_name}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при разборе JSON:\n{e}")

    def fill_table_from_dicts(self, table, values_list, skip_auto_keys=None):
        """Заполняет таблицу из списка словарей"""
        if skip_auto_keys is None:
            skip_auto_keys = set()

        if not values_list:
            return

        # Подгоняем размер
        table.setRowCount(len(values_list))
        expected_cols = len(values_list[0]) - len(skip_auto_keys)
        table.setColumnCount(expected_cols)

        for row, row_data in enumerate(values_list):
            col = 0
            for key, value in row_data.items():
                if key in skip_auto_keys:
                    continue
                table.setItem(row, col, QTableWidgetItem(str(value)))
                col += 1

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.del_row()
        elif event.key() == Qt.Key_Insert:
            self.add_row()
        else:
            super().keyPressEvent(event)
