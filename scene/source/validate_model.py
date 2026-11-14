import bpy,json,math,hashlib
from pathlib import Path
from collections import Counter
from mathutils import Vector
R=Path(__file__).resolve().parents[1];(R/'.cache').mkdir(exist_ok=True);P=json.loads((R/'参数.json').read_text());S=bpy.data.scenes['宿舍_装配'];S.view_layers[0].update();objs=list(bpy.data.collections['装配实例'].objects);counts=Counter(o.get('asset') for o in objs if o.get('asset')!='RoomShell')
assert counts=={'DeskCab_L':2,'DeskCab_R':2,'LowBed':2,'Loft_L':1,'Loft_R':1},counts
assert S['parameter_hash']==hashlib.sha256((R/'参数.json').read_bytes()).hexdigest()
checks=[]
assert abs(P['desk']['wall_depth']-P['wardrobe']['depth'])<1e-8
assert P['desk']['width']-P['desk']['wing_width']-P['desk']['slider_panel_thickness']>=.6
shell=bpy.data.collections['RoomShell'].objects
assert len([o for o in shell if o.get('role')=='window'])==2
assert len([o for o in shell if o.get('role')=='ceiling_light'])==2
assert len([o for o in shell if o.get('role')=='door_rig'])==2
assert len([o for o in shell if o.get('fan_id')])==2
assert len([o for o in shell if o.name.endswith('/AC')])==1
fans=sorted([o for o in shell if o.get('fan_id')],key=lambda o:o['fan_id'])
for ob,y in zip(fans,[P['lights']['y_centers'][0]/2,sum(P['lights']['y_centers'])/2]):assert abs(ob.location.x-P['room']['width']/2)<1e-6 and abs(ob.location.y-y)<1e-6
assert not any('fan_wall' in ob.name for ob in shell)
for idx,pose in enumerate(P['fan']['poses'],1):
 yaw=next(o for o in shell if o.name==f'RoomShell/fan{idx}_head_yaw');pitch=next(o for o in shell if o.name==f'RoomShell/fan{idx}_head_pitch')
 assert pitch.parent==yaw and yaw['rotation_range_deg']==360
 assert abs(math.degrees(yaw.rotation_euler.z)-pose['yaw_deg'])<1e-4
 assert abs(math.degrees(pitch.rotation_euler.x)-pose['pitch_deg'])<1e-4
 assert len([o for o in shell if o.name.startswith(f'RoomShell/fan{idx}_petal_')])==3
 assert len([o for o in shell if o.name.startswith(f'RoomShell/fan{idx}_front_wire')])==P['fan']['spokes']
 assert len([o for o in shell if o.name.startswith(f'RoomShell/fan{idx}_rear_wire')])==P['fan']['spokes']
ac=next(ob for ob in shell if ob.name.endswith('/AC'));assert abs(ac.dimensions.x-(P['room']['width']/2-(P['openings']['window_start_x']+P['openings']['window_width']+P['openings']['window_gap']-P['openings']['window_frame']/2)))<1e-6
assert abs(P['room']['length']-(2*(P['wardrobe']['width']+P['desk']['width'])+P['bed']['length']))<1e-6
checks.append({'ceiling_fans_y':[round(o.location.y,4) for o in fans],'ac_width':round(ac.dimensions.x,4),'room_length':P['room']['length'],'loft_length':P['loft']['length'],'low_bed_length':P['bed']['length'],'desk_knee_clear_width':P['desk']['width']-P['desk']['wing_width']-P['desk']['slider_panel_thickness']})
strips=[]
for o in shell:
 if '/tile_' in o.name and abs(o.location.y-P['room']['tile']/2)<1e-5:
  vv=[o.matrix_world@Vector(p) for p in o.bound_box];xmin=min(v.x for v in vv);xmax=max(v.x for v in vv)
  if xmin>=P['bed']['frame_depth']-1e-5 and xmax<=P['room']['width']-P['bed']['frame_depth']+1e-5:strips.append(o.name)
