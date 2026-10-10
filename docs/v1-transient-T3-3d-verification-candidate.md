# T3 full 3D verification candidate

**Status: specialist-derived candidate pending independent equation-level
review; no engine is implemented.** This is the first full 3D elastic
material/contact verification increment on the [v1 integration path](v1-integration-critical-path.md).
It can advance while the separate [T2 reel-pickup decision](v1-transient-T2-pickup-decision.md)
is pending. Rigid planes are a flat-tool limit; success here does not satisfy
cylindrical rolling, plasticity, friction, or the required dynamic compliant
elastic-roll mode. The shipped T3 strip/contact domain remains full 3D.

## Manufactured elastic block with closed frictionless contact

Use a total-Lagrangian strip block on reference coordinates `X` (rolling),
`Y` (width), `Z` (thickness):

```text
Omega0=[0,L]x[0,B]x[0,H], (L,B,H)=(0.1,0.04,0.002) m
E=2e8 Pa, nu=0.3, rho0=2000 kg/m^3
mu=E/[2(1+nu)], lambda_L=E nu/[(1+nu)(1-2nu)]
Psi(F)=mu/2*(tr(F^T F)-3)-mu ln J+lambda_L/2*(ln J)^2
P=mu*(F-F^(-T))+lambda_L*ln(J)*F^(-T), J=det(F)>0.
```

