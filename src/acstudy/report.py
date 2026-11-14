"""Generate the public report from the confirmed manual-restart scenarios."""
from pathlib import Path
import numpy as np
from .plots import NAMES,TYPES
from .model import POLICIES
from .analysis import ROOM_AREAS
from .presentation import baseline,STRATA,PUBLIC_POLICIES,paired_values
from .confirmed import CASES

ROOMS={'base':'约22.94㎡（3.7×6.2米）','tile80':'0.8米砖对照26.66㎡（4.3×6.2米）','upper':'口述上限29.76㎡（4.8×6.2米）'}
INTRO = '厂区宿舍有条规定：一到上班时间就断电，周六周日也一样，到了休息时间才能再开。我想让他们取消这条规定。光说热没人听，只好去算：一直开着和到点关掉，到底哪个更费电。\n\n说实话挺无奈的。想吹上空调，得先做一个研究。'

SLOTS={'morning':'10:30–10:40','noon':'12:00–13:30','afternoon':'15:00–15:10'}

def qi(values,d=1):
    a=np.asarray(values,dtype=float);a=a[np.isfinite(a)]
    if not len(a):return '无适用日'
    lo,mid,hi=np.quantile(a,[.05,.5,.95])
    return f'{mid:.{d}f}（{lo:.{d}f}–{hi:.{d}f}）'


