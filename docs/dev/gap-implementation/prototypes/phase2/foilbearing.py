import math
def constant(eps=1e-6, step=1e-3, hmax=1e4):
    # H''' = (1 - H)/H^3, integrate towards xi -> -infinity from H = 1 + eps*exp(-xi) at xi = 0
    y = [1 + eps, -eps, eps]
    def f(y): return [y[1], y[2], (1 - y[0])/y[0]**3]
    h = -step; n = 0
    while y[0] < hmax and n < 10**7:
        k1 = f(y); k2 = f([a + 0.5*h*b for a, b in zip(y, k1)]); k3 = f([a + 0.5*h*b for a, b in zip(y, k2)]); k4 = f([a + h*b for a, b in zip(y, k3)])
        y = [a + h*(b + 2*c + 2*d + e)/6 for a, b, c, d, e in zip(y, k1, k2, k3, k4)]; n += 1
    return y[2], y[0], n
for eps, step, hmax in ((1e-6, 1e-3, 1e4), (1e-8, 1e-3, 1e5), (1e-6, 5e-4, 1e5)):
    print(eps, step, hmax, constant(eps, step, hmax))
mu, R, V, T = 1.8e-5, 0.125, 10.0, 720.0
print('film R 0.125:', 0.643*R*(6*mu*2*V/T)**(2/3), ' coil R 0.3:', 0.643*0.3*(6*mu*2*V/T)**(2/3))
