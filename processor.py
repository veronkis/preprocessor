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
                Fe = q * L / 2
                F[i] += Fe
                F[i+1] += Fe
        return F

    def apply_supports(self, K, F):
        fixed = []
        if self.supports:
            s = self.supports[0]['side']
            if s == "Слева":
                fixed.append(0)
            elif s == "Справа":
                fixed.append(self.n_nodes - 1)
            elif s == "Обе":
                fixed.extend([0, self.n_nodes - 1])
        for idx in fixed:
            K[idx, :] = 0
            K[:, idx] = 0
            K[idx, idx] = 1
            F[idx] = 0
        return K, F

    def solve(self):
        K = self.assemble_global_K()
        F = self.assemble_global_F()
        K, F = self.apply_supports(K, F)
        try:
            U = np.linalg.solve(K, F)
        except np.linalg.LinAlgError as e:
            raise RuntimeError(f"Невозможно решить систему: {e}")
        return U

    def calculate_internal_forces_coefficients(self, U):
        """
        Вычисление коэффициентов для продольных сил в стержнях
        Возвращает список [N0, N1] для каждого стержня, где N(x) = N0 + N1*x
        """
        N_coeffs = []
        for i, bar in enumerate(self.bars):
            L, A, E = bar['L'], bar['A'], bar['E']
            q = bar.get('q', 0)
            
            # Усилие от деформации
            delta_U = U[i+1] - U[i]
            N_elastic = (A * E / L) * delta_U
            
            # Усилие от погонной нагрузки
            N_q = q * L / 2
            
            # Коэффициенты для N(x) = N0 + N1*x
            N0 = N_elastic - N_q  # Усилие в начале стержня
            N1 = -q  # Производная от погонной нагрузки
            
            N_coeffs.append([N0, N1])
        
        return N_coeffs

    def calculate_displacement_coefficients(self, U):
        """
        Вычисление коэффициентов для перемещений в стержнях
        Возвращает список [u0, u1, u2] для каждого стержня, где u(x) = u0 + u1*x + u2*x^2
        """
        U_coeffs = []
        for i, bar in enumerate(self.bars):
            L, A, E = bar['L'], bar['A'], bar['E']
            q = bar.get('q', 0)
            
            # Коэффициенты для u(x)
            u0 = U[i]  # Перемещение в начале стержня
            
            # Линейная составляющая
            delta_U = U[i+1] - U[i]
            u1 = delta_U / L - (q * L) / (2 * A * E)
            
            # Квадратичная составляющая от погонной нагрузки
            u2 = q / (2 * A * E)
            
            U_coeffs.append([u0, u1, u2])
        
        return U_coeffs
