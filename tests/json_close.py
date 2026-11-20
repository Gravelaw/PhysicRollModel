"""Compare two JSON-like values, allowing floats to differ in their last digits.

A result recomputed on one platform and an artifact generated on another can differ in the last
digit of a float (the C library's elementary functions are not bit-identical across platforms).
``first_difference`` returns ``None`` when two values are equal apart from that, otherwise a
string naming the first path at which they differ and both values, so that a failing test says
what differs instead of printing a diff of the whole structure.
"""
import math

REL_TOL = 1e-9
ABS_TOL = 1e-12


def first_difference(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL, path='$'):
    if isinstance(a, bool) or isinstance(b, bool):
        return None if a is b else f'{path}: {a!r} != {b!r}'
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b or math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol):
            return None
        return f'{path}: {a!r} != {b!r}'
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return f'{path}: keys differ: {sorted(set(a) ^ set(b))}'
        for k in a:
            d = first_difference(a[k], b[k], rel_tol, abs_tol, f'{path}.{k}')
            if d:
                return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f'{path}: lengths {len(a)} != {len(b)}'
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, rel_tol, abs_tol, f'{path}[{i}]')
            if d:
                return d
        return None
    return None if a == b else f'{path}: {a!r} != {b!r}'