This compressible neo-Hookean law is selected for **elastic code
verification only**. The [INL material implementation](https://salamander.inl.gov/source/materials/lagrangian/ComputeNeoHookeanStress.html)
documents the same class of finite-strain response; it does not validate
our engine or select the eventual finite-strain J2 material model.

Set `phi=sin^2(pi X/L) sin^2(pi Y/B) sin^2(pi Z/H)` and the exact motion

```text
x=X+a_x sin(Omega t) phi
y=Y+a_y sin(Omega t) phi
z=[1-gamma(t)]Z+a_z sin(Omega t) phi
(a_x,a_y,a_z)=(2,1,0.1)e-6 m
gamma(t)=.002+.0005 sin(Omega t), Omega=2 pi*10^4 s^-1
0<=t<=.0002 s (two periods).
```

Manufacture body acceleration independently as
`b=x_ddot-rho0^(-1) Div_X P`. Generate its reference derivatives using an
independent symbolic expression and quadrature, not the runtime element
gradient or constitutive routine. This is a code-verification case following
the [Sandia method-of-manufactured-solutions framework](https://www.sandia.gov/research/publications/details/code-verification-by-the-method-of-manufactured-solutions-2000-06-01/),
not a measured strip deformation.

Sample the full field at least at `t=0`, the first quarter period
`0.000025 s`, half period `0.00005 s`, three-quarter period `0.000075 s`,
and corresponding `0.000125` and `0.000175 s` points in the second period.
Compare each displacement component and off-diagonal deformation/stress
component, not only total force. The interior 3D sinusoidal
displacement vanishes at integer half periods; comparisons only at the
initial and terminal times would miss the intended cross-width and shear
test. Check nonzero subcycle body and boundary work, not just cancellation
over complete periods.

The bottom plane is `z=0`; the top plane is `z=H[1-gamma(t)]`. Use
frictionless unilateral contact at the thickness faces and the exact nominal
traction `P N` on the four lateral faces. Initialize position, velocity and
stress from the exact state at `t=0`, which is already compressed. Initial
velocity includes `a_i*Omega*phi` in every component and
`-gamma_dot(0)*Z` in the thickness component. Reference mass is exactly
`rho0*L*B*H=0.016 kg`. Do not
add an independent normal displacement condition at contact nodes. The
dynamic initial-value problem fixes in-plane rigid motion without artificial
point clamps. Since `phi` and its first derivatives vanish on every
boundary, the contact-face `F=diag(1,1,s)`, `s=1-gamma`, and the exact
pressure and top resultant are

```text
p=-[mu*(s-1/s)+lambda_L*ln(s)/s]>0
F_top=p*L*B.
```

Independent scalar evaluation gives:

| Compression `gamma` | Pressure (Pa) | Top force (N) |
|---:|---:|---:|
| 0.0015 | 404409.629013 | 1617.638516 |
| 0.0020 | 539463.851242 | 2157.855405 |
| 0.0025 | 674643.942717 | 2698.575771 |

The top-tool power is `p*L*B*H*gamma_dot`, positive in compression. The
bottom and lateral work vanish for this exact boundary motion, although
lateral tractions need not vanish. The oracle energy relation is

```text
d/dt integral_Omega0 [rho0*|x_dot|^2/2+Psi] dV
 = integral_Omega0 rho0*b.x_dot dV + p*L*B*H*gamma_dot.
```

## Proposed numerical gate before implementation

Prototype the same input/oracle pack on `8x4x2`, `16x8x4`, and `32x16x8`
3D meshes with a separate time-refinement sequence. An explicit prototype
must meet its actual element and contact stability limit; render-frame times
are not solver time steps. Declare element, quadrature, locking/hourglass
treatment, contact enforcement, physical versus algorithmic dissipation,
accepted-step rollback and all boundary-work terms before measuring error.

Initial **provisional aspirations**, not endorsed acceptance thresholds, are
relative mass defect `<1e-8`; normalized finest-grid displacement, stress
and contact-force errors `<1e-3`; and scaled work/energy residual `<1e-3`
with a nonzero characteristic scale. The element order, exact norms,
nonzero scales, stress measure (for example first Piola stress), sampled
components and time steps must be fixed before any thresholds are frozen.
In particular, low-order elements on the proposed eight-cell thickness
grid may not resolve stress derivatives of `sin^2(pi Z/H)` to `<1e-3`;
refine further if needed. Require separate spatial and temporal
convergence, contact-parameter refinement if penetration is regularized,
and reported tangential traction/work, complementarity, minimum `J` and
artificial energy. The always-closed case tests a full 3D elastic field and
normal contact, but not contact activation, slip, plasticity, curved tools
or free width spread.

## Follow-on gates required for the v1 modes

The rigid-tool path next needs independent finite-strain J2 material-point
paths, elastic impact/release, frictional sliding/stick transitions,
finite-curvature contact and a separately converged full-width transient
cylindrical rolling reference. [Hesch and Betsch's dynamic contact work](https://www.mb.uni-siegen.de/nm/forschung/paper/ijnmemortarcontact.pdf)
supports checking contact energy and momentum, but its examples are
two-dimensional and frictionless; it is not the missing full 3D rolling
reference.

For the compliant mode, first verify the roll/stand structure without strip
contact. A simply supported slender-beam limit across width gives the
independent first-mode checks

```text
rho*A*w_tt+E*I*w_YYYY=q1*sin(pi Y/B), w=w_YY=0 at Y=0,B
w(Y,0)=w_t(Y,0)=0; load is constant in time after its step application
omega1=(pi/B)^2 sqrt(EI/(rho*A))
w(Y,t)=[q1/(EI(pi/B)^4)]*[1-cos(omega1*t)]*sin(pi Y/B).
```

For `B=1 m`, radius `0.01 m`, `E=2e11 Pa`, density `7800 kg/m^3`
and `q1=1 N/m`, the slender limit has `f1=39.7701819454 Hz` and
static mode amplitude `6.5355272861e-6 m`. This is not an exact finite
cylinder result: journal constraints, shear and rotary inertia must be
declared, and an antisymmetric width mode must test against accidental
symmetry constraints. Then verify support eigenvalues and impulses,
nonuniform width loading, preloaded vibration, asymmetric upper/lower
motion and lift-off/re-contact, spin/prestress and modal reduction against
the unreduced structural model. Keep the strip/contact engine full 3D
throughout; a beam roll is only a structural verification limit.

At any T2/T3 interface, contact tractions and power must balance between
bodies, with frictional dissipation separate. Shaft inertia and deformational
roll/stand inertia have distinct owners. Span and 3D strip domains must not
own the same mass or compliance. A moving cut transfers material label,
mass, momentum, energy and plastic history. Rejected nonlinear/contact
trials restore all history. Finite-strain J2 details, element locking,
contact/friction regularization, journal support, cut transfer and an
independent finite-width transient rolling reference remain open choices.
