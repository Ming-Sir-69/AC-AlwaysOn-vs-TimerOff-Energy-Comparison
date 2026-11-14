import bpy,json
from pathlib import Path
r=Path(__file__).resolve().parents[1];(r/'.cache').mkdir(exist_ok=True);p=json.loads((r/'参数.json').read_text());o=p['openings'];shell=bpy.data.collections['RoomShell'];wins=[x for x in shell.objects if x.get('role')=='window'];glass=next(x for x in shell.objects if x.name.endswith('/balcony_glass'));panel=next(x for x in shell.objects if x.name.endswith('/balcony_metal_lower'));lever=next(x for x in shell.objects if x.name.endswith('/balcony_L_lever'))
assert abs(panel.dimensions.z-o['balcony_height']/2)<1e-6
assert glass.location.z-glass.dimensions.z/2>o['balcony_height']/2
assert lever.data.splines[0].points[0].co.x<o['balcony_width']/2
assert any('balcony_right_hinge' in ob.name for ob in shell.objects)
assert lever.data.materials[0].name=='door_black_hardware'
assert panel.data.materials[0].name=='balcony_champagne_bronze'
rows=[]
for ob in wins:
 w,h=round(ob.dimensions.x,6),round(ob.dimensions.z,6);fw=o['window_frame'];rows.append({'name':ob.name,'glass_mesh_width_m':w,'glass_mesh_height_m':h,'glass_mesh_area_m2':w*h,'exposed_width_m':w-fw,'exposed_height_m':h-fw,'exposed_area_m2':(w-fw)*(h-fw)})
w,h=round(glass.dimensions.x,6),round(glass.dimensions.z,6);rows.append({'name':glass.name,'glass_mesh_width_m':w,'glass_mesh_height_m':h,'glass_mesh_area_m2':w*h,'exposed_width_m':w,'exposed_height_m':h,'exposed_area_m2':w*h})
report={'room_net_dimensions_m':[p['room']['width'],p['room']['length'],p['room']['height']],'door_srgb_hex':p['palette']['balcony_bronze'],'door_metallic':.78,'door_roughness':.38,'entry_oak_srgb':[p['palette']['entry_oak_light'],p['palette']['entry_oak_dark']],'glazing':rows,'total_glass_mesh_area_m2':sum(x['glass_mesh_area_m2'] for x in rows),'total_exposed_glazing_area_m2':sum(x['exposed_area_m2'] for x in rows),'thermal_recommended_area':'exposed glazing only; frames accounted separately','basis':'模型参数，非现场测量。窗框中心线沿玻璃片四边，各遮挡半框宽；门上半玻璃网格已按门扇框内净尺寸裁切。','checks':'PASS'}
(r/'.cache/opening_geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
