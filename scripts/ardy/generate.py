"""Explicit offline clip generation; uses NVIDIA's genuine Core model and correction.

Run in the dedicated ARDY environment. No substitute embeddings or fake motion.
"""
import os
from pathlib import Path
import subprocess
import sys

from convert_motion import convert


def main():
    if len(sys.argv)!=4:raise SystemExit('Usage: generate.py "motion description" duration output.glb')
    prompt,seconds,output=sys.argv[1:];duration=float(seconds)
    if not prompt.strip() or len(prompt)>1000 or not 1<=duration<=10:raise ValueError('Use a description under 1000 characters and 1–10 seconds.')
    root=Path(__file__).resolve().parents[2];repo=root/'.runtime/ardy';destination=Path(output).resolve()
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Fixed argv, no shell. Keep model-based text encoding local to this worker.
    env={**os.environ,'TEXT_ENCODER_MODE':'local'}
    subprocess.run([sys.executable,str(repo/'scripts/generate.py'),prompt,'--model','core','--duration',str(duration),'--num_samples','1','--output',str(destination.with_suffix(''))],cwd=repo,env=env,check=True)
    convert(destination.with_suffix('.npz'),destination)
    print('ARDY_GLB_READY',destination)


if __name__=='__main__':main()
