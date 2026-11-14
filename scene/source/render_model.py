import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1]
(ROOT/'.cache').mkdir(exist_ok=True);P=json.loads((ROOT/'参数.json').read_text());META=json.loads((ROOT/'model_index.json').read_text());W,L,H=[P['room'][k] for k in ['width','length','height']]
SC=bpy.data.scenes['宿舍_装配'];args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [];USE_METAL='--metal' in args;args=[a for a in args if a!='--metal'];stage=args[0] if args else 'parts';selected=args[1:] or list(META['assets'])
if USE_METAL:
 pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='METAL';pref.get_devices();assert any(d.type=='METAL' for d in pref.devices)
 for device in pref.devices:device.use=device.type=='METAL'
 print('Using Metal GPU',flush=True)
def reset():
 for o in bpy.data.objects:o.hide_render=False
 for o in bpy.data.objects:
  if o.get('display_light'):o.hide_render=False

def setup(sc,x,y,samples):
 sc.render.engine='CYCLES';sc.cycles.device='GPU' if USE_METAL else 'CPU';sc.cycles.samples=samples;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=P['render']['adaptive_threshold'];sc.cycles.use_denoising=True
 sc.render.resolution_x=x;sc.render.resolution_y=y;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.film_transparent=True;sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast'
def camera(sc,name,pos,target,points,margin=1.15,persp=None,fit_perspective=False):
 data=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,data);sc.collection.objects.link(o);o.location=pos;q=(Vector(target)-o.location).to_track_quat('-Z','Y');o.rotation_euler=q.to_euler();data.type='PERSP' if persp else 'ORTHO';data.sensor_fit='HORIZONTAL';data.clip_start=.015;data.clip_end=150;sc.camera=o
 if persp:
  data.lens=persp
  if fit_perspective:
   right=q@Vector((1,0,0));up=q@Vector((0,1,0));forward=(Vector(target)-Vector(pos)).normalized();aspect=sc.render.resolution_x/sc.render.resolution_y;th=data.sensor_width/(2*persp);tv=th/aspect;need=0
   for point in points:
    v=Vector(point)-Vector(target);depth=v.dot(forward);need=max(need,abs(v.dot(right))*margin/th-depth,abs(v.dot(up))*margin/tv-depth)
   o.location=Vector(target)-forward*need
 else:
  right=q@Vector((1,0,0));up=q@Vector((0,1,0));xx=[Vector(p).dot(right) for p in points];yy=[Vector(p).dot(up) for p in points];aspect=sc.render.resolution_x/sc.render.resolution_y;data.ortho_scale=max(max(xx)-min(xx),(max(yy)-min(yy))*aspect)*margin
 sc.view_layers[0].update();return o
def bbox(col):
 def hierarchy_matrix(ob):
  return hierarchy_matrix(ob.parent)@ob.matrix_parent_inverse@ob.matrix_basis if ob.parent else ob.matrix_basis
 ps=[]
 for o in col.objects:
  if o.type in ['MESH','CURVE']:
   if col.name=='CeilingFan':
    if o.type=='MESH':ps += [hierarchy_matrix(o)@v.co for v in o.data.vertices]
    else:ps += [hierarchy_matrix(o)@Vector(p.co[:3]) for sp in o.data.splines for p in sp.points]
   else:ps += [o.matrix_world@Vector(v) for v in o.bound_box]
 lo=[min(v[i] for v in ps) for i in range(3)];hi=[max(v[i] for v in ps) for i in range(3)];corners=[(x,y,z) for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]];return lo,hi,corners

def coords(sc,points):
 out=[]
 for v in points:
  c=world_to_camera_view(sc,sc.camera,Vector(v));out.append([c.x*sc.render.resolution_x,(1-c.y)*sc.render.resolution_y])
 return out

def render(sc,file):
 file.parent.mkdir(parents=True,exist_ok=True);sc.render.filepath=str(file);print('RENDER',file.name,flush=True);bpy.ops.render.render(write_still=True,scene=sc.name)

def addarea(sc,name,pos,target,energy,size):
 dat=bpy.data.lights.new(name,'AREA');dat.energy=energy;dat.shape='DISK';dat.size=size;o=bpy.data.objects.new(name,dat);sc.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o

