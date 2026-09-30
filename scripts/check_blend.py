"""blender -b artifacts/mill.blend --python-exit-code 1 --python scripts/check_blend.py"""
import json
import math
import bpy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from physicroll import Scenario
from physicroll.sensors import marker_positions

scene=bpy.context.scene
s=json.loads(scene['scenario_json'])
assert scene.unit_settings.scale_length==1
ids=[o['equipment_id'] for o in scene.objects if 'equipment_id' in o]
assert len(ids)==len(set(ids))
s=Scenario.from_dict(s)
for sensor_id,pos in marker_positions(s).items():
    marker=bpy.data.objects['sensor_marker_'+sensor_id]
    assert marker['sensor_id']==sensor_id
    assert all(math.isclose(marker.location[i],pos[i],abs_tol=1e-6) for i in range(3))
for name in ['stand01_work_upper','stand01_work_lower','stand01_backup_upper','stand01_backup_lower',
             'entry_coil','exit_coil','entry_reel_mandrel','exit_reel_mandrel','entry_gauge_sensor','exit_gauge_sensor','strip_product']:
    assert name in ids,name
upper=bpy.data.objects['stand01_work_upper']
lower=bpy.data.objects['stand01_work_lower']
assert math.isclose(upper.location.z-lower.location.z-2*s.work_roll_radius_m,s.exit_thickness_m,abs_tol=1e-7)
strip=bpy.data.objects['strip_product']
assert strip['thickness_scale']==1
v=strip.data.vertices
assert math.isclose(v[2].co.z-v[1].co.z,s.entry_thickness_m,rel_tol=1e-6)
assert math.isclose(v[-2].co.z-v[-3].co.z,s.exit_thickness_m,rel_tol=1e-6)
assert math.isclose(strip.dimensions.y,s.width_m,rel_tol=1e-6)
# Every strip mesh edge belongs to exactly two faces (closed manifold).
edges={}
for poly in strip.data.polygons:
    for a,b in zip(poly.vertices,list(poly.vertices[1:])+[poly.vertices[0]]):
        key=tuple(sorted((a,b)))
        edges[key]=edges.get(key,0)+1
assert set(edges.values())=={2}
print(f'PASS: {len(ids)} unique equipment IDs; roll gap, true strip gauge, width and closed strip mesh')
