# processor.py
import numpy as np


def calculate_structure(window, n_points_per_bar_table=5, n_points_per_bar_graph=100):
    """
    Расчёт конструкции методом перемещений на основе таблиц окна.
    """
    # --- Считываем таблицу стержней (L, A, E) ---
    bars = []
    for row in range(window.table_1.table.rowCount()):
        try:
            L_item = window.table_1.table.item(row, 0)
            A_item = window.table_1.table.item(row, 1)
            E_item = window.table_1.table.item(row, 2)
            if not (L_item and A_item and E_item):
                continue
            L = float(L_item.text())
            A = float(A_item.text())
            E = float(E_item.text())
            bars.append((L, A, E))
        except Exception:
            continue

    n_bars = len(bars)
    if n_bars == 0:
        raise ValueError("Не заданы стержни для расчёта.")
    n_nodes = n_bars + 1

    # --- Распределённые нагрузки (q на стержень) ---
    q_loads = {}
    for row in range(window.table_2.table.rowCount()):
        try:
            bar_item = window.table_2.table.item(row, 0)
            q_item = window.table_2.table.item(row, 1)
            if not bar_item or not q_item:
                continue
            bar_num = int(float(bar_item.text()))
            q = float(q_item.text())
            if 1 <= bar_num <= n_bars:
                q_loads[bar_num] = q
        except Exception:
            continue

    # --- Сосредоточенные нагрузки (F на узел) ---
    F_loads = {}
    for row in range(window.table_3.table.rowCount()):
        try:
            node_item = window.table_3.table.item(row, 0)
            F_item = window.table_3.table.item(row, 1)
            if not node_item or not F_item:
                continue
            node = int(float(node_item.text()))
            F = float(F_item.text())
            if 1 <= node <= n_nodes:
                F_loads[node] = F
        except Exception:
            continue

    # --- Сборка глобальной матрицы жёсткости K и вектора нагрузок b ---
    K = np.zeros((n_nodes, n_nodes), dtype=float)
    b = np.zeros(n_nodes, dtype=float)

    for i, (L, A, E) in enumerate(bars):
        k = E * A / L
        K[i, i] += k
        K[i, i + 1] -= k
        K[i + 1, i] -= k
        K[i + 1, i + 1] += k

        q = q_loads.get(i + 1, 0.0)
        b[i] += q * L / 2.0
        b[i + 1] += q * L / 2.0

    # добавляем сосредоточенные силы
    for node, F in F_loads.items():
        b[node - 1] += F

    # --- Граничные условия (заделки) ---
    # --- Граничные условия (заделки) ---
    left_fixed = getattr(window, "left_fixed", False)
    right_fixed = getattr(window, "right_fixed", False)
    fixed_dofs = []
    if left_fixed:
        fixed_dofs.append(0)
    if right_fixed:
        fixed_dofs.append(n_nodes - 1)
    free_dofs = [i for i in range(n_nodes) if i not in fixed_dofs]

    # ИСПРАВЛЕНИЕ: Если обе опоры закреплены, НЕ освобождаем правую, а используем статически неопределимый расчет
    if len(free_dofs) == 0 and n_nodes > 1:
        # Для статически неопределимой системы используем другой подход
        # Оставляем обе опоры закрепленными, но решаем специальным методом
        print("Статически неопределимая система: обе опоры закреплены")
        # В этом случае все перемещения должны быть нулевыми
        U = np.zeros(n_nodes, dtype=float)

        # Но усилия могут быть ненулевыми из-за распределенных нагрузок
        # Рассчитываем усилия отдельно для статически неопределимой системы
    else:
        # Статически определимая система - решаем как обычно
        if len(free_dofs) == 0:
            raise ValueError("Нет свободных степеней свободы для расчёта.")

        # Решаем систему для свободных степеней свободы
        K_ff = K[np.ix_(free_dofs, free_dofs)]
        b_f = b[free_dofs]

        try:
            U_f = np.linalg.solve(K_ff, b_f)
        except np.linalg.LinAlgError:
            U_f = np.linalg.pinv(K_ff) @ b_f

        # Собираем полный вектор перемещений
        U = np.zeros(n_nodes, dtype=float)
        for idx, dof in enumerate(free_dofs):
            U[dof] = U_f[idx]
        for dof in fixed_dofs:
            U[dof] = 0.0

    # --- Усилия и напряжения "в узле" / средние по стержню ---
    N_list = []
    sigma_list = []
    for i, (L, A, E) in enumerate(bars):
        q = q_loads.get(i + 1, 0.0)
        U1 = U[i]
        U2 = U[i + 1]
        N_val = E * A / L * (U2 - U1) + q * (L / 2.0)
        sigma_val = N_val / A if A != 0 else 0.0
        N_list.append(N_val)
        sigma_list.append(sigma_val)

    # --- Подробная таблица: ключевые точки + n_points_per_bar точек на каждом стержне ---
    table_data = []
    total_x = 0.0

    for i, (L, A, E) in enumerate(bars, start=1):
        q = q_loads.get(i, 0.0)
        U1 = U[i - 1]
        U2 = U[i]
        n_pts = max(2, int(n_points_per_bar_table))
        step = L / (n_pts - 1)

        for j in range(0, n_pts):
            x_local = j * step
            x_global = total_x + x_local

            try:
                correction = (q / (2.0 * E * A)) * (x_local * (L - x_local)) if (E != 0 and A != 0) else 0.0
            except Exception:
                correction = 0.0

            u_linear = U1 * (1.0 - x_local / L) + U2 * (x_local / L)
            u_x = u_linear + correction

            N_x = E * A / L * (U2 - U1) + q * (L / 2.0 - x_local)
            sigma_x = N_x / A if A != 0 else 0.0

            table_data.append({
                "bar": i,
                "x": float(round(x_global, 8)),
                "u": float(u_x),
                "N": float(N_x),
                "sigma": float(sigma_x)
            })

        total_x += L

    # --- Дополнительная таблица для графиков (много точек) ---
    graph_data = []
    total_x = 0.0

    for i, (L, A, E) in enumerate(bars, start=1):
        q = q_loads.get(i, 0.0)
        U1 = U[i - 1]
        U2 = U[i]
        n_pts = max(2, int(n_points_per_bar_graph))
        step = L / (n_pts - 1)

        for j in range(0, n_pts):
            x_local = j * step
            x_global = total_x + x_local

            try:
                correction = (q / (2.0 * E * A)) * (x_local * (L - x_local)) if (E != 0 and A != 0) else 0.0
            except Exception:
                correction = 0.0

            u_linear = U1 * (1.0 - x_local / L) + U2 * (x_local / L)
            u_x = u_linear + correction

            N_x = E * A / L * (U2 - U1) + q * (L / 2.0 - x_local)
            sigma_x = N_x / A if A != 0 else 0.0

            graph_data.append({
                "bar": i,
                "x": float(round(x_global, 8)),
                "u": float(u_x),
                "N": float(N_x),
                "sigma": float(sigma_x)
            })

        total_x += L

    return {
        "U": U,
        "N": N_list,
        "sigma": sigma_list,
        "table": table_data,
        "graph_table": graph_data
    }


