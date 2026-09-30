"""Generate disconnected equipment/sensor outputs without Blender or dependencies."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll import Scenario,solve
from physicroll.equipment import EquipmentAssumptions,evaluate_equipment
from physicroll.sensors import sensor_manifest

p=argparse.ArgumentParser()
p.add_argument('--scenario',type=Path,default=ROOT/'scenarios/baseline.json')
p.add_argument('--equipment',type=Path,default=ROOT/'scenarios/baseline.equipment.json')
p.add_argument('--out',type=Path,default=ROOT/'artifacts')
a=p.parse_args()
s=Scenario.from_dict(json.loads(a.scenario.read_text()))
e=EquipmentAssumptions.from_dict(json.loads(a.equipment.read_text()))
result=solve(s)
a.out.mkdir(parents=True,exist_ok=True)
for name,data in [('equipment.result.json',evaluate_equipment(s,e,result)),('sensor_manifest.json',sensor_manifest(s,result))]:
    (a.out/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    print(a.out/name)
