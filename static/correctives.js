import * as THREE from 'three';

const specs = [
  ['corrective_elbow_L', 'LeftArm', 'LeftForeArm', 'LeftHand'],
  ['corrective_elbow_R', 'RightArm', 'RightForeArm', 'RightHand'],
  ['corrective_knee_L', 'LeftUpLeg', 'LeftLeg', 'LeftFoot'],
  ['corrective_knee_R', 'RightUpLeg', 'RightLeg', 'RightFoot'],
];
const canonical = name => name.replace(/^mixamorig:?/, '');

// Explicit authored corrective morphs only. Existing avatars and facial morphs
// remain untouched; angle comes from actual world-space joint positions.
export class PoseCorrectives {
  constructor(root) {
    this.root = root;
    this.bindings = [];
    const bones = new Map(), meshes = [];
    root.traverse(node => {
      if (node.isBone) bones.set(canonical(node.name), node);
      if (node.morphTargetDictionary && node.morphTargetInfluences) meshes.push(node);
    });
    for (const [key, ...names] of specs) {
      const joints = names.map(name => bones.get(name));
      const targets = meshes.filter(mesh => mesh.morphTargetDictionary[key] !== undefined)
        .map(mesh => [mesh.morphTargetInfluences, mesh.morphTargetDictionary[key]]);
      if (joints.every(Boolean) && targets.length) this.bindings.push({ joints, targets, value: 0 });
    }
    this.a = new THREE.Vector3(); this.b = new THREE.Vector3(); this.c = new THREE.Vector3();
  }
  update(seconds) {
    if (!this.bindings.length) return;
    this.root.updateMatrixWorld(true);
    const alpha = 1 - Math.exp(-Math.max(0, seconds) / .04);
    for (const binding of this.bindings) {
      binding.joints[0].getWorldPosition(this.a);
      binding.joints[1].getWorldPosition(this.b);
      binding.joints[2].getWorldPosition(this.c);
      this.a.sub(this.b); this.c.sub(this.b);
      const product = this.a.length() * this.c.length();
      const angle = product > 1e-10 ? Math.PI - Math.acos(THREE.MathUtils.clamp(this.a.dot(this.c) / product, -1, 1)) : 0;
      const target = THREE.MathUtils.clamp(angle / 1.6, 0, 1);
      binding.value += (target - binding.value) * alpha;
      for (const [influences, index] of binding.targets) influences[index] = binding.value;
    }
  }
}
