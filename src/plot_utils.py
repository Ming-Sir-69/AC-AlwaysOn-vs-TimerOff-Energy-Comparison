"""
绘图工具模块

提供 matplotlib 中文字体配置、配色方案和图表保存功能。
"""

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os


def setup_chinese_font():
    """
    配置 matplotlib 中文字体

    依次尝试以下策略:
    1. 在已注册字体中查找常见中文字体
    2. 在系统字体目录中查找字体文件并注册
    """
    # 尝试查找可用的中文字体
    chinese_fonts = [
        'SimHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC',
        'Noto Sans SC', 'Source Han Sans SC', 'AR PL UMing CN',
        'Microsoft YaHei', 'PingFang SC', 'Heiti SC',
    ]
    available = [f.name for f in fm.fontManager.ttflist]

    for font_name in chinese_fonts:
        if font_name in available:
            matplotlib.rcParams['font.sans-serif'] = (
                [font_name] + matplotlib.rcParams['font.sans-serif']
            )
            matplotlib.rcParams['axes.unicode_minus'] = False
            print(f"[字体] 使用已注册字体: {font_name}")
            return

    # 如果没有找到中文字体，尝试从系统字体目录加载
    font_paths = [
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    ]

    for fp in font_paths:
        if os.path.exists(fp):
            fm.fontManager.addfont(fp)
            prop = fm.FontProperties(fname=fp)
            font_name = prop.get_name()
            matplotlib.rcParams['font.sans-serif'] = (
                [font_name] + matplotlib.rcParams['font.sans-serif']
            )
            matplotlib.rcParams['axes.unicode_minus'] = False
            print(f"[字体] 从文件加载字体: {fp} -> {font_name}")
            return

    # 最终回退：尝试下载字体
    font_dir = os.path.expanduser('~/.fonts')
    os.makedirs(font_dir, exist_ok=True)

    print("[字体] 警告: 未找到中文字体，中文标签可能无法正常显示")
    print("[字体] 建议安装: apt-get install fonts-wqy-microhei")
    matplotlib.rcParams['axes.unicode_minus'] = False


# 在模块导入时自动配置
setup_chinese_font()

# 配色方案
COLORS = {
    'scheme_a': '#2196F3',       # 蓝色 - 方案A（常开）
    'scheme_b': '#F44336',       # 红色 - 方案B（关机）
    'critical': '#FF9800',       # 橙色 - 临界区
    'levels': [                  # 多水平配色
        '#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#C62828', '#00796B'
    ],
    'background': '#FAFAFA',
    'grid': '#E0E0E0',
    'text': '#212121',
    'accent': '#FF5722',
}


def save_fig(fig, filename, chart_dir, dpi=150):
    """
    保存图表到指定目录

    参数:
        fig (matplotlib.figure.Figure): 图表对象
        filename (str): 文件名（含扩展名，如 'main_effects.png'）
        chart_dir (str): 保存目录路径
        dpi (int): 分辨率，默认 150

    返回:
        str: 保存后的文件完整路径
    """
    os.makedirs(chart_dir, exist_ok=True)
    filepath = os.path.join(chart_dir, filename)
    fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"[图表] 已保存: {filepath}")
    return filepath


if __name__ == '__main__':
    # 测试中文字体配置
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.linspace(0, 10, 100)
    ax.plot(x, np.sin(x), color=COLORS['scheme_a'], label='方案A（常开）')
    ax.plot(x, np.cos(x), color=COLORS['scheme_b'], label='方案B（关机）')
    ax.set_title('中文字体测试：空调耗电对比')
    ax.set_xlabel('出门时长（小时）')
    ax.set_ylabel('耗电量（kWh）')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 保存到临时目录
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_charts')
    save_fig(fig, 'font_test.png', test_dir)
    print("字体测试图表已生成")
