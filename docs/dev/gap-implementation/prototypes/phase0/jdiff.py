import json, sys, math
def walk(a, b, path, out, tol=0.0):
    if type(a) != type(b) and not (isinstance(a,(int,float)) and isinstance(b,(int,float))):
        out.append((path, a, b)); return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a: out.append((path + '/' + k, '<absent>', b[k]))
            elif k not in b: out.append((path + '/' + k, a[k], '<absent>'))
            else: walk(a[k], b[k], path + '/' + k, out, tol)
    elif isinstance(a, list):
        if len(a) != len(b): out.append((path, f'len {len(a)}', f'len {len(b)}')); return
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, f'{path}[{i}]', out, tol)
    else:
        if a != b: out.append((path, a, b))
def diff(a, b):
    out = []; walk(a, b, '', out); return out
if __name__ == '__main__':
    a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
    d = diff(a, b)
    print(len(d), 'differences')
    import collections
    tops = collections.Counter(p.split('/')[1].split('[')[0] + '/' + (p.split('/')[2].split('[')[0] if p.count('/')>1 else '') for p,_,_ in d)
    for k, v in tops.most_common(): print('  ', v, k)
    for p, x, y in d[: int(sys.argv[3]) if len(sys.argv) > 3 else 60]:
        sx = json.dumps(x)[:90] if not isinstance(x, str) else x[:90]
        sy = json.dumps(y)[:90] if not isinstance(y, str) else y[:90]
        print(p, '|', sx, '->', sy)
