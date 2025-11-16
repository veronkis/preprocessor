import sys
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, 
    QTableWidgetItem, QLabel, QLineEdit, QPushButton, QHeaderView,
    QMessageBox, QGroupBox, QFormLayout, QWidget, QComboBox
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class ResultsDialog(QDialog):
    def __init__(self, bars, U, N_coeffs, U_coeffs, parent=None):
        super().__init__(parent)
        self.bars = bars
        self.U = U
        self.N_coeffs = N_coeffs
        self.U_coeffs = U_coeffs
        self.total_length = sum(bar['L'] for bar in bars)
        
        self.setWindowTitle("Результаты расчёта стержневой системы")
        self.setModal(True)
        self.resize(1200, 800)
        
        self.init_ui()
        self.calculate_all_results()
        
        # АВТОМАТИЧЕСКИ ПЕРЕХОДИМ НА ВКЛАДКУ С ПЕРЕМЕЩЕНИЯМИ УЗЛОВ
        self.tabs.setCurrentIndex(0)
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Заголовок
        title_label = QLabel("Результаты расчёта напряжённо-деформированного состояния")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        
        # Вкладка 1: Таблица перемещений узлов (Δ)
        self.tab_deltas = QWidget()
        self.setup_tab_deltas()
        self.tabs.addTab(self.tab_deltas, "📊 Перемещения узлов")
        
        # Вкладка 2: Графики
        self.tab_plots = QWidget()
        self.setup_tab_plots()
        self.tabs.addTab(self.tab_plots, "📈 Эпюры")
        
        # Вкладка 3: Таблицы результатов
        self.tab_tables = QWidget()
        self.setup_tab_tables()
        self.tabs.addTab(self.tab_tables, "📋 Таблицы результатов")
        
        # Вкладка 4: Результаты в сечении
        self.tab_section = QWidget()
        self.setup_tab_section()
        self.tabs.addTab(self.tab_section, "📍 Результаты в сечении")
        
        layout.addWidget(self.tabs)
        
        # Кнопки внизу
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Сохранить отчёт")
        self.save_btn.setStyleSheet("background-color: #a2d4a2; font-weight:bold; padding:6px")
        self.save_btn.clicked.connect(self.save_report)
        
        self.close_btn = QPushButton("❌ Закрыть")
        self.close_btn.setStyleSheet("background-color: #ffaaaa; font-weight:bold; padding:6px")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def setup_tab_deltas(self):
        layout = QVBoxLayout()
        
        # Информация о системе
        info_label = QLabel(f"Конструкция состоит из {len(self.bars)} стержней и {len(self.U)} узлов")
        info_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)
        
        # Таблица перемещений узлов
        self.delta_table = QTableWidget()
        self.delta_table.setRowCount(len(self.U))
        self.delta_table.setColumnCount(3)
        self.delta_table.setHorizontalHeaderLabels(["Узел", "Перемещение Δ, м", "Перемещение Δ, мм"])
        self.delta_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # СИНИЙ ЦВЕТ ДЛЯ ЗАГОЛОВКОВ ТАБЛИЦЫ
        self.delta_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #2E5CB8; color: white; font-weight: bold; }"
        )
        
        # УБИРАЕМ НУМЕРАЦИЮ СТРОК (вертикальные заголовки)
        self.delta_table.verticalHeader().setVisible(False)
        
        # ДЕЛАЕМ ТАБЛИЦУ НЕРЕДАКТИРУЕМОЙ
        self.delta_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.delta_table.setSelectionMode(QTableWidget.NoSelection)
        
        for i, displacement in enumerate(self.U):
            self.delta_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            # Убрана экспоненциальная форма
            self.delta_table.setItem(i, 1, QTableWidgetItem(f"{displacement:.8f}"))
            self.delta_table.setItem(i, 2, QTableWidgetItem(f"{displacement * 1000:.6f}"))
            
            # Делаем все ячейки нередактируемыми
            for col in range(3):
                item = self.delta_table.item(i, col)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        
        layout.addWidget(QLabel("Перемещения узлов конструкции:"))
        layout.addWidget(self.delta_table)
        
        self.tab_deltas.setLayout(layout)
    
    def setup_tab_plots(self):
        layout = QVBoxLayout()
        
        # Создаем matplotlib figure с тремя subplots
        self.fig = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.fig)
        
        layout.addWidget(QLabel("Эпюры компонент напряжённо-деформированного состояния:"))
        layout.addWidget(self.canvas)
        
        self.tab_plots.setLayout(layout)
    
    def setup_tab_tables(self):
        layout = QVBoxLayout()
        
        # Создаем три группы для таблиц
        n_group = QGroupBox("Продольные силы Nx")
        sigma_group = QGroupBox("Нормальные напряжения σx")
        u_group = QGroupBox("Перемещения Ux")
        
        # Таблица продольных сил
        self.n_table = QTableWidget()
        self.n_table.setColumnCount(3)
        self.n_table.setHorizontalHeaderLabels(["Номер стержня", "Nx в начале стержня, Н", "Nx в конце стержня, Н"])
        self.n_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # СИНИЙ ЦВЕТ ДЛЯ ЗАГОЛОВКОВ ТАБЛИЦЫ
        self.n_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #2E5CB8; color: white; font-weight: bold; }"
        )
        
        self.n_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.n_table.setSelectionMode(QTableWidget.NoSelection)
        
        # Таблица напряжений
        self.sigma_table = QTableWidget()
        self.sigma_table.setColumnCount(4)
        self.sigma_table.setHorizontalHeaderLabels(["Номер стержня", "σx в начале стержня, Па", "σx в конце стержня, Па", "Допустимое напряжение, Па"])
        self.sigma_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # СИНИЙ ЦВЕТ ДЛЯ ЗАГОЛОВКОВ ТАБЛИЦЫ
        self.sigma_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #2E5CB8; color: white; font-weight: bold; }"
        )
        
        self.sigma_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sigma_table.setSelectionMode(QTableWidget.NoSelection)
        
        # Таблица перемещений
        self.u_table = QTableWidget()
        self.u_table.setColumnCount(3)
        self.u_table.setHorizontalHeaderLabels(["Номер стержня", "Ux в начале стержня, м", "Ux в конце стержня, м"])
        self.u_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # СИНИЙ ЦВЕТ ДЛЯ ЗАГОЛОВКОВ ТАБЛИЦЫ
        self.u_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #2E5CB8; color: white; font-weight: bold; }"
        )
        
        self.u_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.u_table.setSelectionMode(QTableWidget.NoSelection)
        
        # Убираем нумерацию строк для всех таблиц
        self.n_table.verticalHeader().setVisible(False)
        self.sigma_table.verticalHeader().setVisible(False)
        self.u_table.verticalHeader().setVisible(False)
        
        # Располагаем таблицы в группах
        n_layout = QVBoxLayout()
        n_layout.addWidget(self.n_table)
        n_group.setLayout(n_layout)
        
        sigma_layout = QVBoxLayout()
        sigma_layout.addWidget(self.sigma_table)
        sigma_group.setLayout(sigma_layout)
        
        u_layout = QVBoxLayout()
        u_layout.addWidget(self.u_table)
        u_group.setLayout(u_layout)
        
        # Добавляем группы в основной layout
        layout.addWidget(n_group)
        layout.addWidget(sigma_group)
        layout.addWidget(u_group)
        
        self.tab_tables.setLayout(layout)
    
    def setup_tab_section(self):
        layout = QVBoxLayout()
        
        # Группа для ввода данных
        input_group = QGroupBox("Параметры сечения")
        input_layout = QFormLayout()
        
        # Выбор элемента
        self.element_combo = QComboBox()
        for i, bar in enumerate(self.bars):
            self.element_combo.addItem(f"Стержень {i+1} (L={bar['L']} м, A={bar['A']} м²)")
        
        # Ввод локальной координаты
        self.local_coord_input = QLineEdit()
        self.local_coord_input.setPlaceholderText(f"0 - {self.bars[0]['L']:.2f} м")
        
        # Кнопка расчета
        self.calc_btn = QPushButton("🔍 Рассчитать в сечении")
        self.calc_btn.setStyleSheet("background-color: #a2d4a2; font-weight:bold; padding:4px")
        self.calc_btn.clicked.connect(self.calculate_section)
        
        input_layout.addRow("Элемент:", self.element_combo)
        input_layout.addRow("Локальная координата, м:", self.local_coord_input)
        input_layout.addRow(self.calc_btn)
        input_group.setLayout(input_layout)
        
        # Обновляем подсказку при изменении выбранного элемента
        self.element_combo.currentIndexChanged.connect(self.update_coord_placeholder)
        
        # Группа для результатов
        results_group = QGroupBox("Результаты в сечении")
        results_layout = QFormLayout()
        
        self.section_element = QLabel("-")
        self.section_local_coord = QLabel("-")
        self.section_global_coord = QLabel("-")
        self.section_Nx = QLabel("-")
        self.section_sigma = QLabel("-")
        self.section_Ux = QLabel("-")
        
        # Установим стили для результатов
        for label in [self.section_element, self.section_local_coord, self.section_global_coord, 
                     self.section_Nx, self.section_sigma, self.section_Ux]:
            label.setStyleSheet("background-color: #f0f0f0; padding: 4px; border: 1px solid #ccc;")
        
        results_layout.addRow("Элемент:", self.section_element)
        results_layout.addRow("Локальная координата, м:", self.section_local_coord)
        results_layout.addRow("Глобальная координата, м:", self.section_global_coord)
        results_layout.addRow("Продольная сила Nx, Н:", self.section_Nx)
        results_layout.addRow("Нормальное напряжение σx, Па:", self.section_sigma)
        results_layout.addRow("Перемещение Ux, м:", self.section_Ux)
        
        results_group.setLayout(results_layout)
        
        layout.addWidget(input_group)
        layout.addWidget(results_group)
        layout.addStretch()
        
        self.tab_section.setLayout(layout)
    
    def update_coord_placeholder(self):
        """Обновление подсказки для ввода локальной координаты при смене элемента"""
        element_idx = self.element_combo.currentIndex()
        if 0 <= element_idx < len(self.bars):
            bar_length = self.bars[element_idx]['L']
            self.local_coord_input.setPlaceholderText(f"0 - {bar_length:.2f} м")

    def calculate_section(self):
        """Расчет результатов в конкретном сечении по локальной координате"""
        try:
            element_idx = self.element_combo.currentIndex()
            if element_idx < 0 or element_idx >= len(self.bars):
                QMessageBox.warning(self, "Ошибка", "Выберите корректный элемент")
                return
            
            x_local = float(self.local_coord_input.text())
            bar = self.bars[element_idx]
            
            if x_local < 0 or x_local > bar['L']:
                QMessageBox.warning(self, "Ошибка", 
                                f"Локальная координата должна быть в диапазоне [0, {bar['L']:.2f}] м")
                return
                
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректное числовое значение для локальной координаты")
            return
        
        # Расчет глобальной координаты
        x_global = sum(bar['L'] for bar in self.bars[:element_idx]) + x_local
        
        # Расчет компонент НДС
        Nx = self.N_coeffs[element_idx][0] + x_local * self.N_coeffs[element_idx][1]
        sigma_x = Nx / bar['A']
        Ux = self.U_coeffs[element_idx][0] + x_local * self.U_coeffs[element_idx][1] + (x_local**2) * self.U_coeffs[element_idx][2]
        
        # Обновление интерфейса
        self.section_element.setText(f"Стержень {element_idx + 1}")
        self.section_local_coord.setText(f"{x_local:.4f}")
        self.section_global_coord.setText(f"{x_global:.4f}")
        self.section_Nx.setText(f"{Nx:.4f}")
        self.section_sigma.setText(f"{sigma_x:.4f}")
        self.section_Ux.setText(f"{Ux:.8f}")
    
    def calculate_all_results(self):
        """Расчет всех результатов для отображения"""
        self.calculate_plots()
        self.calculate_tables()
    
    def calculate_plots(self):
        """Расчет и отображение графиков"""
        self.fig.clear()
        
        # Подготовка данных для графиков
        x_global = []
        Nx_values = []
        sigma_values = []
        Ux_values = []
        
        current_position = 0
        for i, bar in enumerate(self.bars):
            x_local = np.linspace(0, bar['L'], int(100 * bar['L'] / self.total_length))
            
            for x in x_local:
                global_x = current_position + x
                x_global.append(global_x)
                
                Nx = self.N_coeffs[i][0] + x * self.N_coeffs[i][1]
                Nx_values.append(Nx)
                sigma_values.append(Nx / bar['A'])
                Ux_values.append(self.U_coeffs[i][0] + x * self.U_coeffs[i][1] + (x**2) * self.U_coeffs[i][2])
            
            current_position += bar['L']
        
        # Создание subplots
        ax1 = self.fig.add_subplot(311)
        ax2 = self.fig.add_subplot(312)
        ax3 = self.fig.add_subplot(313)
        
        # Эпюра Nx
        ax1.plot(x_global, Nx_values, 'r-', linewidth=2)
        ax1.set_title('Эпюра продольных сил Nx')
        ax1.set_ylabel('Nx, Н')
        ax1.grid(True)
        ax1.fill_between(x_global, Nx_values, alpha=0.3, color='red')
        
        # Эпюра σx
        ax2.plot(x_global, sigma_values, 'b-', linewidth=2)
        ax2.set_title('Эпюра нормальных напряжений σx')
        ax2.set_ylabel('σx, Па')
        ax2.grid(True)
        ax2.fill_between(x_global, sigma_values, alpha=0.3, color='blue')
        
        # Эпюра Ux
        ax3.plot(x_global, Ux_values, 'g-', linewidth=2)
        ax3.set_title('Эпюра перемещений Ux')
        ax3.set_ylabel('Ux, м')
        ax3.set_xlabel('Длина конструкции, м')
        ax3.grid(True)
        ax3.fill_between(x_global, Ux_values, alpha=0.3, color='green')
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    def calculate_tables(self):
        """Заполнение таблиц результатов для начальных и конечных точек стержней"""
        n_data = []
        sigma_data = []
        u_data = []
        
        for i, bar in enumerate(self.bars):
            L = bar['L']
            A = bar['A']
            E = bar['E']
            sigma_allowable = bar['sigma']  # Допускаемое напряжение из входных данных
            
            # Расчет для начала стержня (x=0)
            Nx_start = self.N_coeffs[i][0] + 0 * self.N_coeffs[i][1]  # N(x) = N0 + N1*x при x=0
            sigma_start = Nx_start / A  # σ = N/A
            
            # Расчет для конца стержня (x=L)
            Nx_end = self.N_coeffs[i][0] + L * self.N_coeffs[i][1]  # N(x) = N0 + N1*x при x=L
            sigma_end = Nx_end / A  # σ = N/A
            
            # Перемещения в начале и конце стержня
            Ux_start = self.U_coeffs[i][0]  # u(x) = u0 + u1*x + u2*x² при x=0
            Ux_end = self.U_coeffs[i][0] + L * self.U_coeffs[i][1] + (L**2) * self.U_coeffs[i][2]  # при x=L
            
            # Данные для таблицы продольных сил
            n_data.append([
                str(i + 1),
                f"{Nx_start:.4f}",
                f"{Nx_end:.4f}"
            ])
            
            # Данные для таблицы напряжений
            sigma_data.append([
                str(i + 1),
                f"{sigma_start:.4f}",
                f"{sigma_end:.4f}",
                f"{sigma_allowable:.4f}"
            ])
            
            # Данные для таблицы перемещений
            u_data.append([
                str(i + 1),
                f"{Ux_start:.8f}",
                f"{Ux_end:.8f}"
            ])
        
        # Заполняем таблицу продольных сил
        self.n_table.setRowCount(len(n_data))
        for row, data in enumerate(n_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.n_table.setItem(row, col, item)
        
        # Заполняем таблицу напряжений
        self.sigma_table.setRowCount(len(sigma_data))
        for row, data in enumerate(sigma_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.sigma_table.setItem(row, col, item)
        
        # Заполняем таблицу перемещений
        self.u_table.setRowCount(len(u_data))
        for row, data in enumerate(u_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.u_table.setItem(row, col, item)
    
    def save_report(self):
        """Сохранение полного отчёта"""
        from PySide6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(self, 'Сохранить отчёт', filter='*.csv')
        if not filename:
            return
            
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        try:
            # Создание DataFrame с результатами по стержням
            n_data = []
            sigma_data = []
            u_data = []
            
            for i, bar in enumerate(self.bars):
                L = bar['L']
                A = bar['A']
                sigma_allowable = bar['sigma']  # Допускаемое напряжение из входных данных
                
                # Расчет для начала стержня (x=0)
                Nx_start = self.N_coeffs[i][0] + 0 * self.N_coeffs[i][1]
                sigma_start = Nx_start / A
                
                # Расчет для конца стержня (x=L)
                Nx_end = self.N_coeffs[i][0] + L * self.N_coeffs[i][1]
                sigma_end = Nx_end / A
                
                # Перемещения
                Ux_start = self.U_coeffs[i][0]
                Ux_end = self.U_coeffs[i][0] + L * self.U_coeffs[i][1] + (L**2) * self.U_coeffs[i][2]
                
                n_data.append({
                    'Номер стержня': i + 1,
                    'Nx в начале стержня, Н': Nx_start,
                    'Nx в конце стержня, Н': Nx_end
                })
                
                sigma_data.append({
                    'Номер стержня': i + 1,
                    'σx в начале стержня, Па': sigma_start,
                    'σx в конце стержня, Па': sigma_end,
                    'Допустимое напряжение, Па': sigma_allowable
                })
                
                u_data.append({
                    'Номер стержня': i + 1,
                    'Ux в начале стержня, м': Ux_start,
                    'Ux в конце стержня, м': Ux_end
                })
            
            df_n = pd.DataFrame(n_data)
            df_sigma = pd.DataFrame(sigma_data)
            df_u = pd.DataFrame(u_data)
            
            # Добавление информации о перемещениях узлов
            nodes_data = []
            for i, u in enumerate(self.U):
                nodes_data.append({
                    'Узел': i + 1,
                    'Перемещение Δ, м': f"{u:.8f}",
                    'Перемещение Δ, мм': f"{u * 1000:.6f}"
                })
            df_nodes = pd.DataFrame(nodes_data)
            
            # Сохранение в файл с дополнительной информацией
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("ОТЧЁТ ПО РАСЧЁТУ СТЕРЖНЕВОЙ СИСТЕМЫ\n")
                f.write("=====================================\n")
                f.write(f"Количество элементов: {len(self.bars)}\n")
                f.write(f"Общая длина конструкции: {self.total_length:.4f} м\n")
                f.write(f"Количество узлов: {len(self.U)}\n")
                
                # Анализ результатов
                max_disp = np.max(self.U)
                min_disp = np.min(self.U)
                max_node = np.argmax(self.U) + 1
                min_node = np.argmin(self.U) + 1
                
                f.write(f"Максимальное перемещение: узел {max_node}, Δ = {max_disp:.8f} м\n")
                f.write(f"Минимальное перемещение: узел {min_node}, Δ = {min_disp:.8f} м\n")
                f.write("=====================================\n\n")
                
                f.write("ПЕРЕМЕЩЕНИЯ УЗЛОВ:\n")
                df_nodes.to_csv(f, index=False, sep=';')
                f.write("\n\nПРОДОЛЬНЫЕ СИЛЫ:\n")
                df_n.to_csv(f, index=False, sep=';')
                f.write("\n\nНОРМАЛЬНЫЕ НАПРЯЖЕНИЯ:\n")
                df_sigma.to_csv(f, index=False, sep=';')
                f.write("\n\nПЕРЕМЕЩЕНИЯ СТЕРЖНЕЙ:\n")
                df_u.to_csv(f, index=False, sep=';')
            
            QMessageBox.information(self, "Успех", f"Отчёт сохранён в файл:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении отчёта:\n{e}")