def write_report(root,mc,sobol,config):
    root=Path(root);full_mc=mc;mc=baseline(mc);base=mc[mc.room=='base']
    lines=['# 宿舍供电时刻、空调电量与温湿度','',
      INTRO,'',scene_intro(),'',*opening(base),'',
      '**以下为中位数（5–95%情景范围），不是实测置信区间。** 三种房间、两种空调、七条规则配对计算，人员日历和气象共用。','',
      '## 先看结果','',
      '取消强制断电，并不等于全天开空调。更实际的对照是保留整间供电，人走自己关空调、人回再开；休息日有人时保持供电。','']
    for kind in TYPES:
        cur=base[(base.kind==kind)&(base.policy=='cut_all')].sort_values('sample')
        own=base[(base.kind==kind)&(base.policy=='manual')].sort_values('sample')
        lines.append(f'- {TYPES[kind]}：现行规定相对一直开节电 {qi(cur.saving_pct)}%；改成自主开关，整季相对现行规定多用 {qi(own.energy_kWh.to_numpy()-cur.energy_kWh.to_numpy(),0)} kWh。')
    lines+=['','**工作日两次10分钟供电时无人，空调不会自己开，因此没有空调制冷恢复。** 午休只有回来才开；下班也要到家后手动开。提前恢复电源不等于提前制冷，这一点会改变规则之间的取舍。','',
      '## 已确认与仍在假设的条件','',
      '- 实际四人间、住4人。家具是两张高架床、两张落地床、四张L形桌、四只双门铁柜。房间工作尺寸约3.7×6.2×2.8米，依据过道横向三块砖加两排家具、家具占满长墙及口述，仍非实测；净宽3.6–4.4、净长6.0–6.4、净高2.6–3.2米作为情景范围。床长约占3.3格，场景判读地砖更可能0.6米，把握中低，仍未实测。0.8米砖的4.3×6.2米及口述上限4.8×6.2米另列对照。',
      '- 每天含休息日均按四段断电：08:00–10:30、10:40–12:00、13:30–15:00、15:10–17:30。其间供电10、90、10分钟；17:30至次日08:00持续供电。断电时包括壁挂风扇在内的全部用电设备停转；这不等于门窗漏风或自然换气为零。',
      '- 来电后空调必须手动重新打开。工作日两次短休无人，不开机；午休返回概率基准0.5、情景0–1，固定随机日历共享。返回日假设12:00后5分钟抵达（范围0–15分钟）；下班后30分钟抵达，即基准18:00（延迟范围0–60分钟）。到家或休息日来电后，再等1分钟手动开机（范围0–5分钟）。返回日按4人同时回来简化，实际可能只有部分人回。',
      '- 阳台外墙有两扇磨砂窗及半玻璃半金属门。两窗净玻璃各0.495×1.085米，门上半净玻璃0.830×0.9975米，净玻璃合计1.902075㎡；1.6–2.4㎡作为照片推算与遮框误差的情景范围，非测量置信区间。门下半不透明金属板按0.945㎡、框按0.4638375㎡单列，均不透射太阳辐射；框不再叠加算成玻璃。金属板及框的传热、太阳吸收是未测假设，范围见方法和参数表。已确认二楼、非转角、阳台朝西，方位270°±30°；两侧长墙邻室，另一端走廊，总层数未知，二楼按非顶层处理。下午两段断电与西晒重合，中间15:00只有10分钟供电。',
      '- 四套家具有效热容暂取0.5 MJ/K、范围0.2–1.0 MJ/K，质量未测，未采用未经测量的精确质量。内墙地顶有效热容按面积密度缩放：约130 kJ/(㎡·K)，情景52–313 kJ/(㎡·K)；物性按面积密度给定；家具热容不再乘四，也不随房间面积重复放大。',
      '- 基准空调制冷量3500 W，情景2600–5000 W，机型与性能均未核；所有房间对照使用相同机组参数。气象为深圳SWERA与广州CSWD典型年，各64个参数样本（默认共128），不是实际厂区天气。广州原始RH有38小时为101%，保留原文件，换算时按100%并保存清单。','',
      *building_table(full_mc),'## 电量：一直开、现行规定、自主开关','',
      '制冷季假设五月至十月连续184天，起始星期一；不从典型年拼接年份推断真实星期。单日电量是季内工作日平均，整季含休息日；只计空调，不含风扇等其他电器电量。下表使用二楼按非顶层、单面外墙、西向±30°的128个配对样本（两站各64组），对应主房间的尺寸包络（21.60–28.16㎡），不是只固定22.94㎡的结果；时间曲线和确定算例另用22.94㎡基准。均匀抽样是试算选择，不把“地砖更可能0.6米”强行量化为概率。','',
      '|空调|一直开：工作日日均 kWh|现行规定：工作日日均 kWh|一直开：整季 kWh|现行规定：整季 kWh|节电比例 %|',
      '|---|---|---|---|---|---|']
    for kind in TYPES:
        a=base[(base.kind==kind)&(base.policy=='always')];b=base[(base.kind==kind)&(base.policy=='cut_all')]
        lines.append(f'|{TYPES[kind]}|{qi(a.workday_kWh)}|{qi(b.workday_kWh)}|{qi(a.energy_kWh,0)}|{qi(b.energy_kWh,0)}|{qi(b.saving_pct)}|')
    lines+=['','|空调|现行规定整季 kWh|自主开关整季 kWh|自主开关比现行规定多用 kWh|来电自启假设整季 kWh|',
            '|---|---|---|---|---|']
    for kind in TYPES:
        a=base[(base.kind==kind)&(base.policy=='cut_all')].sort_values('sample')
        b=base[(base.kind==kind)&(base.policy=='manual')].sort_values('sample')
        c=base[(base.kind==kind)&(base.policy=='auto_restore')]
        lines.append(f'|{TYPES[kind]}|{qi(a.energy_kWh,0)}|{qi(b.energy_kWh,0)}|{qi(b.energy_kWh.to_numpy()-a.energy_kWh.to_numpy(),0)}|{qi(c.energy_kWh,0)}|')
    lines+=['','差值按同一情景配对计算，中位数分别统计，不一定等于两列中位数相减。来电自启只是功能相反的假想对照，不是本人机组的真实行为；其人员日历不变。','',
      '![电量](figures/01_energy.png)','',
      '## 两次10分钟、午休90分钟究竟能恢复多少','',
      '温差为供电前温度减去窗口结束温度，正数是降温、负数是升温。RH受温度与水量共同影响；含湿量下降才表示空气里的水蒸气减少。每个情景先对季内同类日取平均，再跨情景给范围。','',
      '|日型|空调|供电窗口|开始室温 °C|结束室温 °C|降温 °C|开始RH %|结束RH %|含湿量下降 g/kg|',
      '|---|---|---|---|---|---|---|---|---|']
    for dtype,title in [('work','工作日全部'),('returned','仅午休返回日'),('rest','休息日')]:
        for kind in TYPES:
            s=base[(base.kind==kind)&(base.policy=='cut_all')]
            for slot,label in SLOTS.items():
                if dtype=='returned' and slot!='noon':continue
                pre=dtype+'_'+slot+'_'
                lines.append('|'+ '|'.join([title,TYPES[kind],label]+[qi(s[pre+c]) for c in ['start_C','end_C','drop_C','start_RH','end_RH','drop_w_gkg']])+'|')
    lines+=['','工作日全部平均包含无人返回、不启动空调的午休；返回日另列，避免把两者混淆。极低返回概率情景若没有返回日，其条件统计不适用，但仍保留在全季电量和全部工作日统计中。两次10分钟的工作日温湿变化来自自然热湿交换与残余回蒸，不是空调制冷。','',
      '|空调|窗口|现行规定结束室温 °C|假设自启结束室温 °C|现行规定结束RH %|假设自启结束RH %|',
      '|---|---|---|---|---|---|']
    for kind in TYPES:
        a=base[(base.kind==kind)&(base.policy=='cut_all')];b=base[(base.kind==kind)&(base.policy=='auto_restore')]
        for slot in ['morning','afternoon']:
            pre='work_'+slot+'_'
            lines.append(f'|{TYPES[kind]}|{SLOTS[slot]}|{qi(a[pre+"end_C"])}|{qi(b[pre+"end_C"])}|{qi(a[pre+"end_RH"])}|{qi(b[pre+"end_RH"])}|')
    lines+=['','10分钟不足以证明连续30分钟舒适；午休13:30后仍会再次断电。逐日窗口前后状态、在室标志、冷凝、排水、回蒸和电量在 `results/west_window_daily.csv.gz`。','',
      '![短暂供电](figures/06_short_supply.png)','',
      '## 下班到家后，多久凉下来、多久温湿同时合适','',
      '从实际到家时刻计时，已包含到家后开机反应；不把无人时从17:30送电到回家的延迟说成人在室内等待。温度条件为不高于28°C并持续30分钟；联合条件再要求RH≤65%。均为计算阈值，未含风速、辐射温度、空气质量及个人感受。','',
      '|空调|17:30送电时室温 °C|到家时室温 °C|到家RH %|到家热指数 °C|30分钟仍未温度达标 %|90分钟仍未温度达标 %|90分钟仍未联合达标 %|六小时仍未联合达标 %|',
      '|---|---|---|---|---|---|---|---|---|']
    for kind in TYPES:
        s=base[(base.kind==kind)&(base.policy=='cut_all')]
        vals=[qi(s[c]) for c in ['restore_C','return_C','return_RH','return_HI']]+[qi(100*s[c]) for c in ['temperature_unmet_30min','temperature_unmet_90min','joint_unmet_90min','recovery_unmet_fraction']]
        lines.append('|'+ '|'.join([TYPES[kind]]+vals)+'|')
    lines+=['','不把六小时封顶中位数当成保证恢复时刻。连续30分钟的要求较严格，温控启停略微反复越线也会使其不达标，不表示整个观察期都处在高温高湿。原始逐日恢复事件和截尾标志在 `results/west_recovery_daily.csv.gz`；数据仍保存温度与联合恢复两列，主要阅读上表未达标比例。一直开也可能有高湿或容量不足，不能把现行规定的全部等待都归因于断电。','',
      '![工作日温湿度](figures/02_recovery.png)','',
      '## 休息日有人，却仍然断电','',
      '|空调|断电时段平均室温 °C|同一时段平均RH %|季内休息日最高室温 °C|休息日>28°C小时数|休息日RH>65%小时数|休息日日均节电 kWh|',
      '|---|---|---|---|---|---|---|']
    for kind in TYPES:
        a=base[(base.kind==kind)&(base.policy=='always')].sort_values('sample')
        s=base[(base.kind==kind)&(base.policy=='cut_all')].sort_values('sample')
        vals=[qi(s[c],0 if 'hours' in c else 1) for c in ['rest_cut_mean_C','rest_cut_mean_RH','rest_peak_C','rest_hot_hours','rest_humid_hours']]
        lines.append('|'+ '|'.join([TYPES[kind]]+vals+[qi(a.restday_kWh.to_numpy()-s.restday_kWh.to_numpy())])+'|')
    lines+=['','最高温是季内休息日的最高值，不是日均。断电时壁挂风扇和其他通风设备也停止，因此实际体验还少了吹风；模型没有计算风速体感，不能据此精确评估床位舒适。漏风和自然换气仍保留假设，不写成零通风。','',
      '![休息日](figures/03_restday.png)','',
      '## 替代规则的取舍','',
      '“提前供电·仍需手动”合并到“仅工作日断电”展示：工作日11:00、16:30提前来电时仍无人，不会预冷；两条规则都在休息日持续供电。两者的制冷可用时段相同，微小电量差来自额外通电期间的待机与其他电器热源；完整原始七规则仍保留在数据表。无人时30°C属于设备支持温控管理的条件对照，尚未核实本机有此功能。','',
      '|空调|规则|整季电量 kWh|相对一直开节电 %|新增有人热暴露 °C·h|有人RH>65%小时数|',
      '|---|---|---|---|---|---|']
    for kind in TYPES:
        a=base[(base.kind==kind)&(base.policy=='always')].sort_values('sample')
        for pol in PUBLIC_POLICIES:
            s=base[(base.kind==kind)&(base.policy==pol)].sort_values('sample')
            lines.append(f'|{TYPES[kind]}|{NAMES[pol]}|{qi(s.energy_kWh,0)}|{qi(s.saving_pct)}|{qi(s.occupied_degree_hours.to_numpy()-a.occupied_degree_hours.to_numpy(),0)}|{qi(s.occupied_humid_hours,0)}|')
    lines+=['','热暴露为有人时超过28°C的幅度乘时长，不含风速和过冷代价。高温与高湿小时可能重叠，不能相加。RH小时也不能单独排名：更热的空气本身会压低RH读数，即使水分没有减少，较少RH超标小时也不表示更舒适。','',
      '![规则取舍](figures/04_policies.png)','',
      '## 尺寸对照','',
      '三个房间均为四人、同一套家具数量和同一台空调参数。主房间按尺寸范围抽样，0.8米砖与口述上限对照固定长宽，层高、门窗和机组等共用配对参数。不是三间实测宿舍，也不是面积纯因果效应。','',
      '|房间|空调|现行规定整季电量 kWh|相对一直开节电 %|休息日最高室温 °C|六小时未联合达标 %|',
      '|---|---|---|---|---|---|']
    for room in ROOMS:
        for kind in TYPES:
            s=mc[(mc.room==room)&(mc.kind==kind)&(mc.policy=='cut_all')]
            lines.append(f'|{ROOMS[room]}|{TYPES[kind]}|{qi(s.energy_kWh,0)}|{qi(s.saving_pct)}|{qi(s.rest_peak_C)}|{qi(100*s.recovery_unmet_fraction)}|')
    lines+=['','精确工作尺寸的基准结果见 `results/west_room_comparison.csv`。墙窗传热、屋面、室内蓄热与空调单位面积能力都会一起改变，不只改变空气体积。','',
      '![尺寸对照](figures/07_rooms.png)','',
      '## 启停与折算效率','',
      '折算效率为整季实际输出冷量/空调总电量，含风机和待机，不是能效标签；未把两类机组的差距拟合到预设比例。','',
      '|空调|一直开：每天启动|现行规定：每天启动|一直开：折算效率|现行规定：折算效率|',
      '|---|---|---|---|---|']
    for kind in TYPES:
        a=base[(base.kind==kind)&(base.policy=='always')];b=base[(base.kind==kind)&(base.policy=='cut_all')]
        lines.append(f'|{TYPES[kind]}|{qi(a.cycles_per_day)}|{qi(b.cycles_per_day)}|{qi(a.delivered_cop,2)}|{qi(b.delivered_cop,2)}|')
    lines+=['',*timer_table(root),'## 哪些条件更影响结果','',
      f'仅针对深圳站一个炎热周、主房间及固定时刻，以{config["sobol_n"]}对基础样本和{config["n_parameters"]}个输入做全局敏感性分析；不代表整季名次。该扫描固定非顶层、单面外墙，方位限制为西向±30°，不再把顶层/转角当未知开关。指数大小仍依赖26个未定输入的所选范围。输入含返回和手动反应延迟，已知人数不再抽样。总效应包含交互，不加总成百分比，区间是配对重采样95%范围。','']
    for kind in TYPES:
        for output,title in [('saving_kWh','节电量'),('extra_degree_hours','热暴露')]:
            s=sobol[(sobol.kind==kind)&(sobol.output==output)].nlargest(3,'ST')
            lines.append(f'- {TYPES[kind]}{title}：'+'、'.join(f'{r.label} {r.ST:.2f}（{r.ST_low:.2f}–{r.ST_high:.2f}）' for r in s.itertuples())+'。')
    lines+=['','区间重叠时不强调精确排名。主相图固定四人、相同门窗与机组，按固定断电与手动行为扫描面积及墙体传热；不以单段时长替代规定。','',
      '![敏感性](figures/05_sensitivity.png)','', '![相图](figures/00_phase.png)','',
      '## 方法、核对与局限','',
      '- 空气、内墙家具蓄热体、外墙屋顶合并节点，共三个热节点；另有空气含湿量和盘管存水状态。一分钟积分，逐时气象驱动，人员与设备热源随在室和供电变化。',
      '- 定频最短开机基准300秒、核对范围180–600秒，最短停机180秒、核对范围120–300秒；另做两站整季3×3时间组合扫描。这两项未加入原全局抽样，启动次数是计时器与控制假设的产物，不能当作实机预测；启动爬升基准45秒、范围15–90秒。变频有部分负荷效率和容量约束；两类曲线是假设，未有厂家校准。电量按实际可用容量和效率计算，未把空气侧上限再算成额外损耗。',
      '- 除湿按进风温湿度、有效盘管露点、风量与旁通比例动态分配显潜热，记录盘管存水、排水和停机回蒸；另扫盘管温度/风量/存水量。盘管露点在每条轨迹内固定（基准12°C），不随变频转速改变，可能高估低速除湿。仍没有独立湿控、材料吸湿、湿盘管完整厂家曲线或床位空间差异，不能保证主观不闷。',
      '- 内置热水余额只是离散自检。`audit.py`在一个炎热周内、无预热且初态已知时，另从输入气象与保存状态做热、水后处理记账；冷量与运行比例仍读自模拟输出，电量是按同一功率公式重算。篡改输出的测试能检出部分差错，但没有独立求解控制与盘管，也不是整季或实测验证。证据见 `results/west_independent_budgets.csv`。',
      '- 一节点指数解、三节点矩阵指数解、湿量混合解析解及步长/预热/收尾/气象替换检查均有记录。五分钟显式步长在紧凑主房间不稳定，已拒绝，不列作物理结果；主结果用一分钟。**没有运行EnergyPlus对算，没有现场温湿度与电量验证。** 两周电费较低的回忆最多说方向一致。',
      '- 外墙有效蓄热只相当于约36毫米混凝土，并非实际墙厚；屋面与墙共用U值和一个节点，可能夸大顶层高温，尤其高温尾部，不能把高温尾部当现场预测。无阳台挑檐遮阳，人体显热/潜热各为常数、不随室温调整。相邻房间热交换、门窗实际开合、天空长波、风扇体感未模拟；风机热未单独反馈室内。门窗默认关闭，换气是假设。若阳台门经常开着，需另算换气工况。',
      '- 参数范围、来源、固定与派生方式见 `data/confirmed_parameters.csv`；详见 [模型与来源](模型与来源.md)。家具材料质量尚未核实，不能拿场景概念图当作精确热模型或气流仿真。','',
      '## 复现与待核实资料','',
      '逐分钟曲线以无损压缩的 `.csv.gz` 保存，读取后的数值不变。公开包保留定稿房间的完整汇总结果与西向逐分钟轨迹；广朝向的逐分钟轨迹可选生成，不随包提供。如需生成广朝向轨迹，运行 `uv run --frozen python run.py --traces-only`。','',
      '在本目录运行，需Python 3.12与uv，按锁文件安装依赖；原始气象和哈希已保存。','',
      '```sh','uv run --frozen python -m pytest -q','uv run --frozen python run_confirmed.py','uv run --frozen python verify_confirmed.py','uv run --frozen python render_figures.py --report','```','',
      '场景重建需要Blender 4.2 LTS，已用4.2.23验证。运行 `blender --background --factory-startup --python scene/source/build_model.py` 可生成场景；五个视角的渲染和JPG压缩命令见 [场景说明](scene/README.md)。场景图不参与热计算。','',
      '只更新图表、不运行仿真时，可运行 `uv run --frozen python render_figures.py --report`。图表需系统苹方SC、Noto Sans SC或思源黑体之一；图件使用苹方SC，导出的SVG已转曲，阅读图件不依赖字体安装。','',
      f'默认{config["mc_n"]}个共用参数样本。西向主基准三种房间×两类机组×七条规则，共{config["mc_n"]*42}条整季轨迹；朝东/顶层/转角各在主房间计算一直开、现行和自己开关，共{config["mc_n"]*18}条对照，总计{config["mc_n"]*60}条。Sobol基础样本{config["sobol_n"]}对、26个输入。随机种子固定，执行测试、数据、八张核心图及四张补充图和本文生成；每张有亮暗、宽窄四版PNG与SVG。','',
      '二楼、非转角、阳台朝西已经确认；总层数未知，非顶层仍是明确假设。方位精度、净尺寸与层高、玻璃面积、门窗开合、机组曲线和返回延迟仍非实测，是结果的未解决局限；将来有实测温湿度和分项电量后才能进一步校准。','']
    text='\n'.join(lines)
    import re
    text=re.sub(r'^!\[.*?\]\(figures/[^)]+\)\s*$', '', text, flags=re.M)
    head,details=text.split('## 先看结果',1)
    text=head+visual_story(root)+'\n'+scene_gallery()+'\n## 数据表、口径与模型边界\n\n'+details
    (root/'README.md').write_text(text)




