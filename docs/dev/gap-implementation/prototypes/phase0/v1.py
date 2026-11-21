import sys, math, json
sys.path.insert(0, '/home/user/PhysicRollModel')
sys.dont_write_bytecode = True
from physicroll.foil_bite import solve_mattress_bite
R=0.089; Ys=230e6; Er=230e9; mu=0.03
nu=0.3; E=Er*(1-nu**2)
Y=Ys*math.sqrt(3)/2
def wbar(h0,h1,mu=mu,R=R,tb=0.0,tf=0.0,**kw):
    r=solve_mattress_bite(h0,h1,1.0,R,Y,mu,tb,tf,roll_youngs_modulus_pa=E,roll_poisson_ratio=nu,**kw)
    return r['force_per_width_n_m']*Er/(R*Ys**2), r
w,r=wbar(20e-6,15e-6)
print('E',E,'Y',Y)
print('V1 Wbar',repr(w),'F/w',repr(r['force_per_width_n_m']),'ratio118',w/118,'ratio62',w/62, r['regime'], r['forward_slip_fraction'], r['flags'])
print('torque Qbar?', r['torque_per_work_roll_nm'])
for cells in (200,400,800):
    w2,_=wbar(20e-6,15e-6,cells=cells); print(cells,repr(w2))
# Fig1 regime I 140um 50%
w,r=wbar(140e-6,70e-6); print('Fig1 140um 50%',w,r['regime'])
# V2: 73->31um mu .026 tensions 24.6, 30.4 MPa
for RR in (0.089,0.135):
    try:
        w,r=wbar(73e-6,31.39e-6,mu=0.026,R=RR,tb=0.107*Ys,tf=0.132*Ys); print('V2',RR,w,r['force_per_width_n_m'],r['regime'])
    except Exception as e: print('V2 fail',RR,e)
    try:
        w,r=wbar(73e-6,31e-6,mu=0.026,R=RR,tb=0.107*Ys,tf=0.132*Ys); print('V2b',RR,w,r['force_per_width_n_m'],r['regime'])
    except Exception as e: print('V2 fail',RR,e)
