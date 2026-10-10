# T2A9 matched reaction-mode reversal design candidate

**Status: independently derived design candidate, not implemented.** This
is the next restricted T2 verification case after T2A8. It tests an actual
winding-to-release donor switch with a smooth zero-speed crossing while
all span tension stays positive. Reel speed and torque are reactions to
the elastic port. It cannot establish arbitrary applied-torque release,
incompatible stored-strain pickup, slack or a physical rolling mill.

## Exact standing-wave episode

Use `L=1 m`, `mu0=0.1 kg/reference m`, `EA=10 N`, `c0=10 m/s`,
`lambda0=1.01`, `delta=0.001`, `k=pi/2 rad/reference m`, and
`t_rev=0.02 s`. Over `0<=t<=0.04 s`, use

```text
x(S,t)=lambda0*S+(delta/k)*sin(k*S)*cos(c0*k*(t-t_rev))
lambda(S,t)=lambda0+delta*cos(k*S)*cos(c0*k*(t-t_rev))
v(S,t)=-delta*c0*sin(k*S)*sin(c0*k*(t-t_rev)).
```

This solves the linear elastic wave equation and has `lambda>=1.009`.
The left spatial endpoint is fixed, `v(0,t)=0`, supplying one reflecting
mechanical boundary condition. At the fixed right endpoint, solve
`x(Sb,t)=L` for the material cut. Its material flux is positive before
`t_rev`, zero there, and negative afterward. Because the standing wave
retraces its material map in time, each released label has exactly the
stretch it had when deposited. This is a deliberately matched zero-loss
fixture, not an inferred property of general wound strip.

Eliminating time from `x(Sb,t)=L` gives the right-port stretch as a
function of the cut label:

```text
w(S)=lambda0+k*(L-lambda0*S)*cot(k*S)
w'(S)=-k*lambda0*cot(k*S)-k²*(L-lambda0*S)*csc²(k*S).
```

On the winding half, this externally declared exact profile supplies the
one incoming right-port mechanical condition; save the **original**
material-label profile of each accepted deposited interval. On the
release half, obtain the incoming condition from the exposed stored
record, including its material-label derivative for reaction torque,
not by replaying the external profile. With computed outgoing
`r=v-c0*lambda`, set `lambda_p=w_exposed`,
`v_p=r+c0*lambda_p`, `q=v_p/lambda_p`, `ell_dot=q`,
`Sb_dot=-q`, `omega=v_p/R`, and `theta_dot=omega`. The donor switch
occurs at the **computed** first `v_p=0`, with no scheduled state reset.
The exact profile and its derivative agree from both sides of this switch,
so this manufactured case has no velocity jump, impulse or extra transfer
work. A mismatch outside this fixture needs a transition law.

The initial cut is `S0=0.9894996247259713887694`, and the reel has
`ell0=1 m`. Its old `[S0,S0+1]` interval is immutable, with uniform
retained stretch `w(S0)=1.010015685968241193`. New wound intervals append
at labels below `S0` with the analytic profile `w(S)` restricted to each
interval. Release removes those intervals from the outside in; stop at
the first computed return to `S0`. Do not consume the old interval.
Keep the exact stored-energy integral in material label separate from the
Heun `qW` transfer quadrature; their difference is a numerical diagnostic.
A test must mutate one stored interval after deposition and confirm that
the release boundary responds to that interval. An implementation that
replays the external `w(S)` throughout release is invalid even if its
unperturbed field matches the exact wave.

## Reel reaction and shared ledgers

Use the T2A6 ideal annulus `R(ell),J(ell)`, and no independent reel torque
or speed input. Differentiate the computed outgoing characteristic from
the numerical span rates. Then

```text
v_p_dot=r_dot-c0*q*w'(Sb)
R_dot=(h0/pi)*q/(2*R)
alpha=v_p_dot/R-v_p*R_dot/R²
tau_reaction=J*alpha+R*T.
```

The right span face and reel share
`F=(q,mu0*q*v_p-T)` and
`F_E=q*(mu0*v_p²/2+W(w_exposed))-T*v_p` at the same accepted stages.
Check `d(J*omega)/dt=tau-R*T+mu0*q*R*v_p` and
`d(K+U)/dt=tau*omega+F_E`. Use signed fluxes on each half of the
episode, rather than cancellation over the entire symmetric cycle as the
only check. Initial, reversal and terminal field/mass/energy ownership
must remain identifiable; a frame sample cannot advance history.