if stage=='parts':
 card=bpy.data.scenes.new('零件卡');card.world=bpy.data.worlds.new('Card world');card.world.use_nodes=True
 bg=next(n for n in card.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.8,.8,.8,1);bg.inputs['Strength'].default_value=.65
 setup(card,800,560,P['render']['card_samples']);meta={}
 for key in selected:
  reset();col=bpy.data.collections[key];lo,hi,corners=bbox(col);center=Vector([(a+b)/2 for a,b in zip(lo,hi)]);inst=bpy.data.objects.new('Card instance',None);inst.instance_type='COLLECTION';inst.instance_collection=col;card.collection.objects.link(inst)
  dim=max(hi[i]-lo[i] for i in range(3));lights=[addarea(card,'Card softbox',center+Vector((dim,-dim,dim*2)),center,350*max(1,dim),max(2,dim*1.5)),addarea(card,'Card fill',center+Vector((-dim,0,dim)),center,150*max(1,dim),max(2,dim))]
  if key=='CeilingFan':
   lights[0].data.energy=35;lights[1].data.energy=12;lights[0].data.size=1;lights[1].data.size=1
  info={'title':META['assets'][key]['title'],'nominal':META['assets'][key]['nominal'],'bbox':[lo,hi],'views':{}}
  sign=-1 if key in ['Desk_R','DeskCab_R','RoomShell'] else 1
  for view,offset in [('front',(0,-12,0)),('side',(12*sign,0,0)),('top',(0,0,12)),('iso',(6*sign,-8,6))]:
   reset()
   if key=='RoomShell':
    for o in col.objects:
     owner=o.get('wall_owner','');role=o.get('role','')
     o.hide_render=(role=='ceiling' or (view=='front' and owner=='near') or (view=='side' and owner=='west') or (view=='iso' and owner in ['near','west']) or (view=='top' and role=='wall_head'))
   if key in ['Loft_L','Loft_R'] and view=='front':
    for o in col.objects:
     if '/back_guard' in o.name or '/back_curved_post' in o.name:o.hide_render=True
   cam=camera(card,'Card camera',center+Vector(offset),center,corners,1.20);file=ROOT/'零件卡/底图'/f'{key}_{view}.png';render(card,file)
   if key in ['Loft_L','Loft_R'] and view=='front':
    edge=P['bed']['post_inset']+P['loft']['end_post']/2;ga,gb=col['guard_extent'];z=P['loft']['deck_height']+P['loft']['end_height']+P['loft']['end_arch']+.13;info['openings']=[{'width':col['left_opening'],'points':coords(card,[(edge,0,z),(ga,0,z)])},{'width':col['right_opening'],'points':coords(card,[(gb,0,z),(P['loft']['length']-edge,0,z)])}]
   info['views'][view]={'file':str(file.relative_to(ROOT)),'bbox_pixels':coords(card,corners)};bpy.data.objects.remove(cam,do_unlink=True)
  meta[key]=info;bpy.data.objects.remove(inst,do_unlink=True)
  for o in lights:bpy.data.objects.remove(o,do_unlink=True)
 old=ROOT/'.cache/零件卡投影.json';prior=json.loads(old.read_text()) if old.exists() else {};prior.update(meta);old.write_text(json.dumps(prior,ensure_ascii=False,indent=2))
 print('PARTS_OK',len(meta))
