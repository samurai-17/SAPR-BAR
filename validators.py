from PyQt5.QtWidgets import QMessageBox


def validate_data_on_save(w):
    """Проверяет корректность данных при сохранении"""
    try:
        n_bars = w.table_1.table.rowCount()

        # Проверяем стержни
        for row in range(n_bars):
            L_item = w.table_1.table.item(row, 0)
            A_item = w.table_1.table.item(row, 1)
            if not L_item or not A_item:
                QMessageBox.warning(w, "Ошибка", f"Пустое значение в строке {row + 1} таблицы 'Стержни'")
                return False
            try:
                L = float(L_item.text())
                A = float(A_item.text())
                if L <= 0 or A <= 0:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"Длина и площадь поперечного сечения должны быть > 0 (строка {row + 1})"
                    )
                    return False
            except ValueError:
                QMessageBox.warning(w, "Ошибка", f"Некорректное число в таблице 'Стержни' (строка {row + 1})")
                return False

        # Проверяем распределенные нагрузки
        for row in range(w.table_2.table.rowCount()):
            bar_item = w.table_2.table.item(row, 0)
            q_item = w.table_2.table.item(row, 1)
            if not bar_item or not q_item:
                continue
            bar_num = int(bar_item.text())
            if bar_num < 1 or bar_num > n_bars:
                QMessageBox.warning(
                    w, "Ошибка",
                    f"В таблице 'Распределенные нагрузки' указан стержень №{bar_num}, "
                    f"но всего стержней: {n_bars}"
                )
                return False

        # Проверяем сосредоточенные нагрузки
        n_nodes = n_bars + 1
        for row in range(w.table_3.table.rowCount()):
            node_item = w.table_3.table.item(row, 0)
            F_item = w.table_3.table.item(row, 1)
            if not node_item or not F_item:
                continue
            node_num = int(node_item.text())
            if node_num < 1 or node_num > n_nodes:
                QMessageBox.warning(
                    w, "Ошибка",
                    f"В таблице 'Сосредоточенные нагрузки' указан узел №{node_num}, "
                    f"но всего узлов: {n_nodes}"
                )
                return False

        return True

    except Exception as e:
        QMessageBox.critical(w, "Ошибка", f"Ошибка при проверке данных: {e}")
        return False


def validate_data_on_load(w, data):
    """Проверяет корректность данных перед загрузкой из JSON"""
    try:
        t = data["Tables"][0]
        sterzhni = t.get("values", [])
        raspr = t.get("values_raspr", [])
        sosred = t.get("value_sosred", [])

        n_bars = len(sterzhni)
        n_nodes = n_bars + 1

        # Проверяем содержимое таблиц
        for row_index, row in enumerate(sterzhni):
            try:
                L = float(row.get("bar_length", 0))
                A = float(row.get("bar_cross_section", 0))
                if L <= 0 or A <= 0:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"Неверное значение длины или сечения в строке {row_index + 1} таблицы 'Стержни'"
                    )
                    return False
            except ValueError:
                QMessageBox.warning(w, "Ошибка", f"Некорректные данные в 'Стержнях' (строка {row_index + 1})")
                return False

        for row_index, row in enumerate(raspr):
            try:
                bar_num = int(row.get("bar_number_raspr", 0))
                if bar_num < 1 or bar_num > n_bars:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"Неверный номер стержня ({bar_num}) в распределённых нагрузках"
                    )
                    return False

            except ValueError:
                QMessageBox.warning(w, "Ошибка", f"Некорректные данные в распределённых нагрузках (строка {row_index + 1})")
                return False

        for row_index, row in enumerate(sosred):
            try:
                node_num = int(row.get("node_number", 0))
                if node_num < 1 or node_num > n_nodes:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"Неверный номер узла ({node_num}) в сосредоточенных нагрузках"
                    )
                    return False
            except ValueError:
                QMessageBox.warning(w, "Ошибка", f"Некорректные данные в сосредоточенных нагрузках (строка {row_index + 1})")
                return False

        return True

    except Exception as e:
        QMessageBox.critical(w, "Ошибка", f"Ошибка при проверке JSON: {e}")
        return False
