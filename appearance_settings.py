"""Shared, allowlisted appearance choices for Studio and the embedded assistant."""
import json, math, os, tempfile
from pathlib import Path
PATH=Path(__file__).resolve().parent/'.runtime/appearance.json'
DEFAULTS={'blouseColor':'petrol','hairTone':'darkblonde','lightingLook':'daylight','lightBrightness':'1'}
CHOICES={'blouseColor':{'petrol','navy','ivory','plum'},'hairTone':{'original','warm','darkblonde','brunette'},'lightingLook':{'daylight','portrait','neutral'}}
def validate(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULTS):raise ValueError('Unsupported appearance setting')
    result=dict(DEFAULTS)
    for key,item in value.items():
        if key in CHOICES:
            if not isinstance(item,str) or item not in CHOICES[key]:raise ValueError('Unsupported appearance choice')
            result[key]=item
        else:
            if isinstance(item,bool) or not isinstance(item,(str,int,float)):raise ValueError('Invalid brightness')
            n=float(item)
            if not math.isfinite(n) or not .65<=n<=1.25:raise ValueError('Brightness must be between 0.65 and 1.25')
            result[key]=str(n)
    return result

def read():
    try:
        if PATH.is_symlink():return dict(DEFAULTS)
        return validate(json.loads(PATH.read_text()))
    except (ValueError,OSError,TypeError):return dict(DEFAULTS)

def save(value):
    result=validate(value);PATH.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=PATH.parent,prefix='appearance-',suffix='.tmp',delete=False) as stream:
        json.dump(result,stream);temporary=Path(stream.name)
    temporary.replace(PATH);return result
