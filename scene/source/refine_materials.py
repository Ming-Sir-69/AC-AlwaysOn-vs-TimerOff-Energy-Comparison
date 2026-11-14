# Procedural surface and daylight pass. Furniture dimensions and assembly untouched.
def noise_color(mat,low,high,scale,random=False):
 n=mat.node_tree.nodes;l=mat.node_tree.links
 tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=scale;tex.inputs['Detail'].default_value=3
 co=n.new('ShaderNodeTexCoord');l.new(co.outputs['Object'],tex.inputs['Vector']);fac=tex.outputs['Fac']
 if random:
  info=n.new('ShaderNodeObjectInfo');mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.16;l.new(fac,mix.inputs[1]);l.new(info.outputs['Random'],mix.inputs[2]);fac=mix.outputs[0]
 ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=rgb(low);ramp.color_ramp.elements[1].color=rgb(high);l.new(fac,ramp.inputs[0]);l.new(ramp.outputs[0],n['Surface'].inputs['Base Color'])
noise_color(M['tile'],'#93938F','#B4B1A9',5,True)
noise_color(M['wall'],'#D9D0BE','#EEE8DC',2.4)
M['tile'].node_tree.nodes['Surface'].inputs['Roughness'].default_value=.86
M['blue'].node_tree.nodes['Surface'].inputs['Roughness'].default_value=.34
micro(M['blue'],240,.10,.00025)
M['lamp'].node_tree.nodes['Surface'].inputs['Emission Strength'].default_value=0
# Muted blue-grey woven checks: 9cm pitch, broad secondary bands, tiny thread relief.
m=M['fabric'];n=m.node_tree.nodes;l=m.node_tree.links
for node in list(n):
 if node.name!='Surface' and node.type!='OUTPUT_MATERIAL':n.remove(node)
tc=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');l.new(tc.outputs['Object'],sep.inputs[0]);bands=[]
for axis in ['X','Y']:
 mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=math.tau/.09;l.new(sep.outputs[axis],mul.inputs[0]);sn=n.new('ShaderNodeMath');sn.operation='SINE';l.new(mul.outputs[0],sn.inputs[0]);gt=n.new('ShaderNodeMath');gt.operation='GREATER_THAN';gt.inputs[1].default_value=.40;l.new(sn.outputs[0],gt.inputs[0]);bands.append(gt.outputs[0])
