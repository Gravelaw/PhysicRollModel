import math
print("1. Lechler spray width B (water, 3 bar) vs geometric 2H tan(a/2)")
B = {20:(100,200),30:(150,300),45:(220,440),60:(330,630)}  # smaller-flow group, H=250/500
for a,(b250,b500) in B.items():
    g250=2*250*math.tan(math.radians(a/2)); g500=2*500*math.tan(math.radians(a/2))
    print(f"  {a:2d} deg: H250 B={b250} geo={g250:.0f} ratio={b250/g250:.2f} | H500 B={b500} geo={g500:.0f} ratio={b500/g500:.2f}")
print("2. sqrt law, Lechler 664.844 table (l/min): 0.5..10 bar")
tab={0.5:6.25,1:8.84,2:12.5,3:15.31,5:19.67,7:23.39,10:27.95}
for p,q in tab.items(): print(f"  p={p:4} Q={q:6.2f} Q/sqrt(p)={q/math.sqrt(p):.3f}")
# Tucker equal flow pressures
q844=19.76; q804=15.81
for p in (2.5,4.2,5.83): print(f"  652.844 at {p} bar -> {q844*math.sqrt(p/5):.2f}")
for p in (3.9,6.5,9.1): print(f"  652.804 at {p} bar -> {q804*math.sqrt(p/5):.2f}")
print("3. density correction 1/sqrt(SG):", {sg:round(1/math.sqrt(sg),3) for sg in (0.76,0.78,0.80,0.82)})
print("4. Shao 2015 CFD roll speed: omega=31.746 rad/s, R=0.2108 m ->", round(31.746*0.2108,2),"m/s =",round(31.746*0.2108*60),"m/min; mill speeds 252/282 m/min")
print("5. Yin 2005 jet velocity |v| and rho v^2/2 (rho=800):")
for vx,vy in ((24.0,-10.6),(24.0,-12.0),(30.5,-13.5)):
    v=math.hypot(vx,vy); print(f"  ({vx},{vy}) |v|={v:.1f} m/s, p_dyn={800*v*v/2/1e5:.2f} bar")
print("6. Flow per metre of barrel per row:")
for name,q,p in (("664.844 @5bar",19.67,0.052),("664.844 @3bar",15.31,0.052),("Innoval 3+6+12 l/min @52mm",21,0.052),("Hobbis 35 l/min level 7 @52mm",35,0.052),("Hobbis 35 @26",35,0.026)):
    print(f"  {name}: {q/p:.0f} L/min/m")
print("  old foil mill 1200 L/min over 1.4 m max width:",round(1200/1.4),"L/min/m (all headers)")
print("7. Overlap definitions for project demo (pitch 52 mm, overlap_fraction 0.688):")
p=52; W=p/(1-0.688); print(f"  W_eff={W:.1f} mm; (W-p)/W={(W-p)/W:.3f}; (W-p)/p={(W-p)/p:.2f}; W/p={W/p:.2f}")
for o in (0.10,0.30,0.50):
    print(f"  overlap {o}: W=p/(1-o)={p/(1-o):.1f} mm; W=p(1+o)={p*(1+o):.1f} mm")
print("   Lechler 1/4..1/3 of B: W=",round(p/(1-0.25),1),"..",round(p/(1-1/3),1))
print("8. Tucker Brno averages over 900 mm of surface; circumferential equivalent if roll D=0.65 m (ASSUMED, rig of Hnizdil 2024):")
C=math.pi*0.65
for h in (5.991,10.255,14.040,13.427,16.706): print(f"  {h:.3f} kW -> {h*0.9/C:.2f} kW/m2K")
print("9. Shao 2.5-4.3 kW/m2K on a sprayed arc phi -> circumferential mean:")
for deg in (20,30,60,90):
    print(f"  phi={deg}: {2.5*deg/360:.2f}-{4.3*deg/360:.2f}")
print("10. valve timing vs roll revolution:")
for D,v in ((0.23,25.0),(0.254,25.0),(0.42,4.2)):
    T=math.pi*D/v; print(f"  D={D} m v={v} m/s rev={T*1000:.0f} ms; 30 ms response = {0.030/T:.2f} rev; 5 Hz period = {0.2/T:.1f} rev")
print("11. Footprint ripple: sum of identical profiles at pitch p, W/p ratio r")
def prof(x,W,kind):
    u=abs(2*x/W)
    if u>1: return 0.0
    return 1.0 if kind=='tophat' else (1-u*u if kind=='parab' else 1-u)
for kind in ('tophat','parab','tri'):
    for r in (1.11,1.43,2.0,3.21):
        W=r; xs=[i/400 for i in range(400)]  # one pitch
        vals=[sum(prof(x-k,W,kind) for k in range(-6,7)) for x in xs]
        m=sum(vals)/len(vals); print(f"  {kind:6s} W/p={r:4.2f}: min/mean={min(vals)/m:.3f} max/mean={max(vals)/m:.3f}")
print("12. single-nozzle loss: deficit FWHM / pitch (deficit = profile of one nozzle normalised by mean)")
for kind in ('tophat','parab','tri'):
    for r in (1.43,3.21):
        W=r; area={'tophat':W,'parab':2*W/3,'tri':W/2}[kind]
        peak=1/area  # peak deficit relative to mean (mean = 1 per pitch)
        half= W if kind=='tophat' else (W/math.sqrt(2) if kind=='parab' else W/2)
        print(f"  {kind:6s} W/p={r}: peak deficit={peak:.2f} of mean, FWHM={half:.2f} p")
