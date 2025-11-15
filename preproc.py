import sys
from PyQt5.QtWidgets import (
    QWidget, QApplication, QHBoxLayout, QVBoxLayout,
    QCheckBox, QSizePolicy, QGroupBox, QPushButton,
    QTabWidget, QTextEdit, QMessageBox, QLabel,
    QTableWidget, QTableWidgetItem
)
from PyQt5 import QtGui, QtCore
from tables import Table
from draw_area import DrawArea
from processor import calculate_structure  # ✅ добавили
from postprocessor import PostProcessorArea
import validators

class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.set_window_settings()

        # создаём вкладки
        self.tabs = QTabWidget()

        # три вкладки
        self.tab_pre = QWidget()
        self.tab_proc = QWidget()
        self.tab_post = QWidget()

        self.tabs.addTab(self.tab_pre, "Препроцессор")
        self.tabs.addTab(self.tab_proc, "Процессор")
        self.tabs.addTab(self.tab_post, "Постпроцессор")

        # инициализация каждой вкладки
        self.main_layout = QHBoxLayout()
        self.init_preprocessor_ui()   # твой основной UI для препроцессора
        self.init_processor_ui()      # новая вкладка с расчётом
        self.init_postprocessor_ui()  # пока пустая

        # общий layout
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def set_window_settings(self):
        self.setWindowTitle("WASUPR")
        icon = QtGui.QIcon("image/chekanin_photo1.png")
        self.setWindowIcon(icon)
        self.resize(1280, 720)

    # ==========================
    #  ПРЕПРОЦЕССОР
    # ==========================
    def init_preprocessor_ui(self):
        left = self.create_button_section()
        self.main_layout.addWidget(left, 0)

        self.draw_area = DrawArea(self)
        self.draw_area.setMinimumWidth(500)
        self.draw_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.draw_area, 1)

        right = self.create_tables_section()
        self.main_layout.addWidget(right, 0)

        self.tab_pre.setLayout(self.main_layout)

    # ==========================
    #  ПРОЦЕССОР
    # ==========================
    def init_processor_ui(self):
        layout = QVBoxLayout()

        # кнопка расчёта
        self.btn_calc = QPushButton("🧮 Рассчитать конструкцию")
        self.btn_calc.clicked.connect(self.run_calculation)
        layout.addWidget(self.btn_calc)

        # таблица результатов
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["№ стержня", "x (м)", "u(x)", "N(x)", "σ(x)"])
        layout.addWidget(self.results_table)

        # 🔹 текстовый блок для вывода дельт (узловых перемещений)
        from PyQt5.QtWidgets import QTextEdit
        self.delta_output = QTextEdit()
        self.delta_output.setReadOnly(True)
        self.delta_output.setMinimumHeight(80)
        layout.addWidget(self.delta_output)

        self.tab_proc.setLayout(layout)

    def run_calculation(self):
        """Расчёт конструкции и вывод таблицы результатов"""

        data = self.draw_area.structure_data
        if not validators.validate_data_on_save(self):
            QMessageBox.warning(self, "Ошибка", "Ошибки в параметрах препроцессора")
            return

        if not data:
            QMessageBox.warning(self, "Ошибка", "Конструкция не построена!")
            return


        try:
            results = calculate_structure(self, n_points_per_bar_table=5, n_points_per_bar_graph=100)  # передаём окно, т.к. данные из таблиц

            rows = results["table"]
            self.results_table.setRowCount(len(rows))

            for r, row_data in enumerate(rows):
                self.results_table.setItem(r, 0, QTableWidgetItem(str(row_data["bar"])))
                self.results_table.setItem(r, 1, QTableWidgetItem(f"{row_data['x']:.5f}"))
                self.results_table.setItem(r, 2, QTableWidgetItem(f"{row_data['u']:.6e}"))
                self.results_table.setItem(r, 3, QTableWidgetItem(f"{row_data['N']:.6e}"))
                self.results_table.setItem(r, 4, QTableWidgetItem(f"{row_data['sigma']:.6e}"))

            self.proc_results = results  # сохраняем для постпроцессора
            U = results["U"]
            text_lines = ["Узловые перемещения (Δ):"]
            for i, val in enumerate(U, start=1):
                text_lines.append(f"Δ{i} = {val:.6e} м")
            self.delta_output.setText("\n".join(text_lines))

            self.post_area.set_data(self.draw_area.structure_data, results)

            QMessageBox.information(self, "Готово", "✅ Расчёт выполнен! Таблица обновлена.")



        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при расчёте:\n{e}")

    # ==========================
    #  ПОСТПРОЦЕССОР
    # ==========================
    def init_postprocessor_ui(self):
        layout = QVBoxLayout()
        self.post_area = PostProcessorArea(self)
        layout.addWidget(self.post_area)
        self.tab_post.setLayout(layout)

    # def show_epures(self):
    #     if not hasattr(self, "results_table") or self.results_table.rowCount() == 0:
    #         QMessageBox.warning(self, "Ошибка", "Сначала рассчитайте конструкцию на вкладке 'Процессор'.")
    #         return
    #
    #     if not self.draw_area.structure_data:
    #         QMessageBox.warning(self, "Ошибка", "Конструкция не построена.")
    #         return
    #
    #     try:
    #         from processor import calculate_structure
    #         results = calculate_structure(self)
    #         self.post_area.set_results(self.draw_area.structure_data, results)
    #         QMessageBox.information(self, "Готово", "✅ Эпюры построены!")
    #     except Exception as e:
    #         QMessageBox.critical(self, "Ошибка", f"Ошибка при построении эпюр:\n{e}")

    def show_post_results(self):
        if not hasattr(self, "proc_results"):
            QMessageBox.warning(self, "Ошибка", "Сначала выполните расчёт.")
            return
        self.post_area.set_data(self.draw_area.structure_data, self.proc_results)

    # ==========================
    #  Остальные твои функции — без изменений
    # ==========================
    def create_button_section(self):
        btn_layout = QVBoxLayout()
        btn_layout.addStretch(1)

        self.chk_show_tables = QCheckBox("Показать / скрыть таблицы")
        self.chk_left_fixed = QCheckBox("Левая заделка")
        self.chk_right_fixed = QCheckBox("Правая заделка")
        self.btn_save_all = QPushButton("💾 Сохранить все таблицы")
        self.btn_load_all = QPushButton("📂 Загрузить все таблицы")
        self.btn_draw = QPushButton("🎨 Отрисовать конструкцию")

        self.chk_left_fixed.stateChanged.connect(lambda s: setattr(self, "left_fixed", bool(s)))
        self.chk_right_fixed.stateChanged.connect(lambda s: setattr(self, "right_fixed", bool(s)))

        self.left_fixed = False
        self.right_fixed = False

        self.btn_save_all.clicked.connect(lambda: self.table_1.table.save_all_tables())
        self.btn_load_all.clicked.connect(lambda: self.table_1.table.load_all_tables())
        self.chk_show_tables.clicked.connect(self.ch_click)
        self.btn_draw.clicked.connect(self.draw_construction)

        btn_layout.addWidget(self.chk_show_tables)
        btn_layout.addWidget(self.chk_left_fixed)
        btn_layout.addWidget(self.chk_right_fixed)
        btn_layout.addWidget(self.btn_save_all)
        btn_layout.addWidget(self.btn_load_all)
        btn_layout.addWidget(self.btn_draw)
        btn_layout.addStretch(1)

        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        btn_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        btn_widget.setFixedWidth(180)
        return btn_widget

    def create_tables_section(self):
        st_layout = QVBoxLayout()
        st_layout.setSpacing(10)
        table_layout = QHBoxLayout()

        self.table_1 = self.create_table_group(
            "Стержни", 4, 1,
            ["Длина(L)", "Поперечное сечение(A)", "Модуль упругости(E)", "Напряжение(σ)"],
            ["1"]
        )
        st_layout.addWidget(self.table_1)

        self.table_2 = self.create_table_group(
            "Распределенные нагрузки", 2, 1, ["№ стержня", "q"], ["1"]
        )
        table_layout.addWidget(self.table_2)

        self.table_3 = self.create_table_group(
            "Сосредоточенные нагрузки", 2, 1, ["№ узла", "F"], ["1"]
        )
        table_layout.addWidget(self.table_3)

        st_layout.addLayout(table_layout)

        table_widget = QWidget()
        table_widget.setLayout(st_layout)
        table_widget.setMinimumWidth(520)
        table_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        return table_widget

    def create_table_group(self, title, col_c, row_c, hor_lab, ver_lab):
        group = QGroupBox(title)
        group.setAlignment(QtCore.Qt.AlignHCenter)
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()

        table = Table(self, title, col_c, row_c, hor_lab, ver_lab)
        table.btn_add = QPushButton("Добавить")
        table.btn_add.clicked.connect(table.add_row)
        table.btn_del = QPushButton("Удалить")
        table.btn_del.clicked.connect(table.del_row)

        vbox.addWidget(table)
        hbox.addWidget(table.btn_add)
        hbox.addWidget(table.btn_del)
        vbox.addLayout(hbox)
        group.setLayout(vbox)
        group.table = table
        return group

    def ch_click(self):
        visible = not self.table_1.isVisible()
        self.table_1.setVisible(visible)
        self.table_2.setVisible(visible)
        self.table_3.setVisible(visible)

    def show_post_results(self):
        if not hasattr(self, "results_table") or not hasattr(self, "draw_area"):
            QMessageBox.warning(self, "Ошибка", "Нет данных для построения!")
            return
        if not hasattr(self, "proc_results"):
            QMessageBox.warning(self, "Ошибка", "Сначала выполните расчёт.")
            return

        self.post_area.set_data(self.draw_area.structure_data, self.proc_results)


    def draw_construction(self):
        self.draw_area.redraw_structure()


if __name__ == '__main__':
    from PyQt5.QtWinExtras import QtWin
    myappid = 'mycompany.myproduct.subproduct.version'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("image/chekanin_photo1.png"))
    ex = Window()
    ex.show()
    sys.exit(app.exec_())