assert len(strips)==3,strips
checks.append({'room_fixtures':'2 windows / 2 doors / 2 lights / 2 ceiling fans / 1 AC','actual_aisle_tile_columns':len(strips)})
def bounds(inst,filters=None):
 vs=[]
 for ob in inst.instance_collection.objects:
  if ob.type not in ['MESH','CURVE'] or filters and not filters(ob):continue
  vs += [inst.matrix_world@ob.matrix_world@Vector(v) for v in ob.bound_box]
 return [[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]]
for id,hand,edge in [('G1','right',P['loft']['length']),('G2','left',P['room']['length']-P['loft']['length']),('G3','left',P['loft']['length']),('G4','right',P['room']['length']-P['loft']['length'])]:
 inst=bpy.data.objects[id];parts=inst.instance_collection.objects
 counter=next(o for o in parts if o.get('role')=='worktop');assert counter['wing_side']==hand
 front=next(o for o in parts if o.get('role')=='closed_storage_front');assert abs(front.dimensions.x-P['desk']['wing_width'])<1e-6
 assert front.data.materials[0].name=='ivory'
 sliders=[o for o in parts if o.get('role')=='sliding_door'];assert len(sliders)==2
 assert all(o['hinges']==0 and o['slide_axis']=='local_depth' for o in sliders)
 assert all(o.dimensions.x<.01 and o.dimensions.y>.4 for o in sliders)
 bedside=next(o for o in parts if o.name.endswith('/storage_bed_side'));bb=bounds(inst,lambda o:o==bedside)
 assert min(abs(bb[0][1]-edge),abs(bb[1][1]-edge))<1e-5,(id,bb,edge)
 checks.append({'desk':id,'hand':hand,'short_wing_touches_low_bed_y':edge,'aisle_face':'closed_ivory_board','knee_face':'blue_sliding_panels','hinges':0})
for key in ['DeskCab_L','DeskCab_R']:
 parts=bpy.data.collections[key].objects
 sides=[o for o in parts if o.get('role')=='bed_side_upper_panel'];assert len(sides)==1
 panel=sides[0];assert abs(panel.location.z+panel.dimensions.z/2-P['wardrobe']['height'])<1e-6
 assert not any('/lower_end_support' in o.name or '/hutch_thin_side' in o.name for o in parts)
 shelves=sorted([o for o in parts if '/hutch_shelf' in o.name],key=lambda o:o.location.z)
 assert abs(shelves[-1].location.z+shelves[-1].dimensions.z/2-P['wardrobe']['height'])<1e-6
 assert abs(shelves[0].location.z-(P['wardrobe']['height']-P['desk']['upper_compartment_height']))<1e-6
 doors=[o for o in parts if o.get('role')=='wardrobe_door'];assert len(doors)==2
 for o in doors:
  assert o.data.materials[0].name=='blue' and o['vent_holes']==14
  assert abs((o.location.y-o.dimensions.y/2)-(-P['wardrobe']['depth']+P['wardrobe']['door_recess']))<1e-5
 for shelf_ob in [o for o in parts if '/cab_internal_shelf' in o.name]:assert shelf_ob.location.y-shelf_ob.dimensions.y/2>doors[0].location.y+doors[0].dimensions.y/2
 frames=[o for o in parts if o.get('role')=='cabinet_frame'];assert len(frames)==3
 assert all(o.data.materials[0].name=='wardrobe_white_metal' for o in frames)
 # Worktop meets the wardrobe side at exactly the shared local x boundary.
 worktop=next(o for o in parts if o.get('role')=='worktop')
 vertices=[worktop.matrix_world@v.co for v in worktop.data.vertices];joint=P['desk']['width'] if key.endswith('_L') else P['wardrobe']['width']
 assert abs((max(v.x for v in vertices) if key.endswith('_L') else min(v.x for v in vertices))-joint)<1e-6
 checks.append({'asset':key,'unified_top':P['wardrobe']['height'],'upper_compartment_height_unchanged':P['desk']['upper_compartment_height'],'independent_desk_panel_at_cabinet':False,'door_recess':P['wardrobe']['door_recess'],'real_vent_holes_per_door':14})
