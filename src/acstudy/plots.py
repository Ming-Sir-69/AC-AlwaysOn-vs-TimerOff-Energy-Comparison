"""Editorial research figures. Rendering only; simulation results stay unchanged."""
from pathlib import Path
import glob,json,math,textwrap,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager,colors,ticker,patheffects
from .model import LUNCH_CALENDAR,Parameters
from .presentation import baseline,PUBLIC_POLICIES

NAMES={'manual':'自主开关·全程供电','always':'一直开','cut_all':'现行规定·手动开机','cut_workday':'仅工作日断电',
       'early60':'提前供电·仍需手动','setback30':'无人时调至30°C',
       'precool_restday':'预冷+休息日供电','auto_restore':'来电自启·假设对照'}
TYPES={'fixed':'定频','inverter':'变频'}
SHORT={'manual':'自己开关','always':'一直开','cut_all':'现行规定','cut_workday':'工作日断电','early60':'提前供电',
       'setback30':'无人时30 °C','precool_restday':'预冷方案','auto_restore':'来电自启（假设）'}
ROOMS={'base':'22.94㎡基准','tile80':'26.66㎡·0.8米砖','upper':'29.76㎡口述上限'}
THEMES={
 '亮':dict(bg='#F4EFE4',ink='#2E2A26',muted='#6B655C',grid='#E2DBCD',amber='#B07A00',blue='#1B74B5',gray='#8A8478',shade='#2E2A26'),
 '暗':dict(bg='#2E2A26',ink='#F1EBDF',muted='#A8A196',grid='#423D38',amber='#B88610',blue='#3A88B8',gray='#9A948A',shade='#F1EBDF')}
FONT_REG=None;FONT_BOLD=None;MANIFEST=[]


def setup():
    global FONT_REG,FONT_BOLD
    if FONT_REG:return
    candidates=glob.glob('/System/Library/AssetsV2/com_apple_MobileAsset_Font*/**/PingFang.ttc',recursive=True)
    candidates+=['/System/Library/Fonts/PingFang.ttc']
    for candidate in candidates:
        if not Path(candidate).exists():continue
        # Collection face zero is HK on some systems. Extract SC locally for
        # rendering; these system-font files remain in ignored scratch storage.
        from fontTools.ttLib import TTCollection
        collection=TTCollection(candidate,lazy=True)
        target=Path(__file__).resolve().parents[2]/'.cache/fonts';target.mkdir(parents=True,exist_ok=True)
        for index,font in enumerate(collection.fonts):
            if font['name'].getDebugName(1)=='PingFang SC' and font['name'].getDebugName(2) in ['Regular','Semibold']:
                path=target/('PingFangSC-'+font['name'].getDebugName(2)+'.ttf')
                if not path.exists():font.save(path)
                font_manager.fontManager.addfont(str(path))
                if font['name'].getDebugName(2)=='Regular':FONT_REG=str(path)
                else:FONT_BOLD=str(path)
        if FONT_REG:break
    if not FONT_REG:
        for family in ['Noto Sans SC','Noto Sans CJK SC','Source Han Sans SC']:
            try:FONT_REG=font_manager.findfont(family,fallback_to_default=False);break
            except ValueError:pass
    if not FONT_REG:raise RuntimeError('Install PingFang SC or Noto Sans SC before rendering Chinese figures')
    FONT_BOLD=FONT_BOLD or FONT_REG
    plt.rcParams.update({'svg.fonttype':'path','axes.unicode_minus':False,'figure.dpi':100,
       'savefig.dpi':100,'axes.spines.top':False,'axes.spines.right':False,
       'axes.spines.left':False,'axes.spines.bottom':True,'axes.grid':False,
       'xtick.major.size':0,'ytick.major.size':0,'axes.formatter.useoffset':False})


def q(values):
    a=np.asarray(values,float);a=a[np.isfinite(a)]
    return np.quantile(a,[.05,.25,.5,.75,.95])


def wrap(s,units):
    out=[];line='';size=0.
    for token in re.findall(r'[A-Za-z0-9]+(?:[.\-–/][A-Za-z0-9]+)*%?|\n|.',s):
        w=sum(1 if ord(ch)>255 else .55 for ch in token)
        if token=='\n':out.append(line);line='';size=0;continue
        if size+w>units and line:
            out.append(line);line='';size=0
        line+=token;size+=w
    if line:out.append(line)
    return out