def visual_story(root):
    import html,json
    manifest=json.loads((Path(root)/'figures/manifest.json').read_text())
    items={item['name']:item for item in manifest}
    def pic(name):
        title=html.escape(items[name]['title'],quote=True)
        return ('<picture>\n'
          f'  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="figures/{name}_暗_窄.svg">\n'
          f'  <source media="(max-width: 600px)" srcset="figures/{name}_亮_窄.svg">\n'
          f'  <source media="(prefers-color-scheme: dark)" srcset="figures/{name}_暗.svg">\n'
          f'  <img src="figures/{name}_亮.svg" alt="{title}" width="830">\n'
          '</picture>\n')
    blocks=['## 先看图\n',
      '以下电量与季节峰温图用128组西向±30°样本；二楼按非顶层，单面外墙。日内曲线固定西向270°；敏感性也固定非顶层、单面外墙，只分析西向范围和其余未定输入。受热是有人时超过28度的幅度乘时长，不是健康等级。\n',pic('00_主结论'),
      '## 一天里的室温与湿度\n',
      '工作日短休无人，来电不会自动制冷；午休返回才开机。工作日与休息日上下对齐、共用坐标。这里是定频基准示例；居中的30分钟滑动平均会模糊启停边界，不用它读精确开机时刻或峰值。原始统计仍用一分钟数据。\n',pic('02_一天室温'),pic('03_一天湿度'),
      '## 休息日在屋里要承受什么\n',pic('04_休息日'),
      '## 规则之间怎样取舍\n',pic('05_规则取舍'),
      '## 哪些假设最影响结论\n',pic('06_影响因素'),
      '## 附图与机型对照\n',
      '整季电量、房间大小、附加面积扫描、空气含水量，以及变频机的关键比较列在这里。完整数字表和方法说明在图后。\n',
      pic('01_电量'),pic('07_房间对照'),pic('附01_相图'),pic('附02_含湿量'),pic('附03_变频主结论'),pic('附04_变频规则取舍')]
    return '\n'.join(blocks)