def calculate_reactions(window):
    """Вычисляет реакции в заделках после выполнения calculate_structure."""
    try:
        # считываем таблицу стержней
        bars = []
        for row in range(window.table_1.table.rowCount()):
            try:
                L = float(window.table_1.table.item(row, 0).text())
                A = float(window.table_1.table.item(row, 1).text())
                E = float(window.table_1.table.item(row, 2).text())
                bars.append((L, A, E))
            except Exception:
                continue

        n_nodes = len(bars) + 1
        if n_nodes <= 1:
            return {}

        K = np.zeros((n_nodes, n_nodes))
        b = np.zeros(n_nodes)

        # распределённые нагрузки
        q_loads = {}
        for row in range(window.table_2.table.rowCount()):
            try:
                bar_num = int(window.table_2.table.item(row, 0).text())
                q = float(window.table_2.table.item(row, 1).text())
                q_loads[bar_num] = q
            except Exception:
                continue

        # сборка матрицы жёсткости
        for i, (L, A, E) in enumerate(bars):
            k = E * A / L
            K[i, i] += k
            K[i, i + 1] -= k
            K[i + 1, i] -= k
            K[i + 1, i + 1] += k

            q = q_loads.get(i + 1, 0.0)
            b[i] += q * L / 2
            b[i + 1] += q * L / 2

        # сосредоточенные нагрузки
        for row in range(window.table_3.table.rowCount()):
            try:
                node = int(window.table_3.table.item(row, 0).text())
                F = float(window.table_3.table.item(row, 1).text())
                b[node - 1] += F
            except Exception:
                continue

        U = window.proc_results["U"]
        R = np.dot(K, U) - b

        left_fixed = getattr(window, "left_fixed", False)
        right_fixed = getattr(window, "right_fixed", False)

        reactions = {}
        if left_fixed:
            reactions[1] = R[0]
        if right_fixed:
            reactions[n_nodes] = R[-1]

        return reactions
    except Exception:
        return {}