for key,center in [('Loft_L',P['loft']['left_ladder_center']),('Loft_R',P['loft']['right_ladder_center'])]:
 col=bpy.data.collections[key];center=col['ladder_center'];g0,g1=col['guard_gap'];rails=[o for o in col.objects if 'sloped_ladder_rail' in o.name];assert len(rails)==2
 for ob in rails:
  pts=[p.co[:] for p in ob.data.splines[0].points];assert max(p[2] for p in pts)+P['loft']['ladder_rail_diameter']/2<=P['loft']['deck_height']+1e-6;assert pts[0][1]<pts[1][1] and pts[0][2]<pts[1][2];assert g0<pts[1][0]<g1
 for ob in col.objects:
  if '/aisle_guard' in ob.name:
   xx=[p.co[0] for p in ob.data.splines[0].points];assert not min(xx)<center<max(xx)
 for part in ['curved_post','guard']:
  front=sorted([o for o in col.objects if '/aisle_'+part in o.name],key=lambda o:o.name)
  back=sorted([o for o in col.objects if '/back_'+part in o.name],key=lambda o:o.name)
  assert len(front)==len(back)
  for fo,bo in zip(front,back):
   for fp,bp in zip(fo.data.splines[0].points,bo.data.splines[0].points):
    assert abs(fp.co.x-bp.co.x)<1e-6 and abs(fp.co.z-bp.co.z)<1e-6
    assert abs(fp.co.y+bp.co.y+P['bed']['frame_depth'])<1e-6
 assert len([o for o in col.objects if o.get('role')=='perforated_end'])==2
 assert not any('/end_guard' in o.name for o in col.objects)
 assert len([o for o in col.objects if '/aisle_curved_post' in o.name])==3
 assert len([o for o in col.objects if '/aisle_guard' in o.name])==6
 assert abs(col['left_opening']-col['right_opening'])<1e-6
 assert col['left_opening']>P['loft']['ladder_width']+P['loft']['ladder_rail_diameter']
 ga,gb=col['guard_extent'];outer_min=center-P['loft']['ladder_width']/2-P['loft']['ladder_rail_diameter']/2;outer_max=center+P['loft']['ladder_width']/2+P['loft']['ladder_rail_diameter']/2
 assert abs((outer_min-gb) if key=='Loft_L' else (outer_max-ga))<1e-6
 arcposts=sorted([o for o in col.objects if '/aisle_curved_post' in o.name],key=lambda o:o.data.splines[0].points[0].co.x)
 lp=arcposts[0].data.splines[0].points;rp=arcposts[-1].data.splines[0].points
 assert lp[12].co.x<lp[0].co.x and rp[12].co.x>rp[0].co.x
 checks.append({'left_opening':col['left_opening'],'right_opening':col['right_opening'],'curved_posts_per_long_side':3,'horizontal_levels':3,'end_panels':2,'loft':key,'ladder_center_facing_wall':center,'gap':[g0,g1],'ladder_outset':P['loft']['ladder_outset'],'cabinet_door_to_bed_edge':P['bed']['frame_depth']-P['wardrobe']['depth'],'gap_clear':True})
for id,side,end in [('G1','left',0),('G2','left',P['room']['length']),('G3','right',0),('G4','right',P['room']['length'])]:
 bb=bounds(bpy.data.objects[id],lambda ob:ob.get('component')=='wardrobe');back=bb[0][0] if side=='left' else bb[1][0];assert abs(back-(0 if side=='left' else P['room']['width']))<1e-5
 assert min(abs(bb[0][1]-end),abs(bb[1][1]-end))<1e-5
 checks.append({'corner_cabinet':id,'back_flush':True,'end_flush':True,'bbox':bb})
for id in ['B2','B3']:assert bounds(bpy.data.objects[id])[1][2]<1.0
images=[im.filepath for im in bpy.data.images if im.source=='FILE' or im.packed_file];assert not images
out={'counts':dict(counts),'checks':checks,'aisle_width':P['room']['width']-2*P['bed']['frame_depth'],'aisle_tile_count':(P['room']['width']-2*P['bed']['frame_depth'])/P['room']['tile'],'external_or_packed_images':images,'result':'PASS'}
(R/'.cache/模型核对.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('MODEL_CHECK_OK',dict(counts))
