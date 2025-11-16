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
        
        self.setWindowTitle("Результаты расчёта")
        self.setModal(True)
        self.resize(1200, 800)
        
        self.init_ui()
        self.calculate_all_results()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        
        # Вкладка 1: Таблица перемещений узлов (Δ)
        self.tab_deltas = QWidget()
        self.setup_tab_deltas()
        self.tabs.addTab(self.tab_deltas, "Перемещения узлов")
        
        # Вкладка 2: Графики
        self.tab_plots = QWidget()
        self.setup_tab_plots()
        self.tabs.addTab(self.tab_plots, "Графики")
        
        # Вкладка 3: Таблицы результатов
        self.tab_tables = QWidget()
        self.setup_tab_tables()
        self.tabs.addTab(self.tab_tables, "Таблицы результатов")
        
        # Вкладка 4: Результаты в сечении (ИЗМЕНЕНА)
        self.tab_section = QWidget()
        self.setup_tab_section()
        self.tabs.addTab(self.tab_section, "Результаты в сечении")
        
        layout.addWidget(self.tabs)
        
        # Кнопки внизу
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить отчёт")
        self.save_btn.clicked.connect(self.save_report)
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def setup_tab_deltas(self):
        layout = QVBoxLayout()
        
        # Таблица перемещений узлов
        self.delta_table = QTableWidget()
        self.delta_table.setRowCount(len(self.U))
        self.delta_table.setColumnCount(2)
        self.delta_table.setHorizontalHeaderLabels(["Узел", "Перемещение Δ, м"])
        self.delta_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        for i, displacement in enumerate(self.U):
            self.delta_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.delta_table.setItem(i, 1, QTableWidgetItem(f"{displacement:.6e}"))
        
        layout.addWidget(QLabel("Перемещения узлов конструкции:"))
        layout.addWidget(self.delta_table)
        
        self.tab_deltas.setLayout(layout)
    
    def setup_tab_plots(self):
        layout = QVBoxLayout()
        
        # Создаем matplotlib figure с тремя subplots
        self.fig = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.fig)
        
        layout.addWidget(self.canvas)
        self.tab_plots.setLayout(layout)
    
    def setup_tab_tables(self):
        layout = QVBoxLayout()
        
        # Создаем таблицы для Nx, σx, Ux
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Глобальная координата, м", "Элемент", "Локальная координата, м", 
            "Nx, Н", "σx, Па", "Ux, м"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        layout.addWidget(QLabel("Подробные результаты по сечениям:"))
        layout.addWidget(self.results_table)
        
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
        self.calc_btn = QPushButton("Рассчитать в сечении")
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
        """Заполнение таблиц результатов"""
        results = []
        
        for i, bar in enumerate(self.bars):
            x_points = np.linspace(0, bar['L'], 8)
            
            for x_local in x_points:
                x_global = sum(bar['L'] for bar in self.bars[:i]) + x_local
                
                Nx = self.N_coeffs[i][0] + x_local * self.N_coeffs[i][1]
                sigma_x = Nx / bar['A']
                Ux = self.U_coeffs[i][0] + x_local * self.U_coeffs[i][1] + (x_local**2) * self.U_coeffs[i][2]
                
                results.append([
                    f"{x_global:.4f}",
                    str(i + 1),
                    f"{x_local:.4f}",
                    f"{Nx:.4f}",
                    f"{sigma_x:.4f}",
                    f"{Ux:.6e}"
                ])
        
        self.results_table.setRowCount(len(results))
        for row, data in enumerate(results):
            for col, value in enumerate(data):
                self.results_table.setItem(row, col, QTableWidgetItem(value))
    
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
        self.section_Ux.setText(f"{Ux:.6e}")
    
    def save_report(self):
        """Сохранение полного отчёта"""
        from PySide6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(self, 'Сохранить отчёт', filter='*.csv')
        if not filename:
            return
            
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        try:
            # Создание DataFrame с результатами
            results_data = []
            for i, bar in enumerate(self.bars):
                x_points = np.linspace(0, bar['L'], 8)
                for x_local in x_points:
                    x_global = sum(bar['L'] for bar in self.bars[:i]) + x_local
                    
                    Nx = self.N_coeffs[i][0] + x_local * self.N_coeffs[i][1]
                    sigma_x = Nx / bar['A']
                    Ux = self.U_coeffs[i][0] + x_local * self.U_coeffs[i][1] + (x_local**2) * self.U_coeffs[i][2]
                    
                    results_data.append({
                        'Глобальная координата, м': x_global,
                        'Элемент': i + 1,
                        'Локальная координата, м': x_local,
                        'Nx, Н': Nx,
                        'σx, Па': sigma_x,
                        'Ux, м': Ux
                    })
            
            df = pd.DataFrame(results_data)
            
            # Добавление информации о перемещениях узлов
            nodes_data = []
            for i, u in enumerate(self.U):
                nodes_data.append({
                    'Узел': i + 1,
                    'Перемещение Δ, м': u
                })
            df_nodes = pd.DataFrame(nodes_data)
            
            # Сохранение в файл с дополнительной информацией
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("ОТЧЁТ ПО РАСЧЁТУ СТЕРЖНЕВОЙ СИСТЕМЫ\n")
                f.write("=====================================\n")
                f.write(f"Количество элементов: {len(self.bars)}\n")
                f.write(f"Общая длина конструкции: {self.total_length:.4f} м\n")
                f.write(f"Количество узлов: {len(self.U)}\n")
                f.write("=====================================\n\n")
                
                f.write("ПЕРЕМЕЩЕНИЯ УЗЛОВ:\n")
                df_nodes.to_csv(f, index=False, sep=';')
                f.write("\n\nРЕЗУЛЬТАТЫ ПО СЕЧЕНИЯМ:\n")
                df.to_csv(f, index=False, sep=';')
            
            QMessageBox.information(self, "Успех", f"Отчёт сохранён в файл:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении отчёта:\n{e}")