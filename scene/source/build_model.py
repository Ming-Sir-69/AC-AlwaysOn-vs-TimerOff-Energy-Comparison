import bpy, bmesh, json, math, hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
(ROOT/'.cache').mkdir(exist_ok=True)
P=json.loads((ROOT/'参数.json').read_text());R=P['room'];D=P['desk'];C=P['wardrobe'];B=P['bed'];F=P['loft'];O=P['openings']
# Longitudinal dimensions follow the desk/cabinet modules automatically.
wall_depth_changed=D['wall_depth']!=C['depth'];D['wall_depth']=C['depth']
derived_loft=D['width']+C['width'];derived_room=2*derived_loft+B['length']
if wall_depth_changed or F.get('length')!=derived_loft or R['length']!=derived_room:
 F['length']=derived_loft;R['length']=derived_room;(ROOT/'参数.json').write_text(json.dumps(P,ensure_ascii=False,indent=2))
W,L,H=R['width'],R['length'],R['height']
assert abs(2*(D['width']+C['width'])+B['length']-L)<1e-7
assert abs(D['width']+C['width']-F['length'])<1e-7
assert abs(W-2*B['frame_depth']-3*R['tile'])<1e-7
assert F['deck_height']-B['deck_thickness']>C['height']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
 if c.users==0:bpy.data.collections.remove(c)
bpy.context.preferences.filepaths.save_version=0
SC=bpy.context.scene;SC.name='宿舍_装配';SC.unit_settings.system='METRIC';SC['parameter_hash']=hashlib.sha256((ROOT/'参数.json').read_bytes()).hexdigest()
LIB=bpy.data.scenes.new('零件库');M={};ASSETS={};ACTIVE=None

def rgb(h):
 c=[int(h[i:i+2],16)/255 for i in (1,3,5)]
 return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)+(1,)
def material(name,key,rough=.7,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');bs.name='Surface';bs.inputs['Base Color'].default_value=rgb(P['palette'].get(key,key));bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
 out=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface']);return m
def micro(m,scale=90,strength=.12,distance=.001):
 n=m.node_tree.nodes;l=m.node_tree.links;no=n.new('ShaderNodeTexNoise');no.inputs['Scale'].default_value=scale;no.inputs['Detail'].default_value=2;b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=strength;b.inputs['Distance'].default_value=distance;l.new(no.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],n['Surface'].inputs['Normal'])
for key in ['wall','skirt','tile','grout','ivory','blue','orange','steel','skirting']:
 M[key]=material(key,key,.85 if key in ['wall','skirt','tile','grout'] else .46,.3 if key in ['blue','steel'] else 0)
M['wardrobe_white_metal']=material('wardrobe_white_metal','ivory',.46,.3)
for k in ['wall','skirt','tile']:micro(M[k])
M['wood']=material('wood','wood_light',.52);n=M['wood'].node_tree.nodes;l=M['wood'].node_tree.links;t=n.new('ShaderNodeTexCoord');v=n.new('ShaderNodeVectorMath');v.operation='MULTIPLY';v.inputs[1].default_value=(3,38,3);l.new(t.outputs['Object'],v.inputs[0]);no=n.new('ShaderNodeTexNoise');no.inputs['Scale'].default_value=2.8;no.inputs['Detail'].default_value=3;l.new(v.outputs[0],no.inputs['Vector']);r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.12;r.color_ramp.elements[0].color=rgb(P['palette']['wood_dark']);r.color_ramp.elements[1].position=.88;r.color_ramp.elements[1].color=rgb(P['palette']['wood_light']);l.new(no.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],n['Surface'].inputs['Base Color']);micro(M['wood'],150,.1,.0007)
M['door_wood']=M['wood'].copy();M['door_wood'].name='vertical_door_wood'
for node in M['door_wood'].node_tree.nodes:
 if node.bl_idname=='ShaderNodeVectorMath' and node.operation=='MULTIPLY':node.inputs[1].default_value=(40,3,1.3)
M['fabric']=material('fabric','fabric',.96);n=M['fabric'].node_tree.nodes;l=M['fabric'].node_tree.links;tc=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');l.new(tc.outputs['Object'],sep.inputs[0]);stripes=[]
for axis in ['X','Y']:
 mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=2*math.pi/.045;l.new(sep.outputs[axis],mul.inputs[0]);sn=n.new('ShaderNodeMath');sn.operation='SINE';l.new(mul.outputs[0],sn.inputs[0]);ab=n.new('ShaderNodeMath');ab.operation='ABSOLUTE';l.new(sn.outputs[0],ab.inputs[0]);gt=n.new('ShaderNodeMath');gt.operation='GREATER_THAN';gt.inputs[1].default_value=.965;l.new(ab.outputs[0],gt.inputs[0]);stripes.append(gt)
