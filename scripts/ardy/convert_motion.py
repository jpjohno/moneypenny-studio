"""Convert genuine ARDY Core output to a self-contained animation-only GLB.

No body, portrait, textures or generated motion is invented by this converter.
Skeleton metadata comes from the installed NVIDIA ARDY package (Apache-2.0).
"""
import json
from pathlib import Path
import struct

import numpy as np
from scipy.spatial.transform import Rotation


def to_glb(rotations, positions, neutral, names, parents, fps):
    rotations=np.asarray(rotations,dtype=np.float32)
    positions=np.asarray(positions,dtype=np.float32)
    neutral=np.asarray(neutral,dtype=np.float32)
    frames,joints=rotations.shape[:2]
    if rotations.shape!=(frames,joints,3,3) or positions.shape!=(frames,3) or neutral.shape!=(joints,3):
        raise ValueError('Unexpected ARDY motion dimensions.')
    if not 2<=frames<=1800 or not 1<=fps<=120 or len(names)!=joints or len(parents)!=joints:
        raise ValueError('Unsupported ARDY clip size or frame rate.')
    if any(not np.isfinite(a).all() for a in (rotations,positions,neutral)):
        raise ValueError('ARDY returned non-finite motion.')
    if parents[0]!=-1 or any(not 0<=parents[i]<i for i in range(1,joints)):
        raise ValueError('Unsupported skeleton hierarchy.')
    if not np.allclose(rotations @ rotations.swapaxes(-1,-2),np.eye(3),atol=.015) or not np.allclose(np.linalg.det(rotations),1,atol=.015):
        raise ValueError('ARDY returned invalid joint rotations.')
    binary=bytearray();views=[];accessors=[]
    def add(array,kind,component=5126):
        array=np.ascontiguousarray(array)
        while len(binary)%4:binary.append(0)
        index=len(views);views.append({'buffer':0,'byteOffset':len(binary),'byteLength':array.nbytes});binary.extend(array.tobytes())
        value={'bufferView':index,'componentType':component,'count':len(array),'type':kind}
        if kind in ('SCALAR','VEC3') and component==5126:
            value['min']=np.atleast_1d(array.min(axis=0)).tolist();value['max']=np.atleast_1d(array.max(axis=0)).tolist()
        accessors.append(value);return len(accessors)-1
    nodes=[]
    for i,name in enumerate(names):
        offset=neutral[i]-(neutral[parents[i]] if i else 0)
        node={'name':name,'translation':offset.tolist()}
        children=[j for j,p in enumerate(parents) if p==i]
        if children:node['children']=children
        nodes.append(node)
    time=add(np.arange(frames,dtype=np.float32)/fps,'SCALAR');samplers=[];channels=[]
    for i in range(joints):
        values=Rotation.from_matrix(rotations[:,i]).as_quat().astype(np.float32)
        # Keep quaternion signs continuous for interpolation.
        for f in range(1,frames):
            if values[f]@values[f-1]<0:values[f]*=-1
        samplers.append({'input':time,'output':add(values,'VEC4'),'interpolation':'LINEAR'})
        channels.append({'sampler':len(samplers)-1,'target':{'node':i,'path':'rotation'}})
    samplers.append({'input':time,'output':add(positions,'VEC3'),'interpolation':'LINEAR'})
    channels.append({'sampler':len(samplers)-1,'target':{'node':0,'path':'translation'}})
    # An invisible carrier triangle keeps the exported hierarchy a standard glTF skin.
    attrs={'POSITION':add(np.array([[0,0,0],[.0001,0,0],[0,.0001,0]],dtype=np.float32),'VEC3'),
           'JOINTS_0':add(np.zeros((3,4),dtype=np.uint16),'VEC4',5123),
           'WEIGHTS_0':add(np.tile(np.array([1,0,0,0],dtype=np.float32),(3,1)),'VEC4')}
    inverse=np.tile(np.eye(4,dtype=np.float32),(joints,1,1));inverse[:,:3,3]=-neutral
    bind=add(inverse.transpose(0,2,1).reshape(joints,16),'MAT4')
    nodes.append({'name':'Motion carrier','mesh':0,'skin':0})
    value={'asset':{'version':'2.0','generator':'Moneypenny ARDY bridge'},'scene':0,'scenes':[{'nodes':[0,joints]}],
           'nodes':nodes,'skins':[{'joints':list(range(joints)),'skeleton':0,'inverseBindMatrices':bind}],
           'meshes':[{'primitives':[{'attributes':attrs,'mode':4}]}],
           'animations':[{'name':'ARDY generated motion','samplers':samplers,'channels':channels}],
           'buffers':[{'byteLength':len(binary)}],'bufferViews':views,'accessors':accessors}
    metadata=json.dumps(value,separators=(',',':')).encode();metadata+=b' '*((-len(metadata))%4);binary+=b'\0'*((-len(binary))%4)
    return struct.pack('<III',0x46546c67,2,28+len(metadata)+len(binary))+struct.pack('<II',len(metadata),0x4e4f534a)+metadata+struct.pack('<II',len(binary),0x004e4942)+binary


def convert(source,destination):
    from ardy.skeleton import CoreSkeleton27
    skeleton=CoreSkeleton27()
    with np.load(source,allow_pickle=False) as motion:
        payload=to_glb(motion['local_rot_mats'],motion['root_positions'],skeleton.neutral_joints.numpy(),skeleton.bone_order_names,skeleton.joint_parents.tolist(),float(motion['fps']))
    Path(destination).write_bytes(payload)


if __name__=='__main__':
    import sys
    convert(sys.argv[1],sys.argv[2])
