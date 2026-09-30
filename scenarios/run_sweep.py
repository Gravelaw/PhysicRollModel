"""Independent steady states, not a controller response or time simulation."""
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll import Scenario, solve

base = json.loads((ROOT/'scenarios/baseline.json').read_text())
rows = []
for reduction in [0.1,0.2,0.25,0.3,0.4]:
    for mu in [.04,.06,.08,.1]:
        d = {**base,'name':f'synthetic_r{reduction}_mu{mu}',
             'exit_thickness_m':base['entry_thickness_m']*(1-reduction),'friction_coefficient':mu}
        row = {'reduction_fraction':reduction,'friction_coefficient':mu,'status':'accepted',
               'separating_force_n':'','roll_mechanical_power_w':'','exit_speed_m_s':'','reason':''}
        try:
            r = solve(Scenario.from_dict(d))
            row.update({k:r[k] for k in ['separating_force_n','roll_mechanical_power_w','exit_speed_m_s']})
        except ValueError as exc:
            row.update(status='rejected',reason=str(exc))
        rows.append(row)
out = ROOT/'artifacts/sweep.csv'
out.parent.mkdir(exist_ok=True)
with out.open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print(f'{len(rows)} synthetic scenarios -> {out}')
