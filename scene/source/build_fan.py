# Shared native fan geometry; no product imagery is embedded.
def build_ceiling_fan():
 global ACTIVE
 fa=P['fan'];collection('CeilingFan','吸顶摇头风扇 · 无字圆标',{'width':fa['diameter'],'depth':fa['diameter'],'height':fa['overall_height']})
 M['fan_white']=material('fan_white','#EEEFEA',.30)
 M['fan_wire']=material('fan_white_wire','#F2F2ED',.32,.22)
 M['fan_blade']=material('fan_translucent_petals','#DAE2E2',.24);M['fan_blade'].node_tree.nodes['Surface'].inputs['Transmission Weight'].default_value=.42;M['fan_blade'].node_tree.nodes['Surface'].inputs['IOR'].default_value=1.46
 M['fan_ring']=material('fan_badge_grey','#B2B6B6',.5)
 def empty(name,parent=None,loc=(0,0,0)):
  ob=bpy.data.objects.new('CeilingFan/'+name,None);ACTIVE.objects.link(ob);ob.parent=parent;ob.location=loc;ob['role']='fan';return ob
 root=empty('mount_root');yaw=empty('head_yaw',root,(0,0,fa['head_center_height']));pitch=empty('head_pitch',yaw);pitch.rotation_euler.x=math.radians(fa['card_pitch_deg']);yaw['rotation_range_deg']=360
 def cyl(name,loc,radius,depth,mat='fan_white',parent=root,axis='Z'):
  bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth,location=loc);ob=adopt(bpy.context.object,name,mat,'fan');ob.parent=parent
  if axis=='Y':ob.rotation_euler.x=math.pi/2
  b=ob.modifiers.new('soft_rim','BEVEL');b.width=.002;b.segments=3
  for poly in ob.data.polygons:poly.use_smooth=True
  ob.modifiers.new('weighted_normals','WEIGHTED_NORMAL');return ob
 def line(name,pts,r,mat='fan_wire',parent=pitch):
  ob=tube(name,pts,r,mat,'fan');ob.parent=parent;return ob
 top=fa['overall_height'];cyl('ceiling_cylinder',(0,0,top-.045),.072,.09);cyl('rotating_neck',(0,0,top-.112),.045,.05)
 cyl('oscillation_housing',(0,0,top-.15),.054,.065)
 line('pivot_fork_left',[(-.043,0,top-.16),(-.043,0,fa['head_center_height'])],.012,'fan_white',root)
 line('pivot_fork_right',[(.043,0,top-.16),(.043,0,fa['head_center_height'])],.012,'fan_white',root)
 cyl('motor_body',(0,.095,0),.057,.105,parent=pitch,axis='Y');cyl('motor_back',(0,.152,0),.046,.014,parent=pitch,axis='Y')
 for k in range(18):
  a=math.tau*k/18;line('motor_vent',[(.046*math.cos(a),.16,.046*math.sin(a)),(.032*math.cos(a),.16,.032*math.sin(a))],.0009,'fan_ring')
 R=fa['diameter']/2
 for side in [-1,1]:
  depth=fa['front_dome'] if side==-1 else fa['back_dome']
  def yy(r):return side*depth*(1-(r/R)**2)
  for fraction in [.28,.60,.86,1]:
   rr=R*fraction;line('front_ring' if side==-1 else 'rear_ring',[(rr*math.cos(math.tau*k/128),yy(rr),rr*math.sin(math.tau*k/128)) for k in range(129)],fa['wire_radius'] if fraction<1 else fa['rim_radius'])
  for k in range(fa['spokes']):
   aa=math.tau*k/fa['spokes'];pts=[]
   for j in range(18):
    rr=.04+(R-.04)*j/17;a=aa+.06*(rr/R);pts.append((rr*math.cos(a),yy(rr),rr*math.sin(a)))
   line('front_wire' if side==-1 else 'rear_wire',pts,fa['wire_radius'])
 # Thick outside seam and four clasp blocks.
 for k in range(4):
  a=math.tau*k/4;ob=box('cage_clasp',(R*math.cos(a),0,R*math.sin(a)),(.012,.018,.018),'fan_white','fan');ob.parent=pitch
 cyl('blank_badge',(0,-fa['front_dome']-.003,0),.047,.007,parent=pitch,axis='Y')
 line('badge_thin_grey_ring',[(.038*math.cos(math.tau*k/96),-fa['front_dome']-.007,.038*math.sin(math.tau*k/96)) for k in range(97)],.00065,'fan_ring')
 # Closed Catmull-Rom petals, with subtle camber and translucent plastic.
 control=[(-.025,.025),(-.080,.09),(-.108,.155),(-.055,.192),(.035,.191),(.080,.165),(.043,.107),(.024,.035)]
 outline=[]
 for i in range(len(control)):
  p0=Vector(control[(i-1)%len(control)]);p1=Vector(control[i]);p2=Vector(control[(i+1)%len(control)]);p3=Vector(control[(i+2)%len(control)])
  for j in range(10):
   t=j/10;v=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t);outline.append(v)
 for k in range(3):
  a=math.tau*k/3;verts=[]
  for p in outline:
   x,z=p;xx=x*math.cos(a)-z*math.sin(a);zz=x*math.sin(a)+z*math.cos(a);verts.append((xx,.006*math.sin(x*20)+.005,zz))
  me=bpy.data.meshes.new('petal');me.from_pydata(verts,[],[tuple(range(len(verts)))]);me.update();ob=bpy.data.objects.new('CeilingFan/petal_'+str(k+1),me);ACTIVE.objects.link(ob);me.materials.append(M['fan_blade']);ob.parent=pitch;ob['role']='fan_blade';sol=ob.modifiers.new('thin_plastic','SOLIDIFY');sol.thickness=.0015
 cyl('blade_hub',(0,-.005,0),.032,.026,parent=pitch,axis='Y')
 LIB.view_layers[0].update()

def place_ceiling_fans():
 col=bpy.data.collections['CeilingFan'];fa=P['fan']
 for idx,pose in enumerate(fa['poses'],1):
  mapping={}
  for ob in col.objects:
   cp=ob.copy();ACTIVE.objects.link(cp);cp.name='RoomShell/fan'+str(idx)+'_'+ob.name.split('/')[-1];cp['wall_owner']='ceiling';cp['role']='fan';mapping[ob]=cp
  for old,cp in mapping.items():cp.parent=mapping.get(old.parent)
  root=next(cp for old,cp in mapping.items() if old.name.endswith('/mount_root'));root.location=(W/2,pose['y'],H-fa['overall_height']);root['fan_id']=idx
  yaw=next(cp for old,cp in mapping.items() if old.name.endswith('/head_yaw'));yaw.rotation_euler.z=math.radians(pose['yaw_deg']);yaw['yaw_deg']=pose['yaw_deg']
  pitch=next(cp for old,cp in mapping.items() if old.name.endswith('/head_pitch'));pitch.rotation_euler.x=math.radians(pose['pitch_deg']);pitch['pitch_deg']=pose['pitch_deg']
