"""Read-only runtime inventory. Never loads weights or prints credentials."""
import json
import os
from pathlib import Path


def inspect():
    import torch
    import ardy
    from ardy.skeleton import CoreSkeleton27
    from huggingface_hub import try_to_load_from_cache
    from huggingface_hub.constants import HF_TOKEN_PATH
    CoreSkeleton27()  # Verify the packaged skeleton assets, not only an import.
    cuda=torch.cuda.is_available()
    correction=False
    try:
        from motion_correction import motion_postprocess
        correction=True
    except ImportError:
        try:
            import _motion_correction
            correction=True
        except ImportError:pass
    def cached(repo,file):return isinstance(try_to_load_from_cache(repo,file),str)
    checkpoint=cached('nvidia/ARDY-Core-RP-20FPS-Horizon40','config.yaml')
    encoder=cached('meta-llama/Meta-Llama-3-8B-Instruct','config.json')
    token=bool(os.environ.get('HF_TOKEN')) or Path(HF_TOKEN_PATH).is_file()
    reasons=[]
    if not token and not encoder:reasons.append('Access to the required Llama text model is not configured.')
    if not checkpoint:reasons.append('The ARDY motion checkpoint has not been downloaded.')
    # Cached config files alone never prove complete model weights or model access.
    return {'installed':True,'cuda':cuda,'device':torch.cuda.get_device_name(0) if cuda else 'CPU',
            'notes':[] if cuda else ['Native CPU fallback is available. Text-to-motion speed on this Mac is unverified.'],
            'torch':torch.__version__,'correction':correction,'checkpoint_config_cached':checkpoint,
            'encoder_config_cached':encoder,'token_configured':token,'ready':False,
            'reasons':reasons or ['Run an explicit generation smoke test to verify complete weights and access.']}


if __name__=='__main__':
    try:result=inspect()
    except Exception as error:result={'installed':False,'ready':False,'reasons':['ARDY runtime check failed: '+type(error).__name__]}
    print(json.dumps(result))
