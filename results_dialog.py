import sys
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, 
    QTableWidgetItem, QLabel, QLineEdit, QPushButton, QHeaderView,
    QMessageBox, QGroupBox, QFormLayout, QWidget, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class ResultsDialog(QDialog):
    def __init__(self, bars, U, N_coeffs, U_coeffs, parent=None, supports=None, node_forces=None):
        super().__init__(parent)
        self.bars = bars
        self.U = U
        self.N_coeffs = N_coeffs
        self.U_coeffs = U_coeffs
        self.total_length = sum(bar['L'] for bar in bars)
        
        # Сохраняем данные о нагрузках и опорах
        self.supports = supports if supports is not None else []
        self.node_forces = node_forces if node_forces is not None else []
        
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
        
        # Создаем четыре группы для таблиц
        n_group = QGroupBox("Продольные силы Nx")
        sigma_group = QGroupBox("Нормальные напряжения σx")
        u_group = QGroupBox("Перемещения Ux")
        detailed_group = QGroupBox("Детальные результаты по стержням")
        
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
        
        # Таблица напряжений - УВЕЛИЧИВАЕМ КОЛИЧЕСТВО СТОЛБЦОВ ДО 5
        self.sigma_table = QTableWidget()
        self.sigma_table.setColumnCount(5)  # Было 4, стало 5
        self.sigma_table.setHorizontalHeaderLabels([
            "Номер стержня", 
            "σx в начале стержня, Па", 
            "σx в конце стержня, Па", 
            "Допускаемое напряжение, Па",
            "Соответствие норме"  # НОВЫЙ СТОЛБЕЦ
        ])
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
        
        # НОВАЯ ТАБЛИЦА: Детальные результаты по стержням
        detailed_layout = QVBoxLayout()
        
        # Выбор стержня для детальной таблицы
        detail_selection_layout = QHBoxLayout()
        detail_selection_layout.addWidget(QLabel("Выберите стержень:"))
        self.detail_bar_combo = QComboBox()
        for i, bar in enumerate(self.bars):
            self.detail_bar_combo.addItem(f"Стержень {i+1} (L={bar['L']} м)")
        self.detail_bar_combo.currentIndexChanged.connect(self.update_detailed_table)
        detail_selection_layout.addWidget(self.detail_bar_combo)
        detail_selection_layout.addStretch()
        
        detailed_layout.addLayout(detail_selection_layout)
        
        # Таблица детальных результатов
        self.detailed_table = QTableWidget()
        self.detailed_table.setColumnCount(5)
        self.detailed_table.setHorizontalHeaderLabels(["Индекс", "x, м", "Nx, Н", "σx, Па", "Ux, м"])
        self.detailed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # СИНИЙ ЦВЕТ ДЛЯ ЗАГОЛОВКОВ ТАБЛИЦЫ
        self.detailed_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #2E5CB8; color: white; font-weight: bold; }"
        )
        
        self.detailed_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detailed_table.setSelectionMode(QTableWidget.NoSelection)
        self.detailed_table.verticalHeader().setVisible(False)
        
        detailed_layout.addWidget(self.detailed_table)
        detailed_group.setLayout(detailed_layout)
        
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
        layout.addWidget(detailed_group)  # Добавляем новую группу
        
        self.tab_tables.setLayout(layout)
    
    def update_detailed_table(self):
        """Обновление детальной таблицы при выборе стержня"""
        bar_idx = self.detail_bar_combo.currentIndex()
        if bar_idx < 0 or bar_idx >= len(self.bars):
            return
            
        bar = self.bars[bar_idx]
        L = bar['L']
        A = bar['A']
        
        # Создаем точки с шагом 0.1 м
        step = 0.1
        x_points = np.arange(0, L + step, step)
        # Убедимся, что последняя точка точно равна L
        if x_points[-1] > L:
            x_points[-1] = L
        elif x_points[-1] < L:
            x_points = np.append(x_points, L)
        
        # Создаем данные для таблицы
        self.detailed_table.setRowCount(len(x_points))
        
        for i, x in enumerate(x_points):
            # Расчет компонент НДС
            Nx = self.N_coeffs[bar_idx][0] + x * self.N_coeffs[bar_idx][1]
            sigma_x = Nx / A
            Ux = (self.U_coeffs[bar_idx][0] + 
                  x * self.U_coeffs[bar_idx][1] + 
                  (x**2) * self.U_coeffs[bar_idx][2])
            
            # Заполняем строку таблицы
            self.detailed_table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.detailed_table.setItem(i, 1, QTableWidgetItem(f"{x:.4f}"))
            self.detailed_table.setItem(i, 2, QTableWidgetItem(f"{Nx:.4f}"))
            self.detailed_table.setItem(i, 3, QTableWidgetItem(f"{sigma_x:.4f}"))
            self.detailed_table.setItem(i, 4, QTableWidgetItem(f"{Ux:.8f}"))
            
            # Делаем все ячейки нередактируемыми
            for col in range(5):
                item = self.detailed_table.item(i, col)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    
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
        self.section_sigma_allowable = QLabel("-")  # НОВОЕ: допускаемое напряжение
        self.section_compliance = QLabel("-")       # НОВОЕ: соответствие норме
        self.section_Ux = QLabel("-")
        
        # Установим стили для результатов
        for label in [self.section_element, self.section_local_coord, self.section_global_coord, 
                    self.section_Nx, self.section_sigma, self.section_sigma_allowable,
                    self.section_compliance, self.section_Ux]:
            label.setStyleSheet("background-color: #f0f0f0; padding: 4px; border: 1px solid #ccc;")
        
        results_layout.addRow("Элемент:", self.section_element)
        results_layout.addRow("Локальная координата, м:", self.section_local_coord)
        results_layout.addRow("Глобальная координата, м:", self.section_global_coord)
        results_layout.addRow("Продольная сила Nx, Н:", self.section_Nx)
        results_layout.addRow("Нормальное напряжение σx, Па:", self.section_sigma)
        results_layout.addRow("Допускаемое напряжение, Па:", self.section_sigma_allowable)  # НОВАЯ СТРОКА
        results_layout.addRow("Соответствие норме:", self.section_compliance)              # НОВАЯ СТРОКА
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
        
        # Проверка соответствия допустимому напряжению
        sigma_allowable = bar['sigma']
        if abs(sigma_x) <= sigma_allowable:
            compliance_text = "✅ Да (напряжение в норме)"
            compliance_style = "background-color: #d4ffd4; color: #006400; padding: 4px; border: 1px solid #00aa00;"
        else:
            compliance_text = "❌ Нет (превышение допустимого напряжения!)"
            compliance_style = "background-color: #ffd4d4; color: #8b0000; padding: 4px; border: 1px solid #ff0000; font-weight: bold;"
        
        # Обновление интерфейса
        self.section_element.setText(f"Стержень {element_idx + 1}")
        self.section_local_coord.setText(f"{x_local:.4f}")
        self.section_global_coord.setText(f"{x_global:.4f}")
        self.section_Nx.setText(f"{Nx:.4f}")
        self.section_sigma.setText(f"{sigma_x:.4f}")
        self.section_sigma_allowable.setText(f"{sigma_allowable:.4f}")
        self.section_compliance.setText(compliance_text)
        self.section_compliance.setStyleSheet(compliance_style)
        self.section_Ux.setText(f"{Ux:.8f}")
    
    def calculate_all_results(self):
        """Расчет всех результатов для отображения"""
        self.calculate_plots()
        self.calculate_tables()
        self.update_detailed_table()  # Инициализируем детальную таблицу
    
    def calculate_plots(self):
        """Расчет и отображение графиков эпюр с глобальными координатами под каждым эпюром"""
        self.fig.clear()
        
        # Устанавливаем размер фигуры
        self.fig.set_size_inches(12, 10)
        
        # Рассчитываем общую длину конструкции и позиции узлов
        total_length = sum(bar['L'] for bar in self.bars)
        node_positions = [0]
        for bar in self.bars:
            node_positions.append(node_positions[-1] + bar['L'])
        
        # Создаем 3 subplot для эпюр с увеличенными вертикальными отступами
        gs = self.fig.add_gridspec(3, 1, height_ratios=[1, 1, 1])
        
        # Subplot для эпюр
        ax1 = self.fig.add_subplot(gs[0])
        ax2 = self.fig.add_subplot(gs[1])
        ax3 = self.fig.add_subplot(gs[2])
        
        # Подготовка данных для графиков
        x_global = []
        Nx_values = []
        sigma_values = []
        Ux_values = []
        
        current_position = 0
        for i, bar in enumerate(self.bars):
            # Увеличиваем количество точек для более гладких графиков
            x_local = np.linspace(0, bar['L'], int(200 * bar['L'] / total_length))
            
            for x in x_local:
                global_x = current_position + x
                x_global.append(global_x)
                
                # Расчет по коэффициентам
                Nx = self.N_coeffs[i][0] + x * self.N_coeffs[i][1]
                Nx_values.append(Nx)
                
                sigma_values.append(Nx / bar['A'])
                
                # Расчет перемещений
                Ux = (self.U_coeffs[i][0] + 
                    x * self.U_coeffs[i][1] + 
                    (x**2) * self.U_coeffs[i][2])
                Ux_values.append(Ux)
            
            current_position += bar['L']
        
        # Устанавливаем одинаковые пределы по X для всех subplot
        x_min = 0
        x_max = total_length
        
        # Связываем оси X всех subplot
        ax1.set_xlim(x_min, x_max)
        ax2.set_xlim(x_min, x_max)
        ax3.set_xlim(x_min, x_max)
        
        # Эпюра Nx с увеличенными отступами для заголовка
        ax1.plot(x_global, Nx_values, 'r-', linewidth=2)
        ax1.set_title('Эпюра продольных сил Nx', fontsize=12, fontweight='bold', pad=20)  # Увеличен pad
        ax1.set_ylabel('Nx, Н', fontsize=10, labelpad=10)  # Добавлен labelpad
        ax1.grid(True, alpha=0.3)
        ax1.fill_between(x_global, Nx_values, alpha=0.3, color='red')
        
        # Эпюра σx с увеличенными отступами для заголовка
        ax2.plot(x_global, sigma_values, 'b-', linewidth=2)
        ax2.set_title('Эпюра нормальных напряжений σx', fontsize=12, fontweight='bold', pad=20)  # Увеличен pad
        ax2.set_ylabel('σx, Па', fontsize=10, labelpad=10)  # Добавлен labelpad
        ax2.grid(True, alpha=0.3)
        ax2.fill_between(x_global, sigma_values, alpha=0.3, color='blue')
        
        # Эпюра Ux с увеличенными отступами для заголовка
        ax3.plot(x_global, Ux_values, 'g-', linewidth=2)
        ax3.set_title('Эпюра перемещений Ux', fontsize=12, fontweight='bold', pad=20)  # Увеличен pad
        ax3.set_ylabel('Ux, м', fontsize=10, labelpad=10)  # Добавлен labelpad
        ax3.set_xlabel('Координата x, м', fontsize=10, labelpad=10)  # Добавлен labelpad
        ax3.grid(True, alpha=0.3)
        ax3.fill_between(x_global, Ux_values, alpha=0.3, color='green')
        
        # Добавляем вертикальные линии в местах узлов
        for pos in node_positions:
            for ax in [ax1, ax2, ax3]:
                ax.axvline(x=pos, color='k', linestyle='-', alpha=0.5, linewidth=1)
        
        # ДОБАВЛЯЕМ ПОДПИСИ ГЛОБАЛЬНЫХ КООРДИНАТ ПОД КАЖДЫМ ЭПЮРОМ
        
        # Определяем шаг для делений в зависимости от общей длины
        if total_length <= 2:
            step = 0.25
        elif total_length <= 10:
            step = 0.5
        else:
            step = total_length / 10
        
        # Создаем равномерные деления с выбранным шагом
        x_ticks = np.arange(0, total_length + step/2, step)
        
        # Устанавливаем деления на оси X для ВСЕХ графиков
        for ax in [ax1, ax2, ax3]:
            ax.set_xticks(x_ticks)
            ax.set_xticklabels([f'{x:.2f}' for x in x_ticks], fontsize=8)
        
        # Добавляем вертикальные линии для основных делений
        for x in x_ticks:
            if x not in node_positions:  # Узлы уже отмечены
                for ax in [ax1, ax2, ax3]:
                    ax.axvline(x=x, color='gray', linestyle=':', alpha=0.3, linewidth=0.5)
        
        # Улучшаем читаемость подписей осей
        for ax in [ax1, ax2, ax3]:
            ax.tick_params(axis='both', which='major', labelsize=8)
            # Убедимся, что оси X отображаются для всех графиков
            ax.tick_params(axis='x', which='both', labelbottom=True)
        
        # Убираем подписи осей X для верхних графиков
        ax1.set_xlabel('')
        ax2.set_xlabel('')
        
        # ДОБАВЛЯЕМ ПОДПИСИ ЗНАЧЕНИЙ В НАЧАЛЕ И КОНЦЕ СТЕРЖНЕЙ
        
        # Вычисляем значения в узлах для каждого стержня
        current_position = 0
        for i, bar in enumerate(self.bars):
            L = bar['L']
            A = bar['A']
            
            # Координаты начала и конца стержня
            x_start = current_position
            x_end = current_position + L
            
            # Значения в начале стержня (x=0)
            Nx_start = self.N_coeffs[i][0]
            sigma_start = Nx_start / A
            Ux_start = self.U_coeffs[i][0]
            
            # Значения в конце стержня (x=L)
            Nx_end = self.N_coeffs[i][0] + L * self.N_coeffs[i][1]
            sigma_end = Nx_end / A
            Ux_end = self.U_coeffs[i][0] + L * self.U_coeffs[i][1] + (L**2) * self.U_coeffs[i][2]
            
            # Подписи для эпюры Nx
            ax1.annotate(f'{Nx_start:.2f}', xy=(x_start, Nx_start), xytext=(5, 5),
                        textcoords='offset points', fontsize=8, color='darkred',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='darkred', lw=0.5))
            
            ax1.annotate(f'{Nx_end:.2f}', xy=(x_end, Nx_end), xytext=(5, 5),
                        textcoords='offset points', fontsize=8, color='darkred',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='darkred', lw=0.5))
            
            # Подписи для эпюры σx
            ax2.annotate(f'{sigma_start:.2f}', xy=(x_start, sigma_start), xytext=(5, 5),
                        textcoords='offset points', fontsize=8, color='darkblue',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='darkblue', lw=0.5))
            
            ax2.annotate(f'{sigma_end:.2f}', xy=(x_end, sigma_end), xytext=(5, 5),
                        textcoords='offset points', fontsize=8, color='darkblue',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='darkblue', lw=0.5))
            
            # Подписи для эпюры Ux
            ax3.annotate(f'{Ux_start:.6f}', xy=(x_start, Ux_start), xytext=(5, 5),
                        textcoords='offset points', fontsize=8, color='darkgreen',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='darkgreen', lw=0.5))
            
            ax3.annotate(f'{Ux_end:.6f}', xy=(x_end, Ux_end), xytext=(5, 5),
                        textcoords='offset points', fontsize=8, color='darkgreen',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='darkgreen', lw=0.5))
            
            current_position += L
        
        # Обеспечиваем одинаковое соотношение сторон для всех графиков
        # Увеличиваем отступы со всех сторон, особенно сверху и снизу
        self.fig.tight_layout(rect=[0.03, 0.03, 0.97, 0.97], pad=4.0, h_pad=3.0)
        
        # Синхронизируем масштабирование по оси X
        def on_xlim_changed(event_ax):
            xlim = event_ax.get_xlim()
            for ax in [ax1, ax2, ax3]:
                if ax != event_ax:
                    ax.set_xlim(xlim)
        
        # Подключаем обработчики изменения масштаба
        ax1.callbacks.connect('xlim_changed', on_xlim_changed)
        ax2.callbacks.connect('xlim_changed', on_xlim_changed)
        ax3.callbacks.connect('xlim_changed', on_xlim_changed)
        
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
            
            # Определяем максимальное по модулю напряжение в стержне
            max_sigma = max(abs(sigma_start), abs(sigma_end))
            
            # Проверяем соответствие допустимому напряжению
            if max_sigma <= sigma_allowable:
                compliance = "✅ Да"
                compliance_color = "green"
            else:
                compliance = "❌ Нет"
                compliance_color = "red"
            
            # Перемещения в начале и конце стержня
            Ux_start = self.U_coeffs[i][0]  # u(x) = u0 + u1*x + u2*x² при x=0
            Ux_end = self.U_coeffs[i][0] + L * self.U_coeffs[i][1] + (L**2) * self.U_coeffs[i][2]  # при x=L
            
            # Данные для таблицы продольных сил
            n_data.append([
                str(i + 1),
                f"{Nx_start:.4f}",
                f"{Nx_end:.4f}"
            ])
            
            # Данные для таблицы напряжений (теперь 5 столбцов)
            sigma_data.append([
                str(i + 1),
                f"{sigma_start:.4f}",
                f"{sigma_end:.4f}",
                f"{sigma_allowable:.4f}",
                compliance  # НОВЫЙ СТОЛБЕЦ
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
                
                # Окрашиваем ячейку с проверкой соответствия
                if col == 4:  # Столбец "Соответствие норме"
                    if "✅" in value:
                        item.setBackground(QColor(200, 255, 200))  # Зеленый фон для "Да"
                    else:
                        item.setBackground(QColor(255, 200, 200))  # Красный фон для "Нет"
                
                self.sigma_table.setItem(row, col, item)
        
        # Заполняем таблицу перемещений
        self.u_table.setRowCount(len(u_data))
        for row, data in enumerate(u_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.u_table.setItem(row, col, item)
    
    def save_report(self):
        """Сохранение полного отчёта в PDF"""
        from PySide6.QtWidgets import QFileDialog
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import datetime
        import tempfile
        import os
        import numpy as np

        # Регистрация шрифта с поддержкой кириллицы
        try:
            # Попробуем использовать стандартный шрифт с кириллицей
            pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
            FONT_NAME = 'Arial'
        except:
            try:
                # Альтернативный шрифт
                pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
                FONT_NAME = 'DejaVuSans'
            except:
                # Если шрифты не найдены, используем стандартный (кириллица может не отображаться)
                FONT_NAME = 'Helvetica'

        filename, _ = QFileDialog.getSaveFileName(self, 'Сохранить отчёт в PDF', filter='*.pdf')
        if not filename:
            return
            
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        try:
            # Создаем временный файл для графиков
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_plot_path = tmp.name

            # Сохраняем графики в временный файл
            self.fig.savefig(temp_plot_path, dpi=150, bbox_inches='tight', format='png')
            
            # Создаем документ PDF
            doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
            elements = []
            styles = getSampleStyleSheet()
            
            # Создаем стили с правильным шрифтом
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=FONT_NAME,
                fontSize=16,
                spaceAfter=30,
                alignment=1,
                textColor=colors.darkblue
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName=FONT_NAME,
                fontSize=12,
                spaceAfter=12,
                spaceBefore=12,
                textColor=colors.darkblue
            )
            
            subheading_style = ParagraphStyle(
                'SubheadingStyle',
                parent=styles['Heading3'],
                fontName=FONT_NAME,
                fontSize=11,
                spaceAfter=8,
                spaceBefore=8,
                textColor=colors.darkblue
            )
            
            normal_style = ParagraphStyle(
                'NormalStyle',
                parent=styles['Normal'],
                fontName=FONT_NAME,
                fontSize=10
            )
            
            # Заголовок отчета
            title = Paragraph("ОТЧЁТ ПО РАСЧЁТУ СТЕРЖНЕВОЙ СИСТЕМЫ", title_style)
            elements.append(title)
            
            # Информация о системе
            elements.append(Paragraph(f"Дата создания: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", normal_style))
            elements.append(Paragraph(f"Количество элементов: {len(self.bars)}", normal_style))
            elements.append(Paragraph(f"Общая длина конструкции: {self.total_length:.4f} м", normal_style))
            elements.append(Paragraph(f"Количество узлов: {len(self.U)}", normal_style))
            
            # Анализ результатов
            max_disp = np.max(self.U)
            min_disp = np.min(self.U)
            max_node = np.argmax(self.U) + 1
            min_node = np.argmin(self.U) + 1
            
            # Раздел 1: Перемещения узлов
            elements.append(Paragraph("1. ПЕРЕМЕЩЕНИЯ УЗЛОВ", heading_style))
            node_data = [["Узел", "Перемещение Δ, м", "Перемещение Δ, мм"]]
            for i, u in enumerate(self.U):
                node_data.append([str(i+1), f"{u:.8f}", f"{u*1000:.6f}"])
            
            node_table = Table(node_data, colWidths=[30*mm, 60*mm, 60*mm])
            node_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2E5CB8")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), FONT_NAME),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('FONTNAME', (0,1), (-1,-1), FONT_NAME),
                ('FONTSIZE', (0,1), (-1,-1), 9),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black)
            ]))
            elements.append(node_table)
            elements.append(Spacer(1, 25))
            
            # Раздел 2: Эпюры
            elements.append(Paragraph("2. ЭПЮРЫ НАПРЯЖЁННО-ДЕФОРМИРОВАННОГО СОСТОЯНИЯ", heading_style))
            try:
                # Добавляем изображение с графиками
                img = Image(temp_plot_path, width=160*mm, height=120*mm)
                elements.append(img)
                elements.append(Spacer(1, 15))
            except Exception as e:
                elements.append(Paragraph("Ошибка при загрузке графиков", normal_style))
            
            elements.append(Spacer(1, 20))
            
            # Раздел 3: Таблицы результатов
            elements.append(Paragraph("3. ТАБЛИЦЫ РЕЗУЛЬТАТОВ", heading_style))
            
            # Таблица продольных сил
            elements.append(Paragraph("Продольные силы Nx", heading_style))
            n_data = [["Номер стержня", "Nx в начале, Н", "Nx в конце, Н"]]
            for i, bar in enumerate(self.bars):
                L = bar['L']
                Nx_start = self.N_coeffs[i][0] + 0 * self.N_coeffs[i][1]
                Nx_end = self.N_coeffs[i][0] + L * self.N_coeffs[i][1]
                n_data.append([str(i+1), f"{Nx_start:.4f}", f"{Nx_end:.4f}"])
            
            n_table = Table(n_data, colWidths=[30*mm, 50*mm, 50*mm])
            n_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2E5CB8")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), FONT_NAME),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('FONTNAME', (0,1), (-1,-1), FONT_NAME),
                ('FONTSIZE', (0,1), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black)
            ]))
            elements.append(n_table)
            elements.append(Spacer(1, 15))
            
          # Таблица нормальных напряжений - ОБНОВЛЕНА С ДОБАВЛЕНИЕМ СТОЛБЦА "СООТВЕТСТВИЕ НОРМЕ"
            elements.append(Paragraph("Нормальные напряжения σx", heading_style))
            sigma_data = [["Номер стержня", "σx в начале, Па", "σx в конце, Па", "Допускаемое напряжение, Па", "Соответствие норме"]]

            for i, bar in enumerate(self.bars):
                L = bar['L']
                A = bar['A']
                sigma_allowable = bar['sigma']
                
                # Расчет напряжений в начале и конце стержня
                Nx_start = self.N_coeffs[i][0] + 0 * self.N_coeffs[i][1]
                Nx_end = self.N_coeffs[i][0] + L * self.N_coeffs[i][1]
                sigma_start = Nx_start / A
                sigma_end = Nx_end / A
                
                # Определяем максимальное по модулю напряжение в стержне
                max_sigma = max(abs(sigma_start), abs(sigma_end))
                
                # Проверяем соответствие допустимому напряжению
                if max_sigma <= sigma_allowable:
                    compliance = "Да"
                else:
                    compliance = "Нет (Превышение)"
                
                sigma_data.append([
                    str(i+1), 
                    f"{sigma_start:.4f}", 
                    f"{sigma_end:.4f}", 
                    f"{sigma_allowable:.4f}",
                    str(compliance)
                ])

            # Уменьшаем ширину столбцов, чтобы добавить пятый столбец
            sigma_table = Table(sigma_data, colWidths=[20*mm, 35*mm, 35*mm, 35*mm, 35*mm])
            sigma_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2E5CB8")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), FONT_NAME),
                ('FONTSIZE', (0,0), (-1,0), 8),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('FONTNAME', (0,1), (-1,-1), FONT_NAME),
                ('FONTSIZE', (0,1), (-1,-1), 7),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ]))
            elements.append(sigma_table)
            elements.append(Spacer(1, 15))
            
            # Таблица перемещений стержней
            elements.append(Paragraph("Перемещения стержней Ux", heading_style))
            u_data = [["Номер стержня", "Ux в начале, м", "Ux в конце, м"]]
            for i, bar in enumerate(self.bars):
                L = bar['L']
                Ux_start = self.U_coeffs[i][0]
                Ux_end = self.U_coeffs[i][0] + L * self.U_coeffs[i][1] + (L**2) * self.U_coeffs[i][2]
                u_data.append([str(i+1), f"{Ux_start:.8f}", f"{Ux_end:.8f}"])
            
            u_table = Table(u_data, colWidths=[30*mm, 60*mm, 60*mm])
            u_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2E5CB8")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), FONT_NAME),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('FONTNAME', (0,1), (-1,-1), FONT_NAME),
                ('FONTSIZE', (0,1), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black)
            ]))
            elements.append(u_table)
            
            # Раздел 4: Детальные результаты по стержням
            elements.append(PageBreak())  # Новый раздел на новой странице
            elements.append(Paragraph("4. ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ ПО СТЕРЖНЯМ", heading_style))
            
            for bar_idx, bar in enumerate(self.bars):
                L = bar['L']
                A = bar['A']
                
                # Подзаголовок для текущего стержня
                elements.append(Paragraph(f"Стержень {bar_idx+1} (L={L:.3f} м, A={A:.6f} м²)", subheading_style))
                
                # Создаем точки с шагом 0.1 м
                step = 0.1
                x_points = np.arange(0, L + step, step)
                # Убедимся, что последняя точка точно равна L
                if x_points[-1] > L:
                    x_points[-1] = L
                elif x_points[-1] < L:
                    x_points = np.append(x_points, L)
                
                # Создаем данные для таблицы
                detailed_data = [["Индекс", "x, м", "Nx, Н", "σx, Па", "Ux, м"]]
                
                for i, x in enumerate(x_points):
                    # Расчет компонент НДС
                    Nx = self.N_coeffs[bar_idx][0] + x * self.N_coeffs[bar_idx][1]
                    sigma_x = Nx / A
                    Ux = (self.U_coeffs[bar_idx][0] + 
                        x * self.U_coeffs[bar_idx][1] + 
                        (x**2) * self.U_coeffs[bar_idx][2])
                    
                    detailed_data.append([
                        str(i),
                        f"{x:.4f}",
                        f"{Nx:.4f}",
                        f"{sigma_x:.4f}",
                        f"{Ux:.8f}"
                    ])
                
                # Создаем таблицу с детальными результатами
                detailed_table = Table(detailed_data, colWidths=[20*mm, 25*mm, 35*mm, 35*mm, 45*mm])
                detailed_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2E5CB8")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), FONT_NAME),
                    ('FONTSIZE', (0,0), (-1,0), 8),
                    ('BOTTOMPADDING', (0,0), (-1,0), 8),
                    ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                    ('FONTNAME', (0,1), (-1,-1), FONT_NAME),
                    ('FONTSIZE', (0,1), (-1,-1), 7),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.lightgrey])
                ]))
                
                elements.append(detailed_table)
                elements.append(Spacer(1, 15))
                
                # Добавляем разрыв страницы после каждого стержня, если он не последний
                if bar_idx < len(self.bars) - 1:
                    elements.append(PageBreak())
            
            # Строим PDF
            doc.build(elements)
            
            # Удаляем временный файл
            if os.path.exists(temp_plot_path):
                os.unlink(temp_plot_path)
            
            QMessageBox.information(self, "Успех", f"Отчёт сохранён в файл:\n{filename}")
            
        except ImportError as e:
            QMessageBox.critical(self, "Ошибка", 
                            "Для сохранения в PDF необходимо установить библиотеки:\n"
                            "pip install reportlab pillow")
        except Exception as e:
            # Удаляем временный файл в случае ошибки
            if 'temp_plot_path' in locals() and os.path.exists(temp_plot_path):
                os.unlink(temp_plot_path)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении отчёта:\n{str(e)}")