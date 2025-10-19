from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem


def get_fixation_state(w):
    """Безопасно получает состояние заделок"""
    left_fixed = False
    right_fixed = False

    # Если чекбоксы существуют — читаем их
    if hasattr(w, "chk_left_fixed"):
        try:
            left_fixed = bool(w.chk_left_fixed.isChecked())
        except Exception:
            pass
    elif hasattr(w, "left_fixed"):
        left_fixed = bool(getattr(w, "left_fixed", False))

    if hasattr(w, "chk_right_fixed"):
        try:
            right_fixed = bool(w.chk_right_fixed.isChecked())
        except Exception:
            pass
    elif hasattr(w, "right_fixed"):
        right_fixed = bool(getattr(w, "right_fixed", False))

    return left_fixed, right_fixed


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
            if not bar_item or bar_item.text() == '':
                if not q_item or q_item.text() == '':
                    bar_item = QTableWidgetItem("1")
                    w.table_2.table.setItem(row, 0, QTableWidgetItem("1"))
                    w.table_2.table.setItem(row, 1, QTableWidgetItem("0"))
                else:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"Распределенные нагрузки' не указан стержень, "
                        f"но указана сила q"
                    )
                    return False
            else:
                if not q_item or q_item.text() == '':
                    w.table_2.table.setItem(row, 1, QTableWidgetItem("0"))

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
            if not node_item or node_item.text() == '':
                if not F_item or F_item.text() == '':
                    node_item = QTableWidgetItem("1")
                    w.table_3.table.setItem(row, 0, QTableWidgetItem("1"))
                    w.table_3.table.setItem(row, 1, QTableWidgetItem("0"))
                else:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"В таблице 'Сосредоточенные нагрузки' не указан узел, "
                        f"но указана сила F"
                    )
                    return False
            else:
                if not F_item or F_item.text() == '':
                    w.table_3.table.setItem(row, 1, QTableWidgetItem("0"))

            node_num = int(node_item.text())
            if node_num < 1 or node_num > n_nodes:
                QMessageBox.warning(
                    w, "Ошибка",
                    f"В таблице 'Сосредоточенные нагрузки' указан узел №{node_num}, "
                    f"но всего узлов: {n_nodes}"
                )
                return False

            F_val = 0.0
            if F_item and F_item.text().strip() != "":
                try:
                    F_val = float(F_item.text())
                except ValueError:
                    QMessageBox.warning(w, "Ошибка", f"Некорректное значение F (строка {row + 1}).")
                    return False

            left_fixed = getattr(w, "left_fixed", False)
            right_fixed = getattr(w, "right_fixed", False)

            # запрет сохранять ненулевую силу в заделанном узле
            if (left_fixed and node_num == 1 and abs(F_val) > 0.0) or (
                    right_fixed and node_num == n_nodes and abs(F_val) > 0.0):
                side = "левом" if (left_fixed and node_num == 1) else "правом"
                QMessageBox.warning(
                    w,
                    "Ошибка",
                    f"Нельзя задать ненулевую сосредоточенную силу в {side} заделанном узле (узел {node_num})."
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

        # --- читаем флаги заделок из JSON, если они там есть ---
        left_fixed = bool(data.get("left_fixed", False))
        right_fixed = bool(data.get("right_fixed", False))

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
                F_val = float(row.get("f_value", 0))
                if node_num < 1 or node_num > n_nodes:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"Неверный номер узла ({node_num}) в сосредоточенных нагрузках"
                    )
                    return False
            except ValueError:
                QMessageBox.warning(w, "Ошибка", f"Некорректные данные в сосредоточенных нагрузках (строка {row_index + 1})")
                return False



            if (left_fixed and node_num == 1 and abs(F_val) > 0.0) or (
                    right_fixed and node_num == n_nodes and abs(F_val) > 0.0):
                side = "левом" if (left_fixed and node_num == 1) else "правом"
                QMessageBox.warning(w, "Ошибка",
                                    f"Файл содержит ненулевую силу в {side} заделанном узле (узел {node_num}).")
                return False

        return True

    except Exception as e:
        QMessageBox.critical(w, "Ошибка", f"Ошибка при проверке JSON: {e}")
        return False