Independent high-precision landmarks: at reversal,
`Sb=0.9894687795361282210577`, `ell=1.000030845189843168 m`,
newly deposited `U=1.547233710226713621e-8 J`, `omega=0`, and
`tau=-0.006857761152179466757 Nm`. Initially,
`omega=0.03041718386794983516 rad/s` and
`tau=-0.006025022663259069518 Nm`. At the exact return time `0.04 s`,
`ell=1 m`, `omega` is the negative of its initial value, newly deposited
`U=0`, and `theta=0`. The exact full-cycle drive work and each net
right-port kinetic, strain and traction integral are zero; compare their
nonzero half-cycle integrals independently.

For `[0,0.02 s]`, independent high-precision integrals are: drive work
`-1.975564009452073484e-6 J`, advected kinetic energy
`+7.423185831184365109e-12 J`, deposited strain energy
`+1.547233710226713621e-8 J`, traction work
`+3.120433871294104210e-6 J`, reel angle
`+3.066982961368447013e-4 rad`, reaction torque impulse
`-1.315853104706966185e-4 N m s`, and advected angular impulse
`+6.486187963675360678e-10 N m s`. The release half has opposite
energy, work and angle integrals. Torque and advected-angular impulses
repeat their winding-half signs. Independent tests must integrate to the
**computed** event time when comparing numerical work; comparison only at
the exact scheduled `0.02 s` would mix event-time error with work error.

## Gate before implementation

Proposed grids are 64, 128 and 256 cells at reconstructed-stage Courant
limit `0.35`, plus 128 cells at `0.175` and `0.0875`. Observe `0`,
`0.01 s`, the located reversal, `0.03 s` and the located return. Locate
the first computed right-flux sign change `+` to `-` (exact `0.02 s`),
then the return of `Sb-S0` from negative to zero (exact `0.04 s`).
Use full coupled trials from the same committed state and verify opposite
**endpoint** signs at both ends of each bracket, width at most `1e-9 s`.
A stage-only sign excursion is a guard, not an event. Do not overwrite
velocity or inventory to hit an analytical event time. Resolve and record
signed transfer through both event neighborhoods. Allow exactly one
reversal and one return; stop before the old interval is consumed.

Proposed terminal residuals are `|q|<=2e-10 reference m/s` at reversal
and `|Sb-S0|<=1e-11 m` at return. On the finest grid, both event-time
errors should be below `1e-4 s`; do not demand a trend below the
`1e-9 s` event-bracket floor. Keep all used stretch states at least
`1.008`. Normalize stretch RMS by `delta` and velocity RMS by
`c0*delta`; require both normalized errors below
`0.01`, peak inventory error below `1e-7 m`, reel speed error below
`1e-4 rad/s` and reaction-torque error below `1e-4 Nm`.
For half-cycle integrals, require drive-work error below `2e-8 J`,
traction below `3e-8 J`, strain below `1e-10 J`, kinetic below
`1e-13 J`, angle below `3e-6 rad`, torque impulse below
`1e-6 N m s` and advected-angular impulse below `1e-11 N m s`.
Per-step span/combined mass and label-inventory defects should stay below
`1e-11` in their SI units; cumulative angular defect below
`1e-8 N m s`, reel/combined energy below `1e-8 J`, exact stored-energy
ownership below `1e-14 J`, and storage-versus-stage-flux defect below
`1e-10 J`. Require decreasing spatial errors and ledger defects above
roundoff, plus decreasing fixed-grid temporal field differences. These
are **proposed preimplementation synthetic gates**, not measured passes
or physical accuracy claims.

The solver must save original deposited profiles and leave the old
interval immutable. A test should mutate one newly stored profile after
reversal while preserving tautness, recompute its owned energy, and
confirm that exposed stretch, boundary speed, reel speed and reaction
torque respond. This rejects an implementation that replays the global
programmed `w(S)` on release. Reel inertia affects reaction torque in
this mode, not the span trajectory; no dynamic inertia feedback is
claimed. Actual torque-driven reversal, stored-strain mismatch, contact
losses, slack and site qualification remain separate gates.

[Lee, Leok and McClamroch](https://ccom.ucsd.edu/reports/UCSD-CCoM-09-01.pdf)
derive a retrieval loss for a different inextensible wound-side model;
its sign is not a loss law for this ideal matched elastic reversal.
[Singh and Hanna](https://arxiv.org/abs/1611.03332) likewise analyze
admissibility at moving string discontinuities, without validating this
synthetic cold-rolling boundary.
