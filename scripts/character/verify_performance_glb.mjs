// Validate the actual private export's geometry and facial/rig contract with
// Three.js. Image decoding/rendering is deliberately not claimed by this check.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { PoseCorrectives } from '../../static/correctives.js';

const file = process.argv[2] || '.runtime/character-workshop/Moneypenny-Performance-Candidate-v6.glb';
const bytes = fs.readFileSync(file);
assert.equal(bytes.readUInt32LE(0), 0x46546c67);
assert.equal(bytes.readUInt32LE(4), 2);
assert.equal(bytes.readUInt32LE(8), bytes.length);
assert.ok(bytes.length < 80 * 1024 * 1024);
const length = bytes.readUInt32LE(12);
const gltfJSON = JSON.parse(bytes.subarray(20, 20 + length).toString());
assert.ok(gltfJSON.skins?.length);
assert.ok((gltfJSON.buffers || []).every(buffer => !buffer.uri));
assert.ok((gltfJSON.images || []).every(image => image.bufferView !== undefined && !image.uri));
const embeddedImages = gltfJSON.images?.length || 0;
const pbrNormals = (gltfJSON.materials || []).filter(material => material.normalTexture).length;
assert.ok(pbrNormals > 0, 'Baked normal texture is absent');
// Keep all geometry, skin buffers, morphs, metadata and the original binary
// buffer. Remove material/image definitions only to avoid pretending that Node
// decoded browser textures. Native Blender renders separately verify the look.
const geometryJSON = structuredClone(gltfJSON);
delete geometryJSON.materials; delete geometryJSON.textures; delete geometryJSON.images;
for (const mesh of geometryJSON.meshes || []) for (const primitive of mesh.primitives) delete primitive.material;
const encoded = Buffer.from(JSON.stringify(geometryJSON));
const padding = (4 - encoded.length % 4) % 4;
const binary = bytes.subarray(20 + length);
const header = Buffer.alloc(20);
header.writeUInt32LE(0x46546c67, 0); header.writeUInt32LE(2, 4);
header.writeUInt32LE(20 + encoded.length + padding + binary.length, 8);
header.writeUInt32LE(encoded.length + padding, 12); header.writeUInt32LE(0x4e4f534a, 16);
const geometryGLB = Buffer.concat([header, encoded, Buffer.alloc(padding, 32), binary]);
const parsed = await new GLTFLoader().parseAsync(geometryGLB.buffer.slice(geometryGLB.byteOffset, geometryGLB.byteOffset + geometryGLB.byteLength), '');
const root = parsed.scene;
const bones = new Map(), meshes = [];
root.traverse(node => { if (node.isBone) bones.set(node.name, node); if (node.isSkinnedMesh) meshes.push(node); });
for (const name of ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'LeftEye', 'RightEye']) assert.ok(bones.has(name), name);
for (const side of ['Left', 'Right']) {
  for (const name of ['Shoulder', 'Arm', 'ForeArm', 'Hand', 'UpLeg', 'Leg', 'Foot', 'ToeBase']) assert.ok(bones.has(side + name), side + name);
  for (const finger of ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']) for (const n of [1, 2, 3]) assert.ok(bones.has(side + 'Hand' + finger + n));
}
const body = meshes.find(mesh => mesh.morphTargetDictionary?.viseme_aa !== undefined && mesh.morphTargetDictionary?.corrective_elbow_L !== undefined);
assert.ok(body, 'No speaking body with corrective morphs');
const visemes = ['aa', 'CH', 'DD', 'E', 'FF', 'I', 'kk', 'nn', 'O', 'PP', 'RR', 'sil', 'SS', 'TH', 'U'];
for (const name of visemes.map(name => 'viseme_' + name).concat(['eyeBlinkLeft', 'eyeBlinkRight', 'mouthSmileLeft', 'mouthSmileRight'])) assert.ok(body.morphTargetDictionary[name] !== undefined, name);
root.updateMatrixWorld(true); for (const mesh of meshes) mesh.skeleton.update();
const a = new THREE.Vector3(), b = new THREE.Vector3();
const movement = {};
for (const name of ['viseme_aa', 'viseme_PP', 'eyeBlinkLeft']) {
  const index = body.morphTargetDictionary[name]; let maximum = 0;
  const positions = body.geometry.getAttribute('position');
  for (let i = 0; i < positions.count; i++) {
    body.morphTargetInfluences[index] = 0; body.getVertexPosition(i, a);
    body.morphTargetInfluences[index] = .65; body.getVertexPosition(i, b);
    assert.ok([...a.toArray(), ...b.toArray()].every(Number.isFinite)); maximum = Math.max(maximum, a.distanceTo(b));
  }
  body.morphTargetInfluences[index] = 0; assert.ok(maximum > 1e-5, name); movement[name] = maximum;
}
const correctives = new PoseCorrectives(root);
assert.equal(correctives.bindings.length, 4);
correctives.update(1);
assert.ok(correctives.bindings.every(binding => Number.isFinite(binding.value) && binding.value >= 0 && binding.value <= 1));
const garmentNames = meshes.filter(mesh => mesh.userData.wardrobeSlot).map(mesh => mesh.name);
assert.ok(garmentNames.length >= 2);
const report = { file, bytes: bytes.length, bones: bones.size, skinned_meshes: meshes.length,
  speech_visemes: visemes.length, actual_deformation_m: movement, corrective_bindings: correctives.bindings.length,
  embedded_images: embeddedImages, materials_with_normals: pbrNormals, garments: garmentNames,
  geometry_and_rig_verified: true, texture_decode_verified_by_this_check: false,
  actual_browser_acceptance: false };
fs.writeFileSync('.runtime/character-workshop/performance-glb-verification.json', JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
