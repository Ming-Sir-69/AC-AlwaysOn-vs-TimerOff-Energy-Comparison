"""
正交表生成模块

提供 L25(5^6)、L50(5^6) 正交表以及临界区加密补充实验设计。
"""

import numpy as np
from itertools import product


def get_L25():
    """
    基础 L25(5^6) 正交表

    返回:
        numpy array, shape=(25, 6), 值为 0-4（索引），对应 5 个水平。
    """
    L25_STANDARD = np.array([
        [0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1], [0, 2, 2, 2, 2, 2],
        [0, 3, 3, 3, 3, 3], [0, 4, 4, 4, 4, 4],
        [1, 0, 1, 2, 3, 4], [1, 1, 2, 3, 4, 0], [1, 2, 3, 4, 0, 1],
        [1, 3, 4, 0, 1, 2], [1, 4, 0, 1, 2, 3],
        [2, 0, 2, 4, 1, 3], [2, 1, 3, 0, 2, 4], [2, 2, 4, 1, 3, 0],
        [2, 3, 0, 2, 4, 1], [2, 4, 1, 3, 0, 2],
        [3, 0, 3, 1, 4, 2], [3, 1, 4, 2, 0, 3], [3, 2, 0, 3, 1, 4],
        [3, 3, 1, 4, 2, 0], [3, 4, 2, 0, 3, 1],
        [4, 0, 4, 3, 2, 1], [4, 1, 0, 4, 3, 2], [4, 2, 1, 0, 4, 3],
        [4, 3, 2, 1, 0, 4], [4, 4, 3, 2, 1, 0],
    ])
    return L25_STANDARD.copy()


def verify_orthogonality(array, q):
    """
    验证正交性：任意两列的所有水平对出现次数相等。

    参数:
        array: numpy array, shape=(n, k)
        q: 每个因子的水平数

    返回:
        (bool, str): (是否正交, 详细信息)
    """
    n, k = array.shape
    expected = n / (q * q)

    for c1 in range(k):
        for c2 in range(c1 + 1, k):
            # 统计每对水平组合的出现次数
            pair_counts = {}
            for i in range(n):
                pair = (int(array[i, c1]), int(array[i, c2]))
                pair_counts[pair] = pair_counts.get(pair, 0) + 1

            counts = list(pair_counts.values())
            if len(counts) != q * q:
                return False, f"列 {c1} 与列 {c2}: 水平对数量 {len(counts)} != {q*q}"

            if not all(abs(c - expected) < 1e-9 for c in counts):
                return False, (f"列 {c1} 与列 {c2}: 水平对出现次数不等 "
                               f"(期望 {expected}, 实际 {set(counts)})")

    return True, f"正交性验证通过 (n={n}, k={k}, q={q}, 期望每对出现 {expected} 次)"


def get_L50():
    """
    升级 L50(5^6) 正交表

    构造方法：使用两个 L25 表拼接，第二个 L25 的每列加 2（模 5），
    然后验证正交性。如果简单拼接不正交，则使用穷举搜索寻找合适的偏移量。

    返回:
        numpy array, shape=(50, 6), 值为 0-4（索引），对应 5 个水平。
    """
    L25 = get_L25()

    # 尝试所有可能的偏移量 (0-4)，寻找使拼接结果正交的偏移
    for offset in range(5):
        part1 = L25
        part2 = (L25 + offset) % 5
        candidate = np.vstack([part1, part2])

        is_ortho, msg = verify_orthogonality(candidate, 5)
        if is_ortho:
            print(f"[L50] 使用偏移量 offset={offset} 构造成功: {msg}")
            return candidate

    # 如果所有单偏移都不行，尝试对不同列使用不同偏移
    # 穷举搜索：对6列各选一个偏移量
    print("[L50] 单一偏移量无法满足正交性，尝试多列独立偏移穷举搜索...")
    from itertools import product as iprod

    for offsets in iprod(range(5), repeat=6):
        part2 = (L25 + np.array(offsets)) % 5
        candidate = np.vstack([L25, part2])
        is_ortho, msg = verify_orthogonality(candidate, 5)
        if is_ortho:
            print(f"[L50] 多列偏移 {offsets} 构造成功: {msg}")
            return candidate

    # 最终回退：直接返回偏移2的版本并发出警告
    print("[L50] 警告: 未能找到严格正交的 L50 表，使用 offset=2 的近似版本")
    part2 = (L25 + 2) % 5
    return np.vstack([L25, part2])


