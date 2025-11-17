import os
from reportlab.platypus import PageBreak
from reportlab.lib.styles import ParagraphStyle
import tempfile
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTabWidget, QTextEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer
from processor import calculate_reactions
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure



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

        # 🔹 КНОПКА ФОРМИРОВАНИЯ ОТЧЕТА PDF
        self.report_button = QPushButton("📊 Сформировать отчет (PDF)")
        self.report_button.clicked.connect(self.generate_pdf_report)
        self.report_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        v1.addWidget(self.report_button)

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

        # 🔹 Область для проверки прочности (добавляем под таблицей)
        self.safety_check_widget = QWidget()
        safety_layout = QVBoxLayout()
        self.safety_check_widget.setLayout(safety_layout)

        # Заголовок проверки прочности
        self.safety_title = QLabel("Проверка прочности:")
        self.safety_title.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
        safety_layout.addWidget(self.safety_title)

        # Текст с результатами
        self.safety_result = QLabel("")
        self.safety_result.setWordWrap(True)
        self.safety_result.setStyleSheet("padding: 10px; border-radius: 5px; font-size: 11pt;")
        self.safety_result.setMinimumHeight(80)
        safety_layout.addWidget(self.safety_result)

        # Сначала скрываем область проверки прочности
        self.safety_check_widget.setVisible(False)
        v2.addWidget(self.safety_check_widget)

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

    def generate_pdf_report(self):
        """Формирует отчет в PDF с правильной кодировкой"""
        if not self.results or not self.structure_data:
            QMessageBox.warning(self, "Ошибка", "Сначала выполните расчёт в процессоре!")
            return

        temp_files = []

        try:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Сохранить отчет PDF", "отчет.pdf", "PDF Files (*.pdf)", options=options
            )

            if not file_name:
                return

            # Сохраняем конструкцию и графики
            structure_image = self._save_structure_simple()
            if structure_image:
                temp_files.append(structure_image)

            graph_files = self._save_graphs_simple()
            temp_files.extend(graph_files)

            doc = SimpleDocTemplate(file_name, pagesize=A4)
            elements = []

            # РЕГИСТРИРУЕМ ШРИФТ С ПОДДЕРЖКОЙ КИРИЛЛИЦЫ
            try:
                # Пробуем разные шрифты с кириллицей
                font_paths = [
                    'C:/Windows/Fonts/arial.ttf',  # Windows
                    '/usr/share/fonts/truetype/freefont/FreeSans.ttf',  # Linux
                    '/Library/Fonts/Arial.ttf',  # Mac
                    'arial.ttf'
                ]

                font_registered = False
                for font_path in font_paths:
                    try:
                        pdfmetrics.registerFont(TTFont('ArialUnicode', font_path))
                        font_name = 'ArialUnicode'
                        font_registered = True
                        break
                    except:
                        continue

                if not font_registered:
                    # Если не нашли шрифт, используем стандартный
                    font_name = 'Helvetica'
            except:
                font_name = 'Helvetica'

            # Создаем стили с правильным шрифтом
            styles = getSampleStyleSheet()

            # Переопределяем стили с нашим шрифтом
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=16,
                spaceAfter=30,
                alignment=1,
                textColor=colors.HexColor('#2c3e50')
            )

            heading2_style = ParagraphStyle(
                'Heading2',
                parent=styles['Heading2'],
                fontName=font_name,
                fontSize=14,
                spaceAfter=12,
                textColor=colors.HexColor('#2c3e50')
            )

            heading3_style = ParagraphStyle(
                'Heading3',
                parent=styles['Heading3'],
                fontName=font_name,
                fontSize=12,
                spaceAfter=8,
                textColor=colors.HexColor('#34495e')
            )

            normal_style = ParagraphStyle(
                'Normal',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                spaceAfter=6
            )

            # Заголовок - используем Unicode символы напрямую
            elements.append(Paragraph("ОТЧЕТ ПО РАСЧЕТУ КОНСТРУКЦИИ", title_style))
            elements.append(Spacer(1, 20))

            # 1. Таблицы препроцессора
            elements.append(Paragraph("1. ТАБЛИЦЫ ИЗ ПРЕПРОЦЕССОРА", heading2_style))
            elements.append(Spacer(1, 10))

            # Таблица стержней
            elements.append(Paragraph("Стержни", heading3_style))
            elements.append(Spacer(1, 5))

            table_number_style = ParagraphStyle(
                'TableNumber',
                parent=normal_style,
                alignment=2,  # 2 = RIGHT
                fontSize=9,
                spaceAfter=5
            )
            elements.append(Paragraph("Таблица 1", table_number_style))  # НОМЕР ТАБЛИЦЫ СПРАВА

            # Используем простые заголовки для теста
            table1_data = [["№", "Длина, м", "Поперечное сечение, м²", "Модуль упругости, Па", "Напряжение σ, Па"]]
            table_1 = self.parent_window.table_1.table
            for row in range(table_1.rowCount()):
                row_data = [str(row + 1)]
                for col in range(table_1.columnCount()):
                    item = table_1.item(row, col)
                    row_data.append(item.text() if item else "0")
                table1_data.append(row_data)

            table1 = Table(table1_data, colWidths=[30, 70, 90, 110, 90])
            table1.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table1)
            elements.append(Spacer(1, 15))

            # Таблица распределенных нагрузок
            elements.append(Paragraph("Распределенные нагрузки", heading3_style))
            elements.append(Spacer(1, 5))
            elements.append(Paragraph("Таблица 2", table_number_style))  # НОМЕР ТАБЛИЦЫ СПРАВА

            table2_data = [["Стержень", "q, Н/м"]]
            table_2 = self.parent_window.table_2.table
            for row in range(table_2.rowCount()):
                row_data = []
                for col in range(table_2.columnCount()):
                    item = table_2.item(row, col)
                    row_data.append(item.text() if item else "")
                if any(row_data):
                    table2_data.append(row_data)

            table2 = Table(table2_data, colWidths=[70, 80])
            table2.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e67e22')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef9e7')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table2)
            elements.append(Spacer(1, 15))

            # Таблица сосредоточенных нагрузок
            elements.append(Paragraph("Сосредоточенные нагрузки", heading3_style))
            elements.append(Spacer(1, 5))
            elements.append(Paragraph("Таблица 3", table_number_style))  # НОМЕР ТАБЛИЦЫ СПРАВА

            table3_data = [["Узел", "F, Н"]]
            table_3 = self.parent_window.table_3.table
            for row in range(table_3.rowCount()):
                row_data = []
                for col in range(table_3.columnCount()):
                    item = table_3.item(row, col)
                    row_data.append(item.text() if item else "")
                if any(row_data):
                    table3_data.append(row_data)

            table3 = Table(table3_data, colWidths=[70, 80])
            table3.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f4ecf7')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table3)
            elements.append(Spacer(1, 20))

            # 2. Опоры
            elements.append(Paragraph("2. ИНФОРМАЦИЯ ОБ ОПОРАХ", heading2_style))
            elements.append(Spacer(1, 10))

            left_fixed = getattr(self.parent_window, "left_fixed", False)
            right_fixed = getattr(self.parent_window, "right_fixed", False)

            # Простые предложения вместо таблицы
            left_support_type = "жесткая заделка" if left_fixed else "отсутствует"
            right_support_type = "жесткая заделка" if right_fixed else "отсутствует"

            elements.append(Paragraph(f"• Левая опора: {left_support_type}", normal_style))
            elements.append(Spacer(1, 5))
            elements.append(Paragraph(f"• Правая опора: {right_support_type}", normal_style))

            elements.append(PageBreak())

            # 3. Конструкция
            elements.append(Paragraph("3. КОНСТРУКЦИЯ", heading2_style))
            elements.append(Spacer(1, 10))

            if structure_image and os.path.exists(structure_image):
                try:
                    structure_img = Image(structure_image, width=600, height=400)
                    elements.append(structure_img)
                    elements.append(Spacer(1, 5))
                    # Подпись по центру
                    caption_style = ParagraphStyle(
                        'Caption',
                        parent=normal_style,
                        alignment=1,  # 1 = CENTER
                        fontSize=9,
                        spaceBefore=5,
                        spaceAfter=10
                    )
                    elements.append(Paragraph("Рис. 1 - Схема конструкции", caption_style))
                except Exception as e:
                    print(f"Ошибка вставки конструкции: {e}")
                    elements.append(Paragraph("Схема конструкции", normal_style))
            else:
                elements.append(Paragraph("Схема конструкции", normal_style))

            elements.append(PageBreak())

            # 4. Результаты по стержням
            elements.append(Paragraph("4. РЕЗУЛЬТАТЫ", heading2_style))
            elements.append(Spacer(1, 10))

            bars = self.structure_data.get("bars", [])
            all_rows = self.results.get("table", [])

            table_counter = 4  # Начинаем с таблицы 4

            for bar_num in range(1, len(bars) + 1):
                elements.append(Paragraph(f"Стержень {bar_num}", heading3_style))
                elements.append(Spacer(1, 5))
                elements.append(Paragraph(f"Таблица {table_counter}", table_number_style))

                bar_rows = [r for r in all_rows if int(r.get("bar", 0)) == bar_num]
                if bar_rows:
                    table_data = [["x, м", "u(x), м", "N(x), Н", "σ(x), Па"]]

                    points_to_show = [0]
                    if len(bar_rows) > 2:
                        points_to_show.append(len(bar_rows) // 2)
                    if len(bar_rows) > 1:
                        points_to_show.append(len(bar_rows) - 1)
                    if len(bar_rows) > 4:
                        points_to_show.extend([1, len(bar_rows) - 2])

                    for point_idx in sorted(set(points_to_show))[:5]:
                        if point_idx < len(bar_rows):
                            row = bar_rows[point_idx]
                            table_data.append([
                                f"{row['x']:.4f}",
                                f"{row['u']:.2e}",
                                f"{row['N']:.2e}",
                                f"{row['sigma']:.2e}"
                            ])

                    bar_table = Table(table_data, colWidths=[70, 100, 100, 100])
                    bar_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), font_name),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e8f6f3')),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ]))
                    elements.append(bar_table)
                    elements.append(Spacer(1, 15))
                    table_counter += 1

            elements.append(PageBreak())

            # 5. Графики
            elements.append(Paragraph("5. ГРАФИКИ", heading2_style))
            elements.append(Spacer(1, 10))

            graph_types = ["Перемещения u(x)", "Силы N(x)", "Напряжения σ(x)"]
            figure_counter = 2  # Начинаем с рисунка 2 (рисунок 1 - это конструкция)

            for i, (graph_type, graph_file) in enumerate(zip(graph_types, graph_files)):
                if graph_file and os.path.exists(graph_file):
                    try:
                        elements.append(Paragraph(graph_type, heading3_style))
                        elements.append(Spacer(1, 5))

                        graph_img = Image(graph_file, width=400, height=250)
                        elements.append(graph_img)
                        elements.append(Spacer(1, 20))

                        # ПОДПИСЬ ГРАФИКА
                        caption_style = ParagraphStyle(
                            'Caption',
                            parent=normal_style,
                            alignment=1,  # CENTER
                            fontSize=9,
                            spaceBefore=5,
                            spaceAfter=10
                        )
                        elements.append(Paragraph(f"Рис. {figure_counter} - {graph_type}", caption_style))
                        elements.append(Spacer(1, 15))

                        figure_counter += 1  # Увеличиваем счетчик для следующего рисунка

                        if graph_type == "Перемещения u(x)":
                            elements.append(PageBreak())

                    except Exception as e:
                        print(f"Ошибка вставки графика: {e}")

            # Собираем PDF
            doc.build(elements)

            QMessageBox.information(self, "Успех", f"PDF отчет сохранен в:\n{file_name}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при формировании PDF отчета:\n{str(e)}")
        finally:
            # Удаляем временные файлы
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except:
                    pass

    def _save_structure_simple(self):
        """ПРОСТОЙ метод сохранения конструкции"""
        try:
            draw_area = self.parent_window.draw_area

            # Просто захватываем виджет
            pixmap = draw_area.grab()

            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_file.close()

            success = pixmap.save(temp_file.name, 'PNG')

            if success:
                return temp_file.name
            return None

        except Exception as e:
            print(f"Ошибка сохранения конструкции: {e}")
            return None

    def _create_structure_section(self, heading2_style, structure_image):
        """Раздел с конструкцией"""
        elements = []

        elements.append(Paragraph("3. КОНСТРУКЦИЯ", heading2_style))
        elements.append(Spacer(1, 10))

        try:
            # Увеличиваем размер изображения
            structure_img = Image(structure_image, width=500, height=300)  # Больший размер
            elements.append(structure_img)
            elements.append(Spacer(1, 5))
            elements.append(Paragraph("Рис. 1 - Расчетная схема конструкции",
                                      ParagraphStyle('Caption', fontSize=9, alignment=1)))

        except Exception as e:
            elements.append(Paragraph(f"Не удалось загрузить изображение конструкции: {str(e)}",
                                      ParagraphStyle('Normal', fontSize=10)))

        return elements

    def _save_graphs_simple(self):
        """ПРОСТОЙ метод сохранения графиков"""
        graph_files = []
        graph_types = ["u(x) — Перемещения", "N(x) — Продольная сила", "σ(x) — Напряжения"]

        for i, graph_type in enumerate(graph_types):
            try:
                self.combo_graph.setCurrentIndex(i)
                self.update_graphs()

                ax = self.figure.axes[0]

                # Фиксируем легенду в правом верхнем углу
                if ax.get_legend():
                    legend = ax.get_legend()
                    legend.set_bbox_to_anchor((0.98, 0.98))  # Право-верх с небольшим отступом
                    legend.set_loc('upper left')

                # Увеличиваем размер для сохранения
                original_size = self.figure.get_size_inches()
                self.figure.set_size_inches(12, 8)

                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)

                self.figure.savefig(temp_file.name,
                                    dpi=200,
                                    bbox_inches='tight',
                                    facecolor='white')

                # Возвращаем размер
                self.figure.set_size_inches(original_size)
                self.canvas.draw()

                temp_file.close()
                graph_files.append(temp_file.name)

            except Exception as e:
                print(f"Ошибка сохранения графика {graph_type}: {e}")

        return graph_files

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
            self.safety_check_widget.setVisible(False)
            return

        try:
            all_rows = self.results["table"]
            bars = self.structure_data.get("bars", [])
            selected = self.combo_select_bar.currentText()

            if selected.startswith("Стержень"):
                bar_num = int(selected.split()[-1])

                # Вычисляем границы ВСЕХ стержней
                bar_boundaries = []
                total_x = 0.0
                for i, bar_data in enumerate(bars, start=1):
                    try:
                        L = float(bar_data[0])
                    except Exception:
                        L = 0.0
                    bar_boundaries.append((i, total_x, total_x + L))
                    total_x += L

                # Находим границы выбранного стержня
                start_x, end_x = 0.0, 0.0
                for bar_info in bar_boundaries:
                    if bar_info[0] == bar_num:
                        start_x, end_x = bar_info[1], bar_info[2]
                        break

                # Собираем точки для этого стержня
                rows = []
                for r in all_rows:
                    try:
                        xg = float(r.get("x", 0.0))
                        current_bar = int(r.get("bar", 0))
                    except Exception:
                        continue

                    # Точка принадлежит стержню если:
                    if ((abs(xg - start_x) < 1e-9 or abs(xg - end_x) < 1e-9 or
                         (xg > start_x and xg < end_x)) and
                            current_bar == bar_num):
                        rows.append({
                            "bar": bar_num,
                            "x": float(xg),
                            "u": float(r.get("u", 0.0)),
                            "N": float(r.get("N", 0.0)),
                            "sigma": float(r.get("sigma", 0.0))
                        })

                # Если точек мало - интерполируем
                rows = self._ensure_min_points(rows, min_points=10, bar_num=bar_num)

                # Заполняем таблицу
                self._fill_table(rows)

                # Показываем проверку прочности для отдельного стержня
                self._show_safety_check(rows, bar_num)

            else:
                # Сводная таблица - показываем общую проверку прочности конструкции
                rows = all_rows
                self._fill_table(rows)
                self._show_overall_safety_check(rows)

        except Exception as e:
            print(f"[Ошибка при обновлении таблицы] {e}")
            self.safety_check_widget.setVisible(False)

    def _show_overall_safety_check(self, rows):
        """Показывает проверку прочности для всей конструкции"""
        if not rows:
            self.safety_check_widget.setVisible(False)
            return

        # Собираем максимальные напряжения по всем стержням
        bar_max_stresses = {}
        for row in rows:
            bar_num = row["bar"]
            sigma_abs = abs(row["sigma"])
            if bar_num not in bar_max_stresses or sigma_abs > bar_max_stresses[bar_num]:
                bar_max_stresses[bar_num] = sigma_abs

        # Проверяем прочность каждого стержня
        unsafe_bars = []
        safety_factors = {}

        for bar_num, max_sigma in bar_max_stresses.items():
            allowed_sigma = self._get_allowed_sigma_for_bar(bar_num)
            if allowed_sigma is not None:
                is_safe = max_sigma <= abs(allowed_sigma)
                safety_factor = abs(allowed_sigma) / max_sigma if max_sigma != 0 else float('inf')
                safety_factors[bar_num] = safety_factor

                if not is_safe:
                    unsafe_bars.append(bar_num)

        # Формируем текст результата
        if not safety_factors:
            safety_text = "Не удалось проверить прочность: отсутствуют данные о допустимых напряжениях"
            bg_color = "#fff3cd"
            text_color = "#856404"
        else:
            min_safety_factor = min(safety_factors.values())
            overall_is_safe = len(unsafe_bars) == 0

            safety_text = "<b>Проверка прочности конструкции:</b><br>"

            # Добавляем информацию по каждому стержню
            for bar_num in sorted(safety_factors.keys()):
                status = "✅" if bar_num not in unsafe_bars else "❌"
                safety_text += f"Стержень {bar_num}: {status} (K={safety_factors[bar_num]:.3f})<br>"

            safety_text += f"<br><b>Минимальный коэффициент запаса: {min_safety_factor:.3f}</b><br>"

            if overall_is_safe:
                safety_text += "<b style='color: green;'>КОНСТРУКЦИЯ ПРОЧНА</b>"
                bg_color = "#d4edda"
                text_color = "#155724"
            else:
                safety_text += f"<b style='color: red;'>КОНСТРУКЦИЯ НЕПРОЧНА</b><br>"
                safety_text += f"Не обеспечена прочность стержней: {', '.join(map(str, unsafe_bars))}"
                bg_color = "#f8d7da"
                text_color = "#721c24"

        # Обновляем виджеты
        self.safety_title.setText("Проверка прочности конструкции:")
        self.safety_result.setText(safety_text)
        self.safety_result.setStyleSheet(f"""
            padding: 15px; 
            background-color: {bg_color}; 
            border-radius: 8px; 
            color: {text_color};
            border: 1px solid {text_color}20;
            font-size: 11pt;
        """)
        self.safety_check_widget.setVisible(True)

    def _fill_table(self, rows):
        """Заполняет таблицу с подсветкой напряжений, не удовлетворяющих условию прочности"""
        self.table_widget.blockSignals(True)
        self.table_widget.clearContents()
        self.table_widget.setRowCount(0)

        if not rows:
            self.table_widget.blockSignals(False)
            return

        self.table_widget.setRowCount(len(rows))

        for i, r in enumerate(rows):
            bar_num = r["bar"]
            sigma_value = r["sigma"]

            # Создаем элементы таблицы
            self.table_widget.setItem(i, 0, QTableWidgetItem(str(bar_num)))
            self.table_widget.setItem(i, 1, QTableWidgetItem(f"{r['x']:.5f}"))
            self.table_widget.setItem(i, 2, QTableWidgetItem(f"{r['u']:.6e}"))
            self.table_widget.setItem(i, 3, QTableWidgetItem(f"{r['N']:.6e}"))

            # Ячейка напряжения - проверяем условие прочности
            sigma_item = QTableWidgetItem(f"{sigma_value:.6e}")

            # Получаем допустимое напряжение для этого стержня
            allowed_sigma = self._get_allowed_sigma_for_bar(bar_num)
            if allowed_sigma is not None:
                # Проверяем условие прочности
                if abs(sigma_value) > abs(allowed_sigma):
                    # Напряжение превышает допустимое - подсвечиваем красным
                    sigma_item.setBackground(Qt.red)
                    sigma_item.setForeground(Qt.white)
                    sigma_item.setToolTip(
                        f"Напряжение превышает допустимое: {abs(sigma_value):.6e} > {abs(allowed_sigma):.6e}")

            self.table_widget.setItem(i, 4, sigma_item)

        self.table_widget.blockSignals(False)

    def _show_safety_check(self, rows, bar_num):
        """Показывает проверку прочности под таблицей"""
        if not rows:
            self.safety_check_widget.setVisible(False)
            return

        # Находим максимальные по модулю значения для этого стержня
        max_N = max(abs(row["N"]) for row in rows)
        max_sigma = max(abs(row["sigma"]) for row in rows)

        # Получаем допустимое напряжение для этого стержня из препроцессора
        allowed_sigma = self._get_allowed_sigma_for_bar(bar_num)

        if allowed_sigma is None:
            self.safety_title.setText("Проверка прочности:")
            self.safety_result.setText("Допускаемое напряжение не задано в препроцессоре")
            self.safety_result.setStyleSheet(
                "padding: 10px; background-color: #fff3cd; border-radius: 5px; color: #856404;")
            self.safety_check_widget.setVisible(True)
            return

        # Проверяем прочность
        is_safe = max_sigma <= abs(allowed_sigma)
        safety_factor = abs(allowed_sigma) / max_sigma if max_sigma != 0 else float('inf')

        # Форматируем текст как на картинке
        safety_text = (
            f"<b>Проверка прочности стержня {bar_num}:</b><br>"
            f"Максимальное напряжение: {max_sigma:.6f}<br>"
            f"Допускаемое напряжение: {abs(allowed_sigma):.6f}<br>"
        )

        if is_safe:
            safety_text += f"<b style='color: green;'>ПРОЧНОСТЬ ОБЕСПЕЧЕНА</b><br>"
            bg_color = "#d4edda"
            text_color = "#155724"
        else:
            safety_text += f"<b style='color: red;'>ПРОЧНОСТЬ НЕ ОБЕСПЕЧЕНА</b><br>"
            bg_color = "#f8d7da"
            text_color = "#721c24"

        safety_text += f"Коэффициент запаса: {safety_factor:.3f}"

        # Обновляем виджеты
        self.safety_title.setText(f"Проверка прочности стержня {bar_num}:")
        self.safety_result.setText(safety_text)
        self.safety_result.setStyleSheet(f"""
            padding: 15px; 
            background-color: {bg_color}; 
            border-radius: 8px; 
            color: {text_color};
            border: 1px solid {text_color}20;
            font-size: 11pt;
        """)
        self.safety_check_widget.setVisible(True)

    def _get_allowed_sigma_for_bar(self, bar_num):
        """Получает допустимое напряжение для стержня из таблицы препроцессора"""
        try:
            # В таблице стержней (table_1) допустимое напряжение находится в 4-м столбце (индекс 3)
            table_1 = self.parent_window.table_1.table

            for row in range(table_1.rowCount()):
                if row + 1 == bar_num:  # Нумерация стержней с 1
                    sigma_item = table_1.item(row, 3)  # 4-й столбец - напряжение
                    if sigma_item and sigma_item.text().strip():
                        return float(sigma_item.text())
            return None
        except Exception:
            return None

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
        с подписью крайних точек и автоматическим логарифмическим масштабированием
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
        all_ys = []  # Для сбора всех значений Y для анализа масштаба
        all_xs = []  # Для сбора всех значений X для анализа масштаба

        # Сначала соберем все данные для анализа масштабов
        bar_data_points = []
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

            if bar_points:
                # Сортируем по x
                bar_points.sort(key=lambda r: r["x"])
                bar_data_points.append((bar_index, bar_points, start_x, end_x, L))

                # Собираем координаты для анализа масштаба
                xs = [row["x"] for row in bar_points]
                all_xs.extend(xs)

                if selected == 0:
                    ys = [row["u"] for row in bar_points]
                elif selected == 1:
                    ys = [row["N"] for row in bar_points]
                else:
                    ys = [row["sigma"] for row in bar_points]
                all_ys.extend(ys)

            total_x += L

        # 🔹 АВТОМАТИЧЕСКОЕ МАСШТАБИРОВАНИЕ ПО ОСИ X
        x_log_scale = False
        if all_xs:
            x_range = max(all_xs) - min(all_xs)
            x_max_abs = max(abs(min(all_xs)), abs(max(all_xs)))

            # Если диапазон по X очень большой (например, 1 и 1e12) - логарифмический масштаб
            if x_range > 1e3:  # Если разброс больше миллиона
                ax.set_xscale('log')
                xlabel = "x, м (лог. масштаб)"
                x_log_scale = True
            else:
                xlabel = "x, м (глобальная координата)"
                x_log_scale = False

        # 🔹 АВТОМАТИЧЕСКОЕ МАСШТАБИРОВАНИЕ ПО ОСИ Y
        ylabel_suffix = ""
        if all_ys:
            # Проверяем диапазон значений для определения необходимости логарифмического масштаба
            max_abs_val = max(abs(min(all_ys)), abs(max(all_ys))) if all_ys else 1
            non_zero_ys = [abs(y) for y in all_ys if abs(y) > 1e-15]
            min_abs_nonzero = min(non_zero_ys) if non_zero_ys else max_abs_val

            # Если диапазон значений превышает 4 порядка - используем логарифмический масштаб
            if non_zero_ys and (max_abs_val / min_abs_nonzero > 1e4):
                ax.set_yscale('symlog', linthresh=min_abs_nonzero * 10)
                ylabel_suffix = " (симм. лог. масштаб)"
            else:
                # Если значения очень маленькие или очень большие - используем научную нотацию
                if max_abs_val < 1e-3 or max_abs_val > 1e6:
                    ax.ticklabel_format(axis='y', style='sci', scilimits=(-3, 3))
                ylabel_suffix = ""

        # Теперь рисуем графики с учетом выбранного масштаба
        for bar_index, bar_points, start_x, end_x, L in bar_data_points:
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

            # 🔹 ПОДПИСИ КРАЙНИХ ТОЧЕК - ВСЕГДА для всех стержней
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

        # Устанавливаем подписи осей
        ax.set_xlabel(xlabel if 'xlabel' in locals() else "x, м")
        ax.set_ylabel(ylabel + ylabel_suffix if 'ylabel' in locals() else "")
        ax.set_title(title if 'title' in locals() else "")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend()

        # 🔹 Добавляем информацию о масштабе
        scale_info = []
        if ax.get_xscale() == 'log':
            scale_info.append("Лог. масштаб по X")
        if ax.get_yscale() == 'symlog':
            scale_info.append("Симм. лог. масштаб по Y")
        elif ax.get_yscale() == 'log':
            scale_info.append("Лог. масштаб по Y")

        if scale_info:
            ax.text(0.02, 0.98, "\n".join(scale_info),
                    transform=ax.transAxes, fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.7),
                    verticalalignment='top')

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

