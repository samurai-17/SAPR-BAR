import sys
from PyQt5.QtWidgets import (
    QWidget, QApplication, QHBoxLayout, QVBoxLayout,
    QCheckBox, QSizePolicy, QGroupBox, QPushButton
)
from PyQt5 import QtGui, QtCore
from tables import Table
from draw_area import DrawArea


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.set_window_settings()

        # главный layout: 3 колонки (левая панель, центр — DrawArea, правая панель таблиц)
        self.main_layout = QHBoxLayout()
        self.init_ui()

    def set_window_settings(self):
        self.setWindowTitle("WASUPR")
        icon = QtGui.QIcon("image/chekanin_photo1.png")
        self.setWindowIcon(icon)
        self.resize(1280, 720)

    def create_button_section(self):
        """Левая панель с контролами"""
        btn_layout = QVBoxLayout()
        btn_layout.addStretch(1)

        self.chk_show_tables = QCheckBox("Показать / скрыть таблицы")
        self.chk_left_fixed = QCheckBox("Левая заделка")
        self.chk_right_fixed = QCheckBox("Правая заделка")
        btn_save_all = QPushButton("💾 Сохранить все таблицы")
        btn_load_all = QPushButton("📂 Загрузить все таблицы")
        btn_draw = QPushButton("🎨 Отрисовать конструкцию")

        btn_save_all.clicked.connect(lambda: self.table_1.table.save_all_tables())
        btn_load_all.clicked.connect(lambda: self.table_1.table.load_all_tables())
        self.chk_show_tables.clicked.connect(self.ch_click)
        btn_draw.clicked.connect(self.draw_construction)

        # порядок и отступы
        btn_layout.addWidget(self.chk_show_tables)
        btn_layout.addWidget(self.chk_left_fixed)
        btn_layout.addWidget(self.chk_right_fixed)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(btn_save_all)
        btn_layout.addWidget(btn_load_all)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(btn_draw)
        btn_layout.addStretch(1)

        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        # фиксируем ширину левой панели, чтобы центр мог растягиваться
        btn_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        btn_widget.setFixedWidth(180)
        return btn_widget

    def create_tables_section(self):
        """Правая панель — таблицы (обёртка)"""
        st_layout = QVBoxLayout()
        st_layout.setSpacing(10)
        table_layout = QHBoxLayout()

        # Таблица стержней
        self.table_1 = self.create_table_group(
            "Стержни", 4, 1,
            ["Длина(L)", "Поперечное сечение(A)", "Модуль упругости(E)", "Напряжение(σ)"],
            ["1"]
        )
        st_layout.addWidget(self.table_1)

        # Таблица распределённых нагрузок
        self.table_2 = self.create_table_group(
            "Распределенные нагрузки", 2, 1, ["№ стержня", "q"], ["1"]
        )
        table_layout.addWidget(self.table_2)

        # Таблица сосредоточенных нагрузок
        self.table_3 = self.create_table_group(
            "Сосредоточенные нагрузки", 2, 1, ["№ узла", "F"], ["1"]
        )
        table_layout.addWidget(self.table_3)

        st_layout.addLayout(table_layout)

        table_widget = QWidget()
        table_widget.setLayout(st_layout)
        # даём правой панели минимум места, но не даём ей "поглотить" центр
        table_widget.setMinimumWidth(520)
        table_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        return table_widget

    def init_ui(self):
        # сборка: левая панель, центр (DrawArea), правая панель
        left = self.create_button_section()
        self.main_layout.addWidget(left, 0)   # stretch 0 — фиксированная

        # центр — DrawArea (растягивается)
        self.draw_area = DrawArea(self)
        self.draw_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.draw_area, 1)  # stretch 1 — занимает все свободное

        right = self.create_tables_section()
        self.main_layout.addWidget(right, 0)  # stretch 0 — фиксированная

        # подключаем изменение таблиц (не автоотрисовка; оставляем только привязки кнопок)
        # если захотим автоперерисовку — можно закомментировать

        self.setLayout(self.main_layout)

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

    def draw_construction(self):
        """Нажатие кнопки — нарисовать конструкцию в центре"""
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
