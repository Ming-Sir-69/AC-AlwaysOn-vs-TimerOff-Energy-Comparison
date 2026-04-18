"""生成收敛过程图表"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from plot_utils import setup_chinese_font, save_fig

setup_chinese_font()

from binary_search_critical import iterative_converge, run_convergence_study, ThermalParams
from config import UA_DEFAULT, COP_DEGRADATION

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHART_DIR = os.path.join(BASE, 'outputs', 'charts')

scenarios = {
    '低温低惯性': {'T_out': 28, 'T_in_init': 26, 'T_set': 22, 'tau': 2, 'COP': 2.6},
    '中温中惯性': {'T_out': 32, 'T_in_init': 30, 'T_set': 24, 'tau': 6, 'COP': 3.3},
    '高温高惯性': {'T_out': 38, 'T_in_init': 36, 'T_set': 26, 'tau': 12, 'COP': 4.0},
    '极端高温': {'T_out': 40, 'T_in_init': 38, 'T_set': 26, 'tau': 9, 'COP': 3.0},
    '低温高惯性': {'T_out': 28, 'T_in_init': 26, 'T_set': 22, 'tau': 12, 'COP': 3.6},
}

all_results = run_convergence_study(scenarios, UA=UA_DEFAULT, COP_deg=COP_DEGRADATION)

# 覆写：用更少采样点（n_samples=5）让每轮区间缩小更慢，展示更多轮收敛
all_results_v2 = {}
for name, combo in scenarios.items():
    params = ThermalParams(
        T_out=combo['T_out'], T_in_init=combo['T_in_init'],
        T_set=combo['T_set'], tau_k=combo['tau'], COP=combo['COP'],
        UA=UA_DEFAULT, COP_degradation=COP_DEGRADATION
    )
    df = iterative_converge(params, n_samples=5)
    all_results_v2[name] = df
    print(f"  {name}(v2): {len(df)}轮收敛, 临界时长={df.iloc[-1]['t_estimate']:.4f}h")

# 使用v2版本（更多轮次）生成图表
all_results = all_results_v2

# 图1：单工况收敛过程曲线（以中温中惯性为例）
fig, ax1 = plt.subplots(figsize=(12, 7))
df = all_results['中温中惯性']
ax1.plot(df['round'], df['interval_width'], 'o-', color='#2196F3', linewidth=2, markersize=8, label='区间宽度 (h)')
ax1.set_xlabel('迭代轮次', fontsize=12)
ax1.set_ylabel('区间宽度 (h)', fontsize=12, color='#2196F3')
ax1.tick_params(axis='y', labelcolor='#2196F3')

ax2 = ax1.twinx()
ax2.plot(df['round'], df['t_estimate'], 's--', color='#F44336', linewidth=2, markersize=8, label='临界点估计值 (h)')
ax2.set_ylabel('临界点估计值 (h)', fontsize=12, color='#F44336')
ax2.tick_params(axis='y', labelcolor='#F44336')

# 标注收敛轮次
if len(df) > 0:
    final = df.iloc[-1]
    ax1.annotate(f'{len(df)}轮收敛\n精度={final["interval_width"]:.4f}h',
                xy=(final['round'], final['interval_width']),
                xytext=(final['round']+0.5, final['interval_width']*1.5),
                fontsize=11, color='#4CAF50', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#4CAF50'))

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labels1+labels2, loc='upper right')
ax1.set_title('迭代收敛过程（中温中惯性工况）', fontsize=14)
ax1.grid(True, alpha=0.3)
save_fig(fig, '收敛过程曲线_1200x750.png', CHART_DIR)

# 图2：多工况收敛对比
fig, ax = plt.subplots(figsize=(12, 7))
colors = ['#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#C62828']
for idx, (name, df) in enumerate(all_results.items()):
    ax.plot(df['round'], df['interval_width'], 'o-', color=colors[idx],
            linewidth=2, markersize=6, label=name)
ax.set_xlabel('迭代轮次', fontsize=12)
ax.set_ylabel('区间宽度 (h)', fontsize=12)
ax.set_title('多工况收敛速度对比', fontsize=14)
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_yscale('log')  # 对数坐标更清晰
save_fig(fig, '多工况收敛对比_1200x750.png', CHART_DIR)

print("收敛图表生成完成")
