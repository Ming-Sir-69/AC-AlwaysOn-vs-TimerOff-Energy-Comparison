<picture>
  <source media="(prefers-color-scheme: dark)" srcset="readme-assets/header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="readme-assets/header-light.svg">
  <img alt="空调常开还是定时关？ · ✦ EricMingle69" src="readme-assets/header-light.svg" width="100%">
</picture>

<p align="center">
  <a href="README.md">简体中文</a> · <a href="README.en.md">English</a> · <a href="PERSONAL-NOTICE.md">✦ EricMingle69</a>
</p>

# 空调常开还是定时关？

比较“持续恒温”与“外出关机、返回重启”的能耗研究。
项目将牛顿冷却模型、田口正交实验与 ANOVA 分析连接到图表和报告。

## 先看结果，再读假设

| 目的 | 入口 |
| --- | --- |
| 理解数学模型和引用 | [公式与来源索引](docs/07_公式汇总与来源索引.md) |
| 了解开发与复现流程 | [README_DEV.md](README_DEV.md) |
| 查看交互图表 | [能耗对比仪表盘](interactive/能耗对比交互仪表盘.html) |
| 阅读结果 | [图表](outputs/charts/) · [Excel](空调能耗仿真结果.xlsx) · [综合报告](空调能耗对比研究_综合分析报告.pptx) |

仪表盘是 HTML 文件，可下载到本地后用浏览器打开。

## 在独立副本中复现

准备 Python 与 pip，在仓库根目录执行：

```sh
cd src
python3 -m pip install -r requirements.txt
python3 run_simulation.py
```

入口会重新生成 CSV、图表和根目录 Excel；运行前保留需要比较的旧产出。
Python 最低版本、系统字体及完整环境组合仍需结合开发文档核对。

## 从源码继续研究

[主入口](src/run_simulation.py)负责仿真流程；[配置](src/config.py)定义参数；[热模型](src/thermal_model.py)描述模型计算。
报告中的节能结论属于特定假设和参数下的模型结果，不能直接当作任意房间或设备的实测承诺。

## 使用范围

解释结果时请同时给出环境、边界条件、参数与实测验证范围。
仓库未提供覆盖原代码与研究资料的 LICENSE；引用和再分发需分别确认来源与许可。

---

文档维护：**✦ EricMingle69** · [Ming-Sir-69](https://github.com/Ming-Sir-69)  
[个人标识、许可与权限说明](PERSONAL-NOTICE.md) · 明暗页眉随 GitHub 主题自动切换。
