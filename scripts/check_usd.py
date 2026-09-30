"""Optional independent OpenUSD check; requires usd-core, not required for smoke."""
import json
from pathlib import Path
from pxr import Usd,UsdGeom,UsdShade

ROOT=Path(__file__).resolve().parents[1]
stage=Usd.Stage.Open(str(ROOT/'artifacts/mill.usda'))
assert stage
assert UsdGeom.GetStageUpAxis(stage)=='Z'
assert UsdGeom.GetStageMetersPerUnit(stage)==1
assert stage.GetDefaultPrim().GetName()=='Mill'
ids=[]
for prim in stage.Traverse():
    if not prim.IsA(UsdGeom.Mesh):
        continue
    mesh=UsdGeom.Mesh(prim)
    points=mesh.GetPointsAttr().Get()
    counts=mesh.GetFaceVertexCountsAttr().Get()
    indices=mesh.GetFaceVertexIndicesAttr().Get()
    assert points and sum(counts)==len(indices)
    assert min(indices)>=0 and max(indices)<len(points)
    assert UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
    ids.append(prim.GetAttribute('equipment_id').Get())
    if prim.GetName().startswith('sensor_marker_'):
        assert prim.GetAttribute('sensor_id').Get()==prim.GetName().removeprefix('sensor_marker_')
expected=[x['equipment_id'] for x in json.loads((ROOT/'artifacts/equipment_manifest.json').read_text()) if x['equipment_id']!='floor']
assert sorted(ids)==sorted(expected)
assert len(ids)==len(set(ids))
strip=UsdGeom.Mesh(stage.GetPrimAtPath('/Mill/strip_product'))
points=strip.GetPointsAttr().Get()
s=json.loads((ROOT/'artifacts/process.result.json').read_text())['scenario']
assert abs(points[2][2]-points[1][2]-s['entry_thickness_m'])<1e-9
assert abs(points[-2][2]-points[-3][2]-s['exit_thickness_m'])<1e-9
print(f'PASS: OpenUSD reopened {len(ids)} meshes, valid topology/materials/IDs and true gauge; Z-up metres')
