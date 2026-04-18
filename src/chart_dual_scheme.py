"""
多维度双方案对比散点图模块

生成空调方案A（恒温常开）与方案B（出门关机）的多维度对比图表。

图表清单（共10张）：
  A系列 — 单因子 vs 耗电量（5张）:
    A1: 出门时间 vs 耗电量（L50数据）
    A2: 室外温度 vs 耗电量（L50数据）
    A3: 建筑热惯性τ vs 耗电量（L50数据）
    A4: COP vs 耗电量（L50数据）
    A5: 目标温度 vs 耗电量（L50数据）

  B系列 — E_A vs E_B 二维散点图（3张）:
    B1: L25数据的 E_A vs E_B
    B2: L50数据的 E_A vs E_B
    B3: 临界区加密数据的 E_A vs E_B

  C系列 — 临界点分析（2张）:
    C1: 二分法临界点热力图（T_out x tau）
    C2: 二分法临界点 vs COP和目标温度（多子图）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize
from matplotlib import cm

# 导入项目绘图工具（自动配置中文字体）
from plot_utils import save_fig, COLORS


# ═══════════════════════════════════════════════════════════════
# A系列：单因子 vs 耗电量散点图
# ═══════════════════════════════════════════════════════════════

def plot_scheme_comparison_scatter(df, x_col, x_label, title, output_name, chart_dir):
    """
    通用双方案对比散点图

    蓝色散点+拟合线：方案A（恒温常开）
    红色散点+拟合线：方案B（出门关机）
    绿色星标：临界点（两线交点）

    参数:
        df (pd.DataFrame): 实验结果DataFrame，需包含 x_col, E_A, E_B 列
        x_col (str): X轴因子列名
        x_label (str): X轴标签
        title (str): 图表标题
        output_name (str): 输出文件名
        chart_dir (str): 输出目录

    返回:
        str: 保存后的文件路径
    """
    fig, ax = plt.subplots(figsize=(12, 7))

    # 散点绘制
    ax.scatter(df[x_col], df['E_A'], c=COLORS['scheme_a'], alpha=0.6, s=50,
               label='方案A（恒温常开）')
    ax.scatter(df[x_col], df['E_B'], c=COLORS['scheme_b'], alpha=0.6, s=50,
               label='方案B（出门关机）')

    # 对排序后的数据进行三次多项式拟合
    x_vals = df[x_col].values
    sort_idx = np.argsort(x_vals)
    x_sorted = x_vals[sort_idx]
    E_A_sorted = df['E_A'].values[sort_idx]
    E_B_sorted = df['E_B'].values[sort_idx]

    coef_a = np.polyfit(x_sorted, E_A_sorted, 3)
    coef_b = np.polyfit(x_sorted, E_B_sorted, 3)

    x_fit = np.linspace(x_sorted.min(), x_sorted.max(), 100)
    ax.plot(x_fit, np.polyval(coef_a, x_fit), color=COLORS['scheme_a'],
            linewidth=2, label='方案A拟合线')
    ax.plot(x_fit, np.polyval(coef_b, x_fit), color=COLORS['scheme_b'],
            linewidth=2, label='方案B拟合线')

    # 计算并标注临界点（三次多项式交点，数值求解）
    diff_coefs = np.poly1d(coef_a) - np.poly1d(coef_b)
    roots = diff_coefs.r  # 所有可能的根
    # 筛选在数据范围内的实数根
    real_roots = [r.real for r in roots if abs(r.imag) < 1e-6 and x_sorted.min() <= r.real <= x_sorted.max()]
    if real_roots:
        x_crit = real_roots[0]
        y_crit = np.poly1d(coef_a)(x_crit)
        ax.scatter([x_crit], [y_crit], c='#2ca02c', s=200, marker='*',
                   zorder=5, label=f'临界点={x_crit:.1f}h')
        ax.annotate(f'临界点={x_crit:.1f}h', (x_crit, y_crit),
                    textcoords="offset points", xytext=(10, 10),
                    fontsize=11, color='#2ca02c', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color='#2ca02c'))

    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel('日均耗电量 (kWh)', fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')

    return save_fig(fig, output_name, chart_dir)


# ═══════════════════════════════════════════════════════════════
# B系列：E_A vs E_B 二维散点图
# ═══════════════════════════════════════════════════════════════

def plot_ea_vs_eb_scatter(df, title, output_name, chart_dir):
    """
    E_A vs E_B 二维散点图（含对角临界线）

    红点 = 关机反而费电 (E_B > E_A)
    蓝点 = 关机省电 (E_B < E_A)
    黑色虚线 = 等耗电临界线 (E_A = E_B)

    参数:
        df (pd.DataFrame): 实验结果DataFrame，需包含 E_A, E_B 列
        title (str): 图表标题
        output_name (str): 输出文件名
        chart_dir (str): 输出目录

    返回:
        str: 保存后的文件路径
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    # 对角线（临界线 E_A = E_B）
    max_val = max(df['E_A'].max(), df['E_B'].max()) * 1.1
    ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.5, linewidth=1.5,
            label='等耗电临界线')

    # 按方案优劣着色
    for _, row in df.iterrows():
        color = COLORS['scheme_b'] if row['E_B'] > row['E_A'] else COLORS['scheme_a']
        ax.scatter(row['E_A'], row['E_B'], c=color, alpha=0.7, s=60,
                   edgecolors='white', linewidth=0.5)

    # 自定义图例
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['scheme_b'],
               markersize=10, label='关机反而费电 (E_B > E_A)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['scheme_a'],
               markersize=10, label='关机省电 (E_B < E_A)'),
        Line2D([0], [0], linestyle='--', color='black', alpha=0.5,
               label='等耗电临界线 (E_A = E_B)'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

    ax.set_xlabel('方案A耗电 E_A (kWh)', fontsize=12)
    ax.set_ylabel('方案B耗电 E_B (kWh)', fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')

    return save_fig(fig, output_name, chart_dir)


# ═══════════════════════════════════════════════════════════════
# C系列：临界点分析图表
# ═══════════════════════════════════════════════════════════════

def plot_critical_heatmap(df_critical, chart_dir):
    """
    二分法临界点热力图

    X轴：室外温度 T_out
    Y轴：建筑热惯性 tau
    颜色：临界出门时长 t_critical
    含等高线标注

    参数:
        df_critical (pd.DataFrame): 二分法临界点结果
        chart_dir (str): 输出目录

    返回:
        str: 保存后的文件路径
    """
    # 创建透视表
    pivot = df_critical.pivot_table(
        values='t_critical', index='tau', columns='T_out', aggfunc='mean'
    )

    fig, ax = plt.subplots(figsize=(12, 7))

    # 热力图
    X, Y = np.meshgrid(pivot.columns, pivot.index)
    Z = pivot.values
    cs = ax.contourf(X, Y, Z, levels=20, cmap='YlOrRd', alpha=0.85)

    # 等高线标注
    contours = ax.contour(X, Y, Z, levels=10, colors='black', linewidths=0.5, alpha=0.6)
    ax.clabel(contours, inline=True, fontsize=8, fmt='%.1fh')

    plt.colorbar(cs, ax=ax, label='临界出门时长 (h)')

    ax.set_xlabel('室外温度 T_out (\u00b0C)', fontsize=12)
    ax.set_ylabel('建筑热惯性 \u03c4 (h)', fontsize=12)
    ax.set_title('二分法临界点热力图（T_out \u00d7 \u03c4）', fontsize=14)
    ax.grid(True, alpha=0.2, linestyle='--')

    return save_fig(fig, 'chart_C1_critical_heatmap.png', chart_dir)


def plot_critical_vs_factors(df_critical, chart_dir):
    """
    二分法临界点 vs COP和目标温度（多子图）

    展示不同因子对临界时长的影响：
    - 子图1：T_out vs t_critical（按COP分组）
    - 子图2：tau vs t_critical（按T_set分组）
    - 子图3：COP vs t_critical（按T_out分组）
    - 子图4：T_set vs t_critical（按tau分组）

    参数:
        df_critical (pd.DataFrame): 二分法临界点结果
        chart_dir (str): 输出目录

    返回:
        str: 保存后的文件路径
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    # 子图1：T_out vs t_critical（按COP分组）
    ax = axes[0]
    for cop_val in sorted(df_critical['COP'].unique()):
        subset = df_critical[df_critical['COP'] == cop_val]
        # 对每个T_out取平均
        grouped = subset.groupby('T_out')['t_critical'].mean()
        ax.plot(grouped.index, grouped.values, 'o-', label=f'COP={cop_val}',
                linewidth=2, markersize=6)
    ax.set_xlabel('室外温度 T_out (\u00b0C)', fontsize=11)
    ax.set_ylabel('临界出门时长 (h)', fontsize=11)
    ax.set_title('室外温度 vs 临界时长（按COP分组）', fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='--')

    # 子图2：tau vs t_critical（按T_set分组）
    ax = axes[1]
    for t_set_val in sorted(df_critical['T_set'].unique()):
        subset = df_critical[df_critical['T_set'] == t_set_val]
        grouped = subset.groupby('tau')['t_critical'].mean()
        ax.plot(grouped.index, grouped.values, 'o-', label=f'T_set={t_set_val}\u00b0C',
                linewidth=2, markersize=6)
    ax.set_xlabel('建筑热惯性 \u03c4 (h)', fontsize=11)
    ax.set_ylabel('临界出门时长 (h)', fontsize=11)
    ax.set_title('热惯性 vs 临界时长（按T_set分组）', fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='--')

    # 子图3：COP vs t_critical（按T_out分组）
    ax = axes[2]
    for t_out_val in sorted(df_critical['T_out'].unique()):
        subset = df_critical[df_critical['T_out'] == t_out_val]
        grouped = subset.groupby('COP')['t_critical'].mean()
        ax.plot(grouped.index, grouped.values, 'o-', label=f'T_out={t_out_val}\u00b0C',
                linewidth=2, markersize=6)
    ax.set_xlabel('COP', fontsize=11)
    ax.set_ylabel('临界出门时长 (h)', fontsize=11)
    ax.set_title('COP vs 临界时长（按T_out分组）', fontsize=12)
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3, linestyle='--')

    # 子图4：T_set vs t_critical（按tau分组）
    ax = axes[3]
    for tau_val in sorted(df_critical['tau'].unique()):
        subset = df_critical[df_critical['tau'] == tau_val]
        grouped = subset.groupby('T_set')['t_critical'].mean()
        ax.plot(grouped.index, grouped.values, 'o-', label=f'\u03c4={tau_val}h',
                linewidth=2, markersize=6)
    ax.set_xlabel('目标温度 T_set (\u00b0C)', fontsize=11)
    ax.set_ylabel('临界出门时长 (h)', fontsize=11)
    ax.set_title('目标温度 vs 临界时长（按\u03c4分组）', fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='--')

    fig.suptitle('二分法临界点 — 多因子影响分析', fontsize=15, y=1.02)
    plt.tight_layout()

    return save_fig(fig, 'chart_C2_critical_vs_factors.png', chart_dir)


# ═══════════════════════════════════════════════════════════════
# 总入口函数
# ═══════════════════════════════════════════════════════════════

def generate_all_dual_scheme_charts(df_l25, df_l50, df_cz, df_critical, chart_dir):
    """
    生成所有双方案对比图表（共10张）

    参数:
        df_l25 (pd.DataFrame): L25实验结果
        df_l50 (pd.DataFrame): L50实验结果
        df_cz (pd.DataFrame): 临界区加密实验结果
        df_critical (pd.DataFrame): 二分法临界点搜索结果
        chart_dir (str): 图表输出目录
    """
    print("\n  [A系列] 单因子 vs 耗电量散点图...")

    # A1: 出门时间 vs 耗电量（L50数据）
    plot_scheme_comparison_scatter(
        df_l50, 't_off', '出门时间 (h)',
        '出门时间 vs 日均耗电量（L50实验）',
        'chart_A1_toff_vs_energy.png', chart_dir
    )

    # A2: 室外温度 vs 耗电量（L50数据）
    plot_scheme_comparison_scatter(
        df_l50, 'T_out', '室外温度 (\u00b0C)',
        '室外温度 vs 日均耗电量（L50实验）',
        'chart_A2_Tout_vs_energy.png', chart_dir
    )

    # A3: 建筑热惯性τ vs 耗电量（L50数据）
    plot_scheme_comparison_scatter(
        df_l50, 'tau', '建筑热惯性 \u03c4 (h)',
        '建筑热惯性 vs 日均耗电量（L50实验）',
        'chart_A3_tau_vs_energy.png', chart_dir
    )

    # A4: COP vs 耗电量（L50数据）
    plot_scheme_comparison_scatter(
        df_l50, 'COP', 'COP',
        'COP vs 日均耗电量（L50实验）',
        'chart_A4_COP_vs_energy.png', chart_dir
    )

    # A5: 目标温度 vs 耗电量（L50数据）
    plot_scheme_comparison_scatter(
        df_l50, 'T_set', '目标温度 (\u00b0C)',
        '目标温度 vs 日均耗电量（L50实验）',
        'chart_A5_Tset_vs_energy.png', chart_dir
    )

    print("  [B系列] E_A vs E_B 二维散点图...")

    # B1: L25数据的 E_A vs E_B
    plot_ea_vs_eb_scatter(
        df_l25, 'E_A vs E_B 二维散点图（L25实验）',
        'chart_B1_EAvsEB_L25.png', chart_dir
    )

    # B2: L50数据的 E_A vs E_B
    plot_ea_vs_eb_scatter(
        df_l50, 'E_A vs E_B 二维散点图（L50实验）',
        'chart_B2_EAvsEB_L50.png', chart_dir
    )

    # B3: 临界区加密数据的 E_A vs E_B
    plot_ea_vs_eb_scatter(
        df_cz, 'E_A vs E_B 二维散点图（临界区加密）',
        'chart_B3_EAvsEB_critical_zone.png', chart_dir
    )

    print("  [C系列] 临界点分析图表...")

    # C1: 二分法临界点热力图
    plot_critical_heatmap(df_critical, chart_dir)

    # C2: 二分法临界点 vs COP和目标温度
    plot_critical_vs_factors(df_critical, chart_dir)

    print(f"  全部10张图表已保存至: {chart_dir}/")


if __name__ == '__main__':
    # 独立测试：使用已有数据生成图表
    print("=" * 50)
    print("  双方案对比图表 — 独立测试")
    print("=" * 50)

    from config import DATA_DIR, CHART_DIR

    # 尝试加载已有数据
    data_files = {
        'L25': os.path.join(DATA_DIR, 'L25_base_results.csv'),
        'L50': os.path.join(DATA_DIR, 'L50_enhanced_results.csv'),
        'CZ': os.path.join(DATA_DIR, 'critical_zone_dense_results.csv'),
        'critical': os.path.join(DATA_DIR, 'critical_points_binary_search.csv'),
    }

    dfs = {}
    for name, path in data_files.items():
        if os.path.exists(path):
            dfs[name] = pd.read_csv(path)
            print(f"  已加载 {name}: {len(dfs[name])} 行")
        else:
            print(f"  警告: 未找到 {name} 数据文件 {path}")

    if all(k in dfs for k in ['L25', 'L50', 'CZ', 'critical']):
        generate_all_dual_scheme_charts(
            dfs['L25'], dfs['L50'], dfs['CZ'], dfs['critical'], CHART_DIR
        )
    else:
        print("\n缺少必要数据文件，请先运行 run_simulation.py")