class Card:
    def __init__(self,title,theme,narrow,tag,note,kind='fixed'):
        self.t=THEMES[theme];self.theme=theme;self.narrow=narrow
        self.W,self.H=(800,1000) if narrow else (1600,900)
        self.fig=plt.figure(figsize=(self.W/100,self.H/100),facecolor=self.t['bg'],dpi=100)
        self.body=26 if narrow else 22;self.tick=26 if narrow else 20
        self.note=note;self.tag=tag;self.title=title;self.kind=kind;self.artists=[]
        self.text(.07,.965,tag,18 if not narrow else 26,color='muted')
        display=title.replace('，','，\n',1) if narrow and '\n' not in title and '，' in title else title
        title_lines=wrap(display,21 if narrow else 44)
        for i,line in enumerate(title_lines):self.text(.07,.91-i*(.044 if narrow else .05),line,32 if narrow else 30,bold=True)
        sub_y=.91-(len(title_lines)-1)*(.044 if narrow else .05)-.065
        self.text(.07,sub_y,f'{TYPES[kind]}空调 · 模型情景',26 if narrow else 20,color='muted')
        self.header_bottom=sub_y-.04
        self.fig.add_artist(plt.Line2D([.07,.93],[sub_y-.025]*2,transform=self.fig.transFigure,color=self.t['grid'],lw=1))
    def prop(self,px,bold=False,mono=False):
        return font_manager.FontProperties(fname=None if mono else FONT_BOLD if bold else FONT_REG,
                                          family='DejaVu Sans Mono' if mono else None,size=px*.72)
    def text(self,x,y,s,px=None,color='ink',bold=False,mono=False,ha='left',va='top',**kw):
        a=self.fig.text(x,y,s,color=self.t.get(color,color),fontproperties=self.prop(px or self.body,bold,mono),ha=ha,va=va,**kw)
        self.artists.append(a);return a
    def ax(self,rect,grid=True):
        ax=self.fig.add_axes(rect,facecolor=self.t['bg'])
        for side in ['left','top','right']:ax.spines[side].set_visible(False)
        ax.spines['bottom'].set_color(self.t['grid']);ax.spines['bottom'].set_linewidth(.8)
        ax.tick_params(colors=self.t['muted'],pad=9)
        if grid:ax.grid(axis='y',color=self.t['grid'],linewidth=.65,zorder=0)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v,p:f'{v:,.0f}'))
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v,p:f'{v:,.0f}'))
        return ax
    def labels(self,ax,x=None,y=None):
        if x:ax.set_xlabel(x,fontproperties=self.prop(self.body),color=self.t['muted'],labelpad=15)
        if y:ax.set_ylabel(y,fontproperties=self.prop(self.body),color=self.t['muted'],labelpad=18)
    def interval(self,ax,values,y,policy,vertical=False):
        lo,p25,mid,p75,hi=q(values);color=self.color(policy)
        alpha=1. if policy in ['cut_all','precool_restday'] else .65
        ax.plot([lo,hi],[y,y],color=color,lw=1.44,alpha=alpha,zorder=2,solid_capstyle='round')
        ax.plot([p25,p75],[y,y],color=color,lw=3.0,alpha=alpha,zorder=3,solid_capstyle='round')
        ax.plot(mid,y,marker='D' if policy=='precool_restday' else 'o',ms=11.5 if policy in ['cut_all','precool_restday'] else 10,
                mfc=color,mec=self.t['bg'],mew=1.3,ls='none',zorder=5)
        return lo,mid,hi
    def color(self,p):return self.t['amber'] if p=='cut_all' else self.t['blue'] if p=='precool_restday' else self.t['gray']
    def footer(self):
        note=self.note
        lines=wrap(note,25 if self.narrow else 77)
        if len(lines)>5 and self.narrow:raise ValueError(f'Mobile footer too long: {self.tag}')
        start=.185 if self.narrow else .135
        step=.031 if self.narrow else .027
        for i,line in enumerate(lines):self.text(.07,start-i*step,line,26 if self.narrow else 18,color='muted')
    def finish(self,out,name):
        self.footer()
        for ax in self.fig.axes:
            for a in ax.get_xticklabels()+ax.get_yticklabels():a.set_fontproperties(self.prop(self.tick,mono=True))
            for a in ax.texts:
                if a.get_fontsize()<self.body*.72-.01:a.set_fontproperties(self.prop(self.body))
        self.fig.canvas.draw()
        # All figure-level copy is checked in pixel space, before export.
        renderer=self.fig.canvas.get_renderer();overflow=[]
        for a in self.artists:
            b=a.get_window_extent(renderer)
            if b.x0<12 or b.y0<12 or b.x1>self.W-8 or b.y1>self.H-6:overflow.append(a.get_text())
        if overflow:raise ValueError('Clipped figure copy: '+repr(overflow))
        stem=f'{name}_{self.theme}'+('_窄' if self.narrow else '')
        for ext in ['png','svg']:
            path=Path(out)/(stem+'.'+ext)
            self.fig.savefig(path,facecolor=self.t['bg'],dpi=100,metadata={'Date':None} if ext=='svg' else None)
            if ext=='svg':path.write_text(re.sub(r'<metadata>.*?</metadata>\s*','',path.read_text(),flags=re.S))
        plt.close(self.fig)
        return stem