mx=n.new('ShaderNodeMath');mx.operation='MAXIMUM';l.new(stripes[0].outputs[0],mx.inputs[0]);l.new(stripes[1].outputs[0],mx.inputs[1]);mix=n.new('ShaderNodeMixRGB');mix.inputs[1].default_value=rgb(P['palette']['fabric']);mix.inputs[2].default_value=rgb(P['palette']['fabric_line']);l.new(mx.outputs[0],mix.inputs[0]);l.new(mix.outputs[0],n['Surface'].inputs['Base Color']);micro(M['fabric'],450,.22,.0008)
M['balcony_titanium']=material('balcony_brushed_titanium','balcony_titanium',.36,.85)
n=M['balcony_titanium'].node_tree.nodes;l=M['balcony_titanium'].node_tree.links;tc=n.new('ShaderNodeTexCoord');vm=n.new('ShaderNodeVectorMath');vm.operation='MULTIPLY';vm.inputs[1].default_value=(900,900,3);l.new(tc.outputs['Object'],vm.inputs[0]);no=n.new('ShaderNodeTexNoise');no.inputs['Scale'].default_value=1;no.inputs['Detail'].default_value=2;l.new(vm.outputs[0],no.inputs['Vector']);bu=n.new('ShaderNodeBump');bu.inputs['Strength'].default_value=.13;bu.inputs['Distance'].default_value=.0002;l.new(no.outputs['Fac'],bu.inputs['Height']);l.new(bu.outputs[0],n['Surface'].inputs['Normal'])
M['glass']=material('frosted_glass','#C9D9D6',.48);M['glass'].node_tree.nodes['Surface'].inputs['Transmission Weight'].default_value=.92
M['lamp']=material('lamp','#F2F0E6',.4);M['lamp'].node_tree.nodes['Surface'].inputs['Emission Color'].default_value=(1,.95,.85,1);M['lamp'].node_tree.nodes['Surface'].inputs['Emission Strength'].default_value=3
M['damp']=M['skirt'].copy();M['damp'].name='damp_skirt';n=M['damp'].node_tree.nodes;l=M['damp'].node_tree.links;geo=n.new('ShaderNodeNewGeometry');sep=n.new('ShaderNodeSeparateXYZ');l.new(geo.outputs['Position'],sep.inputs[0]);z=n.new('ShaderNodeMapRange');z.clamp=True;z.inputs['From Min'].default_value=0;z.inputs['From Max'].default_value=.45;z.inputs['To Min'].default_value=.55;z.inputs['To Max'].default_value=0;l.new(sep.outputs['Z'],z.inputs['Value']);no=n.new('ShaderNodeTexNoise');no.inputs['Scale'].default_value=14;no.inputs['Detail'].default_value=5;l.new(geo.outputs['Position'],no.inputs['Vector']);ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.55;ramp.color_ramp.elements[1].position=.7;l.new(no.outputs['Fac'],ramp.inputs[0]);mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';l.new(z.outputs[0],mul.inputs[0]);l.new(ramp.outputs[0],mul.inputs[1]);mix=n.new('ShaderNodeMixRGB');mix.inputs[1].default_value=rgb(P['palette']['skirt']);mix.inputs[2].default_value=rgb(P['palette']['damp']);l.new(mul.outputs[0],mix.inputs[0]);l.new(mix.outputs[0],n['Surface'].inputs['Base Color'])

def collection(key,title,nominal):
 global ACTIVE
 ACTIVE=bpy.data.collections.new(key);LIB.collection.children.link(ACTIVE);ASSETS[key]={'title':title,'nominal':nominal};return ACTIVE
def adopt(o,name,mat,role='',owner=''):
 for c in list(o.users_collection):c.objects.unlink(o)
 ACTIVE.objects.link(o);o.name=ACTIVE.name+'/'+name
 if hasattr(o.data,'materials'):o.data.materials.append(M[mat])
 o['role']=role;o['wall_owner']=owner;return o
def box(name,loc,size,mat='ivory',role='',owner='',bevel=True):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);adopt(o,name,mat,role,owner)
 if bevel:
  b=o.modifiers.new('edge_radius','BEVEL');b.width=min(P['render']['bevel'],min(size)/4);b.segments=2;o.modifiers.new('weighted_normals','WEIGHTED_NORMAL')
 return o
def tube(name,points,r,mat='steel',role='',owner=''):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=2;cu.bevel_depth=r;cu.bevel_resolution=3;cu.use_fill_caps=True;sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
 for v,p in zip(sp.points,points):v.co=(*p,1)
 o=bpy.data.objects.new(name,cu);ACTIVE.objects.link(o);o.name=ACTIVE.name+'/'+name;cu.materials.append(M[mat]);o['role']=role;o['wall_owner']=owner;return o