else:
 review=[o for o in SC.objects if o.get('display_light')];points=[(x,y,z) for x in [0,W] for y in [0,L] for z in [0,H]];center=Vector((W/2,L/2,H/2));meta={}
 def cut(kind):
  reset()
  for o in bpy.data.collections['RoomShell'].objects:
   role=o.get('role','');owner=o.get('wall_owner','')
   if kind=='top':o.hide_render=role in ['ceiling','wall_head']
   elif kind=='left':o.hide_render=role=='ceiling' or owner in ['east','near','far']
   elif kind=='right':o.hide_render=role=='ceiling' or owner in ['west','near','far']
   elif kind=='overview':o.hide_render=role=='ceiling' or owner=='near'
  for ob in bpy.data.collections['装配实例'].objects:
   if kind=='left' and ob.get('side')=='right':ob.hide_render=True
   if kind=='right' and ob.get('side')=='left':ob.hide_render=True
  if kind in ['left','right']:
   for key in ['Loft_L','Loft_R']:
    for o in bpy.data.collections[key].objects:
     if '/back_guard' in o.name or '/back_curved_post' in o.name:o.hide_render=True
  if kind=='top':
   for key in ['Loft_L','Loft_R']:
    for o in bpy.data.collections[key].objects:
     if o.get('role') in ['loft_deck','loft_mattress','perforated_head']:o.hide_render=True
 if stage=='orthos':
  for key,pos,target,sz in [('top',(W/2,L/2,14),(W/2,L/2,0),(1400,1600)),('left',(W+8,L/2,H/2),(0,L/2,H/2),(2400,1000)),('right',(-8,L/2,H/2),(W,L/2,H/2),(2400,1000))]:
   cut(key);setup(SC,*sz,P['render']['ortho_samples']);camera(SC,'正交_'+key,pos,target,points,1.15)
   file=ROOT/'正交图/底图'/f'{key}.png';render(SC,file)
   anchors={}
   for ob in bpy.data.collections['装配实例'].objects:
    if ob.name.startswith('B'):
     v=((P['loft']['length'] if ob['asset'].startswith('Loft') else P['bed']['length'])/2,-P['bed']['frame_depth']/2,P['loft']['deck_height'] if ob['asset'].startswith('Loft') else P['bed']['low_deck_height']);anchors[ob.name]=coords(SC,[ob.matrix_world@Vector(v)])[0]
    elif ob.name.startswith('G'):
     left=ob['asset']=='DeskCab_L';dw=P['desk']['width'];cw=P['wardrobe']['width']
     for prefix,v in [('D',((0 if left else cw)+(P['desk']['wing_width']/2 if left else dw-P['desk']['wing_width']/2),-P['desk']['total_depth']*.82,P['desk']['worktop_height'])),('C',((dw if left else 0)+cw/2,-P['wardrobe']['depth']/2,P['wardrobe']['height']))]:anchors[prefix+ob.name[1:]]=coords(SC,[ob.matrix_world@Vector(v)])[0]
   for idx,y in enumerate([P['lights']['y_centers'][0]/2,sum(P['lights']['y_centers'])/2],1):anchors['F'+str(idx)]=coords(SC,[(W/2,y,H-P['fan']['overall_height']+P['fan']['head_center_height'])])[0]
   for name,v in {'origin':(0,0,0),'width':(W,0,0),'length':(0,L,0),'ceiling':(0,0,H),'entry':(W/2,0,0),'balcony':(W/2,L,0),'ac':(P['ac']['center_x'],L,P['ac']['center_z'])}.items():anchors[name]=coords(SC,[v])[0]
   meta[key]={'file':str(file.relative_to(ROOT)),'anchors':anchors,'loft_outlines':[coords(SC,[(0,0,0),(.95,0,0),(.95,P['loft']['length'],0),(0,P['loft']['length'],0)]),coords(SC,[(W-.95,L-P['loft']['length'],0),(W,L-P['loft']['length'],0),(W,L,0),(W-.95,L,0)])]}
  (ROOT/'.cache/正交投影.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));print('ORTHOS_OK')
 elif stage in ['preview','final']:
  final=stage=='final';res=P['render']['final_width'] if final else P['render']['preview_width'];samples=P['render']['final_samples'] if final else P['render']['preview_samples']
  views=[('进门',(W/2,.28,1.55),(W/2,L-.1,1.4),23,'interior'),('阳台回望',(W/2,L-.24,1.55),(W/2,0,1.4),23,'interior'),('俯视全景',(W/2+.25,-6,7.5),(W/2,L/2,.9),42,'overview'),('左墙侧视',(W+1.0,L/2,1.5),(0,L/2,1.35),18,'left'),('右墙侧视',(-1.0,L/2,1.5),(W,L/2,1.35),18,'right')]
  if len(args)>1:views=[v for v in views if v[0] in args[1:]]
  for name,pos,target,lens,kind in views:
   cut(kind)
   for partkey in ['Loft_L','Loft_R']:
    for ob in bpy.data.collections[partkey].objects:
     if '/back_guard' in ob.name or '/back_curved_post' in ob.name:ob.hide_render=False
   if kind in ['left','right']:
    for ob in bpy.data.collections['RoomShell'].objects:
     if ob.get('role')=='ceiling' or ob.get('wall_owner') in ['near','far']:ob.hide_render=False
   setup(SC,round(res*.76) if kind=='overview' else res,res if kind=='overview' else round(res*.667),samples);SC.render.film_transparent=False
   if kind!='overview':
    for o in review:
     if o.name.startswith('Scene fill'):o.data.energy=18;o.location=(W/2,L/2,H-.15);o.rotation_euler=(Vector((W/2,L/2,0))-o.location).to_track_quat('-Z','Y').to_euler()
   else:
    for o in review:
     if o.name.startswith('Scene fill'):o.data.energy=90;o.location=(W/2,1,5);o.rotation_euler=(Vector((W/2,L/2,0))-o.location).to_track_quat('-Z','Y').to_euler()
   camera(SC,'渲染_'+name,pos,target,points,1.06,lens,kind=='overview');file=ROOT/'renders'/('' if final else '预览')/(name+'.png');render(SC,file)
  print('BEAUTY_OK',stage)
reset();bpy.context.window.scene=SC
defcam=bpy.data.objects.get('SceneCamera')
if defcam:
 defcam.location=(W/2,.28,1.55);defcam.rotation_euler=(Vector((W/2,L-.1,1.4))-defcam.location).to_track_quat('-Z','Y').to_euler();defcam.data.type='PERSP';defcam.data.lens=23;SC.camera=defcam
bpy.context.preferences.filepaths.save_version=0
# Keep the saved file portable; --metal only controls the render session.
SC.cycles.device='CPU'
# Rendering adds inspection cameras but does not rebuild or move furniture.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'dormitory.blend'))
