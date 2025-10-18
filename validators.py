from PyQt5.QtWidgets import QMessageBox


def validate_data_on_save(w):
    """Проверяет корректность данных при сохранении"""
    try:
        n_bars = w.table_1.table.rowCount()

        # Проверяем распределенные нагрузки
        for row in range(w.table_2.table.rowCount()):
            item = w.table_2.table.item(row, 0)
            if not item:
                continue
            bar_num = int(item.text())
            if bar_num < 1 or bar_num > n_bars:
                QMessageBox.warning(
                    w,
                    "Ошибка",
                    f"В таблице 'Распределенные нагрузки' указан стержень №{bar_num}, "
                    f"но всего стержней: {n_bars}"
                )
                return False

        # Проверяем сосредоточенные нагрузки
        n_nodes = n_bars + 1
        for row in range(w.table_3.table.rowCount()):
            item = w.table_3.table.item(row, 0)
            if not item:
                continue
            node_num = int(item.text())
            if node_num < 1 or node_num > n_nodes:
                QMessageBox.warning(
                    w,
                    "Ошибка",
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
        for table_name, table_values in [
            ("Стержни", sterzhni),
            ("Распределенные нагрузки", raspr),
            ("Сосредоточенные нагрузки", sosred)
        ]:
            for row in table_values:
                for key, value in row.items():
                    if str(value).strip() == "":
                        QMessageBox.warning(w, "Ошибка", f"Пустое поле в таблице '{table_name}' ({key})")
                        return False
                    try:
                        if float(value) < 0 and key not in {"q_value", "f_value"}:
                            QMessageBox.warning(
                                w, "Ошибка",
                                f"Отрицательное значение в таблице '{table_name}' ({key})"
                            )
                            return False
                    except ValueError:
                        # bar_number или node_number могут быть не float — пропускаем
                        if not key.startswith(("bar_number", "node_number")):
                            QMessageBox.warning(
                                w, "Ошибка",
                                f"Некорректное число в таблице '{table_name}' ({key})"
                            )
                            return False

        # Проверяем диапазоны номеров
        for row in raspr:
            bar_num = int(row["bar_number_raspr"])
            if bar_num < 1 or bar_num > n_bars:
                QMessageBox.warning(
                    w, "Ошибка",
                    f"Неверный номер стержня ({bar_num}) в распределенных нагрузках"
                )
                return False

        for row in sosred:
            node_num = int(row["node_number"])
            if node_num < 1 or node_num > n_nodes:
                QMessageBox.warning(
                    w, "Ошибка",
                    f"Неверный номер узла ({node_num}) в сосредоточенных нагрузках"
                )
                return False

        return True

    except Exception as e:
        QMessageBox.critical(w, "Ошибка", f"Ошибка при проверке JSON: {e}")
        return False