def opening(base):
    work=paired_values(base,'fixed','manual','workday_kWh')
    rest=paired_values(base,'fixed','manual','restday_kWh')
    extra=paired_values(base,'fixed','manual','energy_kWh')
    return [f'**工作日里，强制断电和“人走自己关”耗电几乎一样；多用的电主要集中在休息日白天有人时。** 按已确认的西向、单面外墙和二楼非顶层假设估算，定频空调每个休息日多用约{rest.median():.1f}度，整季多约{extra.median():.0f}度。换来的是休息日有人时能持续开空调，不必等来电。','',
     f'工作日差值中位数为{work.median():.2f}度/天，取整约0度；存在跨日蓄热和少量待机差异，因此不是数学上全部恰好为零。工作日与休息日的范围、顶层及转角对照见后面的表。','',
     '没有现场电量或温湿度校准，也没有与成熟建筑仿真工具对算。数字是带假设的模型情景，不是宿舍实测；风扇停转的体感未算。']


def building_table(mc):
    rows=['## 朝向、顶层和转角分开看','',
      '二楼、非转角、阳台朝西已确认；总层数未知，非顶层仍为假设。方位为270°±30°。四种工况共用完全相同的128组其他输入、气象和人员日历，朝东只把方位旋转180°，顶层只增加暴露屋面，转角只增加侧外墙及其派生蓄热。三种对照均不是本宿舍已确认状态。','',
      '|建筑工况|空调|样本数|现行相对一直开节电 %|自己开关整季多用 度|工作日日均多用 度|休息日日均多用 度|现行休息日季内最高温 °C|',
      '|---|---|---|---|---|---|---|---|']
    for case,label in CASES:
      part=mc[(mc.room=='base')&(mc.building_case==case)]
      for kind in TYPES:
        cur=part[(part.kind==kind)&(part.policy=='cut_all')]
        rows.append('|'+ '|'.join([label,TYPES[kind],str(len(cur)),qi(cur.saving_pct),qi(paired_values(part,kind,'manual','energy_kWh'),0),qi(paired_values(part,kind,'manual','workday_kWh'),2),qi(paired_values(part,kind,'manual','restday_kWh'),2),qi(cur.rest_peak_C)])+'|')
    rows+=['','下面直接比较同一样本的建筑工况差值；正数表示对照工况比西向基准更高，范围不是两列分位数相减。','',
      '|相对西向基准|空调|现行整季电量变化 度|自己开关额外用电变化 度|现行休息日峰温变化 °C|',
      '|---|---|---|---|---|']
    west=mc[(mc.room=='base')&(mc.building_case=='west')]
    for case,label in CASES[1:]:
      part=mc[(mc.room=='base')&(mc.building_case==case)]
      for kind in TYPES:
        a=west[(west.kind==kind)&(west.policy=='cut_all')].set_index('sample')
        b=part[(part.kind==kind)&(part.policy=='cut_all')].set_index('sample')
        extra=paired_values(part,kind,'manual','energy_kWh')-paired_values(west,kind,'manual','energy_kWh')
        rows.append(f'|{label}|{TYPES[kind]}|{qi(b.energy_kWh-a.energy_kWh,0)}|{qi(extra,0)}|{qi(b.rest_peak_C-a.rest_peak_C)}|')
    return rows+['','未另注明的季节图表都使用西向基准128组。完整数据见 `results/building_confirmed.csv.gz`；本报告只使用定稿房间的当前计算结果。','']


