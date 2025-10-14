from PyQt5.QtWidgets import (
    QItemDelegate, QLineEdit,
)
from PyQt5 import QtCore
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator


class EmptyAllowedValidator(QValidator):
    def init(self, base_validator, parent=None):
        super().__init__(parent)
        self.base_validator = base_validator

    def validate(self, text, pos):
        if text.strip() == "":
            return QValidator.Acceptable, text, pos
        return self.base_validator.validate(text, pos)


class TablesDelegate(QItemDelegate):
    def __init__(self, parent=None, is_int=False, is_positive=False):
        super().__init__(parent)
        self.is_int = is_int
        self.is_positive = is_positive

    def createEditor(self, parent, option, index):
        row_editor = QLineEdit(parent)

        if self.is_int:
            row_validator = QIntValidator()
            if self.is_positive:
                row_validator.setBottom(0)
            row_editor.setValidator(EmptyAllowedValidator(row_validator))
        else:
            row_validator = QDoubleValidator()
            if self.is_positive:
                row_validator.setBottom(0.0)
            row_validator.setNotation(QDoubleValidator.StandardNotation)

        row_validator.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        row_editor.setValidator(EmptyAllowedValidator(row_validator))
        return row_editor
