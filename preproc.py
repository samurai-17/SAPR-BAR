import sys

from PyQt5.QtWidgets import (
    QWidget, QApplication, QHBoxLayout,
    QVBoxLayout, QCheckBox, QSizePolicy,
    QGroupBox, QPushButton
)
from PyQt5 import QtGui, QtCore
from tables import Table


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.set_window_settings()
        self.main_layout = QHBoxLayout()
        self.create_button_section()
        self.initUI()

    def set_window_settings(self):
        # Главное окно
        self.setWindowTitle("WASUPR")
        icon = QtGui.QIcon("image/chekanin_photo1.png")
        self.setWindowIcon(icon)
        self.resize(1280, 720)

    def create_button_section(self):
        # ===== Левая панель кнопок =====
        btn_layout = QVBoxLayout()
        btn1 = QCheckBox("Показать / скрыть таблицы")
        btn2 = QCheckBox("Левая заделка")
        btn3 = QCheckBox("Правая заделка")
        btn_save_all = QPushButton("💾 Сохранить все таблицы")
        btn_load_all = QPushButton("💾 Загрузить все таблицы")

        # кнопка сохранения будет вызывать метод у первой таблицы
        btn_save_all.clicked.connect(lambda: self.table_1.table.save_all_tables()) # noqa
        btn_load_all.clicked.connect(lambda: self.table_1.table.load_all_tables())  # noqa
        btn1.clicked.connect(self.ch_click) # noqa

        btn_layout.addStretch(1)
        btn_layout.addWidget(btn1)
        btn_layout.addWidget(btn2)
        btn_layout.addWidget(btn3)
        btn_layout.addWidget(btn_save_all)
        btn_layout.addWidget(btn_load_all)

        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        btn_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.main_layout.addWidget(btn_widget)

    def initUI(self):
        # ===== Главный layout =====
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(20)

        # ===== Правая панель таблиц =====
        self.st_layout = QVBoxLayout()
        self.table_layout = QHBoxLayout()
        self.st_layout.setSpacing(10)

        # Таблица стержней
        self.table_1 = self.create_table_group("Стержни", 4, 1,
                                               ["Длина(L)", "Поперечное сечение(A)",
                                          "Модуль упругости(E)", "Напряжение(σ)"],
                                               ["1"])
        self.st_layout.addWidget(self.table_1)

        # Таблица распределённых нагрузок
        self.table_2 = self.create_table_group("Распределенные нагрузки", 2, 1,
                                               ["№ стержня", "q"], ["1"])
        self.table_layout.addWidget(self.table_2)

        # Таблица сосредоточенных нагрузок
        self.table_3 = self.create_table_group("Сосредоточенные нагрузки", 2, 1,
                                               ["№ узла", "F"], ["1"])
        self.table_layout.addWidget(self.table_3)

        self.st_layout.addLayout(self.table_layout)

        self.main_layout.addStretch(1)

        self.table_widget = QWidget()
        self.table_widget.setMinimumWidth(650)
        self.table_widget.setLayout(self.st_layout)
        self.table_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.table_widget)
        self.setLayout(self.main_layout)

    def create_table_group(self, title, col_c, row_c, hor_lab, ver_lab):
        """Создаёт группу с заголовком и таблицей внутри"""
        group = QGroupBox(title)
        group.setAlignment(QtCore.Qt.AlignHCenter) # noqa
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()

        table = Table(self, title, col_c, row_c, hor_lab, ver_lab)

        table.btn_add = QPushButton("+")
        table.btn_add.clicked.connect(table.add_row) # noqa
        table.btn_del = QPushButton("-")
        table.btn_del.clicked.connect(table.del_row) # noqa

        vbox.addWidget(table)
        hbox.addWidget(table.btn_add)
        hbox.addWidget(table.btn_del)
        vbox.addLayout(hbox)
        group.setLayout(vbox)

        group.table = table
        return group

    def ch_click(self):
        """Показать/скрыть все таблицы"""
        visible = not self.table_1.isVisible()
        self.table_1.setVisible(visible)
        self.table_2.setVisible(visible)
        self.table_3.setVisible(visible)


if __name__ == '__main__':
    from PyQt5.QtWinExtras import QtWin
    myappid = 'mycompany.myproduct.subproduct.version'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("image/chekanin_photo1.png"))
    ex = Window()
    ex.show()
    sys.exit(app.exec_())