def timer_table(root):
    import pandas as pd
    scan=pd.read_csv(Path(root)/'results/west_cycle_timer_scan.csv')
    rows=['## 启停次数为什么不能当实机预测','',
     '最短开机时间180–600秒、最短停机时间120–300秒分别做3档，两站共54条定频整季轨迹；其余参数固定为22.94㎡、非顶层、单面外墙、朝西270°的默认值。它是额外确定参数扫描，没有并入主情景区间。下表停机时间固定180秒；完整9组合见 `results/west_cycle_timer_scan.csv`。','',
     '|气象|最短开机 分钟|一直开每天启动|现行每天启动|一直开开机段10–90% 分钟|现行相对一直开节电 %|自己开关多用 度/季|',
     '|---|---|---|---|---|---|---|']
    for station in ['shenzhen','guangzhou']:
      for on in [180,300,600]:
        part=scan[(scan.station==station)&(scan.min_on_seconds==on)&(scan.min_off_seconds==180)]
        a=part[part.policy=='always'].iloc[0];b=part[part.policy=='cut_all'].iloc[0]
        rows.append(f'|{station}|{on/60:.0f}|{a.cycles_per_day:.1f}|{b.cycles_per_day:.1f}|{a.run_minutes_p10:.1f}–{a.run_minutes_p90:.1f}|{b.saving_pct:.1f}|{b.manual_extra_kWh:.0f}|')
    return rows+['','开机段按一分钟输出连续运行段统计，剔除边界截断段，保留强制断电中断。基准很多开机段贴着最短时间，时间加倍会显著减少启动次数；节电率的变化需看同站同组合，不能把每天启动数当作现场预测。该扫描已按西向270°更新；以表中的同站5分钟和10分钟两行判断启动数与节电率如何变化。','']


def scene_intro():
    return '![从入户门看宿舍](scene/images/entry.jpg)\n\n<small>示意图，按记忆与照片重建，尺寸为推算；不参与计算。</small>'


def scene_gallery():
    return ('## 这间宿舍\n\n'
      '房间净尺寸3.70×6.20×2.80米；两端各2.10米桌柜与高架床单元，加中段2.00米落地床，组成6.20米房长。两张高架床、两张落地床、四张L形桌及四只双门柜对应四人的蓄热与在室热源；两扇磨砂窗和阳台门上半对应1.90㎡净玻璃，门下半金属板及框单独作为不透明传热分支。\n\n'
      '![阳台回望](scene/images/balcony.jpg)\n\n![俯视全景](scene/images/overview.jpg)\n\n'
      '![左墙侧视](scene/images/left.jpg)\n\n![右墙侧视](scene/images/right.jpg)\n\n'
      '<small>示意图，按记忆与照片重建，尺寸为推算；不参与计算。</small>\n')
