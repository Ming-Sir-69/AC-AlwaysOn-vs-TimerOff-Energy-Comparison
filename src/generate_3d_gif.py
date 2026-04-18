"""
3D旋转GIF生成脚本 — 节能比例三维曲面旋转演示

基于 thermal_model.py 的热力学模型，直接计算节能比例曲面，
生成60帧旋转动画GIF。
"""

import sys
import os
import io
import numpy as np

# 确保可以导入同目录下的 thermal_model
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from PIL import Image

from thermal_model import ThermalParams, energy_scheme_a, energy_scheme_b

# ── 中文字体配置 ──
matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# ── 路径配置 ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
os.makedirs(ASSETS_DIR, exist_ok=True)

# ── 模型参数 ──
T_set = 24
tau = 6
COP = 3.3
UA = 0.1
COP_deg = 0.6

# ── 构建网格 ──
T_out_range = np.linspace(26, 40, 30)
t_off_range = np.linspace(0.5, 16, 30)

X, Y = np.meshgrid(T_out_range, t_off_range)
Z = np.zeros_like(X)

print("正在计算节能比例曲面...")
for i in range(X.shape[0]):
    for j in range(X.shape[1]):
        params = ThermalParams(
            T_out=X[i, j],
            T_in_init=X[i, j] - 2,
            T_set=T_set,
            tau_k=tau,
            COP=COP,
            UA=UA,
            COP_degradation=COP_deg
        )
        E_A = energy_scheme_a(params)
        E_B = energy_scheme_b(params, t_off=Y[i, j])
        Z[i, j] = (E_A - E_B) / E_A * 100 if E_A > 0 else 0

print(f"  X (室外温度): {T_out_range[0]}~{T_out_range[-1]} °C, {len(T_out_range)} 点")
print(f"  Y (外出时长): {t_off_range[0]}~{t_off_range[-1]} h, {len(t_off_range)} 点")
print(f"  Z (节能比例): {Z.min():.2f}% ~ {Z.max():.2f}%")

# ── 生成60帧旋转动画 ──
NUM_FRAMES = 60
frames = []
print(f"\n开始生成 {NUM_FRAMES} 帧3D旋转动画...")

for idx in range(NUM_FRAMES):
    angle = idx * 6  # 每帧旋转6度，共360度

    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')

    surf = ax.plot_surface(X, Y, Z, cmap='RdYlGn', alpha=0.85, edgecolor='none')

    ax.set_xlabel('室外温度 (°C)')
    ax.set_ylabel('外出时长 (h)')
    ax.set_zlabel('节能比例 (%)')
    ax.set_title('节能比例三维曲面 — 空调常开 vs 定时关', fontsize=14, fontweight='bold', pad=15)

    ax.view_init(elev=25, azim=angle)

    # 保存帧到内存
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    frames.append(Image.open(buf).copy())
    plt.close(fig)
    buf.close()

    if (idx + 1) % 10 == 0:
        print(f"  已生成 {idx + 1}/{NUM_FRAMES} 帧")

print(f"  全部 {NUM_FRAMES} 帧生成完毕")

# ── 合成GIF ──
output_path = os.path.join(ASSETS_DIR, '节能比例三维曲面旋转演示.gif')
print(f"\n正在合成GIF: {output_path}")
frames[0].save(
    output_path,
    save_all=True,
    append_images=frames[1:],
    duration=100,  # 10fps
    loop=0         # 无限循环
)

# ── 输出文件信息 ──
gif_size = os.path.getsize(output_path)
print(f"\n最终输出:")
print(f"  文件: {output_path}")
print(f"  大小: {gif_size / 1024 / 1024:.2f} MB")
print(f"  帧数: {NUM_FRAMES}")
print(f"  帧间隔: 100ms (10fps)")
print("\nGIF生成成功!")
