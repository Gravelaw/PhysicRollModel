"""Run source import/unit/range audit before any literature simulation."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll.literature import load_case
p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,default=ROOT/'artifacts/aa5052/unit_audit.json')
a=p.parse_args()
c=load_case(ROOT/'scenarios/literature/shao2015_aa5052')
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(c['unit_audit'],indent=2,allow_nan=False)+'\n')
print(f"PASS: {c['unit_audit']['converted_numeric_values']} source conversions; semantics remain unresolved")
print(a.out)
