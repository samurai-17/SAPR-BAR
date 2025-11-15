from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem


def get_fixation_state(w):
    """Безопасно получает состояние заделок"""
    left_fixed = False
    right_fixed = False

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
            Upr = w.table_1.table.item(row, 2)
            Napr = w.table_1.table.item(row, 3)
            if not L_item or not A_item or not Upr or not Napr:
                QMessageBox.warning(w, "Ошибка", f"Пустое значение в строке {row + 1} таблицы 'Стержни'")
                return False
            try:
                L = float(L_item.text())
                A = float(A_item.text())
                Upr_1 = float(Upr.text())
                Napr_1 = float(Napr.text())
                if L <= 0 or A <= 0:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"Длина и площадь поперечного сечения должны быть > 0 (строка {row + 1})"
                    )
                    return False

                if Upr_1 <= 0 or Napr_1 <= 0:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"Модуль упругости и напряжение должны быть > 0 (строка {row + 1})"
                    )
                    return False

            except ValueError:
                QMessageBox.warning(w, "Ошибка", f"Некорректное число в таблице 'Стержни' (строка {row + 1})")
                return False

        # Проверяем распределенные нагрузки
        used_bars_raspr = set()
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
                        f"В таблице 'Распределенные нагрузки' не указан стержень, "
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
            if bar_num in used_bars_raspr:
                QMessageBox.warning(
                    w, "Ошибка",
                    f"На стержень №{bar_num} задано несколько распределённых нагрузок.\n"
                    f"Допускается только одна нагрузка на стержень."
                )
                return False
            used_bars_raspr.add(bar_num)

        # Проверяем сосредоточенные нагрузки
        n_nodes = n_bars + 1
        used_nodes = set()  # 🔹 Для проверки дубликатов

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

            # 🔹 Проверка на дублирующиеся узлы
            if node_num in used_nodes:
                QMessageBox.warning(
                    w, "Ошибка",
                    f"Узел №{node_num} встречается несколько раз в таблице 'Сосредоточенные нагрузки'.\n"
                    f"Допускается только одна нагрузка на узел."
                )
                return False
            used_nodes.add(node_num)

            F_val = 0.0
            if F_item and F_item.text().strip() != "":
                try:
                    F_val = float(F_item.text())
                except ValueError:
                    QMessageBox.warning(w, "Ошибка", f"Некорректное значение F (строка {row + 1}).")
                    return False

            left_fixed = getattr(w, "left_fixed", False)
            right_fixed = getattr(w, "right_fixed", False)

            if not any([left_fixed, right_fixed]):
                QMessageBox.warning(
                    w,
                    "Ошибка",
                    f"Должна быть как минимум одна заделка"
                )
                return False

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

        left_fixed = bool(data.get("left_fixed", False))
        right_fixed = bool(data.get("right_fixed", False))

        # Проверяем таблицу 'Стержни'
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

        # Проверяем распределённые нагрузки
        used_bars_raspr = set()
        for row_index, row in enumerate(raspr):
            try:
                bar_num = int(row.get("bar_number_raspr", 0))
                if bar_num < 1 or bar_num > n_bars:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"Неверный номер стержня ({bar_num}) в распределённых нагрузках"
                    )
                    return False
                if bar_num in used_bars_raspr:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"В файле несколько распределённых нагрузок на стержень №{bar_num}.\n"
                        f"Допускается только одна нагрузка на стержень."
                    )
                    return False
                used_bars_raspr.add(bar_num)
            except ValueError:
                QMessageBox.warning(w, "Ошибка", f"Некорректные данные в распределённых нагрузках (строка {row_index + 1})")
                return False
# Проверяем сосредоточенные нагрузки
        used_nodes = set()  # 🔹 Проверка на дубликаты
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

                # 🔹 Проверка на дубликаты узлов
                if node_num in used_nodes:
                    QMessageBox.warning(
                        w, "Ошибка",
                        f"В файле указано несколько нагрузок на один узел (№{node_num}).\n"
                        f"Допускается только одна нагрузка на каждый узел."
                    )
                    return False
                used_nodes.add(node_num)

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