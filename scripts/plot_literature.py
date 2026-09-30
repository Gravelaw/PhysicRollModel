"""Optional source comparison plot using installed matplotlib; no model changes."""
import argparse
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('MPLCONFIGDIR','/tmp/physicroll-mpl')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from physicroll.units import from_si
p=argparse.ArgumentParser()
p.add_argument('--input',type=Path,default=ROOT/'artifacts/aa5052/summary.json')
p.add_argument('--out',type=Path,default=ROOT/'artifacts/aa5052/comparison.png')
a=p.parse_args()
r=json.loads(a.input.read_text()); rows=r['baseline_comparison']; xs=[1,2,3]
fig,axes=plt.subplots(1,2,figsize=(12,5.2),layout='constrained')
for ax,keys,unit,dimension,label in [
    (axes[0],['author_measured_force_n','source_model_force_n_separate','predicted_force_n'],'MN','force','Stand separating force [MN]'),
    (axes[1],['author_measured_forward_slip_fraction','source_model_slip_fraction_separate','predicted_forward_slip_fraction'],'%','dimensionless','Forward slip [%; interpretation unresolved]')]:
    for key,color,marker,name in zip(keys,['#183153','#238b45','#c44e17'],['o','s','^'],['Author-reported measurement','Shao et al. model output','Our conditional rigid-slab result']):
        ax.plot(xs,[from_si(row[key],unit,dimension) for row in rows],color=color,marker=marker,label=name,linewidth=1.8)
    ax.set_xticks(xs);ax.set_xlabel('Sequential pass');ax.set_ylabel(label);ax.grid(alpha=.2)
axes[0].legend(fontsize=8,loc='best')
fig.suptitle('AA5052: 4.10 → 1.72 mm, width 1360 mm\nConditional comparison — no fit, no validated material history',fontsize=13)
assumed=r['assumptions']
fig.supxlabel(f"Assumed prior log strain {assumed['prior_log_strain']:g}; {assumed['strain_convention']}/{assumed['stress_convention']}; speed={assumed['speed_interpretation']}.\nSource: Shao et al. (2015), DOI 10.18280/ijht.330113. Measurement uncertainty unreported.",fontsize=8)
a.out.parent.mkdir(parents=True,exist_ok=True)
fig.savefig(a.out,dpi=160)
print(a.out)