def paired(mc,kind,policy,metric,reference='cut_all'):
    a=mc[(mc.kind==kind)&(mc.policy==policy)].set_index('sample')[metric]
    b=mc[(mc.kind==kind)&(mc.policy==reference)].set_index('sample')[metric]
    return (a-b).to_numpy()


def med(mc,kind,policy,col):return float(mc[(mc.kind==kind)&(mc.policy==policy)][col].median())


def dots_card(card,rows,xlabel,extra=None,hero_summary=False):
    n=len(rows)
    if card.narrow:
        rect=[.29,.29,.52,.34 if hero_summary else .44];ax=card.ax(rect,grid=False)
    else:
        rect=[.30,.235,.39,.50];ax=card.ax(rect,grid=False)
        card.text(.735,.76,'中位数 [5–95%]',18,color='muted')
        if extra:card.text(.88,.76,extra,18,color='muted')
    hi=max(q(values)[-1] for _,_,values,_ in rows);lo=min(0.,min(q(values)[0] for _,_,values,_ in rows))
    span=max(hi-lo,1);ax.set_xlim(lo-.07*span,hi+.08*span);ax.set_ylim(n-.5,-.55);ax.set_yticks([])
    ax.xaxis.set_major_locator(ticker.MaxNLocator(4 if card.narrow else 5))
    ax.axvline(0,color=card.t['grid'],lw=1,ls=(0,(2,4)))
    for i,(policy,label,values,secondary) in enumerate(rows):
        l,m,h=card.interval(ax,values,i,policy)
        y=rect[1]+rect[3]*(1-(i+.55)/(n+.05))
        card.text(.065,y,label,card.body,bold=policy in ['cut_all','precool_restday'],va='center',color='ink' if policy in ['cut_all','precool_restday'] else 'muted')
        if card.narrow:
            card.text(.85,y,f'{m:,.0f}',26,mono=True,va='center',ha='left')
            if secondary:card.text(.065,y-.037,secondary,26,color='muted',va='center')
        else:
            card.text(.735,y,f'{m:,.0f} [{l:,.0f}–{h:,.0f}]',22,mono=True,va='center')
            if secondary:card.text(.88,y,secondary,22,mono=True,va='center')
    card.labels(ax,x=xlabel)


def hero(mc,theme,narrow,kind='fixed'):
    extra=paired(mc,kind,'precool_restday','energy_kWh');amount=q(extra)[2]
    title=f'提前预冷、休息日供电，一季多用约 {amount:.0f} kWh'
    note='预冷10–60分钟、休息日供电。非顶层、单面外墙、西向±30°；128个配对情景。细线5–95%，粗线25–75%；是情景范围，不是置信区间。受热按超过28 °C的幅度×时长。'
    if narrow:note='非顶层·单面外墙·西向±30°。细线5–95%，粗线25–75%，不是置信区间；受热按°C·h计。'
    card=Card(title.replace('，','，\n',1) if narrow else title,theme,narrow,'00 / 电量与受热' if kind=='fixed' else '附03 / 变频电量与受热',note,kind)
    if narrow:
        card.text(.07,.760,f'+{amount:.0f}',64,color='blue',bold=True,mono=True)
        card.text(.46,.744,'kWh / 每季',26,color='muted')
        lo,_,_,_,hi=q(extra)
        card.text(.46,.705,f'[{lo:.0f}–{hi:.0f}]',26,mono=True)
        card.text(.46,.667,'5–95%情景范围',26,color='muted')
    else:
        card.text(.78,.941,f'+{amount:.0f}',76,color='blue',bold=True,mono=True)
        card.text(.78,.845,'每季空调电量增量 / kWh',18,color='muted')
    policies=['cut_all','precool_restday','cut_workday','setback30','always','auto_restore','manual']
    if narrow:policies=['cut_all','precool_restday','manual','always']
    policies=sorted(policies,key=lambda p:q(paired(mc,kind,p,'energy_kWh'))[2])
    rows=[]
    for p in policies:
        heat=-q(paired(mc,kind,p,'occupied_degree_hours'))[2]
        secondary=(f'少受热约{heat:.0f}°C·h' if narrow else f'{heat:,.0f}') if p!='cut_all' else ('受热参照' if narrow else '0')
        rows.append((p,SHORT[p],paired(mc,kind,p,'energy_kWh'),secondary))
    dots_card(card,rows,'比现行规定多用的空调电量 / kWh',extra='受热减少 / °C·h',hero_summary=True)
    return card


