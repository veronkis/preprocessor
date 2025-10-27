import sys
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QComboBox,
    QHeaderView, QFrame, QCheckBox, QToolTip, QFileDialog, QMessageBox
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QAction
from PySide6.QtCore import Qt, QRectF

# ------------------------
# Холст для рисования
# ------------------------
class StructureCanvas(QWidget):
    def __init__(self, bars, supports, node_forces, show_grid=True):
        super().__init__()
        self.bars = bars
        self.supports = supports
        self.node_forces = node_forces
        self.show_grid = show_grid
        self.setMouseTracking(True)
        self.hover_text = ""
        self.setMinimumHeight(400)
        self.zoom_factor = 1.0  # Текущий коэффициент увеличения
        self.setToolTip("Колесо мыши — масштабирование, Ctrl+Колесо — быстрое масштабирование")

    def mouseMoveEvent(self, event):
        pos = event.pos()
        self.hover_text = ""
        for rect, val in getattr(self, "q_regions", []):
            if rect.contains(pos):
                self.hover_text = f"q = {val}"
        for rect, val in getattr(self, "F_regions", []):
            if rect.contains(pos):
                self.hover_text = f"F = {val}"
        if self.hover_text:
            QToolTip.showText(event.globalPos(), self.hover_text, self)
        else:
            QToolTip.hideText()

    def wheelEvent(self, event):
        """Обработка колесика мыши для масштабирования"""
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 1 / 1.1
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            factor = factor ** 2  # Быстрое масштабирование при зажатом Ctrl
        self.zoom_factor *= factor
        self.zoom_factor = max(0.2, min(5.0, self.zoom_factor))  # Ограничиваем диапазон зума
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(230, 200, 150))
        painter.setRenderHint(QPainter.Antialiasing)

        if self.show_grid:
            step = 20
            painter.setPen(QPen(QColor(180,180,180),1,Qt.DotLine))
            for x in range(0,self.width(),step):
                painter.drawLine(x,0,x,self.height())
            for y in range(0,self.height(),step):
                painter.drawLine(0,y,self.width(),y)

        if len(self.bars) == 0:
            return

        node_positions = [0]
        for bar in self.bars:
            node_positions.append(node_positions[-1] + float(bar['L']))
        total_length = node_positions[-1] if node_positions[-1]>0 else 10
        base_scale = (self.width() - 100)/total_length
        scale = base_scale * self.zoom_factor  # 🔹 применяем масштабирование
        offset = 50
        y_axis = self.height()//2

        max_A = max([float(bar['A']) for bar in self.bars]+[1])
        thickness_scale = 50/max_A

        painter.setPen(QPen(Qt.black,2))
        painter.drawLine(0,y_axis,self.width(),y_axis)

        # Стержни
        for idx, bar in enumerate(self.bars):
            x1 = offset + node_positions[idx]*scale
            x2 = offset + node_positions[idx+1]*scale
            y = y_axis
            thickness = max(4,float(bar.get('A',1))*thickness_scale)
            rect_top = y - thickness//2
            rect_height = thickness
            painter.setPen(QPen(Qt.black))
            painter.setBrush(QBrush(QColor(100,50,0)))
            painter.drawRect(int(x1), int(rect_top), int(x2-x1), int(rect_height))
            painter.setPen(QPen(Qt.black))
            painter.setBrush(QBrush(Qt.white))
            painter.drawEllipse(int((x1+x2)/2)-6, int(rect_top+rect_height/2)-6, 12, 12)
            painter.drawText(int((x1+x2)/2-3), int(rect_top+rect_height/2+5), str(idx+1))

        # Узлы
        rect_size = 15
        painter.setBrush(QBrush(Qt.white))
        for i,pos in enumerate(node_positions):
            node_x = offset + pos*scale
            painter.setPen(QPen(Qt.black,1,Qt.DotLine))
            painter.drawLine(int(node_x),y_axis,int(node_x),y_axis-40)
            painter.setPen(QPen(Qt.black))
            painter.drawRect(int(node_x-rect_size/2),y_axis-55,rect_size,rect_size)
            painter.drawText(int(node_x-rect_size/2),y_axis-55,rect_size,rect_size,Qt.AlignCenter,str(i+1))

        # Опоры
        line_height = 40
        dash_step = 6
        diag_offset = 6
        for s in self.supports:
            side = s['side']
            painter.setPen(QPen(Qt.black,3))
            painter.setBrush(Qt.black)
            if side in ['Слева','Обе']:
                x_pos = offset
                painter.drawLine(x_pos,y_axis-line_height//2,x_pos,y_axis+line_height//2)
                for i in range(0,line_height,dash_step):
                    painter.drawLine(x_pos, y_axis-line_height//2 + i,
                                     x_pos - diag_offset, y_axis-line_height//2 + i + diag_offset)
            if side in ['Справа','Обе']:
                x_pos = offset + node_positions[-1]*scale
                painter.drawLine(x_pos,y_axis-line_height//2,x_pos,y_axis+line_height//2)
                for i in range(0,line_height,dash_step):
                    painter.drawLine(x_pos, y_axis-line_height//2 + i,
                                     x_pos + diag_offset, y_axis-line_height//2 + i + diag_offset)

        # Погонные нагрузки q
        painter.setPen(QPen(Qt.black, 4))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        self.q_regions = []
        q_y_offset = 35
        edge_margin = 10
        for idx, bar in enumerate(self.bars):
            q = bar.get('q', 0)
            if abs(q) < 0.001:
                continue
            x1 = offset + node_positions[idx] * scale + edge_margin
            x2 = offset + node_positions[idx + 1] * scale - edge_margin
            yq = y_axis - q_y_offset
            step = 25
            arrow_len = 16
            if q > 0:
                current_x = x1
                while current_x + arrow_len < x2:
                    painter.drawLine(current_x, yq, current_x + arrow_len, yq)
                    painter.drawLine(current_x + arrow_len, yq, current_x + arrow_len - 5, yq - 4)
                    painter.drawLine(current_x + arrow_len, yq, current_x + arrow_len - 5, yq + 4)
                    current_x += step
            else:
                current_x = x2
                while current_x - arrow_len > x1:
                    painter.drawLine(current_x, yq, current_x - arrow_len, yq)
                    painter.drawLine(current_x - arrow_len, yq, current_x - arrow_len + 5, yq - 4)
                    painter.drawLine(current_x - arrow_len, yq, current_x - arrow_len + 5, yq + 4)
                    current_x -= step
            painter.drawText((x1 + x2) // 2 - 5, yq - 10, "q")
            self.q_regions.append((QRectF(x1, yq - 10, x2 - x1, 20), q))

        # Сосредоточенные силы F
        painter.setPen(QPen(Qt.black, 5))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        self.F_regions = []
        arrow_len = 14
        F_y_offset = 55
        for f in self.node_forces:
            node_idx = f['node']-1
            if 0<=node_idx<len(node_positions):
                x_node = offset + node_positions[node_idx]*scale
                yF = y_axis - F_y_offset
                if f['F'] > 0:
                    painter.drawLine(x_node, yF, x_node + arrow_len, yF)
                    painter.drawLine(x_node + arrow_len, yF, x_node + arrow_len -4, yF-3)
                    painter.drawLine(x_node + arrow_len, yF, x_node + arrow_len -4, yF+3)
                else:
                    painter.drawLine(x_node, yF, x_node - arrow_len, yF)
                    painter.drawLine(x_node - arrow_len, yF, x_node - arrow_len +4, yF-3)
                    painter.drawLine(x_node - arrow_len, yF, x_node - arrow_len +4, yF+3)
                painter.drawText(x_node -5, yF - 10, "F")
                self.F_regions.append((QRectF(x_node - 20, yF - 15, 40, 30), f['F']))

# ------------------------
# Главное окно
# ------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Препроцессор стержневой системы")
        self.resize(1400,600)
        self.setStyleSheet("background-color: #d4b483;")
        self.statusBar().showMessage("Готово")

        self.bars = []
        self.supports = []
        self.node_forces = []

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()
        main_layout.addLayout(left_panel,1)
        main_layout.addLayout(right_panel,2)

        # ------------------------
        # Таблицы с кнопками
        # ------------------------
        def make_block(title, table):
            frame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            frame.setStyleSheet("background-color: #99ccff; border:1px solid gray;")
            layout = QVBoxLayout(frame)
            label = QLabel(title)
            layout.addWidget(label)
            layout.addWidget(table)
            btn_layout = QHBoxLayout()
            add_btn = QPushButton("➕ Добавить")
            del_btn = QPushButton("🗑 Удалить")
            for btn in [add_btn, del_btn]:
                btn.setStyleSheet("background-color: #d4b483; font-weight:bold; border:1px solid #888; padding:4px")
            add_btn.clicked.connect(lambda _, t=table: self.add_row(t))
            del_btn.clicked.connect(lambda _, t=table: self.delete_row(t))
            btn_layout.addWidget(add_btn)
            btn_layout.addWidget(del_btn)
            layout.addLayout(btn_layout)
            return frame

        self.bar_table = QTableWidget(0,4)
        self.bar_table.setHorizontalHeaderLabels(["L, м", "A, м²", "E, Па", "σ, Па"])
        self.bar_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.node_table = QTableWidget(0,2)
        self.node_table.setHorizontalHeaderLabels(["Номер узла", "F, Н"])
        self.node_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.bar_load_table = QTableWidget(0,2)
        self.bar_load_table.setHorizontalHeaderLabels(["Номер стержня", "q, Н/м"])
        self.bar_load_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        left_panel.addWidget(make_block("Стержни", self.bar_table))
        left_panel.addWidget(make_block("Сосредоточенные силы", self.node_table))
        left_panel.addWidget(make_block("Погонные нагрузки", self.bar_load_table))

        # Заделка
        self.supp_combo = QComboBox()
        self.supp_combo.addItems(["Не выбрано","Слева","Справа","Обе"])
        self.supp_combo.setStyleSheet("background-color: #d4b483; font-weight:bold;")
        left_panel.addWidget(QLabel("Заделка", alignment=Qt.AlignCenter))
        left_panel.addWidget(self.supp_combo)

        # Кнопка очистки всех данных
        clear_btn = QPushButton("🧹 Очистить всё")
        clear_btn.setStyleSheet("background-color: #d4b483; font-weight:bold; border:1px solid #888; padding:4px")
        clear_btn.clicked.connect(self.clear_all)
        left_panel.addWidget(clear_btn)

        # 🔍 Кнопка восстановления масштаба
        reset_zoom_btn = QPushButton("🔍 Восстановить масштаб")
        reset_zoom_btn.setStyleSheet("background-color: #d4b483; font-weight:bold; border:1px solid #888; padding:4px")
        reset_zoom_btn.clicked.connect(self.reset_zoom)
        left_panel.addWidget(reset_zoom_btn)

        left_panel.addStretch()

        # Строка для отображения ошибок (внизу левой панели)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: darkred; font-weight: bold;")
        self.error_label.setWordWrap(True)
        left_panel.addWidget(self.error_label)

        # Холст
        self.canvas = StructureCanvas(self.bars,self.supports,self.node_forces)
        right_panel.addWidget(self.canvas)

        # Сигналы
        self.bar_table.cellChanged.connect(self.update_visual)
        self.node_table.cellChanged.connect(self.update_visual)
        self.bar_load_table.cellChanged.connect(self.update_visual)
        self.supp_combo.currentIndexChanged.connect(self.update_visual)

        # Меню
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        save_action = file_menu.addAction("💾 Сохранить проект")
        load_action = file_menu.addAction("📂 Загрузить проект")
        save_action.triggered.connect(self.save_project)
        load_action.triggered.connect(self.load_project)

        # Меню "Вид"
        view_menu = menubar.addMenu("Вид")
        self.grid_action = QAction("Показывать сетку", self, checkable=True)
        self.grid_action.setChecked(self.canvas.show_grid)
        self.grid_action.triggered.connect(self.toggle_grid)
        view_menu.addAction(self.grid_action)
    # ------------------------
    # Добавление/удаление строк
    # ------------------------
    def add_row(self, table):
        row = table.rowCount()
        table.insertRow(row)
        for i in range(table.columnCount()):
            table.setItem(row,i,QTableWidgetItem(""))
        self.update_visual()

    def delete_row(self, table):
        rows = table.selectionModel().selectedRows()
        for r in reversed(rows):
            table.removeRow(r.row())
        self.update_visual()

    # ------------------------
    # Сетка
    # ------------------------
    def toggle_grid(self):
        self.canvas.show_grid = not self.canvas.show_grid
        self.canvas.update()
        # синхронизируем галочку в меню
        self.grid_action.setChecked(self.canvas.show_grid)

    # ------------------------
    # Очистка всех данных
    # ------------------------
    def clear_all(self):
        for table in [self.bar_table, self.node_table, self.bar_load_table]:
            table.setRowCount(0)
        self.supp_combo.setCurrentIndex(0)
    
        # Проверяем сетку через меню
        self.grid_action.setChecked(True)
        self.canvas.show_grid = True

        self.error_label.setText("")

        # Обнуляем данные
        self.bars = []
        self.supports = []
        self.node_forces = []

        # Обнуляем данные холста
        self.canvas.bars = []
        self.canvas.supports = []
        self.canvas.node_forces = []
        self.canvas.zoom_factor = 1.0  # сброс масштаба
        self.canvas.update()

        self.statusBar().showMessage("Проект очищен")

    # ------------------------
    # Обновление визуализации
    # ------------------------
    def update_visual(self):
        self.bar_table.blockSignals(True)
        self.node_table.blockSignals(True)
        self.bar_load_table.blockSignals(True)

        # Очистка подсветки
        def clear_error_highlights(table):
            for i in range(table.rowCount()):
                for j in range(table.columnCount()):
                    item = table.item(i, j)
                    if item:
                        item.setBackground(Qt.white)
        def mark_error_cell(item):
            if item:
                item.setBackground(QColor(255, 180, 180))
                item.setToolTip("Некорректное значение")

        for t in [self.bar_table, self.node_table, self.bar_load_table]:
            clear_error_highlights(t)

        errors = []

        # -----------------------
        # СТЕРЖНИ
        # -----------------------
        self.bars = []
        for i in range(self.bar_table.rowCount()):
            L_item = self.bar_table.item(i, 0)
            A_item = self.bar_table.item(i, 1)
            E_item = self.bar_table.item(i, 2)
            sigma_item = self.bar_table.item(i, 3)

            has_data = any(item and item.text().strip() for item in [L_item, A_item, E_item, sigma_item])
            if not has_data:
                continue

            try:
                L = float(L_item.text().strip())
                A = float(A_item.text().strip())
                E = float(E_item.text().strip())
                sigma = float(sigma_item.text().strip())
            except Exception:
                errors.append(f"Стержень {i+1}: некорректные числовые данные")
                for item in [L_item, A_item, E_item, sigma_item]:
                    mark_error_cell(item)
                continue

             # 🔹 Дополнительные физические проверки
            valid = True
            if L <= 0:
                errors.append(f"Стержень {i+1}: длина должна быть > 0")
                mark_error_cell(L_item)
                valid = False
            if A <= 0:
                errors.append(f"Стержень {i+1}: площадь должна быть > 0")
                mark_error_cell(A_item)
                valid = False
            if E <= 0:
                errors.append(f"Стержень {i+1}: модуль упругости должен быть > 0")
                mark_error_cell(E_item)
                valid = False
            if sigma <= 0:
                errors.append(f"Стержень {i+1}: допускаемое напряжение должно быть > 0")
                mark_error_cell(sigma_item)
                valid = False 
            if not valid:
                continue

            self.bars.append({'L': L, 'A': A, 'E': E, 'sigma': sigma, 'q': 0.0})

        if self.bar_load_table.rowCount() > len(self.bars):
            errors.append("⚠️ Количество погонных нагрузок больше числа стержней")

        max_node = len(self.bars) + 1
        for i in range(self.node_table.rowCount()):
            node_item = self.node_table.item(i, 0)
            if node_item and node_item.text().strip().isdigit():
                node_idx = int(node_item.text().strip())
                if node_idx < 1 or node_idx > max_node:
                    errors.append(f"⚠️ Узел {node_idx} вне диапазона (1..{max_node})")

        # -----------------------
        # ПОГОННЫЕ НАГРУЗКИ
        # -----------------------
        for bar in self.bars:
            bar['q'] = 0.0

        assigned_bars = set()

        for i in range(self.bar_load_table.rowCount()):
            item_bar = self.bar_load_table.item(i, 0)
            item_q = self.bar_load_table.item(i, 1)
            if not item_bar or not item_bar.text().strip():
                continue
            if not item_q or not item_q.text().strip():
                continue
            try:
                bar_idx = int(item_bar.text().strip()) - 1
                q_val = float(item_q.text().strip())
                if bar_idx < 0 or bar_idx >= len(self.bars):
                    raise ValueError("номер стержня вне диапазона")
                bar_idx = int(item_bar.text().strip()) - 1
                if bar_idx in assigned_bars:
                    errors.append(f"Стержень {bar_idx+1}: погонная нагрузка уже задана")
                    mark_error_cell(item_bar)
                    mark_error_cell(item_q)
                    continue
                assigned_bars.add(bar_idx)
                self.bars[bar_idx]['q'] = q_val
                if abs(q_val) < 0.001:
                    errors.append(f"Стержень {bar_idx+1}: погонная нагрузка q = 0")
                    mark_error_cell(item_q)
                    continue 
            except Exception:
                errors.append(f"Погонная нагрузка {i+1}: некорректные данные")
                mark_error_cell(item_bar)
                mark_error_cell(item_q)
                continue

        # -----------------------
        # СОСРЕДОТОЧЕННЫЕ СИЛЫ
        # -----------------------
        self.node_forces = []
        occupied_nodes = set()
        max_node = len(self.bars) + 1
        for i in range(self.node_table.rowCount()):
            item_node = self.node_table.item(i, 0)
            item_F = self.node_table.item(i, 1)
            if not item_node or not item_node.text().strip():
                continue
            if not item_F or not item_F.text().strip():
                continue
            try:
                node_idx = int(item_node.text().strip())
                F_val = float(item_F.text().strip())
                if node_idx < 1 or node_idx > len(self.bars) + 1:
                    raise ValueError("номер узла вне диапазона")
                if node_idx in occupied_nodes:
                    raise ValueError(f"узел {node_idx} уже имеет сосредоточенную силу")
                if abs(F_val) < 0.001:
                    errors.append(f"Узел {node_idx}: сосредоточенная сила F = 0")
                    mark_error_cell(item_F)
                    continue

                self.node_forces.append({'node': node_idx, 'F': F_val})
                occupied_nodes.add(node_idx)
            except Exception as e:
                errors.append(f"Сила {i+1}: {e}")
                mark_error_cell(item_node)
                mark_error_cell(item_F)
                continue

        # -----------------------
        # ОПОРЫ
        # -----------------------
        side = self.supp_combo.currentText()
        self.supports = []
        if side != "Не выбрано":
            self.supports.append({'side': side})

        # -----------------------
        # ОБНОВЛЕНИЕ ХОЛСТА
        # -----------------------
        self.canvas.bars = self.bars
        self.canvas.supports = self.supports
        self.canvas.node_forces = self.node_forces
        self.canvas.update()

        # Проверка на наличие стержней
        if not self.bars:
            errors.append("Не задано ни одного стержня")

        # Проверка узлов для сосредоточенных сил
        max_node = len(self.bars) + 1
        for nf in self.node_forces:
            if nf['node'] < 1 or nf['node'] > max_node:
                errors.append(f"Сила задана в несуществующем узле {nf['node']}")

        # -----------------------
        # ОТОБРАЖЕНИЕ ОШИБОК
        # -----------------------
        if errors:
            self.error_label.setText("⚠️ " + "; ".join(errors))
        else:
            self.error_label.setText("")

        # Включаем сигналы обратно
        self.bar_table.blockSignals(False)
        self.node_table.blockSignals(False)
        self.bar_load_table.blockSignals(False)

    # ------------------------
    # Восстановление масштаба
    # ------------------------
    def reset_zoom(self):
        self.canvas.zoom_factor = 1.0
        self.canvas.update()
        self.statusBar().showMessage("Масштаб восстановлен")
    
    # ------------------------
    # Сохранение/загрузка
    # ------------------------
    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить проект", "", "Файлы проекта (*.json)")
        if not path:
            return

        project_data = {
            "bars": self.bars,
            "supports": self.supports,
            "node_forces": self.node_forces,
            "show_grid": self.grid_action.isChecked(),  # 🔹 исправлено
            "support_side": self.supp_combo.currentText()
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "Успех", "Проект успешно сохранён!")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить проект:\n{e}")

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить проект", "", "Файлы проекта (*.json)")
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                project_data = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить проект:\n{e}")
            return
        
        # --- БЛОКИРУЕМ СИГНАЛЫ ---
        self.bar_table.blockSignals(True)
        self.node_table.blockSignals(True)
        self.bar_load_table.blockSignals(True)
            
        # --- ОЧИЩАЕМ ТАБЛИЦЫ ---
        self.bar_table.setRowCount(0)
        self.node_table.setRowCount(0)
        self.bar_load_table.setRowCount(0)

        # --- ЗАГРУЖАЕМ ДАННЫЕ ИЗ ФАЙЛА ---
        loaded_bars = project_data.get("bars", [])
        loaded_supports = project_data.get("supports", [])
        loaded_node_forces = project_data.get("node_forces", [])
        support_side = project_data.get("support_side", "Не выбрано")
        show_grid = project_data.get("show_grid", True)

        print(f"Загружено стержней: {len(loaded_bars)}")
        print(f"Загружено опор: {len(loaded_supports)}")
        print(f"Загружено сил: {len(loaded_node_forces)}")

        # --- ЗАПОЛНЯЕМ ТАБЛИЦУ СТЕРЖНЕЙ ---
        for bar in loaded_bars:
            row = self.bar_table.rowCount()
            self.bar_table.insertRow(row)
            # Заполняем все 4 колонки: L, A, E, sigma
            self.bar_table.setItem(row, 0, QTableWidgetItem(str(bar.get('L', ''))))
            self.bar_table.setItem(row, 1, QTableWidgetItem(str(bar.get('A', ''))))
            self.bar_table.setItem(row, 2, QTableWidgetItem(str(bar.get('E', ''))))
            self.bar_table.setItem(row, 3, QTableWidgetItem(str(bar.get('sigma', ''))))

       # Заполняем таблицу сосредоточенных сил
        for nf in loaded_node_forces:
            row = self.node_table.rowCount()
            self.node_table.insertRow(row)
            self.node_table.setItem(row, 0, QTableWidgetItem(str(nf.get("node", ""))))
            self.node_table.setItem(row, 1, QTableWidgetItem(str(nf.get("F", ""))))
        
        self.node_forces = loaded_node_forces
        self.canvas.node_forces = self.node_forces
        self.canvas.update()

        # Заполняем таблицу погонных нагрузок
        for i, bar in enumerate(loaded_bars):
            q_val = bar.get("q", 0)
            if abs(q_val) > 0.001:
                row = self.bar_load_table.rowCount()
                self.bar_load_table.insertRow(row)
                self.bar_load_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
                self.bar_load_table.setItem(row, 1, QTableWidgetItem(str(q_val)))
        
        self.bars = loaded_bars
        self.canvas.bars = self.bars

        # Восстанавливаем настройку сетки
        show_grid = project_data.get("show_grid", True)
        self.grid_action.setChecked(show_grid)
        self.canvas.show_grid = show_grid

        # Восстанавливаем выбранную опору
        self.supp_combo.setCurrentText(support_side)

        # Обновляем данные опор в памяти
        self.supports = loaded_supports

        # Обновляем холст
        self.canvas.supports = self.supports
        self.canvas.update()

        # --- РАЗБЛОКИРУЕМ СИГНАЛЫ ---
        self.bar_table.blockSignals(False)
        self.node_table.blockSignals(False)
        self.bar_load_table.blockSignals(False)
        
        # --- ОБНОВЛЯЕМ ДАННЫЕ В ПАМЯТИ ---
        self.bars = loaded_bars
        self.supports = loaded_supports
        self.node_forces = loaded_node_forces

        # --- ОБНОВЛЯЕМ ХОЛСТ ---
        self.canvas.bars = self.bars
        self.canvas.supports = self.supports
        self.canvas.node_forces = self.node_forces
        self.canvas.zoom_factor = 1.0  # Сбрасываем масштаб
        self.canvas.update()

        # Обновляем визуализацию после того, как все таблицы заполнены
        self.update_visual()

        QMessageBox.information(self, "Успех", "Проект успешно загружен!")    


# ------------------------
# Запуск
# ------------------------
if __name__=="__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())