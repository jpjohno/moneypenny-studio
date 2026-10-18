import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';
import { PoseCorrectives } from '../static/correctives.js';

function setup() {
  const root = new THREE.Group();
  const arm = new THREE.Bone(), elbow = new THREE.Bone(), wrist = new THREE.Bone();
  arm.name = 'mixamorig:LeftArm'; elbow.name = 'mixamorig:LeftForeArm'; wrist.name = 'mixamorig:LeftHand';
  root.add(arm); arm.add(elbow); elbow.add(wrist); elbow.position.x = 1; wrist.position.x = 1;
  const mesh = new THREE.Object3D();
  mesh.morphTargetDictionary = { corrective_elbow_L: 0, viseme_aa: 1 };
  mesh.morphTargetInfluences = [0, .6]; root.add(mesh);
  return { root, elbow, mesh, correctives: new PoseCorrectives(root) };
}
test('corrective follows measured joint bend and releases without touching speech', () => {
  const s = setup(); s.correctives.update(1);
  assert.equal(s.mesh.morphTargetInfluences[0], 0);
  s.elbow.rotation.z = Math.PI / 2; s.correctives.update(1);
  assert.ok(s.mesh.morphTargetInfluences[0] > .98);
  assert.equal(s.mesh.morphTargetInfluences[1], .6);
  s.elbow.rotation.z = 0; s.correctives.update(1);
  assert.ok(s.mesh.morphTargetInfluences[0] < 1e-8);
});
test('world rotation and scale do not change bend; smoothing is frame-rate independent', () => {
  const a = setup(), b = setup();
  b.root.scale.setScalar(.3); b.root.rotation.set(.2, .8, -.5);
  a.elbow.rotation.z = b.elbow.rotation.z = 1;
  for (let i = 0; i < 30; i++) a.correctives.update(1 / 30);
  for (let i = 0; i < 60; i++) b.correctives.update(1 / 60);
  assert.ok(Math.abs(a.mesh.morphTargetInfluences[0] - b.mesh.morphTargetInfluences[0]) < 1e-10);
});
test('avatars without authored corrective shapes are unchanged', () => {
  const root = new THREE.Group(); const c = new PoseCorrectives(root);
  assert.equal(c.bindings.length, 0); c.update(1 / 60);
});