def energy(mc,theme,narrow):
    own=med(mc,'fixed','precool_restday','energy_kWh')
    title=f'预冷方案一季约 {own:.0f} kWh，低于一直开'
    note='预冷方案含休息日供电；定频，非顶层、单面外墙、西向±30°，184天。点为中位数，细线5–95%、粗线25–75%情景范围，不是置信区间。只计空调。'
    if narrow:note='非顶层·西向±30°·184天·仅空调。点为中位数，细线5–95%、粗线25–75%情景范围，非置信区间。'
    card=Card(title,theme,narrow,'01 / 整季电量',note)
    rows=[]
    for p in sorted(['always','cut_all','precool_restday'],key=lambda p:med(mc,'fixed',p,'energy_kWh')):
        rows.append((p,SHORT[p],mc[(mc.kind=='fixed')&(mc.policy==p)].energy_kWh,None))
    dots_card(card,rows,'整个制冷季的空调电量 / kWh')
    return card


def aggregate(a,day,field):
    # Centered 30-minute display smoothing; raw one-minute arrays are untouched.
    values=np.convolve(np.pad(a[:,field],(15,14),mode='edge'),np.ones(30)/30,mode='valid')
    selected=(a[:,0]>day*24)&(a[:,0]<=(day+1)*24)
    return a[selected,0][::5]-24*day,values[selected][::5]


def dodge(targets,low,high,gap):
    order=np.argsort(targets);ys=np.asarray(targets)[order].copy()
    for i in range(1,len(ys)):ys[i]=max(ys[i],ys[i-1]+gap)
    if ys[-1]>high:ys-=ys[-1]-high
    if ys[0]<low:ys+=low-ys[0]
    out=np.empty(len(ys));out[order]=ys
    return out