def prism(name,pts,z0,z1,mat,role=''):
 vs=[(u,-d,z) for z in [z0,z1] for u,d in pts];N=len(pts);faces=[tuple(reversed(range(N))),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],faces);me.update();o=bpy.data.objects.new(name,me);ACTIVE.objects.link(o);o.name=ACTIVE.name+'/'+name;me.materials.append(M[mat]);o['role']=role
 # Recalculate normals for reflected concave caps.
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 b=o.modifiers.new('edge_radius','BEVEL');b.width=P['render']['bevel'];b.segments=3;return o

def build_desk(hand):
 key='Desk_L' if hand=='left' else 'Desk_R';w=D['width'];dep=D['total_depth'];t=D['board'];h=D['worktop_height'];top=C['height'];shelf=top-D['upper_compartment_height'];wing=D['wing_width'];rr=D['inner_radius'];bd=D['wall_depth'];mirror=hand=='right'
 collection(key,('左手' if not mirror else '右手')+' L 形书桌',{'width':w,'depth':dep,'height':top,'hand':hand})
 def ux(u):return w-u if mirror else u
 def bx(name,u,d,z,su,sd,sz,mat='ivory',role='desk'):return box(name,(ux(u),-d,z),(su,sd,sz),mat,role)
 pts=[(0,0),(w,0),(w,bd),(wing+rr,bd)]
 for i in range(1,25):
  a=-math.pi/2-math.pi/2*i/24;pts.append((wing+rr+rr*math.cos(a),bd+rr+rr*math.sin(a)))
 pts += [(wing,dep),(0,dep)]
 if mirror:pts=[(w-u,d) for u,d in reversed(pts)]
 counter=prism('L_worktop',pts,h-D['worktop_thickness'],h,'wood','worktop');counter['hand']=hand;counter['wing_side']=hand
 cabh=h-D['worktop_thickness'];cabd=dep-D['storage_front_inset']
 bx('storage_bed_side',t/2,cabd/2,cabh/2,t,cabd,cabh)
 bx('storage_front_CLOSED',wing/2,cabd-t/2,cabh/2,wing,t,cabh,role='closed_storage_front')
 bx('storage_back',wing/2,t/2,cabh/2,wing,t,cabh)
 bx('storage_bottom',wing/2,cabd/2,D['storage_plinth'],wing,cabd,t)
 bx('storage_top',wing/2,cabd/2,cabh-t/2,wing,cabd,t)
 for j in range(D['storage_shelves']):bx('storage_internal_shelf',wing/2,cabd/2,(j+1)*cabh/(D['storage_shelves']+1),wing-t,cabd-t,t)
 # Blue doors slide along local depth, never rotate on hinges.
 plen=(cabd-2*t+D['slider_overlap'])/2
 for j in range(2):
  dd=t+plen/2+j*(plen-D['slider_overlap']);dd-=D['slider_open_fraction']*(plen-D['slider_overlap']) if j else 0
  u=wing+(j-.5)*D['slider_panel_thickness']
  o=bx('blue_SLIDING_panel_'+str(j+1),u,dd,cabh/2,D['slider_panel_thickness'],plen,cabh-2*D['storage_plinth'],'blue','sliding_door');o['slide_axis']='local_depth';o['hinges']=0
  bx('slider_recessed_pull_'+str(j+1),u+D['slider_panel_thickness'],dd+(-1 if j else 1)*plen*.32,cabh*.54,D['slider_panel_thickness'],D['slider_pull_width'],D['slider_pull_length'],'skirting','slider_pull')
 for z in [D['storage_plinth'],cabh-D['storage_plinth']]:bx('slider_track',wing, cabd/2,z,D['slider_track'],cabd,D['slider_track'],'steel','slider_track')
 bx('wall_back_panel',w/2,t/2,(top+h)/2,w,t,top-h)
 # Keep the existing below-top support; the upper shelf has only shallow sides.
 bx('bed_side_full_height',t/2,D['hutch_depth']/2,(top+h)/2,t,D['hutch_depth'],top-h,role='bed_side_upper_panel')
 for z in [shelf,top-t/2]:bx('hutch_shelf',w/2,D['hutch_depth']/2,z,w,D['hutch_depth'],t)
 bx('hutch_middle_divider',w/2,D['hutch_depth']/2,(shelf+top)/2,t,D['hutch_depth'],top-shelf)
 fs=[(t,D['fan_shelf_back_offset'])]
 for i in range(25):
  a=i*math.pi/2/24;fs.append((t+D['fan_shelf_radius']*math.cos(a),D['fan_shelf_back_offset']+D['fan_shelf_radius']*math.sin(a)))
 if mirror:fs=[(w-u,d) for u,d in reversed(fs)]
 fan=prism('fan_wood_shelf',fs,D['fan_shelf_height']-t,D['fan_shelf_height'],'wood','fan_shelf');fan['side']=hand
 return key

