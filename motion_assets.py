"""Local animation assets. Uploads are inert data and never execute instructions."""
import json
from pathlib import Path
import threading
import uuid
from motion import validate_plan

ROOT=Path(__file__).resolve().parent
DIRECTORY=ROOT/'.runtime/motion-library'
LOCK=threading.Lock()
BUILTINS=[dict(id='studio-wave',name='Studio wave · Blender IK study',url='/static/motions/studio-wave.glb',format='glb',source='Studio Blender-authored study',aliases=['wave','wave hello']),
          dict(id='studio-bow',name='Studio bow',url='/static/motions/studio-bow.motion.json',format='motion',source='Studio authored study',aliases=['bow']),
          dict(id='studio-stretch',name='Studio shoulder stretch',url='/static/motions/studio-stretch.motion.json',format='motion',source='Studio authored study',aliases=['stretch'])]
SEQUENCE_SKILLS={'wave','bow','stretch','turn','bend_forward','walk','dance','jig','idle'}


def library():
    try:items=json.loads((DIRECTORY/'index.json').read_text())
    except (OSError,ValueError):items=[]
    return BUILTINS+items


def add(name,filename,data):
    if not isinstance(name,str) or not name.strip() or len(name)>80:raise ValueError('Give the movement a name under 80 characters.')
    if not 20<len(data)<=24*1024*1024:raise ValueError('Animation files must be under 24 MB.')
    extension=Path(filename).suffix.lower()
    if filename.lower().endswith('.sequence.json'):
        value=json.loads(data)
        if not isinstance(value,dict) or type(value.get('version')) is not int or value['version']!=1 or value.get('kind')!='sequence':
            raise ValueError('Unsupported animation sequence format.')
        if not isinstance(value.get('steps'),list) or any(not isinstance(step,dict) or step.get('skill') not in SEQUENCE_SKILLS for step in value['steps']):
            raise ValueError('The animation sequence contains an unsupported movement.')
        cleaned=validate_plan({'steps':value['steps']})
        # Persist only validated movement data. Unknown fields and embedded
        # instructions are never carried into a reopened animation.
        data=json.dumps({'version':1,'kind':'sequence','name':name.strip(),**cleaned}).encode()
        extension='.sequence.json';kind='sequence'
    elif filename.lower().endswith('.motion.json'):
        value=json.loads(data)
        if value.get('version')!=1:raise ValueError('Unsupported motion format.')
        validate_plan({'steps':[{'skill':'custom','duration':value.get('duration',4),'frames':value.get('frames')}]})
        extension='.motion.json';kind='motion'
    elif extension=='.glb':
        import struct
        if data[:4]!=b'glTF' or struct.unpack_from('<II',data,4)!=(2,len(data)):raise ValueError('Use a GLB 2.0 animation file.')
        length,chunk=struct.unpack_from('<II',data,12)
        if chunk!=0x4e4f534a or 20+length>len(data):raise ValueError('Invalid GLB metadata.')
        value=json.loads(data[20:20+length])
        if not value.get('animations'):raise ValueError('The GLB contains no animation clips.')
        if any(x.get('uri') and not x['uri'].startswith('data:') for x in value.get('buffers',[])+value.get('images',[])):raise ValueError('Animation GLBs must contain all data; external links are not allowed.')
        kind='glb'
    elif extension=='.bvh':
        decoded=data.decode('utf8')
        if not decoded.lstrip().startswith('HIERARCHY') or 'MOTION' not in decoded:raise ValueError('Use a valid BVH motion-capture file.')
        kind='bvh'
    else:raise ValueError('Import GLB, BVH, .motion.json or .sequence.json animation data.')
    identity=str(uuid.uuid4());record=dict(id=identity,name=name.strip(),format=kind,source='Your local animation',url='/api/motion/assets/'+identity,filename=identity+extension,aliases=[])
    with LOCK:
        DIRECTORY.mkdir(parents=True,exist_ok=True)
        items=[r for r in library() if r['id'] not in {b['id'] for b in BUILTINS}]
        (DIRECTORY/record['filename']).write_bytes(data)
        items.append(record);temporary=DIRECTORY/'index.partial';temporary.write_text(json.dumps(items));temporary.replace(DIRECTORY/'index.json')
    return record


def asset(identity):
    record=next((r for r in library() if r['id']==identity and 'filename' in r),None)
    if not record:raise ValueError('Animation not found.')
    return record['filename']