def daily(traces,theme,narrow,field=1,kind='fixed'):
    day=next(i for i in range(5) if LUNCH_CALENDAR[i]<Parameters().lunch_fraction)
    if field==1:title='工作日两次10分钟来电，空调都没有开'
    elif field==5:
        a=traces[('base',kind,'cut_all')];start=a[int((day*24+12)*60)-1,5];end=a[int((day*24+13.5)*60)-1,5]
        title=f'午休开机的示例里，湿度约从{start:.0f}%降到{end:.0f}%'
    else:
        a=traces[('base',kind,'cut_all')];start=1000*a[int((day*24+12)*60)-1,4];end=1000*a[int((day*24+13.5)*60)-1,4]
        title=f'午休示例里，含湿量约从{start:.0f}降到{end:.0f}克/千克'
    note='22.94㎡、四人、西向270°的炎热周示例；曲线为30分钟滑动平均，计算使用一分钟数据。灰带为现行断电时段；预冷方案可提前供电。'
    if field==5:note='22.94㎡·西向270°示例；灰带为现行断电时段，曲线为30分钟滑动平均。降温后RH上升不等于水变多；含湿量另见附图。'
    if narrow:note=('22.94㎡·西向270°·30分钟滑动平均。灰带为现行断电时段；降温后RH上升不等于水变多。' if field==5 else '22.94㎡·西向270°；灰带表示现行断电时段。\n曲线为30分钟滑动平均，并非情景峰值。')
    card=Card(title,theme,narrow,'02 / 一天的室温' if field==1 else '03 / 一天的湿度' if field==5 else '附02 / 空气中的水蒸气',note,kind)
    selected=['always','cut_all','precool_restday'] if not narrow else ['cut_all','precool_restday']
    all_values=[]
    for d in [day,5]:
        for p in selected:
            _,ys=aggregate(traces[('base',kind,p)],d,field);all_values.extend(ys*(1000 if field==4 else 1))
    if field==1:yl=(math.floor(min(all_values)-1),math.ceil(max(all_values)+2))
    elif field==5:yl=(max(0,math.floor(min(all_values)/10)*10-5),min(105,math.ceil(max(all_values)/10)*10+5))
    else:yl=(max(0,math.floor(min(all_values)-1)),math.ceil(max(all_values)+2))
    for row,d in enumerate([day,5]):
        rect=([.16,min(.74,card.header_bottom-.05)-.16 if row==0 else .30,.78,.16 if row==0 else .18] if narrow else [.10,.545 if row==0 else .255,.83,.20])
        ax=card.ax(rect);ax.set_xlim(0,30.5);ax.set_ylim(*yl)
        ax.set_xticks([0,8,12,18,24] if narrow else [0,6,12,18,24]);ax.tick_params(labelbottom=(row==1));ax.yaxis.set_major_locator(ticker.MaxNLocator(3 if narrow else 4))
        for begin,end in [(8,10.5),(10+2/3,12),(13.5,15),(15+1/6,17.5)]:
            ax.axvspan(begin,end,color=card.t['shade'],alpha=.10 if theme=='暗' else .08,lw=0,zorder=0)
            if not narrow or end-begin>=2:
                ax.text((begin+end)/2,yl[1]-.06*(yl[1]-yl[0]),'断电',ha='center',va='top',color=card.t['muted'],fontproperties=card.prop(26 if narrow else 22))
        tails=[]
        for p in selected:
            x,y=aggregate(traces[('base',kind,p)],d,field)
            if field==4:y=y*1000
            ax.plot(x,y,color=card.color(p),lw=(2.16 if p!='always' else 1.44),ls=(0,(6,3)) if p=='precool_restday' else ':' if p=='always' else '-',zorder=4 if p=='precool_restday' else 3 if p=='cut_all' else 1)
            tails.append(float(y[-1]))
        gap=(card.body*1.25)/(rect[3]*card.H)*(yl[1]-yl[0])
        positions=dodge(tails,yl[0]+gap*.8,yl[1]-gap*.8,gap)
        for p,target,label_y in zip(selected,tails,positions):
            ax.plot([24,24.7],[target,label_y],color=card.t['muted'],lw=.6)
            ax.text(24.9,label_y,SHORT[p],va='center',color=card.t['ink'],fontproperties=card.prop(card.body,bold=p!='always'))
        card.text(.10,rect[1]+rect[3]+.034,'工作日 · 午休返回的示例' if row==0 else '休息日 · 全天有人',card.body,bold=True)
        if field==1:
            ax.axhline(28,color=card.t['gray'],ls=(0,(2,3)),lw=.7,alpha=.8)
            if row==0:
                raw=traces[('base',kind,'cut_all')]
                drop=raw[int((d*24+12)*60)-1,1]-raw[int((d*24+13.5)*60)-1,1]
                temp=raw[int((d*24+18.)*60)-1,1]
                if not narrow:
                    sx,sy=aggregate(raw,d,field)
                    for at,text,tx,ty in [(13.5,f'午休开机，实际降约{drop:.1f} °C',10.4,yl[1]-.33*(yl[1]-yl[0])),(18.,f'18:00到家，实际约{temp:.0f} °C',18.3,yl[1]-.12*(yl[1]-yl[0]))]:
                        ax.annotate(text,xy=(at,float(np.interp(at,sx,sy))),xytext=(tx,ty),
                            fontproperties=card.prop(22),color=card.t['ink'],
                            bbox=dict(facecolor=card.t['bg'],edgecolor='none',pad=2,alpha=.92),
                            arrowprops=dict(arrowstyle='-',color=card.t['muted'],lw=.7),zorder=8)
        card.labels(ax,y='室温 / °C' if field==1 else 'RH / %' if field==5 else '含湿量 / g/kg',x='一天里的时间 / 点' if row==1 else None)
    return card


