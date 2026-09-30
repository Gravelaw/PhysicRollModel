"""Compose actual Blender render with an analytical roll-bite inset (Matplotlib)."""
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=ROOT/'artifacts')
    args = p.parse_args()
    result = json.loads((args.out/'process.result.json').read_text())
    s = result['scenario']
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':'#dceaf2',
                         'axes.labelcolor':'#b3cbd9','xtick.color':'#b3cbd9','ytick.color':'#b3cbd9'})
    fig = plt.figure(figsize=(16,10), facecolor='#101e2a')
    fig.text(.035,.951,'PHYSICROLL / 02',size=13,color='#67d6ce',weight='bold')
    fig.text(.035,.90,'Cold rolling · four-high single stand',size=27,weight='bold')
    fig.text(.035,.861,'GENERIC SYNTHETIC DEMONSTRATOR  /  NOT A PLANT REPLICA OR VALIDATED PROCESS MODEL',size=10,color='#f8bb75')
    ax = fig.add_axes([.028,.235,.705,.595])
    ax.imshow(plt.imread(args.out/'overview.png'))
    ax.set_axis_off()
    fig.text(.745,.79,'ROLL BITE / ANALYTICAL SECTION',size=12,weight='bold')
    fig.text(.745,.757,'Rigid circular rolls; prescribed exit gauge',size=9,color='#b3cbd9')
    ax = fig.add_axes([.775,.48,.193,.22],facecolor='#142b3a')
    r,h0,h1 = s['work_roll_radius_m'],s['entry_thickness_m'],s['exit_thickness_m']
    length=result['contact_length_m']
    lo = -max(length*1.3,.005)
    hi = max(length*.3,.002)
    x = np.linspace(lo,hi,300)
    gap=h1+2*x*x/(r+np.sqrt(r*r-x*x))
    strip = np.where(x < -length, h0, np.where(x>0,h1,gap))
    ax.fill_between(x*1000, gap*500, h0*1300,color='#607d8b')
    ax.fill_between(x*1000,-h0*1300,-gap*500,color='#607d8b')
    ax.fill_between(x*1000,-strip*500,strip*500,color='#67d6ce')
    ax.plot(x*1000,gap*500,color='#dceaf2',lw=1)
    ax.plot(x*1000,-gap*500,color='#dceaf2',lw=1)
    ax.axvline(-length*1000,color='#f8bb75',lw=.8,ls='--')
    ax.axvline(0,color='#f8bb75',lw=.8,ls='--')
    ax.set(xlim=(lo*1000,hi*1000),ylim=(-h0*1100,h0*1100),xlabel='X / mm',ylabel='Z / mm')
    ax.tick_params(labelsize=8)
    for spine in ax.spines.values(): spine.set_color('#416175')
    fig.text(.745,.405,'Inset axes have different scales.',size=10,color='#f8bb75')
    fig.text(.745,.38,'Strip thickness is enlarged visually in the inset.',size=9,color='#b3cbd9')
    fig.text(.745,.354,'3D mesh retains true metre dimensions.',size=9,color='#b3cbd9')
    fig.text(.745,.302,f'Entry {h0*1000:.2f} mm  →  exit {h1*1000:.2f} mm',size=12,weight='bold')
    fig.text(.745,.271,f'Contact length {length*1000:.2f} mm',size=11)
    fig.text(.745,.242,'Cyan dots: disconnected sensor positions',size=9,color='#67d6ce')
    fig.text(.035,.205,'EQUIPMENT',size=10,color='#67d6ce',weight='bold')
    fig.text(.12,.205,'Entry reel  →  guides & gauge  →  work / backup rolls  →  gauge & guides  →  exit reel',size=11)
    labels=[('REDUCTION',f"{result['reduction_fraction']:.0%}"),('SEPARATING FORCE',f"{result['separating_force_n']/1e6:.2f} MN"),
            ('ROLL MECHANICAL POWER',f"{result['roll_mechanical_power_w']/1000:.1f} kW"),('MASS FLOW',f"{result['mass_flow_kg_s']:.1f} kg/s")]
    for x,(title,value) in zip([.035,.28,.525,.77],labels):
        fig.text(x,.143,title,size=9,color='#90adbf')
        fig.text(x,.101,value,size=22,weight='bold')
    fig.text(.035,.05,'Illustrative steady state only. No flatness, residual stress, metallurgy, thermal or control-transient solution.',size=10,color='#f8bb75')
    fig.savefig(args.out/'preview.png',dpi=120,facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__=='__main__':
    main()
