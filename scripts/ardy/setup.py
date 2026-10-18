"""Isolated ARDY setup. Does not change system Python, trading or Jarvis services."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import venv


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--download-motion-model',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];manifest=json.loads((root/'ardy-manifest.json').read_text())
    runtime=root/'.runtime';runtime.mkdir(exist_ok=True)
    repo=runtime/'ardy'
    if not repo.exists():
        subprocess.run(['git','clone',manifest['repository'],str(repo)],check=True)
    dirty=subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True)
    current=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if current!=manifest['commit']:
        if dirty:raise RuntimeError('Existing ARDY edits preserved. Resolve them before changing the source revision.')
        subprocess.run(['git','-C',str(repo),'fetch','origin',manifest['commit']],check=True)
        subprocess.run(['git','-C',str(repo),'checkout','--detach',manifest['commit']],check=True)
    environment=runtime/'ardy-venv'
    if not environment.exists():venv.EnvBuilder(with_pip=True).create(environment)
    python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    subprocess.run([str(python),'-m','pip','install','-e',str(repo)],check=True)
    if args.download_motion_model:
        subprocess.run([str(python),'-c','from huggingface_hub import snapshot_download; snapshot_download("nvidia/ARDY-Core-RP-20FPS-Horizon40",max_workers=2)'],check=True)
    result=subprocess.run([str(python),str(Path(__file__).with_name('probe.py'))],capture_output=True,text=True,check=True)
    report=json.loads(result.stdout.strip().splitlines()[-1]);(runtime/'ardy-status.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
