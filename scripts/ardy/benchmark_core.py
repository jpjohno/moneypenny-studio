"""Native motion-core benchmark, WITHOUT text conditioning or displayed output.

Zero text features measure the denoiser/decoder only. This does not establish
instruction following, complete text-to-motion speed, or animation quality.
"""
import argparse
import json
import time

import torch
from ardy.model import load_model


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--device',choices=['cpu','mps'],default='cpu');args=parser.parse_args()
    start=time.perf_counter();model=load_model('core',device='cpu',text_encoder=False)
    # ARDY packages some float64 buffers. Metal supports float32, so explicitly
    # convert before placement; this is an experimental benchmark, not validation
    # of numerical equivalence to NVIDIA's CUDA results.
    if args.device=='mps':
        model=model.float().to('mps');model.device=torch.device('mps')
    loaded=time.perf_counter()-start
    inputs=dict(texts=[''],num_frames=40,num_denoising_steps=int(model.diffusion.num_base_steps),
                pad_mask=torch.ones((1,40),dtype=torch.bool,device=args.device),first_heading_angle=torch.zeros(1,device=args.device),
                motion_mask=None,observed_motion=None,text_feat=torch.zeros((1,1,4096),device=args.device),
                text_pad_mask=torch.zeros((1,1),dtype=torch.bool,device=args.device))
    if args.device=='mps':torch.mps.synchronize()
    start=time.perf_counter()
    with torch.inference_mode():
        motion=model(**inputs)
        output=model.motion_rep.inverse(motion,is_normalized=True)
    if args.device=='mps':torch.mps.synchronize()
    elapsed=time.perf_counter()-start
    assert torch.isfinite(output['local_rot_mats']).all()
    print(json.dumps({'device':args.device,'mode':'unconditioned core benchmark only','text_encoder_used':False,
                      'load_seconds':round(loaded,3),'generation_seconds':round(elapsed,3),'motion_seconds':2,
                      'denoising_steps':int(model.diffusion.num_base_steps),'frames':40,'fps':20,
                      'text_to_motion_verified':False}))


if __name__=='__main__':main()