def restday(mc,theme,narrow):
    current=mc[(mc.kind=='fixed')&(mc.policy=='cut_all')].rest_peak_C;peak=q(current)[2]
    title=f'休息日人在屋里，季内最高温约{peak:.1f} °C'
    note='定频，非顶层、单面外墙、西向±30°；最高温为每个情景整个季节休息日的峰值，不是下午日均。点和线为中位数及5–95%情景范围，非置信区间。'
    if narrow:note='非顶层·西向±30°。最高温是各情景季内休息日峰值，非日均；细线5–95%、粗线25–75%，不是置信区间。'
    card=Card(title,theme,narrow,'04 / 休息日的代价',note)
    card.text(.07,.735,f'{peak:.1f}',110 if narrow else 136,bold=True,mono=True)
    card.text(.07,.735-.125,'°C左右 · 季内峰值的情景中位数',26 if narrow else 22,color='muted')
    card.text(.07,.735-.17,'断电时，壁挂风扇也停转',26 if narrow else 22,bold=True)
    rect=[.29,.29,.57,.23] if narrow else [.48,.29,.37,.38]
    ax=card.ax(rect,grid=False);ax.set_ylim(1.9 if narrow else 1.5,-.5);ax.set_yticks([])
    xhi=max(q(mc[(mc.kind=='fixed')&(mc.policy==p)].rest_peak_C)[-1] for p in ['cut_all','precool_restday']);ax.set_xlim(20,xhi+2);ax.set_xticks([20,30,40])
    for i,p in enumerate(['cut_all','precool_restday']):
        vals=mc[(mc.kind=='fixed')&(mc.policy==p)].rest_peak_C;lo,mid,hi=card.interval(ax,vals,i,p)
        ax.text(-.08,i,SHORT[p],transform=ax.get_yaxis_transform(),ha='right',va='center',color=card.t['ink'],fontproperties=card.prop(card.body,bold=True))
        ax.text(mid,i+(.36 if narrow else .20),f'{mid:.1f} [{lo:.1f}–{hi:.1f}]',ha='center',va='top',color=card.t['muted'],fontproperties=card.prop(card.body,mono=True))
    card.labels(ax,x='休息日最高室温 / °C')
    return card


def policies(mc,theme,narrow,kind='fixed'):
    a=q(paired(mc,kind,'precool_restday','energy_kWh'))[2];heat=-q(paired(mc,kind,'precool_restday','occupied_degree_hours'))[2]
    title=f'预冷方案一季多用约 {a:.0f} kWh，少受热约{heat:.0f}°C·h'
    note='非顶层、单面外墙、西向±30°；128个配对情景。横纵细线分别为5–95%情景范围，不是联合置信区间。受热按人在室内超过28 °C的幅度×时长。'
    if narrow:note='非顶层·西向±30°。细线各为5–95%情景范围，不是联合置信区间；受热按°C·h计。浅折线连接中位数前沿。'
    card=Card(title,theme,narrow,'05 / 规则的取舍' if kind=='fixed' else '附04 / 变频规则取舍',note,kind)
    choices=['always','cut_all','precool_restday','cut_workday','setback30','auto_restore','manual']
    if narrow:choices=['always','cut_all','precool_restday','manual']
    data=[]
    for p in choices:
        sub=mc[(mc.kind==kind)&(mc.policy==p)]
        xx=q(sub.energy_kWh);yy=q(paired(mc,kind,p,'occupied_degree_hours','always'));data.append((p,xx,yy))
    xmax=max(x[-1] for _,x,_ in data);ymax=max(y[-1] for _,_,y in data)
    ax=card.ax([.17,.28,.76,.43] if narrow else [.12,.28,.81,.43]);ax.set_xlim(0,xmax*1.30);ax.set_ylim(-max(100,ymax*.06),ymax*1.07)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(3 if narrow else 5));ax.yaxis.set_major_locator(ticker.MaxNLocator(3 if narrow else 4))
    card.text(.12,.755,'人在屋里超过28 °C的累计程度（°C·h）',26 if narrow else 22,color='muted')
    # Non-dominated frontier from median positions; no implication of optimality
    # outside the supplied scenarios.
    frontier=[];best=float('inf')
    for p,x,y in sorted(data,key=lambda item:item[1][2]):
        if y[2]<best-1e-8:frontier.append((x[2],y[2]));best=y[2]
    if len(frontier)>1:ax.plot(*np.array(frontier).T,color=card.t['grid'],lw=1.1,zorder=1)
    targets=[y[2] for _,x,y in data]
    gap=card.body*1.35/(.43*card.H)*(ax.get_ylim()[1]-ax.get_ylim()[0])
    locations=dodge(targets,0,ymax*.92,gap)
    for (p,x,y),ly in zip(data,locations):
        color=card.color(p);alpha=.85 if p in ['cut_all','precool_restday'] else .40
        ax.plot([x[0],x[-1]],[y[2],y[2]],color=color,lw=1.44,alpha=alpha)
        ax.plot([x[2],x[2]],[y[0],y[-1]],color=color,lw=1.44,alpha=alpha)
        ax.plot(x[2],y[2],marker='D' if p=='precool_restday' else 'o',ms=11.5 if p in ['cut_all','precool_restday'] else 10,mfc=color,mec=card.t['bg'],mew=1.1,ls='none',zorder=5)
        lx=xmax*1.03
        ax.plot([x[2]+xmax*.01,lx-xmax*.02],[y[2],ly],color=card.t['muted'],lw=.55,alpha=.7)
        ax.text(lx,ly,SHORT[p],va='center',color=card.t['ink'] if p in ['cut_all','precool_restday'] else card.t['muted'],fontproperties=card.prop(card.body,bold=p in ['cut_all','precool_restday']))
    card.labels(ax,x='整个制冷季的空调电量 / kWh')
    return card


