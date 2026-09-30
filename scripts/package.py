"""Make a portable ZIP without Git metadata, credentials, dependencies or caches."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=ROOT.parent/'PhysicRollModel-prototype-v0.2.zip')
args=p.parse_args()
include=['README.md','LICENSE','.gitignore','pyproject.toml','requirements-preview.txt','requirements-verify-usd.txt']
for directory in ['physicroll','blender','scenarios','schema','tests','scripts','docs','artifacts']:
    for path in sorted((ROOT/directory).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ['.pyc','.log','.blend1']:
            include.append(path.relative_to(ROOT).as_posix())
args.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name in include:
        archive.write(ROOT/name,'PhysicRollModel/'+name)
print(args.output.resolve())
print('files:',len(include),'bytes:',args.output.stat().st_size)
print('SHA256:',hashlib.sha256(args.output.read_bytes()).hexdigest())