def get_critical_zone_supplementary():
    """
    临界区加密补充实验 — 16组全因子实验

    因子与水平:
        A (出门时间 t_off): [7, 8, 9, 10, 12] → 5 个水平
        B (室外温度 T_out): [30, 32, 34, 36] → 4 个水平
        C (室内初始温 T_in_init): [28] → 固定
        D (目标温度 T_set): [24] → 固定
        E (热惯性 tau): [4, 6, 9] → 3 个水平
        F (COP): [3.0, 3.6] → 2 个水平

    使用 itertools.product 生成所有组合，然后筛选出合理的子集（约 16-20 组），
    优先覆盖 A x B 的组合。

    返回:
        numpy array, shape=(n, 6), 每行对应一组实验参数
        dict, 因子水平映射信息
    """
    A_levels = [7, 8, 9, 10, 12]       # 出门时间 (h)
    B_levels = [30, 32, 34, 36]        # 室外温度 (°C)
    C_levels = [28]                     # 室内初始温度 (°C), 固定
    D_levels = [24]                     # 目标温度 (°C), 固定
    E_levels = [4, 6, 9]               # 热惯性时间常数 (h)
    F_levels = [3.0, 3.6]              # 能效比 COP

    # 生成全因子组合
    all_combos = list(product(A_levels, B_levels, C_levels, D_levels, E_levels, F_levels))
    print(f"[临界区] 全因子组合总数: {len(all_combos)}")

    # 筛选策略：优先覆盖 A x B 的所有 5x4=20 种组合
    # 对每个 A x B 组合，选择中间水平的 E 和 F
    ab_pairs = set()
    selected = []

    # 第一轮：为每个 A x B 组合选一组代表性实验（E=中间值, F=中间值）
    for combo in all_combos:
        a, b, c, d, e, f = combo
        ab_key = (a, b)
        if ab_key not in ab_pairs:
            ab_pairs.add(ab_key)
            selected.append(combo)

    # 第二轮：补充不同 E 和 F 水平的组合，使总数达到约 16-20 组
    # 优先为 A 的中间水平 (8, 9, 10) 补充 E 和 F 的变体
    priority_a = [8, 9, 10]
    remaining = [c for c in all_combos if c not in selected]

    for combo in remaining:
        if len(selected) >= 20:
            break
        a, b, c, d, e, f = combo
        if a in priority_a:
            # 检查是否已有相同 A, B, E, F 的组合
            existing_keys = {(s[0], s[1], s[4], s[5]) for s in selected}
            if (a, b, e, f) not in existing_keys:
                selected.append(combo)

    # 如果还不够，继续补充
    for combo in remaining:
        if len(selected) >= 20:
            break
        if combo not in selected:
            selected.append(combo)

    result = np.array(selected)
    print(f"[临界区] 筛选后实验组数: {len(result)}")

    factor_info = {
        'A': {'name': '出门时间', 'unit': 'h', 'levels': A_levels},
        'B': {'name': '室外温度', 'unit': '°C', 'levels': B_levels},
        'C': {'name': '室内初始温度', 'unit': '°C', 'levels': C_levels},
        'D': {'name': '目标温度', 'unit': '°C', 'levels': D_levels},
        'E': {'name': '热惯性τ', 'unit': 'h', 'levels': E_levels},
        'F': {'name': 'COP', 'unit': '', 'levels': F_levels},
    }

    return result, factor_info


if __name__ == '__main__':
    # 测试 L25
    L25 = get_L25()
    print(f"L25 shape: {L25.shape}")
    ok, msg = verify_orthogonality(L25, 5)
    print(f"L25 正交性: {msg}")

    # 测试 L50
    L50 = get_L50()
    print(f"L50 shape: {L50.shape}")
    ok50, msg50 = verify_orthogonality(L50, 5)
    print(f"L50 正交性: {msg50}")

    # 测试临界区补充
    cz_array, cz_info = get_critical_zone_supplementary()
    print(f"临界区补充 shape: {cz_array.shape}")
    print(f"因子信息: {list(cz_info.keys())}")