def sensitivity(sobol,theme,narrow):
    candidates=sobol[(sobol.kind=='fixed')&(sobol.output=='saving_kWh')]
    s=candidates.nlargest(5 if narrow else 8,'ST')
    if 'precool_minutes' not in set(s.parameter):
        import pandas as pd
        s=pd.concat([s.iloc[:-1],candidates[candidates.parameter=='precool_minutes']])
    s=s.sort_values('ST',ascending=False)
    top=s.iloc[0]
    title=f'西向炎热周里，{top.label}最影响预冷方案用电增量'
    note='定频，深圳炎热周，非顶层、单面外墙、西向±30°。27个未定输入；比较预冷方案减现行电量，细线为重采样95%区间。含交互；列主要输入及预冷提前量，不是整季排名。'
    if narrow:note='非顶层·西向±30°·炎热周·27个输入。\n主要输入及预冷提前量；细线为重采样95%区间。'
    card=Card(title,theme,narrow,'06 / 哪些条件更重要',note)
    ax=card.ax([.30 if narrow else .23,.27,.41 if narrow else .49,.46],grid=False)
    ax.set_ylim(len(s)-.5,-.5);ax.set_xlim(0,max(s.ST_high)*1.05);ax.set_yticks([]);ax.xaxis.set_major_locator(ticker.MaxNLocator(3 if narrow else 4));ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v,p:f'{v:.2f}'))
    for i,r in enumerate(s.itertuples()):
        color=card.t['ink'] if i<3 else card.t['gray']
        ax.plot([0,r.ST],[i,i],color=color,lw=3.0,alpha=.95 if i<3 else .55)
        ax.plot([r.ST_low,r.ST_high],[i,i],color=color,lw=1.44)
        ax.plot(r.ST,i,'o',ms=10,color=color,mec=card.t['bg'],mew=1)
        ax.text(-.05,i,r.label,transform=ax.get_yaxis_transform(),ha='right',va='center',color=card.t['ink'] if i<3 else card.t['muted'],fontproperties=card.prop(card.body,bold=i<3))
        ax.text(1.06,i,f'{r.ST:.2f}\n[{r.ST_low:.2f}–{r.ST_high:.2f}]' if narrow else f'{r.ST:.2f} [{r.ST_low:.2f}–{r.ST_high:.2f}]',transform=ax.get_yaxis_transform(),va='center',color=card.t['ink'] if i<3 else card.t['muted'],fontproperties=card.prop(26 if narrow else 20,mono=True))
    card.labels(ax,x='对预冷方案额外用电的总效应指数')
    return card