add=n.new('ShaderNodeMath');add.operation='ADD';l.new(bands[0],add.inputs[0]);l.new(bands[1],add.inputs[1]);half=n.new('ShaderNodeMath');half.operation='MULTIPLY';half.inputs[1].default_value=.5;l.new(add.outputs[0],half.inputs[0]);mix=n.new('ShaderNodeMixRGB');mix.inputs[1].default_value=rgb('#79848E');mix.inputs[2].default_value=rgb('#B5BBC0');l.new(half.outputs[0],mix.inputs[0]);l.new(mix.outputs[0],n['Surface'].inputs['Base Color'])
wave=n.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='X';wave.inputs['Scale'].default_value=7;wave.inputs['Distortion'].default_value=8;wave.inputs['Detail Scale'].default_value=1.7;l.new(tc.outputs['Object'],wave.inputs['Vector']);bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=.007;l.new(wave.outputs['Color'],bump.inputs['Height']);l.new(bump.outputs[0],n['Surface'].inputs['Normal'])
# Damp / flaking paint lives in the wall shader, no photo planes or external textures.
for key in ['damp','skirt']:
 m=M[key];n=m.node_tree.nodes;l=m.node_tree.links
 for node in list(n):
  if node.name!='Surface' and node.type!='OUTPUT_MATERIAL':n.remove(node)
 geo=n.new('ShaderNodeNewGeometry');sep=n.new('ShaderNodeSeparateXYZ');l.new(geo.outputs['Position'],sep.inputs[0]);no=n.new('ShaderNodeTexNoise');no.inputs['Scale'].default_value=11;no.inputs['Detail'].default_value=4;l.new(geo.outputs['Position'],no.inputs[0]);height=n.new('ShaderNodeMath');height.operation='MULTIPLY';height.inputs[1].default_value=.52;l.new(no.outputs['Fac'],height.inputs[0]);sub=n.new('ShaderNodeMath');sub.operation='SUBTRACT';l.new(height.outputs[0],sub.inputs[0]);l.new(sep.outputs['Z'],sub.inputs[1]);ramp=n.new('ShaderNodeMapRange');ramp.clamp=True;ramp.inputs['From Min'].default_value=-.015;ramp.inputs['From Max'].default_value=.045;l.new(sub.outputs[0],ramp.inputs['Value']);fac=ramp.outputs[0]
 if key=='skirt':
  near=n.new('ShaderNodeMath');near.operation='GREATER_THAN';near.inputs[1].default_value=5.3;l.new(sep.outputs['Y'],near.inputs[0]);mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';l.new(fac,mul.inputs[0]);l.new(near.outputs[0],mul.inputs[1]);fac=mul.outputs[0]
 color=n.new('ShaderNodeMixRGB');color.inputs[1].default_value=rgb(P['palette']['skirt']);color.inputs[2].default_value=rgb('#A1957D');l.new(fac,color.inputs[0]);l.new(color.outputs[0],n['Surface'].inputs['Base Color']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.35;b.inputs['Distance'].default_value=.002;l.new(fac,b.inputs['Height']);l.new(b.outputs[0],n['Surface'].inputs['Normal'])
# Avoid false joints between coplanar wall opening pieces.
for ob in bpy.data.collections['RoomShell'].objects:
 if ob.get('role') in ['wall','wall_head']:
  for mod in list(ob.modifiers):ob.modifiers.remove(mod)
# Preserve the native fan and wooden door; add the ceiling runs feeding both lamps.
ACTIVE=bpy.data.collections['RoomShell']
for j,y in enumerate(P['lights']['y_centers']):
 tube('ceiling_feed_'+str(j),[(W-.035,y,H-.018),(W/2,y,H-.018)],.008,'ivory','fixed','ceiling')
box('ceiling_junction',(W-.025,1.5,H-.035),(.045,.075,.045),'ivory','fixed','ceiling')
# Warm afternoon sunlight through existing openings; shadow-ray transmission avoids
# relying on expensive caustics for rough glass. Visual rays retain frosted glazing.
m=M['glass'];n=m.node_tree.nodes;l=m.node_tree.links;out=next(x for x in n if x.type=='OUTPUT_MATERIAL');path=n.new('ShaderNodeLightPath');transparent=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');l.new(path.outputs['Is Shadow Ray'],mix.inputs[0]);l.new(n['Surface'].outputs[0],mix.inputs[1]);l.new(transparent.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])
bpy.ops.object.light_add(type='SUN',location=(-3,L+4,7));sun=bpy.context.object;sun.name='Afternoon sun';sun.rotation_euler=Vector((.18,-1,-.70)).to_track_quat('-Z','Y').to_euler();sun.data.energy=5.0;sun.data.angle=.085;sun.data.color=(1,.78,.53);sun['display_light']=True
for ob in SC.objects:
 if ob.name.startswith('Window daylight'):ob.data.energy=170;ob.data.color=(.88,.94,1);ob.data.size=2.8
# Separate warm-white camera background from low-energy environmental illumination.
n=SC.world.node_tree.nodes;l=SC.world.node_tree.links;n.clear();ambient=n.new('ShaderNodeBackground');ambient.inputs[0].default_value=(.78,.83,.9,1);ambient.inputs[1].default_value=.28;back=n.new('ShaderNodeBackground');back.inputs[0].default_value=(.88,.85,.79,1);back.inputs[1].default_value=1;path=n.new('ShaderNodeLightPath');mix=n.new('ShaderNodeMixShader');l.new(path.outputs['Is Camera Ray'],mix.inputs[0]);l.new(ambient.outputs[0],mix.inputs[1]);l.new(back.outputs[0],mix.inputs[2]);out=n.new('ShaderNodeOutputWorld');l.new(mix.outputs[0],out.inputs[0])
SC.cycles.max_bounces=10;SC.cycles.diffuse_bounces=6
print('SURFACE_DAYLIGHT_PASS_OK')
# Cycles collection-instance shadow visibility: rough glass transmits the direct
# afternoon beam; the view/reflection material stays frosted.
for ob in bpy.data.collections['RoomShell'].objects:
 if ob.type=='MESH' and any(mat==M['glass'] for mat in ob.data.materials):ob.visible_shadow=False
# Soft transmitted pools from frosted panes, aimed along the afternoon direction.
for idx,(x,z,power) in enumerate([(0.76,1.9,150),(W/2,1.85,180)]):
 bpy.ops.object.light_add(type='SPOT',location=(x,L-.10,z));ob=bpy.context.object;ob.name='Frosted afternoon transmission '+str(idx);ob.rotation_euler=(Vector((x+.6,2.5,.05))-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.energy=power;ob.data.color=(1,.72,.43);ob.data.spot_size=math.radians(38);ob.data.spot_blend=.5;ob.data.shadow_soft_size=.16;ob['display_light']=True
