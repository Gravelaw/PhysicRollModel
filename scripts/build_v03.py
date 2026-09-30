"""Build separately identified, synthetic v0.3 foundation outputs (stdlib only)."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll.model import Scenario
from physicroll.materials import MaterialState,PowerHardeningLaw,pass_with_history
from physicroll.thermal import ThermalStep,step
from physicroll.lubrication import FluidObservation,EffectiveFriction,declared_closure
from physicroll.profile import diagnose_profile
from physicroll.slab import solve_slab

p=argparse.ArgumentParser()
p.add_argument('--scenario',type=Path,default=ROOT/'scenarios/baseline.json')
p.add_argument('--foundations',type=Path,default=ROOT/'scenarios/v03_foundations.json')
p.add_argument('--out',type=Path,default=ROOT/'artifacts/v03_foundations.result.json')
a=p.parse_args()
s=Scenario.from_dict(json.loads(a.scenario.read_text()))
config=json.loads(a.foundations.read_text())
if not config['warning'].startswith('ALL PARAMETERS SYNTHETIC'):
    raise ValueError('synthetic scenario label required')
material=pass_with_history(s,MaterialState(**{**config['material_state'],
    'history':tuple(config['material_state']['history'])}),PowerHardeningLaw(**config['hardening_law']))
out={'status':'SYNTHETIC_FOUNDATIONS_UNCALIBRATED',
     'warning':config['warning'],
     'material':material,
     'slab_optional':solve_slab(s),
     'thermal':step(ThermalStep(**config['thermal_step'])),
     'lubrication':declared_closure(FluidObservation(**config['fluid']),EffectiveFriction(**config['effective_friction'])),
     'profile':diagnose_profile(**config['supplied_profile'])}
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
print(a.out)
