"""Run with Blender 4.3+: blender -b -t 4 --python blender/generate.py -- ..."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'blender'))
from usda import export_meshes
from physicroll import Scenario, solve
from physicroll.equipment import EquipmentAssumptions, evaluate_equipment
from physicroll.sensors import sensor_manifest


def material(name, color, metal=0.0, rough=0.4):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Roughness'].default_value = rough
    return m


def finish(obj, name, mat):
    obj.name = name
    obj.data.name = name + '_mesh'
    obj['equipment_id'] = name
    obj['synthetic_geometry'] = True
    obj.data.materials.append(mat)
    return obj


def box(name, loc, size, mat, bevel=0.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(o, name, mat)
    if bevel:
        mod = o.modifiers.new('edge_radii', 'BEVEL')
        mod.width = min(bevel, min(size) / 4)
        mod.segments = 3
        o.modifiers.new('weighted_normals', 'WEIGHTED_NORMAL')
    return o


def cylinder(name, loc, radius, width, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=width,
                                      location=loc, rotation=(math.pi / 2, 0, 0))
    o = finish(bpy.context.object, name, mat)
    for face in o.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    mod = o.modifiers.new('edge_radii', 'BEVEL')
    mod.width = 0.007
    mod.segments = 2
    o.modifiers.new('weighted_normals', 'WEIGHTED_NORMAL')
    return o


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def generate(s, out, render, equipment):
    result = solve(s)
    if not (0.15 <= s.work_roll_radius_m <= 0.4 and 0.5 <= s.width_m <= 1.8):
        raise ValueError("Scene layout domain: work radius 0.15–0.4 m, strip width 0.5–1.8 m")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene['description'] = 'GENERIC SYNTHETIC 4-HIGH MILL / UNCALIBRATED / X rolling, Y width, Z up / metres'
    scene['scenario_json'] = json.dumps(result['scenario'], sort_keys=True)
    scene['process_result_json'] = json.dumps(result, sort_keys=True)
    scene['equipment_result_json'] = json.dumps(evaluate_equipment(s, equipment, result), sort_keys=True)
    steel = material('roll_steel', (0.48, 0.57, 0.64), 0.8, 0.24)
    blue = material('housing_blue', (0.032, 0.19, 0.26), 0.55)
    dark = material('base_graphite', (0.07, 0.095, 0.12), 0.4)
    orange = material('instrument_amber', (1.0, 0.34, 0.055), 0.25)
    stripmat = material('aluminium_strip', (0.73, 0.85, 0.90), 0.7, 0.28)
    coilmat = material('aluminium_coil', (0.46, 0.60, 0.67), 0.75, 0.32)
    ground = material('floor', (0.16, 0.20, 0.24), 0.15)
    marker_mat = material('sensor_marker_cyan', (0.03, 0.82, 0.80), 0.3)
    r, w, h = s.work_roll_radius_m, s.width_m, s.exit_thickness_m
    backup = 1.8 * r
    barrel = w + 0.4
    pitch = h / 2 + 2 * r + backup
    bottom = -(pitch + backup + 0.28)
    top = -bottom
    if max(equipment.entry_reel_radius_m, equipment.exit_reel_radius_m) > min(.7, abs(bottom)*.48):
        raise ValueError('Reel radius exceeds the generic scene clearance; choose smaller synthetic radii')
    span = max(3.2, 10 * r)
    box('foundation', (0, 0, bottom - 0.1), (2*span+2.2, w+2.2, 0.2), dark)
    for sign, side in [(1, 'upper'), (-1, 'lower')]:
        cylinder('stand01_work_' + side, (0, 0, sign*(r+h/2)), r, barrel, steel)
        cylinder('stand01_backup_' + side, (0, 0, sign*pitch), backup, barrel+0.15, steel)
        for y in [-1, 1]:
            cylinder(f'stand01_work_{side}_journal_{y}', (0, y*(barrel/2+0.13), sign*(r+h/2)), r*.48, .26, dark)
    for y, side in [(-barrel/2-.30, 'operator'), (barrel/2+.30, 'drive')]:
        for x, end in [(-backup-.25, 'entry'), (backup+.25, 'exit')]:
            box(f'stand01_housing_{side}_{end}', (x, y, 0), (.27, .26, 2*top), blue)
        for z, end in [(bottom+.12, 'foot'), (top-.12, 'crown')]:
            box(f'stand01_housing_{side}_{end}', (0, y, z), (2*backup+.78, .32, .3), blue)
        box(f'stand01_screwdown_{side}', (0, y, top+.18), (.28, .28, .36), orange)
        for z, end in [(pitch, 'upper'), (-pitch, 'lower')]:
            box(f'stand01_chock_{side}_{end}', (0,y,z), (.68,.30,.44), dark)
    # Coils are static snapshots; strip is tangent at the top. No coil-build dynamics.
    for x, end in [(-span, 'entry'), (span, 'exit')]:
        cr = equipment.entry_reel_radius_m if x < 0 else equipment.exit_reel_radius_m
        thickness = s.entry_thickness_m if x < 0 else h
        zcoil = -cr - thickness/2
        cylinder(end+'_coil', (x,0,zcoil), cr, w, coilmat)
        cylinder(end+'_reel_mandrel', (x,0,zcoil), cr*.30, w+.75, steel)
        for sign in [-1,1]:
            box(f'{end}_reel_pedestal_{sign}', (x,sign*(w/2+.3),(bottom+zcoil)/2), (.42,.28,zcoil-bottom), blue)
            # Annular end rings suggest wound layers without inventing individual wraps.
            for j in range(4):
                bpy.ops.mesh.primitive_torus_add(major_radius=cr*(.46+.16*j), minor_radius=.004,
                    major_segments=96, minor_segments=8, location=(x,sign*(w/2+.004),zcoil),
                    rotation=(math.pi/2,0,0))
                finish(bpy.context.object, f'{end}_coil_ring_{sign}_{j}', steel)
        gx = x*.53
        for sign in [-1,1]:
            box(f'{end}_gauge_post_{sign}', (gx,sign*(w/2+.18),.05), (.12,.12,.65), orange)
        box(end+'_gauge_bridge', (gx,0,.37), (.13,w+.5,.12), orange)
        box(end+'_gauge_sensor', (gx,0,.21), (.18,.18,.20), dark)
        cylinder(end+'_guide_roll', (gx*.74,0,-.09-thickness/2), .09, w+.16, steel)
        for sign in [-1,1]:
            box(f'{end}_edge_guide_{sign}', (gx*.85,sign*(w/2+.05),0), (.30,.045,.07), orange, .008)
    # Watertight true-gauge mesh follows rigid-circle bite; no visual exaggeration.
    length = result['contact_length_m']
    stations = [(-span, s.entry_thickness_m)]
    if length:
        for i in range(49):
            x = -length + length*i/48
            # Stable circle sagitta avoids cancellation for shallow drafts.
            gap = h + 2*x*x/(r+math.sqrt(r*r-x*x))
            stations.append((x, gap))
    else:
        stations.append((0,h))
    stations.append((span,h))
    verts = [(x,y,z) for x,t in stations for y,z in [(-w/2,-t/2),(w/2,-t/2),(w/2,t/2),(-w/2,t/2)]]
    faces = [(3,2,1,0)]
    for i in range(len(stations)-1):
        for j in range(4):
            faces.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
    n = len(verts)
    faces.append((n-4,n-3,n-2,n-1))
    mesh = bpy.data.meshes.new('strip_mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    o = bpy.data.objects.new('strip_product', mesh)
    scene.collection.objects.link(o)
    finish(o, 'strip_product', stripmat)
    o['thickness_scale'] = 1.0
    o['entry_thickness_m'] = s.entry_thickness_m
    o['exit_thickness_m'] = h
    box('floor', (0,0,bottom-.24), (200,200,.08), ground)
    sensors = sensor_manifest(s, result)
    for signal in sensors['signals']:
        pos = signal['position_m']
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=.035,
            location=(pos['x'], pos['y'], pos['z']))
        obj = finish(bpy.context.object, 'sensor_marker_' + signal['sensor_id'], marker_mat)
        obj['sensor_id'] = signal['sensor_id']
        obj['quantity'] = signal['quantity']
        obj['unit_si'] = signal['unit_si']
        obj['data_status'] = 'disconnected_no_measurement'
    bpy.ops.object.camera_add(location=(8.6,-12.8,7.2))
    camera = bpy.context.object
    camera.name = 'presentation_camera'
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 10.5 * max(1, span/3.2, (w+2)/3)
    aim(camera, (0,0,-.25))
    scene.camera = camera
    for loc, power, size in [((0,-4,8),2200,7), ((-5,2,5),1700,5), ((4,5,6),2500,5)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        lamp = bpy.context.object
        lamp.data.energy, lamp.data.shape, lamp.data.size = power, 'DISK', size
        aim(lamp, (0,0,0))
    scene.world.color = (.3,.3,.3)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = 1600, 950
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(out/'overview.png')
    scene.view_settings.view_transform = 'AgX'
    # Render support objects are excluded from the portable engineering scene.
    bpy.ops.object.select_all(action='DESELECT')
    for obj in scene.objects:
        if 'equipment_id' in obj and obj.name != 'floor':
            obj.select_set(True)
    status = {'blender_version': bpy.app.version_string, 'blend': 'mill.blend', 'render': 'not requested', 'usd': 'not attempted'}
    try:
        bpy.ops.wm.usd_export(filepath=str(out/'mill.usda'), selected_objects_only=True,
                              export_custom_properties=True, generate_preview_surface=True)
        status['usd'] = 'mill.usda'
    except Exception as exc:
        export_meshes(out/'mill.usda', [o for o in scene.objects if o.select_get()], bpy.context.evaluated_depsgraph_get())
        status['usd'] = 'mill.usda (static mesh fallback)'
        status['native_usd_unavailable'] = str(exc)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'mill.blend'))
    if render:
        bpy.ops.render.render(write_still=True)
        status['render'] = 'overview.png'
    (out/'scene_status.json').write_text(json.dumps(status, indent=2)+'\n')
    (out/'process.result.json').write_text(json.dumps(result, indent=2)+'\n')
    (out/'equipment.result.json').write_text(json.dumps(evaluate_equipment(s, equipment, result), indent=2)+'\n')
    (out/'sensor_manifest.json').write_text(json.dumps(sensors, indent=2)+'\n')
    manifest = [{'equipment_id': o['equipment_id'], 'object_name': o.name} for o in scene.objects if 'equipment_id' in o]
    (out/'equipment_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--scenario', type=Path, default=ROOT/'scenarios/baseline.json')
    p.add_argument('--out', type=Path, default=ROOT/'artifacts')
    p.add_argument('--render', action='store_true')
    p.add_argument('--equipment', type=Path, default=ROOT/'scenarios/baseline.equipment.json')
    args = p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    generate(Scenario.from_dict(json.loads(args.scenario.read_text())), args.out, args.render,
             EquipmentAssumptions.from_dict(json.loads(args.equipment.read_text())))
