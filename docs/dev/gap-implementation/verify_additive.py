"""Check that the working-tree artifacts differ from HEAD only by additions.

For every artifacts/band_diagnosis/*.result.json: every path present at HEAD must still hold the
same value; a list may gain elements (the old list must be a subsequence of the new one); new
dict keys are counted. Hypothesis scores, order and standings are printed if they differ.
Run from the repository root.
"""
import glob
import json
import subprocess
import sys


def sub(old, new):
    it = iter(new)
    return all(any(same(o, n) for n in it) for o in old)


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def walk(old, new, path, out):
    if isinstance(old, dict) and isinstance(new, dict):
        for k in old:
            if k not in new:
                out['removed'].append(path + '.' + k)
            else:
                walk(old[k], new[k], path + '.' + k, out)
        out['added'] += [path + '.' + k for k in new if k not in old]
    elif isinstance(old, list) and isinstance(new, list):
        if len(old) == len(new):
            for i, (o, n) in enumerate(zip(old, new)):
                walk(o, n, f'{path}[{i}]', out)
        elif sub(old, new):
            out['list_grew'].append(f'{path} (+{len(new) - len(old)})')
        else:
            out['changed'].append(path + ' (list)')
    elif not same(old, new):
        out['changed'].append(path)


bad = False
for p in sorted(glob.glob('artifacts/band_diagnosis/*.result.json')):
    r = subprocess.run(['git', 'show', 'HEAD:' + p], capture_output=True, text=True)
    if r.returncode:
        print(p, 'NEW FILE')
        continue
    old, new = json.loads(r.stdout), json.load(open(p))
    out = {'added': [], 'removed': [], 'changed': [], 'list_grew': []}
    walk(old, new, '', out)
    hyp = lambda x: [(h['id'], h['score'], h.get('standing')) for h in x.get('hypotheses', [])]
    moved = hyp(old) != hyp(new)
    print(f"{p.split('/')[-1]}: added {len(out['added'])}, lists grown {len(out['list_grew'])}, "
          f"changed {len(out['changed'])}, removed {len(out['removed'])}, "
          f"hypotheses {'MOVED' if moved else 'same'}")
    for k in ('changed', 'removed'):
        for x in out[k][:12]:
            print('   ', k, x)
    if '-v' in sys.argv:
        for x in out['added'] + out['list_grew']:
            print('    +', x)
    bad = bad or out['changed'] or out['removed'] or moved
print('RESULT:', 'NOT ADDITIVE' if bad else 'additive only')
