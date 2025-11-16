# processor.py
import numpy as np

class RodStructureProcessor:
    def __init__(self, bars, node_forces, supports):
        self.bars = bars
        self.node_forces = node_forces
        self.supports = supports
        self.n_nodes = len(bars) + 1

    def assemble_global_K(self):
        K = np.zeros((self.n_nodes, self.n_nodes), dtype=float)
        for i, bar in enumerate(self.bars):
            L, A, E = bar['L'], bar['A'], bar['E']
            k = A * E / L
            k_local = np.array([[k, -k], [-k, k]])
            n1, n2 = i, i + 1
            K[n1:n2+1, n1:n2+1] += k_local
        return K

    def assemble_global_F(self):
        F = np.zeros(self.n_nodes, dtype=float)
        for f in self.node_forces:
            node_idx = f['node'] - 1
            F[node_idx] += f['F']
        for i, bar in enumerate(self.bars):
            q = bar.get('q', 0)
            L = bar['L']
            if abs(q) > 0.0001:
                Fe1 = q * L / 2
                Fe2 = q * L / 2
                F[i] += Fe1
                F[i+1] += Fe2
        return F

    def apply_supports(self, K, F):
        fixed = []
        support_values = []
        
        if self.supports:
            s = self.supports[0]['side']
            if s == "Слева":
                fixed.append(0)
                support_values.append(0.0)
            elif s == "Справа":
                fixed.append(self.n_nodes - 1)
                support_values.append(0.0)
            elif s == "Обе":
                fixed.extend([0, self.n_nodes - 1])
                support_values.extend([0.0, 0.0])
        
        if fixed:
            free_dofs = [i for i in range(self.n_nodes) if i not in fixed]
            K_ff = K[np.ix_(free_dofs, free_dofs)]
            F_f = F[free_dofs]
            
            # Решаем систему только для свободных степеней свободы
            U_f = np.linalg.solve(K_ff, F_f)
            
            # Собираем полный вектор перемещений
            U = np.zeros(self.n_nodes)
            U[free_dofs] = U_f
            U[fixed] = support_values
            
            return U
        else:
            return np.linalg.solve(K, F)

    def solve(self):
        K = self.assemble_global_K()
        F = self.assemble_global_F()
        U = self.apply_supports(K, F)
        return U

    def calculate_internal_forces_coefficients(self, U):
        """
        Правильный расчет коэффициентов для продольных сил
        """
        N_coeffs = []
        for i, bar in enumerate(self.bars):
            L, A, E = bar['L'], bar['A'], bar['E']
            q = bar.get('q', 0)
            
            # Продольная сила от деформации
            delta_U = U[i+1] - U[i]
            N_elastic = (A * E / L) * delta_U
            
            # Продольная сила от погонной нагрузки
            # Для стержня с погонной нагрузкой q:
            # N(x) = N0 - q*x
            N0 = N_elastic + (q * L / 2)
            N1 = -q
            
            N_coeffs.append([N0, N1])
        
        return N_coeffs

    def calculate_displacement_coefficients(self, U):
        """
        ПРАВИЛЬНЫЙ расчет коэффициентов для перемещений
        Основывается на точном решении дифференциального уравнения
        """
        U_coeffs = []
        for i, bar in enumerate(self.bars):
            L, A, E = bar['L'], bar['A'], bar['E']
            q = bar.get('q', 0)
            
            # Узловые перемещения
            u_i = U[i]      # Перемещение в начале стержня
            u_j = U[i+1]    # Перемещение в конце стержня
            
            # Точное решение для стержня с погонной нагрузкой:
            # u(x) = C1 + C2*x - (q*x²)/(2*E*A)
            # Граничные условия:
            # u(0) = u_i, u(L) = u_j
            
            # Из u(0) = u_i => C1 = u_i
            
            # Из u(L) = u_j:
            # u_j = u_i + C2*L - (q*L²)/(2*E*A)
            # => C2 = (u_j - u_i)/L + (q*L)/(2*E*A)
            
            C1 = u_i
            C2 = (u_j - u_i)/L + (q * L) / (2 * E * A)
            
            # Таким образом:
            # u(x) = u_i + [(u_j - u_i)/L + (q*L)/(2*E*A)]*x - (q*x²)/(2*E*A)
            
            # Коэффициенты для представления u(x) = u0 + u1*x + u2*x²
            u0 = C1                              # = u_i
            u1 = C2                              # = (u_j - u_i)/L + (q*L)/(2*E*A)
            u2 = -q / (2 * E * A)                # коэффициент при x²
            
            U_coeffs.append([u0, u1, u2])
        
        return U_coeffs

    def calculate_element_results(self, U):
        """
        Дополнительный метод для расчета результатов по элементам
        Аналогично рабочему процессору
        """
        element_results = []
        for i, bar in enumerate(self.bars):
            L, A, E = bar['L'], bar['A'], bar['E']
            
            # Перемещения узлов
            u_i = U[i]
            u_j = U[i+1]
            
            # Деформация
            strain = (u_j - u_i) / L
            
            # Напряжение
            stress = E * strain
            
            # Продольная сила (в середине стержня, без учета погонной нагрузки)
            axial_force = stress * A
            
            element_results.append({
                'element_id': i + 1,
                'axial_force': axial_force,
                'strain': strain,
                'stress': stress
            })
        
        return element_results