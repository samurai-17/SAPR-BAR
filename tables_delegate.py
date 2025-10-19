from PyQt5.QtWidgets import QItemDelegate, QLineEdit
from PyQt5 import QtCore
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator


class EmptyAllowedValidator(QValidator):
    """Позволяет оставлять ячейку пустой, но при этом проверяет остальные значения."""
    def __init__(self, base_validator, parent=None):
        super().__init__(parent)
        self.base_validator = base_validator

    def validate(self, text, pos):
        # Разрешаем пустую строку
        if text.strip() == "":
            return QValidator.Acceptable, text, pos
        return self.base_validator.validate(text, pos)


class TablesDelegate(QItemDelegate):
    def __init__(self, parent=None, is_int=False, is_positive=False):
        super().__init__(parent)
        self.is_int = is_int
        self.is_positive = is_positive

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)

        # 🔹 Настраиваем валидатор
        if self.is_int:
            validator = QIntValidator()
            if self.is_positive:
                validator.setBottom(0)
        else:
            validator = QDoubleValidator()
            if self.is_positive:
                validator.setBottom(0.0)
            validator.setNotation(QDoubleValidator.StandardNotation)

        validator.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        editor.setValidator(EmptyAllowedValidator(validator))

        # 🔹 Автоматическое добавление "0" перед точкой
        def fix_dot_prefix(text):
            # если пользователь стирает всё — не мешаем
            if not text.strip():
                return
            if text == ".":
                editor.setText("0.")
            elif text == "-.":
                editor.setText("-0.")
            elif text == "+.":
                editor.setText("+0.")

        editor.textEdited.connect(fix_dot_prefix)
        return editor

    def setModelData(self, editor, model, index):
        """Сохраняем значение в таблицу с корректной обработкой формата"""
        text = editor.text().strip()

        # Разрешаем очистку ячейки
        if text == "":
            model.setData(index, "")
            return

        # Добавляем 0 перед точкой, если нужно
        if text.startswith("."):
            text = "0" + text
        elif text.startswith("-."):
            text = "-0" + text[1:]
        elif text.startswith("+."):
            text = "+0" + text[1:]

        # Проверяем корректность значения
        try:
            val = float(text)
            if self.is_positive and val < 0:
                return  # Не сохраняем отрицательные числа
            # 🔹 если число целое — записываем как int
            if self.is_int or val.is_integer():
                text = str(int(val))
            else:
                text = str(val)
        except ValueError:
            return  # игнорируем некорректный ввод

        model.setData(index, text)