def build_wardrobe():
 w,dep,h,t=C['width'],C['depth'],C['height'],C['sheet'];collection('Wardrobe','双开门铁皮衣柜',{'width':w,'depth':dep,'height':h})
 for u in [t/2,w-t/2]:box('side',(u,-dep/2,h/2),(t,dep,h),'wardrobe_white_metal')
 for z in [t/2,h-t/2]:box('cap',(w/2,-dep/2,z),(w,dep,t),'wardrobe_white_metal')
 box('back',(w/2,-t/2,h/2),(w,t,h),'wardrobe_white_metal')
 box('plinth',(w/2,-dep/2,C['plinth']/2),(w,dep,C['plinth']),'ivory')
 shelf_depth=dep-C['door_recess']-2*t-.003
 for i in range(C['shelves']):box('internal_shelf',(w/2,-t-shelf_depth/2,h*(i+1)/(C['shelves']+1)),(w-2*t,shelf_depth,t),'ivory')
 # White sheet frame surrounds inset blue doors.
 fs=C['frame_side'];ft=C['frame_top'];pb=C['plinth'];face=-dep+t/2
 for u in [fs/2,w-fs/2]:box('face_side_frame',(u,face,(h+pb)/2),(fs,t,h-pb),'wardrobe_white_metal','cabinet_frame')
 box('face_top_frame',(w/2,face,h-ft/2),(w,t,ft),'wardrobe_white_metal','cabinet_frame')
 door_y=-dep+C['door_recess']+t/2;dw=(w-2*fs-C['door_gap'])/2;dh=h-ft-pb-C['door_gap']
 for j in range(2):
  u=fs+dw/2+j*(dw+C['door_gap'])
  door=box('hinged_door_'+str(j+1),(u,door_y,(pb+h-ft)/2),(dw,t,dh),'blue','wardrobe_door')
  # True ventilation perforations; one boolean per door, baked into its mesh.
  cutters=[];vx=u+(-1 if j==0 else 1)*dw*.28;vz=h-ft-.075
  for row in range(C['vent_rows']):
   for col in range(C['vent_columns']-row):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=C['vent_radius'],depth=t*4,location=(vx+(col-(C['vent_columns']-row-1)/2)*C['vent_spacing'],door_y,vz-row*C['vent_spacing']),rotation=(math.pi/2,0,0));cutters.append(bpy.context.object)
  bpy.ops.object.select_all(action='DESELECT')
  for ob in cutters:ob.select_set(True)
  bpy.context.view_layer.objects.active=cutters[0];bpy.ops.object.join();cutter=bpy.context.object
  mod=door.modifiers.new('actual_vent_holes','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
  SC.collection.objects.link(door);bpy.context.view_layer.objects.active=door;bpy.ops.object.modifier_apply(modifier=mod.name);SC.collection.objects.unlink(door);bpy.data.objects.remove(cutter,do_unlink=True)
  door['vent_holes']=sum(C['vent_columns']-row for row in range(C['vent_rows']))
  hu=w/2+(-1 if j==0 else 1)*C['handle_offset']
  box('orange_handle',(hu,door_y-t,C['handle_center_height']),(C['handle_width'],t,C['handle_height']),'orange')
  box('blank_orange_tag',(u,door_y-t*.75,C['tag_height_z']),(C['tag_width'],t/2,C['tag_height']),'orange')
 return 'Wardrobe'

def perforated_head(name,u,z):
 width=B['mattress_width'];height=B['head_plate_height'];cols=B['head_holes_across'];rows=B['head_holes_rows'];cw=width/cols;ch=height/rows;vv=[];ff=[]
 for j in range(rows):
  for i in range(cols):
   vc=-(B['frame_depth']-width)/2-(i+.5)*cw;zc=z+(j+.5)*ch-height/2;start=len(vv)
   for inner in [False,True]:
    for k in range(16):
     a=math.tau*k/16;xx,yy=math.cos(a),math.sin(a)
     vx=B['head_hole_radius']*xx if inner else cw/2*xx/max(abs(xx),abs(yy));vz=B['head_hole_radius']*yy if inner else ch/2*yy/max(abs(xx),abs(yy))
     vv.append((u,vc+vx,zc+vz))
   for k in range(16):ff.append((start+k,start+(k+1)%16,start+16+(k+1)%16,start+16+k))
 me=bpy.data.meshes.new(name);me.from_pydata(vv,[],ff);me.update();o=bpy.data.objects.new(name,me);ACTIVE.objects.link(o);o.name=ACTIVE.name+'/'+name;me.materials.append(M['blue']);m=o.modifiers.new('steel_plate','SOLIDIFY');m.thickness=B['head_plate_thickness'];o['role']='perforated_head'

M['end_blue_plastic']=material('end_blue_plastic','#5288C5',.58)

def loft_end_panel(name,u,deck):
 width=B['frame_depth']-2*B['post_inset']-F['end_post'];height=F['end_height']-.025;cols=12;rows=4;cw=width/cols;ch=height/rows;vv=[];ff=[]
 for j in range(rows):
  for i in range(cols):
   vc=-B['frame_depth']/2-width/2+(i+.5)*cw;zc=deck+.025+(j+.5)*ch;start=len(vv)
   for inner in [False,True]:
    for k in range(16):
     a=math.tau*k/16;xx,yy=math.cos(a),math.sin(a)
     vx=.006*xx if inner else cw/2*xx/max(abs(xx),abs(yy));vz=.0075*yy if inner else ch/2*yy/max(abs(xx),abs(yy))
     v=vc+vx;z=zc+vz;arch=F['end_arch']*max(0,1-((v+B['frame_depth']/2)/(width/2))**2);z+=arch*(z-deck-.025)/height;vv.append((u,v,z))
   for k in range(16):ff.append((start+k,start+(k+1)%16,start+16+(k+1)%16,start+16+k))
 me=bpy.data.meshes.new(name);me.from_pydata(vv,[],ff);me.update();ob=bpy.data.objects.new(name,me);ACTIVE.objects.link(ob);ob.name=ACTIVE.name+'/'+name;me.materials.append(M['end_blue_plastic']);ob['role']='perforated_end';mod=ob.modifiers.new('plastic_thickness','SOLIDIFY');mod.thickness=.009

def build_bed(key,loft=False,variant=None):
 length,dep=F['length'] if loft else B['length'],B['frame_depth'];deck=F['deck_height'] if loft else B['low_deck_height'];post=F['end_post'] if loft else B['post'];ins=B['post_inset'];hi=deck+(F['end_height']+F['end_arch'] if loft else B['head_height_above_deck'])
 collection(key,('高架床·'+('左墙版' if variant=='left' else '右墙版')) if loft else '落地单人床',{'width':length,'depth':dep+(F['ladder_outset'] if loft else 0),'height':hi+.012 if loft else hi,'bed_depth':dep,'deck':deck,'variant':variant})
 for u in [ins,length-ins]:
  for v in [-ins,-dep+ins]:
   ph=hi if loft or u>length/2 else deck+B['foot_height_above_deck']
   box('frame_post',(u,v,ph/2),(post,post,ph),'steel','bed_structure')
   if loft:box('blue_post_cap',(u,v,ph+.006),(post+.004,post+.004,.012),'end_blue_plastic','post_cap')
 box('deck',(length/2,-dep/2,deck-B['deck_thickness']/2),(length,dep,B['deck_thickness']),'ivory','loft_deck' if loft else 'low_deck')
 mat=box('mattress',(length/2,-dep/2,deck+B['mattress_thickness']/2),(length-2*B['mattress_end_inset'],B['mattress_width'],B['mattress_thickness']),'fabric','loft_mattress' if loft else 'low_mattress')
 mat.modifiers['edge_radius'].width=.025;mat.modifiers['edge_radius'].segments=4
 if not loft:perforated_head('blue_perforated_head',length-ins,deck+B['mattress_thickness']+B['head_plate_height']/2)
 else:
  for u in [ins,length-ins]:loft_end_panel('blue_end_panel',u,deck)
  for u in [ins,length-ins]:box('end_deck_beam',(u,-dep/2,deck-.045),(post,dep,.09),'steel','bed_structure')
 for v in [-ins,-dep+ins]:box('bed_side_beam',(length/2,v,deck-post/2),(length,post,post),'steel','bed_structure')
 if not loft:
  tube('low_foot_rail',[(ins,-ins,deck+B['foot_height_above_deck']),(ins,-dep+ins,deck+B['foot_height_above_deck'])],post/2,'steel','bed_structure');return key
 # Clear end openings measured between the end-post inner face and guard envelope.
 edge=ins+post/2;far=length-edge;laddergap=F['ladder_width']+F['ladder_rail_diameter'];leftgap=rightgap=F['symmetric_end_gap']
 ga=edge+leftgap;gb=far-rightgap;rad=F['guard_post_diameter']/2;center=gb+laddergap/2 if variant=='left' else ga-laddergap/2;g0,g1=(gb,far) if variant=='left' else (edge,ga)
 for side,v in [('aisle',-dep+ins),('back',-ins)]:
  bow_sign=-1 if side=='aisle' else 1
  us=[ga+rad+.02,(ga+gb)/2,gb-rad-.02];bend=[-1,.6,1]
  for u,sg in zip(us,bend):
   tube(side+'_curved_post',[(u+sg*.02*math.sin(math.pi*t/24),v+bow_sign*F['guard_bow']*math.sin(math.pi*t/24),deck+F['guard_top']*t/24) for t in range(25)],rad,'steel','loft_guard')
  for z in [deck+B['mattress_thickness']+.035,deck+.23,deck+F['guard_top']]:
   phase=math.sin(math.pi*(z-deck)/F['guard_top']);bow=bow_sign*F['guard_bow']*phase;xs=[u+sg*.02*phase for u,sg in zip(us,bend)]
   for a,b in zip(xs,xs[1:]):tube(side+'_guard',[(a,v+bow,z),(b,v+bow,z)],F['guard_tube']/2,'steel','loft_guard')
 for u in [center-F['ladder_width']/2,center+F['ladder_width']/2]:
  rr=F['hook_radius'];cz=deck-F['ladder_rail_diameter']/2-rr;cv=-dep+rr
  points=[(u,-dep-F['ladder_outset'],F['foot_height']),(u,-dep,cz)]
  for j in range(1,25):
   a=math.pi-math.pi*j/24;points.append((u,cv+rr*math.cos(a),cz+rr*math.sin(a)))
  points.append((u,-dep+2*rr,cz-.04));tube('sloped_ladder_rail',points,F['ladder_rail_diameter']/2,'steel','ladder')
 ACTIVE['left_opening']=leftgap;ACTIVE['right_opening']=rightgap;ACTIVE['guard_extent']=[ga,gb]
 for k in range(F['ladder_steps']):
  t=(k+1)/(F['ladder_steps']+1);z=F['foot_height']+(deck-F['foot_height'])*t;v=-dep-F['ladder_outset']*(1-t)
  box('flat_ladder_tread',(center,v,z),(F['ladder_width'],F['tread_depth'],F['tread_thickness']),'steel','ladder')
 ACTIVE['ladder_center']=center;ACTIVE['guard_gap']=[g0,g1];return key

def build_shell():
 collection('RoomShell','房间壳体与固定设施',{'width':W,'depth':L,'height':H})
 t=R['wall'];box('slab',(W/2,L/2,-R['floor']/2-R['tile_thickness']),(W,L,R['floor']),'grout','shell_floor')
 xs=[0]+[R['tile_x_phase']+k*R['tile'] for k in range(10) if 0<R['tile_x_phase']+k*R['tile']<W]+[W]
 for i,(x0,x1) in enumerate(zip(xs,xs[1:])):
  for j in range(math.ceil(L/R['tile'])):
   y0=j*R['tile'];y1=min(L,y0+R['tile']);g=R['grout'];box(f'tile_{i}_{j}',((x0+x1)/2,(y0+y1)/2,-R['tile_thickness']/2),(x1-x0-g,y1-y0-g,R['tile_thickness']),'tile','shell_floor',bevel=False)
 def wallrect(name,side,a,b,z0,z1,head=False):
  if b-a<1e-7 or z1-z0<1e-7:return
  for lo,hi,mat in [(z0,min(z1,R['skirt_height']),'damp' if side=='far' else 'skirt'),(max(z0,R['skirt_height']),z1,'wall')]:
   if hi<=lo:continue
   loc=((a+b)/2,(-t/2 if side=='near' else L+t/2),(lo+hi)/2) if side in ['near','far'] else ((-t/2 if side=='west' else W+t/2),(a+b)/2,(lo+hi)/2)
   size=(b-a,t,hi-lo) if side in ['near','far'] else (t,b-a,hi-lo)
   box(name,loc,size,mat,'wall_head' if head else 'wall',side)
 wallrect('west_wall','west',0,L,0,H);wallrect('east_wall','east',0,L,0,H)
 for side,holes in [('near',[(W/2-O['entry_width']/2,W/2+O['entry_width']/2,0,O['entry_height'])]),('far',[(O['window_start_x']+i*(O['window_width']+O['window_gap']),O['window_start_x']+i*(O['window_width']+O['window_gap'])+O['window_width'],O['window_sill'],O['window_sill']+O['window_height']) for i in range(2)]+[(W/2-O['balcony_width']/2,W/2+O['balcony_width']/2,0,O['balcony_height'])])]:
  ends=sorted(set([0,W]+[v for h in holes for v in h[:2]]))
  for a,b in zip(ends,ends[1:]):
   hole=next((h for h in holes if h[0]<= (a+b)/2<=h[1]),None)
   if hole:wallrect(side+'_sill',side,a,b,0,hole[2]);wallrect(side+'_lintel',side,a,b,hole[3],H,True)
   else:wallrect(side+'_pier',side,a,b,0,H)
 # Ceiling and thin dark skirting; separate wall owners make clean cuts reproducible.
 box('ceiling',(W/2,L/2,H+t/2),(W,L,t),'wall','ceiling','ceiling')
 for side,x in [('west',R['skirting_thickness']/2),('east',W-R['skirting_thickness']/2)]:box('skirting_'+side,(x,L/2,R['skirting_height']/2),(R['skirting_thickness'],L,R['skirting_height']),'skirting','fixed',side)
 for a,b in [(0,W/2-O['balcony_width']/2),(W/2+O['balcony_width']/2,W)]:box('far_skirting',((a+b)/2,L-R['skirting_thickness']/2,R['skirting_height']/2),(b-a,R['skirting_thickness'],R['skirting_height']),'skirting','fixed','far')
 for i in range(2):
  x=O['window_start_x']+i*(O['window_width']+O['window_gap'])+O['window_width']/2;z=O['window_sill']+O['window_height']/2;fw=O['window_frame']
  box('frosted_window_'+str(i+1),(x,L+t/2,z),(O['window_width'],O['glass'],O['window_height']),'glass','window','far')
  for xx in [x-O['window_width']/2,x+O['window_width']/2]:box('window_jamb',(xx,L+t/2,z),(fw,t,O['window_height']),'ivory','window_frame','far')
  for zz in [O['window_sill'],O['window_sill']+O['window_height']]:box('window_rail',(x,L+t/2,zz),(O['window_width'],t,fw),'ivory','window_frame','far')
 for side,yy,ww,hh,angle in [('near',0,O['entry_width'],O['entry_height'],O['entry_angle_deg']),('far',L,O['balcony_width'],O['balcony_height'],O['balcony_angle_deg'])]:
  x0=W/2-ww/2;ang=math.radians(angle);th=O['door_thickness']
  rig=bpy.data.objects.new('door_pose_'+side,None);ACTIVE.objects.link(rig);rig.name=ACTIVE.name+'/door_pose_'+side;rig.location=(x0,yy,0);rig.rotation_euler.z=ang;rig['role']='door_rig';rig['wall_owner']=side
  def leafbox(name,loc,size,mat):
   ob=box(name,loc,size,mat,'door',side);ob.parent=rig;return ob
  if side=='near':leafbox('entry_leaf',(ww/2,0,hh/2),(ww,th,hh),'door_wood')
  else:
   split=hh*O['balcony_split_fraction'];bottom=split+O['balcony_crossbar']/2;top=hh-O['leaf_frame']
   leafbox('balcony_glass',(ww/2,0,(bottom+top)/2),(ww-2*O['leaf_frame'],O['glass'],top-bottom),'glass')
   leafbox('balcony_metal_lower',(ww/2,0,split/2),(ww,th,split),'balcony_titanium')
   for uu in [O['leaf_frame']/2,ww-O['leaf_frame']/2]:leafbox('balcony_leaf_stile',(uu,0,hh/2),(O['leaf_frame'],th,hh),'balcony_titanium')
   leafbox('balcony_leaf_top',(ww/2,0,hh-O['leaf_frame']/2),(ww,th,O['leaf_frame']),'balcony_titanium')
   leafbox('balcony_midrail',(ww/2,0,split),(ww,th,O['balcony_crossbar']),'balcony_titanium')
  sg=1 if side=='near' else -1;hu=ww-O['handle_offset'] if side=='near' else O['handle_offset'];hv=sg*(th/2+O['handle_plate_thickness']/2)
  leafbox('door_handle_plate',(hu,hv,O['handle_height']),(O['handle_plate_width'],O['handle_plate_thickness'],O['handle_plate_height']),'steel' if side=='near' else 'balcony_titanium')
  if side=='far':
   ob=tube('balcony_L_lever',[(hu,sg*th/2,O['handle_height']),(hu,sg*(th/2+O['handle_projection']),O['handle_height']),(hu+O['handle_length'],sg*(th/2+O['handle_projection']),O['handle_height'])],O['handle_radius'],'balcony_titanium','door',side);ob.parent=rig
  else:ob=tube('door_lever',[(hu-O['handle_length']/2,sg*(th/2+O['handle_projection']),O['handle_height']),(hu+O['handle_length']/2,sg*(th/2+O['handle_projection']),O['handle_height'])],O['handle_radius'],'steel','door',side);ob.parent=rig
  for x in [W/2-ww/2,W/2+ww/2]:box('door_jamb',(x,yy,hh/2),(O['door_frame'],t,hh),'ivory' if side=='near' else 'balcony_titanium','door_frame',side)
  box('door_head',(W/2,yy,hh),(ww,t,O['door_frame']),'ivory' if side=='near' else 'balcony_titanium','wall_head',side)
 a=P['ac'];al=O['window_start_x']+O['window_width']+O['window_gap']-O['window_frame']/2;ar=W/2;aw=ar-al;ax=(al+ar)/2;ah=a['height']*aw/a['width'];ad=a['depth']*aw/a['width']
 box('AC',(ax,L-ad/2,a['center_z']),(aw,ad,ah),'ivory','ac','far');box('AC_outlet',(ax,L-ad-.002,a['center_z']-ah*.25),(aw*.86,.006,a['outlet_height']),'skirting','ac','far')
 li=P['lights']
 for i,y in enumerate(li['y_centers']):box('ceiling_strip_'+str(i+1),(W/2,y,H-li['ceiling_gap']),(li['width'],li['length'],li['height']),'lamp','ceiling_light','ceiling')
 pi=P['pier'];box('entry_pilaster',(pi['center_x'],pi['depth']/2,H/2),(pi['width'],pi['depth'],H),'wall','fixed','near')
 for i,path in enumerate(P['conduit']['paths']):tube('surface_conduit_'+str(i),path['points'],P['conduit']['radius'],'ivory','fixed',path['wall'])
 place_ceiling_fans()
 return 'RoomShell'

def build_desk_cabinet_groups():
 build_desk('left');build_desk('right');build_wardrobe()
 wardrobe=bpy.data.collections['Wardrobe']
 for hand,key,deskkey in [('left','DeskCab_L','Desk_L'),('right','DeskCab_R','Desk_R')]:
  group=collection(key,'桌柜组 · '+('左手' if hand=='left' else '右手'),{'width':D['width']+C['width'],'depth':D['total_depth'],'height':C['height'],'hand':hand})
  desk=bpy.data.collections[deskkey];shift=0 if hand=='left' else C['width']
  for ob in list(desk.objects):
   desk.objects.unlink(ob);group.objects.link(ob);ob.name=key+'/'+ob.name.split('/')[-1];ob.location.x+=shift;ob['component']='desk'
  for ob in wardrobe.objects:
   new=ob.copy();new.data=ob.data.copy();group.objects.link(new);new.location.x+=D['width'] if hand=='left' else 0;new.name=key+'/cab_'+ob.name.split('/')[-1];new['component']='wardrobe'
  bpy.data.collections.remove(desk);del ASSETS[deskkey]
 for ob in list(wardrobe.objects):bpy.data.objects.remove(ob,do_unlink=True)
 bpy.data.collections.remove(wardrobe);del ASSETS['Wardrobe']
exec(compile((ROOT/'source/build_fan.py').read_text(),str(ROOT/'source/build_fan.py'),'exec'))
build_ceiling_fan()
build_desk_cabinet_groups();build_bed('LowBed');build_bed('Loft_L',True,'left');build_bed('Loft_R',True,'right');build_shell()
ASSEMBLY=bpy.data.collections.new('装配实例');SC.collection.children.link(ASSEMBLY);instances=[]
def instance(id,key,x,y,angle,side):
 ob=bpy.data.objects.new(id,None);ob.instance_type='COLLECTION';ob.instance_collection=bpy.data.collections[key];ob.location=(x,y,0);ob.rotation_euler.z=math.radians(angle);ASSEMBLY.objects.link(ob);ob['asset']=key;ob['side']=side;ob.empty_display_size=.15;instances.append({'id':id,'asset':key,'side':side,'origin':[x,y,0],'angle':angle});return ob
instance('Room','RoomShell',0,0,0,'shell')
for args in [('G1','DeskCab_R',0,0,90,'left'),('B1','Loft_L',0,0,90,'left'),('B2','LowBed',0,F['length'],90,'left'),('G2','DeskCab_L',0,L-F['length'],90,'left'),('G3','DeskCab_L',W,F['length'],-90,'right'),('B3','LowBed',W,F['length']+B['length'],-90,'right'),('G4','DeskCab_R',W,L,-90,'right'),('B4','Loft_R',W,L,-90,'right')]:instance(*args)
# Studio lighting exists only in scene, never as room fixtures.
SC.world=bpy.data.worlds.new('Room world');SC.world.use_nodes=True;next(n for n in SC.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.75,.8,.85,1);next(n for n in SC.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.18
for name,pos,target,power,size in [('Window daylight',(W/2,L+.8,2.3),(W/2,1,1),550,2.0),('Scene fill',(W/2,1,5),(W/2,L/2,0),700,5.0)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o['display_light']=True
bpy.ops.object.camera_add(location=(-6,-8,7));SC.camera=bpy.context.object;SC.camera.name='SceneCamera';SC.camera.rotation_euler=(Vector((W/2,L/2,1))-SC.camera.location).to_track_quat('-Z','Y').to_euler();SC.camera.data.type='ORTHO';SC.camera.data.ortho_scale=10
SC.render.engine='CYCLES';SC.cycles.device='CPU';SC.cycles.use_denoising=True;SC.cycles.use_adaptive_sampling=True;SC.cycles.adaptive_threshold=P['render']['adaptive_threshold'];SC.view_settings.view_transform='AgX';SC.view_settings.look='AgX - Medium High Contrast'
SC['model_description']='统一参数化宿舍；所有视角复用同一组零件集合'
meta={'parameter_hash':SC['parameter_hash'],'assets':ASSETS,'instances':instances,'clear_aisle':W-2*B['frame_depth'],'tile_columns_in_aisle':(W-2*B['frame_depth'])/R['tile'],'tile_rows':L/R['tile'],'assumptions':P['assumptions']}
(ROOT/'model_index.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
exec(compile((ROOT/'source/refine_materials.py').read_text(),str(ROOT/'source/refine_materials.py'),'exec'))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'dormitory.blend'))
print('MODEL_BUILD_OK',len(ASSETS),'assets',len(instances)-1,'furniture instances')
