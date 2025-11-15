from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTabWidget, QTextEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHBoxLayout,
    QPushButton
)
from PyQt5.QtCore import Qt, QTimer
from processor import calculate_reactions
import numpy as np

# >>>>>>>>>>>>> НОВЫЙ КОД ДЛЯ ГРАФИКОВ >>>>>>>>>>>>>>
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
# <<<<<<<<<<<<< НОВЫЙ КОД ДЛЯ ГРАФИКОВ <<<<<<<<<<<<<<


class PostProcessorArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.results = None
        self.structure_data = None

        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # --- 1. Расчётная информация ---
        self.tab_info = QWidget()
        v1 = QVBoxLayout()
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setAlignment(Qt.AlignTop)
        v1.addWidget(self.info_text)
        self.tab_info.setLayout(v1)
        self.tabs.addTab(self.tab_info, "Расчётная информация")

        # --- 2. Таблицы ---
        self.tab_tables = QWidget()
        v2 = QVBoxLayout()

        # 🔹 Выпадающий список выбора стержня
        self.combo_select_bar = QComboBox()
        self.combo_select_bar.addItem("Выполните расчёт в процессоре")
        self.combo_select_bar.currentIndexChanged.connect(
            lambda _: QTimer.singleShot(0, self.update_table_view)
        )
        v2.addWidget(self.combo_select_bar)

        # 🔹 Таблица
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels(["№ стержня", "x (м)", "u(x)", "N(x)", "σ(x)"])
        v2.addWidget(self.table_widget)

        self.tab_tables.setLayout(v2)
        self.tabs.addTab(self.tab_tables, "Таблицы")

        # --- 3. Графики ---
        self.tab_graphs = QWidget()
        v3 = QVBoxLayout()

        self.combo_graph = QComboBox()
        self.combo_graph.addItems(["u(x) — Перемещения", "N(x) — Продольная сила", "σ(x) — Напряжения"])
        self.combo_graph.currentIndexChanged.connect(self.update_graphs)
        v3.addWidget(self.combo_graph)

        self.figure = Figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        v3.addWidget(self.canvas)

        self.tab_graphs.setLayout(v3)
        self.tabs.addTab(self.tab_graphs, "Графики")

        # --- 4. Решение в точке ---
        self.tab_point = QWidget()
        v4 = QVBoxLayout()

        # 🔹 Выбор стержня
        point_bar_layout = QHBoxLayout()
        point_bar_layout.addWidget(QLabel("Стержень:"))
        self.point_bar_combo = QComboBox()
        self.point_bar_combo.addItem("Выберите стержень")
        point_bar_layout.addWidget(self.point_bar_combo)
        v4.addLayout(point_bar_layout)

        # 🔹 Ввод координаты
        point_coord_layout = QHBoxLayout()
        point_coord_layout.addWidget(QLabel("Локальная координата x (м):"))
        self.point_coord_input = QTextEdit()
        self.point_coord_input.setMaximumHeight(30)
        self.point_coord_input.setPlaceholderText("0.0")
        point_coord_layout.addWidget(self.point_coord_input)
        v4.addLayout(point_coord_layout)

        # 🔹 Кнопка расчёта
        self.point_calc_btn = QPushButton("Рассчитать в точке")
        self.point_calc_btn.clicked.connect(self.calculate_at_point)
        v4.addWidget(self.point_calc_btn)

        # 🔹 Результат
        self.point_result_label = QLabel("Выполните расчёт в процессоре")
        self.point_result_label.setWordWrap(True)
        self.point_result_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        v4.addWidget(self.point_result_label)

        v4.addStretch(1)
        self.tab_point.setLayout(v4)
        self.tabs.addTab(self.tab_point, "Решение в точке")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # =======================================================
    # Обновление данных после выполнения расчёта
    # =======================================================
    def set_data(self, structure_data, results):
        self.structure_data = structure_data
        self.results = results
        self.update_info_tab()
        self.update_tables_tab()
        self.update_point_calculation_tab()
        self.update_graphs()   # <<— графики обновляются сразу

    # =======================================================
    # ВКЛАДКА 1 — Расчётная информация
    # =======================================================
    def update_info_tab(self):
        if not self.results:
            self.info_text.setText("Выполните расчёт в процессоре")
            return

        try:
            results = self.results
            U = results.get("U", [])
            table = results.get("table", [])

            text = ["Узловые перемещения:"]
            for i, val in enumerate(U, start=1):
                text.append(f"Δ{i} = {val:.6e} м")

            reactions = calculate_reactions(self.parent_window)
            if reactions:
                text.append("\nРеакции опор:")
                for node, val in reactions.items():
                    text.append(f"R(узел {node}) = {val:.6e} Н")
            else:
                text.append("\nРеакции опор отсутствуют")

            if table:
                maxN = max(table, key=lambda r: abs(r["N"]))
                maxσ = max(table, key=lambda r: abs(r["sigma"]))
                maxu = max(table, key=lambda r: abs(r["u"]))

                text.append("\nЭкстремальные значения:")
                text.append(f"Максимальное N: {maxN['N']:.6e} Н (стержень {maxN['bar']})")
                text.append(f"Максимальное σ: {maxσ['sigma']:.6e} Па (стержень {maxσ['bar']})")
                text.append(f"Макс. перемещение: {maxu['u']:.6e} м (стержень {maxu['bar']})")

            self.info_text.setText("\n".join(text))

        except Exception as e:
            self.info_text.setText(f"Ошибка:\n{e}")

    # =======================================================
    # ВКЛАДКА 2 — Таблицы
    # =======================================================
    def update_tables_tab(self):
        if not self.results or "table" not in self.results:
            self.combo_select_bar.clear()
            self.combo_select_bar.addItem("Выполните расчёт")
            self.table_widget.setRowCount(0)
            return

        bars = sorted(set(r["bar"] for r in self.results["table"]))
        self.combo_select_bar.blockSignals(True)
        self.combo_select_bar.clear()
        self.combo_select_bar.addItem("Сводная таблица")
        for b in bars:
            self.combo_select_bar.addItem(f"Стержень {b}")
        self.combo_select_bar.blockSignals(False)

        QTimer.singleShot(0, self.update_table_view)

    def update_table_view(self):
        """Обновляет отображение таблицы при выборе стержня"""
        if not self.results or "table" not in self.results or not self.structure_data:
            return

        try:
            all_rows = self.results["table"]
            bars = self.structure_data.get("bars", [])
            selected = self.combo_select_bar.currentText()

            if selected.startswith("Стержень"):
                bar_num = int(selected.split()[-1])

                # вычисляем границы выбранного стержня (глобальные x)
                total_x = 0.0
                start_x = 0.0
                end_x = 0.0
                for i, bar_data in enumerate(bars, start=1):
                    try:
                        L = float(bar_data[0])
                    except Exception:
                        L = 0.0
                    if i == bar_num:
                        start_x = total_x
                        end_x = total_x + L
                        break
                    total_x += L

                # выбираем строки из сводной таблицы, принадлежащие этому стержню
                rows = []
                for r in all_rows:
                    try:
                        if int(r.get("bar", 0)) != bar_num:
                            continue
                        xg = float(r.get("x", 0.0))
                    except Exception:
                        continue
                    # убедимся, что точка лежит внутри границ стержня (глобально)
                    if abs(xg - start_x) < 1e-9 or abs(xg - end_x) < 1e-9 or (xg > start_x and xg < end_x):
                        rows.append({
                            "bar": bar_num,
                            "x": float(xg),
                            "u": float(r.get("u", 0.0)),
                            "N": float(r.get("N", 0.0)),
                            "sigma": float(r.get("sigma", 0.0))
                        })

                # интерполируем до минимум 10 точек для таблицы (как раньше), но передаём bar_num
                rows = self._ensure_min_points(rows, min_points=10, bar_num=bar_num)
            else:
                # сводная таблица: показываем всё (не меняем номера)
                rows = all_rows

            self._fill_table(rows)

        except Exception as e:
            print(f"[Ошибка при обновлении таблицы] {e}")

    def _fill_table(self, rows):
        self.table_widget.blockSignals(True)
        self.table_widget.clearContents()
        self.table_widget.setRowCount(0)

        if not rows:
            self.table_widget.blockSignals(False)
            return

        self.table_widget.setRowCount(len(rows))

        for i, r in enumerate(rows):
            self.table_widget.setItem(i, 0, QTableWidgetItem(str(r["bar"])))
            self.table_widget.setItem(i, 1, QTableWidgetItem(f"{r['x']:.5f}"))
            self.table_widget.setItem(i, 2, QTableWidgetItem(f"{r['u']:.6e}"))
            self.table_widget.setItem(i, 3, QTableWidgetItem(f"{r['N']:.6e}"))
            self.table_widget.setItem(i, 4, QTableWidgetItem(f"{r['sigma']:.6e}"))

        self.table_widget.blockSignals(False)

    def _ensure_min_points(self, rows, min_points=10, bar_num=None):
        """Если в таблице меньше min_points строк, интерполирует значения.
        Теперь принимает опционально bar_num — и гарантированно записывает его в каждую строку.
        """
        if rows is None:
            return []
        if len(rows) >= min_points or len(rows) < 2:
            # если табличка уже достаточна или её нельзя интерполировать — всё ок,
            # но всё равно корректируем поле "bar" если он передан
            if bar_num is not None:
                new_rows = []
                for r in rows:
                    new_r = dict(r)
                    new_r["bar"] = bar_num
                    new_rows.append(new_r)
                return new_rows
            return rows

        # сортировать по x
        rows = sorted(rows, key=lambda r: float(r["x"]))
        xs = np.array([float(r["x"]) for r in rows])
        us = np.array([float(r.get("u", 0.0)) for r in rows])
        Ns = np.array([float(r.get("N", 0.0)) for r in rows])
        sigmas = np.array([float(r.get("sigma", 0.0)) for r in rows])

        # линейная интерполяция на min_points
        new_xs = np.linspace(xs[0], xs[-1], min_points)
        new_us = np.interp(new_xs, xs, us)
        new_Ns = np.interp(new_xs, xs, Ns)
        new_sigmas = np.interp(new_xs, xs, sigmas)

        new_rows = []
        for xv, uv, Nv, sv in zip(new_xs, new_us, new_Ns, new_sigmas):
            new_rows.append({
                "bar": bar_num if bar_num is not None else rows[0].get("bar", 1),
                "x": float(xv),
                "u": float(uv),
                "N": float(Nv),
                "sigma": float(sv)
            })
        return new_rows

    # =======================================================
    # ВКЛАДКА 3 — Графики (НОВЫЙ ФУНКЦИОНАЛ)
    # =======================================================
    def update_graphs(self):
        """
        Построение графиков из данных graph_table (100 точек на стержень)
        с подписью крайних точек
        """
        if not self.results or not self.structure_data:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, "Нет данных", ha='center', va='center')
            self.canvas.draw()
            return

        # Используем graph_table вместо table для графиков
        if "graph_table" not in self.results:
            graph_data = self.results.get("table", [])
        else:
            graph_data = self.results["graph_table"]

        bars = list(self.structure_data.get("bars", []))
        selected = self.combo_graph.currentIndex()

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple", "tab:brown",
                  "tab:pink", "tab:olive", "tab:cyan"]

        total_x = 0.0
        for bar_index, bar_data in enumerate(bars, start=1):
            try:
                L = float(bar_data[0])
            except:
                L = 0.0

            start_x = total_x
            end_x = total_x + L

            # Выбираем точки для текущего стержня из graph_data
            bar_points = []
            for r in graph_data:
                try:
                    if int(r.get("bar", 0)) != bar_index:
                        continue
                    xg = float(r.get("x", 0.0))
                except:
                    continue
                if abs(xg - start_x) < 1e-9 or abs(xg - end_x) < 1e-9 or (xg > start_x and xg < end_x):
                    bar_points.append(r)

            if not bar_points:
                total_x += L
                continue

            # Сортируем по x
            bar_points.sort(key=lambda r: r["x"])

            xs = [row["x"] for row in bar_points]
            if selected == 0:
                ys = [row["u"] for row in bar_points]
                ylabel = "u(x), м"
                title = "Эпюра перемещений"
                value_format = "{:.2e}"
            elif selected == 1:
                ys = [row["N"] for row in bar_points]
                ylabel = "N(x), Н"
                title = "Эпюра продольных сил"
                value_format = "{:.2e}"
            else:
                ys = [row["sigma"] for row in bar_points]
                ylabel = "σ(x), Па"
                title = "Эпюра напряжений"
                value_format = "{:.2e}"

            color = colors[(bar_index - 1) % len(colors)]

            # Рисуем основную линию
            ax.plot(xs, ys, color=color, linewidth=1.2, label=f"Стержень {bar_index}")
            ax.fill_between(xs, ys, 0, color=color, alpha=0.25)

            # 🔹 ПОДПИСИ КРАЙНИХ ТОЧЕК
            if len(bar_points) >= 2:
                # Первая точка (начало стержня)
                first_point = bar_points[0]
                x1, y1 = first_point["x"], first_point["u" if selected == 0 else "N" if selected == 1 else "sigma"]

                # Последняя точка (конец стержня)
                last_point = bar_points[-1]
                x2, y2 = last_point["x"], last_point["u" if selected == 0 else "N" if selected == 1 else "sigma"]

                # Подписи для начала стержня
                ax.annotate(f'{value_format.format(y1)}',
                            xy=(x1, y1),
                            xytext=(5, 5),
                            textcoords='offset points',
                            fontsize=8,
                            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8, edgecolor=color),
                            arrowprops=dict(arrowstyle="->", color=color, lw=0.5))

                # Подписи для конца стержня
                ax.annotate(f'{value_format.format(y2)}',
                            xy=(x2, y2),
                            xytext=(5, 5),
                            textcoords='offset points',
                            fontsize=8,
                            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8, edgecolor=color),
                            arrowprops=dict(arrowstyle="->", color=color, lw=0.5))

                # 🔹 Точки маркеры для наглядности
                ax.scatter([x1, x2], [y1, y2], color=color, s=30, zorder=5)

            total_x += L

        ax.set_xlabel("x, м (глобальная координата)")
        ax.set_ylabel(ylabel if 'ylabel' in locals() else "")
        ax.set_title(title if 'title' in locals() else "")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend()
        self.canvas.draw()

    # =======================================================
    # ВКЛАДКА 4 — Расчёт в точке
    # =======================================================

    def update_point_calculation_tab(self):
        """Обновляет список стержней для выбора во вкладке 'Решение в точке'"""
        if not self.structure_data:
            self.point_bar_combo.clear()
            self.point_bar_combo.addItem("Выберите стержень")
            return

        bars = self.structure_data.get("bars", [])
        self.point_bar_combo.blockSignals(True)
        self.point_bar_combo.clear()
        self.point_bar_combo.addItem("Выберите стержень")
        for i in range(len(bars)):
            self.point_bar_combo.addItem(f"Стержень {i + 1}")
        self.point_bar_combo.blockSignals(False)

    def calculate_at_point(self):
        """Вычисляет значения в заданной точке стержня"""
        if not self.results or not self.structure_data:
            self.point_result_label.setText("Сначала выполните расчёт в процессоре")
            return

        try:
            # Получаем выбранный стержень
            selected_bar_text = self.point_bar_combo.currentText()
            if selected_bar_text == "Выберите стержень":
                self.point_result_label.setText("Выберите стержень")
                return

            bar_num = int(selected_bar_text.split()[-1])

            # Получаем координату
            coord_text = self.point_coord_input.toPlainText().strip()
            if not coord_text:
                self.point_result_label.setText("Введите координату")
                return

            x_local = float(coord_text)

            # Проверяем корректность координаты
            bars = self.structure_data.get("bars", [])
            if bar_num < 1 or bar_num > len(bars):
                self.point_result_label.setText("Неверный номер стержня")
                return

            L = float(bars[bar_num - 1][0])
            if x_local < 0 or x_local > L:
                self.point_result_label.setText(f"Координата должна быть в пределах [0, {L:.3f}] м")
                return

            # Вычисляем глобальную координату
            total_x = 0.0
            for i in range(bar_num - 1):
                total_x += float(bars[i][0])
            x_global = total_x + x_local

            # Ищем ближайшую точку в результатах или интерполируем
            result = self._get_values_at_point(bar_num, x_global, x_local)

            # Форматируем результат
            result_text = (
                f"<b>Результаты в точке:</b><br>"
                f"Стержень: {bar_num}<br>"
                f"Локальная координата: {x_local:.4f} м<br>"
                f"Глобальная координата: {x_global:.4f} м<br><br>"
                f"<b>Значения:</b><br>"
                f"• Перемещение u(x) = {result['u']:.6e} м<br>"
                f"• Продольная сила N(x) = {result['N']:.6e} Н<br>"
                f"• Напряжение σ(x) = {result['sigma']:.6e} Па"
            )

            self.point_result_label.setText(result_text)

        except ValueError:
            self.point_result_label.setText("Ошибка: некорректная координата")
        except Exception as e:
            self.point_result_label.setText(f"Ошибка расчёта: {str(e)}")

    def _get_values_at_point(self, bar_num, x_global, x_local):
        """Возвращает значения в заданной точке (интерполяция при необходимости)"""
        # Ищем точку в таблице результатов
        for row in self.results.get("table", []):
            if (int(row.get("bar", 0)) == bar_num and
                    abs(float(row.get("x", 0)) - x_global) < 1e-9):
                return row

        # Если точка не найдена, интерполируем
        return self._interpolate_at_point(bar_num, x_global, x_local)

    def _interpolate_at_point(self, bar_num, x_global, x_local):
        """Интерполирует значения в заданной точке"""
        # Собираем все точки стержня
        bar_points = []
        for row in self.results.get("table", []):
            if int(row.get("bar", 0)) == bar_num:
                bar_points.append(row)

        if len(bar_points) < 2:
            raise ValueError("Недостаточно точек для интерполяции")

        # Сортируем по координате
        bar_points.sort(key=lambda r: float(r["x"]))

        # Линейная интерполяция
        xs = [float(r["x"]) for r in bar_points]
        us = [float(r["u"]) for r in bar_points]
        Ns = [float(r["N"]) for r in bar_points]
        sigmas = [float(r["sigma"]) for r in bar_points]

        u_interp = np.interp(x_global, xs, us)
        N_interp = np.interp(x_global, xs, Ns)
        sigma_interp = np.interp(x_global, xs, sigmas)

        return {
            "bar": bar_num,
            "x": float(x_global),
            "u": float(u_interp),
            "N": float(N_interp),
            "sigma": float(sigma_interp)
        }

