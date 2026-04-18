# 空调"恒温常开" vs "出门关机"能耗对比研究

## 研究问题

空调一直开着维持恒定温度，与回家开、出门关，哪种方式更省电？

考虑多重维度和不同数值区间，是否存在一个**临界外出时长**，使得两种方式耗电量一致。

## 研究方法

1. **数学建模**：牛顿冷却定律 + 稳态热负荷方程 + COP衰减模型
2. **田口正交实验设计**：L25(5^6) 基础 + L50(5^6) 升级 + 临界区加密补充
3. **Python仿真**：热力学模型 + 能耗对比 + 主效应分析 + ANOVA

## 项目结构

```
├── docs/                  # 数学公式与理论文档（附权威来源URL）
├── outputs/
│   ├── svg_out_clean/     # 公式SVG（矢量）
│   ├── png_out_clean/     # 公式PNG（位图）
│   └── charts/            # 仿真图表
├── src/                   # Python仿真脚本
│   ├── config.py          # 全局配置
│   ├── orthogonal_array.py # 正交表生成
│   ├── thermal_model.py   # 热力学模型
│   ├── energy_simulator.py # 仿真引擎
│   ├── taguchi_analyzer.py # 田口分析
│   ├── plot_utils.py      # 绘图工具
│   ├── export_excel.py    # Excel导出
│   └── run_simulation.py  # 主入口
├── data/                  # CSV数据文件
└── academic_trail/        # Perplexity已有成果
```

## 运行方式

```bash
cd src
pip install -r requirements.txt
python run_simulation.py
```

## 核心结论（预研）

- 存在临界外出时长，取决于隔热性能、COP、温差等因素
- 大样本平均临界点约 **9.4小时**
- 极端工况下（40℃+大热惯性），临界点可达 **14小时以上**
- 短暂外出（<30分钟）不应关机
