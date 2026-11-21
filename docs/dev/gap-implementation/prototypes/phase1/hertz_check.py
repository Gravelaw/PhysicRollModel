"""Self-check of the influence coefficients against Hertz line contact."""
import math, sys
sys.path.insert(0, '.')
from hs_kernel import influence, G

def kappa(k):
    def f(m):
        return 0.0 if m == 0 else m * m * math.log(abs(m))
    return 0.5 * (f(k + 1) - 2 * f(k) + f(k - 1))

# 1. uniform-grid closed form
x = [i * 0.1 for i in range(11)]
I = influence(x)
d = 0.1
err = max(abs(I[j][k] - d * (kappa(j - k) + math.log(d) - 1.5)) for j in range(11) for k in range(1, 10))
print('uniform closed form max abs err', err)
print('kappa(0..3)', [kappa(k) for k in range(4)], '2ln2', 2*math.log(2))
# half hats: two half hats at same node = full hat
x3 = [0.0, 0.1, 0.2]
I3 = influence(x3)
# compare with numerical quadrature of full element
def quad(fun, a, b, n=20000):
    h = (b - a) / n
    return sum(fun(a + (i + 0.5) * h) for i in range(n)) * h
s = 0.37
num = quad(lambda t: (1 - abs(t - 0.1) / 0.1) * math.log(abs(s - t)), 0.0, 0.2)
ana = (G(s - 0.0) - G(s - 0.1)) / 0.1 + (G(s - 0.2) - G(s - 0.1)) / 0.1
print('hat quadrature', num, ana)
from hs_kernel import _half
num = quad(lambda t: (0.1 - t) / 0.1 * math.log(abs(s - t)), 0.0, 0.1)
print('half hat', num, _half(s, 0.0, 0.1))
# non-uniform
xs = [0.0, 0.03, 0.1, 0.22]
In = influence(xs)
num = quad(lambda t: ((t - 0.03) / 0.07 if t < 0.1 else (0.22 - t) / 0.12) * math.log(abs(0.05 - t)), 0.03, 0.22, 200000)
print('nonuniform hat k=2 at node x=0.05?', num)
num = quad(lambda t: ((t - 0.03) / 0.07 if t < 0.1 else (0.22 - t) / 0.12) * math.log(abs(0.0 - t)), 0.03, 0.22, 200000)
print('nonuniform hat k=2 at j=0', num, In[0][2])

# 2. Hertz: p = p0 sqrt(1-x^2/a^2) with p0 = a E*/(2R)  ->  u(0)-u(x) = x^2/(2R)
Estar, R = 230e9, 0.089
a = 1.0e-3
p0 = a * Estar / (2 * R)
P = math.pi * a * p0 / 2
for n in (20, 40, 80, 160):
    xs = [-a + 2 * a * i / n for i in range(n + 1)]
    p = [p0 * math.sqrt(max(0.0, 1 - (xx / a) ** 2)) for xx in xs]
    I = influence(xs)
    u = [-(2 / (math.pi * Estar)) * sum(I[j][k] * p[k] for k in range(1, n)) for j in range(n + 1)]
    mid = n // 2
    worst = 0.0
    for j in range(n + 1):
        exact = xs[j] ** 2 / (2 * R)
        worst = max(worst, abs((u[mid] - u[j]) - exact))
    depth = a * a / (2 * R)
    # interior only (|x| <= 0.8 a)
    worst_in = max(abs((u[mid] - u[j]) - xs[j] ** 2 / (2 * R)) for j in range(n + 1) if abs(xs[j]) <= 0.8 * a)
    load = sum(0.5 * (p[k] + p[k + 1]) * (xs[k + 1] - xs[k]) for k in range(n))
    print(f'n={n:4d} max|err|/depth all nodes {worst/depth:.3e}  |x|<=0.8a {worst_in/depth:.3e}  load err {load/P-1:.3e}')