def rooms(mc,theme,narrow):
    title='房间约23–30平方米，预冷方案都比强制断电多用电'
    note='定频，非顶层、单面外墙、西向±30°，四人同机组。点和细线为预冷方案相对现行规定多用电量的中位数与5–95%情景范围，非置信区间。'
    if narrow:note='非顶层·西向±30°·四人·同机组。点与细线为配对差值的中位数及5–95%情景范围，不是置信区间。'
    card=Card(title,theme,narrow,'07 / 尺寸对照',note)
    rows=[]
    for room,label in ROOMS.items():
        sub=mc[mc.room==room];values=paired(sub,'fixed','precool_restday','energy_kWh')
        rows.append(('precool_restday',({'base':'23㎡基准','tile80':'27㎡对照','upper':'30㎡上限'}[room] if narrow else label.replace('·0.8米砖','').replace('口述上限','上限')),values,None))
    dots_card(card,rows,'预冷方案比现行规定多用 / kWh')
    return card


def phase_plot(phase,theme,narrow):
    p=phase[phase.kind=='fixed'];low,mid,high=np.quantile(p.saving_pct,[0,.5,1])
    title=f'附加面积扫描中，现行规定节电约{low:.0f}%–{high:.0f}%'
    note='定频，西向270°炎热周，四人同机组；附加面积扫描不是房间测量范围。颜色为相对一直开的节电率，等值线为新增受热°C·h。'
    if narrow:note='定频·西向270°·炎热周·附加面积扫描。颜色为节电率，线为受热°C·h；不是测量范围。'
    card=Card(title,theme,narrow,'附01 / 相图',note)
    ax=card.ax([.19,.30,.56,.41] if narrow else [.13,.26,.66,.47],grid=False)
    table=p.pivot(index='u_wall',columns='area',values='saving_pct');heat=p.pivot(index='u_wall',columns='area',values='extra_degree_hours')
    cmap=colors.LinearSegmentedColormap.from_list('brand_amber',[card.t['bg'],card.t['amber']])
    im=ax.pcolormesh(table.columns,table.index,table.values,cmap=cmap,shading='auto',vmin=low,vmax=high,rasterized=False)
    levels=np.linspace(heat.values.min(),heat.values.max(),5 if narrow else 7)[1:-1]
    cs=ax.contour(heat.columns,heat.index,heat.values,levels=levels,colors=card.t['ink'],linewidths=.7)
    texts=ax.clabel(cs,fontsize=card.body*.72,fmt='%.0f')
    for t in texts:t.set_fontproperties(card.prop(card.body));t.set_path_effects([patheffects.withStroke(linewidth=3,foreground=card.t['bg'],alpha=.55)])
    ax.set_xticks([15,30,45]);ax.set_yticks([1,2,3]);ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.1f'))
    card.labels(ax,x='附加扫描面积 / ㎡',y='外墙传热 / W/(㎡·K)')
    cax=card.fig.add_axes([.80,.30,.024,.41] if narrow else [.83,.26,.018,.47])
    cb=card.fig.colorbar(im,cax=cax,orientation='vertical')
    cb.outline.set_visible(False);cb.ax.tick_params(colors=card.t['muted'],length=0,pad=8);cb.set_label('节电比例 / %',fontproperties=card.prop(card.body),color=card.t['muted'],labelpad=12)
    return card


def make_plots(mc,sobol,phase,traces,out,only=None):
    setup();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    mc=baseline(mc);base=mc[mc.room=='base'];manifest=[]
    specs=[
      ('00_主结论',lambda t,n:hero(base,t,n)),('01_电量',lambda t,n:energy(base,t,n)),
      ('02_一天室温',lambda t,n:daily(traces,t,n,1)),('03_一天湿度',lambda t,n:daily(traces,t,n,5)),
      ('04_休息日',lambda t,n:restday(base,t,n)),('05_规则取舍',lambda t,n:policies(base,t,n)),
      ('06_影响因素',lambda t,n:sensitivity(sobol,t,n)),('07_房间对照',lambda t,n:rooms(mc,t,n)),
      ('附01_相图',lambda t,n:phase_plot(phase,t,n)),('附02_含湿量',lambda t,n:daily(traces,t,n,4)),
      ('附03_变频主结论',lambda t,n:hero(base,t,n,'inverter')),('附04_变频规则取舍',lambda t,n:policies(base,t,n,'inverter'))]
    for name,build in specs:
        if only and name not in only:continue
        entry={'name':name,'main':not name.startswith('附'),'files':[]}
        for theme in ['亮','暗']:
            for narrow in [False,True]:
                card=build(theme,narrow)
                entry['title']=card.title.replace('\n','');entry['kind']=card.kind
                entry['files'].append(card.finish(out,name))
        manifest.append(entry)
        print('Rendered:',name,flush=True)
    if not only:(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    return manifest
