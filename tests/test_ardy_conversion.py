"""Optional ARDY conversion checks; run in the dedicated ARDY environment."""
import importlib.util
from pathlib import Path
import json
import struct
import unittest

try:
    import numpy as np
    from scipy.spatial.transform import Rotation
except ImportError:
    np=None


@unittest.skipIf(np is None,'Run this optional suite in .runtime/ardy-venv')
class ConversionTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'scripts/ardy/convert_motion.py'
        spec=importlib.util.spec_from_file_location('ardy_conversion',path);self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.rotations=np.tile(np.eye(3,dtype=np.float32),(3,2,1,1))
        self.rotations[:,1]=Rotation.from_euler('z',np.array([[0],[.3],[0]])).as_matrix()
        self.positions=np.array([[0,1,0],[0,1.1,0],[0,1,0]],dtype=np.float32)
        self.neutral=np.array([[0,1,0],[0,1.5,0]],dtype=np.float32)
    def convert(self):return self.module.to_glb(self.rotations,self.positions,self.neutral,['Hips','Spine'],[-1,0],20)
    def test_self_contained_clip_preserves_joint_and_root_tracks(self):
        data=self.convert();magic,version,length=struct.unpack_from('<III',data)
        self.assertEqual((magic,version,length),(0x46546c67,2,len(data)))
        count=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+count])
        self.assertEqual(len(gltf['animations'][0]['channels']),3)
        self.assertEqual(gltf['nodes'][1]['translation'],[0,.5,0])
        self.assertEqual(gltf['skins'][0]['joints'],[0,1])
        self.assertFalse(any('uri' in item for item in gltf['buffers']))
    def test_bad_rotations_and_nan_are_rejected(self):
        self.rotations[0,0,0,0]=float('nan')
        with self.assertRaises(ValueError):self.convert()
        self.rotations[0,0]=np.eye(3)*2
        with self.assertRaises(ValueError):self.convert()


if __name__=='__main__':unittest.main()
