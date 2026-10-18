import fs from 'node:fs';
import * as THREE from 'three';
export function rig(){
 const data=fs.readFileSync('static/avatars/mpfb.glb');const length=data.readUInt32LE(12);const gltf=JSON.parse(data.subarray(20,20+length).toString());
 const joints=new Set(gltf.skins.flatMap(s=>s.joints));
 const nodes=gltf.nodes.map((node,i)=>{const item=joints.has(i)?new THREE.Bone():new THREE.Object3D();item.name=node.name||'';if(node.translation)item.position.fromArray(node.translation);if(node.rotation)item.quaternion.fromArray(node.rotation);if(node.scale)item.scale.fromArray(node.scale);if(node.matrix)new THREE.Matrix4().fromArray(node.matrix).decompose(item.position,item.quaternion,item.scale);return item;});
 gltf.nodes.forEach((n,i)=>(n.children||[]).forEach(child=>nodes[i].add(nodes[child])));
 const scene=new THREE.Object3D();gltf.scenes[gltf.scene||0].nodes.forEach(i=>scene.add(nodes[i]));scene.updateMatrixWorld(true);
 const armature=scene.getObjectByName('Armature');return {armature,avatarHeight:1.78};
}
