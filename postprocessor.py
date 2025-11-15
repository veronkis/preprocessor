import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from PySide6.QtWidgets import QFileDialog, QMessageBox
import matplotlib
matplotlib.use('QtAgg')

class PostProcessor:
    def __init__(self, kernels, N, U):
        """
        Инициализация постпроцессора
        kernels - список стержней
        N - коэффициенты для продольных сил
        U - коэффициенты для перемещений
        """
        self.kernels = kernels
        self.N = N
        self.U = U
        self.total_length = sum(kernel['L'] for kernel in kernels)
        
    def calculate_section_results(self, x_global):
        """
        Расчёт всех компонент НДС в конкретном сечении
        Возвращает словарь с значениями
        """
        x_current = 0
        for i, kernel in enumerate(self.kernels):
            if x_global <= x_current + kernel['L']:
                x_local = x_global - x_current
                
                # Расчёт Nx
                Nx = self.N[i][0] + x_local * self.N[i][1]
                
                # Расчёт σx
                sigma_x = Nx / kernel['A']
                
                # Расчёт Ux
                Ux = self.U[i][0] + x_local * self.U[i][1] + (x_local**2) * self.U[i][2]
                
                return {
                    'position': round(x_global, 4),
                    'Nx': round(Nx, 4),
                    'sigma_x': round(sigma_x, 4),
                    'Ux': round(Ux, 4),
                    'element': i+1
                }
            x_current += kernel['L']
        
        return None

    def create_results_table(self):
        """
        Создание общей таблицы результатов
        """
        results = []
        
        for i, kernel in enumerate(self.kernels):
            # 8 точек на каждый стержень
            x_points = np.linspace(0, kernel['L'], 8)
            
            for x_local in x_points:
                x_global = sum(kernel['L'] for kernel in self.kernels[:i]) + x_local
                
                Nx = self.N[i][0] + x_local * self.N[i][1]
                sigma_x = Nx / kernel['A']
                Ux = self.U[i][0] + x_local * self.U[i][1] + (x_local**2) * self.U[i][2]
                
                results.append([
                    round(x_global, 4),
                    i + 1,
                    round(x_local, 4),
                    round(Nx, 4),
                    round(sigma_x, 4),
                    round(Ux, 4)
                ])
        
        df = pd.DataFrame(results, columns=[
            'Глобальная координата', 'Элемент', 'Локальная координата',
            'Nx', 'σx', 'Ux'
        ])
        
        return df

    def display_results_table(self):
        """
        Отображение таблицы результатов
        """
        df = self.create_results_table()
        
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_visible(False)
        ax.axis('off')
        ax.axis('tight')
        
        table = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            loc='center',
            cellLoc='center',
            bbox=[0, 0, 1, 1]
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1.2, 1.5)
        
        plt.title("Результаты расчёта компонент НДС", pad=20)
        plt.tight_layout()
        plt.show()
        
        return df

    def plot_epures(self):
        """
        Построение эпюр компонент НДС
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))
        
        # Подготовка данных для графиков
        x_global = []
        Nx_values = []
        sigma_values = []
        Ux_values = []
        
        current_position = 0
        for i, kernel in enumerate(self.kernels):
            x_local = np.linspace(0, kernel['L'], int(100 * kernel['L'] / self.total_length))
            
            for x in x_local:
                global_x = current_position + x
                x_global.append(global_x)
                
                Nx = self.N[i][0] + x * self.N[i][1]
                Nx_values.append(Nx)
                sigma_values.append(Nx / kernel['A'])
                Ux_values.append(self.U[i][0] + x * self.U[i][1] + (x**2) * self.U[i][2])
            
            current_position += kernel['L']
        
        # Эпюра Nx
        ax1.plot(x_global, Nx_values, 'r-', linewidth=2)
        ax1.set_title('Эпюра продольных сил Nx')
        ax1.set_xlabel('Длина конструкции, м')
        ax1.set_ylabel('Nx, Н')
        ax1.grid(True)
        ax1.fill_between(x_global, Nx_values, alpha=0.3, color='red')
        
        # Эпюра σx
        ax2.plot(x_global, sigma_values, 'b-', linewidth=2)
        ax2.set_title('Эпюра нормальных напряжений σx')
        ax2.set_xlabel('Длина конструкции, м')
        ax2.set_ylabel('σx, Па')
        ax2.grid(True)
        ax2.fill_between(x_global, sigma_values, alpha=0.3, color='blue')
        
        # Эпюра Ux
        ax3.plot(x_global, Ux_values, 'g-', linewidth=2)
        ax3.set_title('Эпюра перемещений Ux')
        ax3.set_xlabel('Длина конструкции, м')
        ax3.set_ylabel('Ux, м')
        ax3.grid(True)
        ax3.fill_between(x_global, Ux_values, alpha=0.3, color='green')
        
        plt.tight_layout()
        plt.show()

    def plot_combined_epures(self):
        """
        Построение совмещённых эпюр на конструкции
        """
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Подготовка данных
        x_global = []
        Nx_values = []
        sigma_values = []
        Ux_values = []
        
        current_position = 0
        for i, kernel in enumerate(self.kernels):
            x_local = np.linspace(0, kernel['L'], int(100 * kernel['L'] / self.total_length))
            
            for x in x_local:
                global_x = current_position + x
                x_global.append(global_x)
                
                Nx = self.N[i][0] + x * self.N[i][1]
                Nx_values.append(Nx)
                sigma_values.append(Nx / kernel['A'])
                Ux_values.append(self.U[i][0] + x * self.U[i][1] + (x**2) * self.U[i][2])
            
            current_position += kernel['L']
        
        # Нормализация для совмещения на одном графике
        if max(Nx_values) != min(Nx_values):
            Nx_norm = (Nx_values - np.min(Nx_values)) / (np.max(Nx_values) - np.min(Nx_values))
        else:
            Nx_norm = [0.5] * len(Nx_values)
            
        if max(sigma_values) != min(sigma_values):
            sigma_norm = (sigma_values - np.min(sigma_values)) / (np.max(sigma_values) - np.min(sigma_values))
        else:
            sigma_norm = [0.5] * len(sigma_values)
            
        if max(Ux_values) != min(Ux_values):
            Ux_norm = (Ux_values - np.min(Ux_values)) / (np.max(Ux_values) - np.min(Ux_values))
        else:
            Ux_norm = [0.5] * len(Ux_values)
        
        # Совмещённый график
        ax.plot(x_global, Nx_norm, 'r-', linewidth=2, label='Nx (норм.)')
        ax.plot(x_global, sigma_norm, 'b-', linewidth=2, label='σx (норм.)')
        ax.plot(x_global, Ux_norm, 'g-', linewidth=2, label='Ux (норм.)')
        
        ax.set_title('Совмещённые эпюры компонент НДС на конструкции')
        ax.set_xlabel('Длина конструкции, м')
        ax.set_ylabel('Нормализованные значения')
        ax.legend()
        ax.grid(True)
        
        # Разметка стержней
        current_pos = 0
        for i, kernel in enumerate(self.kernels):
            ax.axvline(x=current_pos, color='k', linestyle='--', alpha=0.5)
            ax.text(current_pos + kernel['L']/2, -0.1, f'Стержень {i+1}', 
                   ha='center', transform=ax.get_xaxis_transform())
            current_pos += kernel['L']
        ax.axvline(x=current_pos, color='k', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        plt.show()

    def generate_report(self, main_window):
        """
        Формирование полного отчёта
        """
        # Создание таблицы результатов
        df = self.create_results_table()
        
        # Расчёт экстремальных значений
        max_Nx = df['Nx'].max()
        min_Nx = df['Nx'].min()
        max_sigma = df['σx'].max()
        min_sigma = df['σx'].min()
        max_Ux = df['Ux'].max()
        min_Ux = df['Ux'].min()
        
        # Сохранение в файл
        filename, _ = QFileDialog.getSaveFileName(main_window, 'Сохранить отчёт', filter='*.csv')
        if filename:
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            # Добавление метаинформации в файл
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("ОТЧЁТ ПО РАСЧЁТУ СТЕРЖНЕВОЙ СИСТЕМЫ\n")
                f.write("=====================================\n")
                f.write(f"Количество элементов: {len(self.kernels)}\n")
                f.write(f"Общая длина конструкции: {self.total_length:.4f} м\n")
                f.write(f"Максимальная продольная сила: {max_Nx:.4f} Н\n")
                f.write(f"Минимальная продольная сила: {min_Nx:.4f} Н\n")
                f.write(f"Максимальное напряжение: {max_sigma:.4f} Па\n")
                f.write(f"Минимальное напряжение: {min_sigma:.4f} Па\n")
                f.write(f"Максимальное перемещение: {max_Ux:.6f} м\n")
                f.write(f"Минимальное перемещение: {min_Ux:.6f} м\n")
                f.write("=====================================\n\n")
            
            # Добавление таблицы результатов
            df.to_csv(filename, mode='a', index=False, encoding='utf-8')
            
            QMessageBox.information(main_window, "Успех", f"Отчёт сохранён в файл:\n{filename}")
            return filename
        return None

    def analyze_results(self):
        """
        Анализ результатов расчёта
        """
        df = self.create_results_table()
        
        max_sigma_abs = df['σx'].abs().max()
        dangerous_sections = df[df['σx'].abs() == max_sigma_abs][['Глобальная координата', 'σx']].values.tolist()
        
        analysis = {
            'max_Nx': df['Nx'].max(),
            'min_Nx': df['Nx'].min(),
            'max_sigma': df['σx'].max(),
            'min_sigma': df['σx'].min(),
            'max_Ux': df['Ux'].max(),
            'min_Ux': df['Ux'].min(),
            'dangerous_sections': dangerous_sections,
            'max_abs_sigma': max_sigma_abs
        }
        
        print("АНАЛИЗ РЕЗУЛЬТАТОВ:")
        print(f"Максимальная продольная сила: {analysis['max_Nx']:.4f} Н")
        print(f"Минимальная продольная сила: {analysis['min_Nx']:.4f} Н")
        print(f"Максимальное напряжение: {analysis['max_sigma']:.4f} Па")
        print(f"Минимальное напряжение: {analysis['min_sigma']:.4f} Па")
        print(f"Максимальное перемещение: {analysis['max_Ux']:.6f} м")
        print(f"Минимальное перемещение: {analysis['min_Ux']:.6f} м")
        print(f"Максимальное по модулю напряжение: {analysis['max_abs_sigma']:.4f} Па")
        print(f"Опасные сечения: {analysis['dangerous_sections']}")
        
        return analysis

    def check_strength(self, bars):
        """
        Проверка прочности по допускаемым напряжениям
        """
        df = self.create_results_table()
        max_stress = df['σx'].abs().max()
        
        results = []
        for i, bar in enumerate(bars):
            allowable_stress = bar['sigma']
            actual_max_stress = df[df['Элемент'] == i+1]['σx'].abs().max()
            safety_factor = allowable_stress / actual_max_stress if actual_max_stress > 0 else float('inf')
            is_safe = actual_max_stress <= allowable_stress
            
            results.append({
                'element': i+1,
                'allowable_stress': allowable_stress,
                'actual_max_stress': actual_max_stress,
                'safety_factor': safety_factor,
                'is_safe': is_safe
            })
            
            print(f"Стержень {i+1}:")
            print(f"  Допускаемое напряжение: {allowable_stress:.2f} Па")
            print(f"  Максимальное напряжение: {actual_max_stress:.2f} Па")
            print(f"  Запас прочности: {safety_factor:.2f}")
            print(f"  Состояние: {'БЕЗОПАСНО' if is_safe else 'ОПАСНО!'}")
        
        return results