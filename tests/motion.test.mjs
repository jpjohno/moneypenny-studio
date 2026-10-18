import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from 'three';
import { MotionDirector, MOTION_SKILLS, movementFromText } from '../static/motion.js';
function rig(){
 const data=fs.readFileSync('static/avatars/mpfb.glb');const length=data.readUInt32LE(12);const gltf=JSON.parse(data.subarray(20,20+length).toString());
 const joints=new Set(gltf.skins.flatMap(s=>s.joints));
 const nodes=gltf.nodes.map((node,i)=>{const item=joints.has(i)?new THREE.Bone():new THREE.Object3D();item.name=node.name||'';if(node.translation)item.position.fromArray(node.translation);if(node.rotation)item.quaternion.fromArray(node.rotation);if(node.scale)item.scale.fromArray(node.scale);if(node.matrix)new THREE.Matrix4().fromArray(node.matrix).decompose(item.position,item.quaternion,item.scale);return item;});
 gltf.nodes.forEach((n,i)=>(n.children||[]).forEach(child=>nodes[i].add(nodes[child])));
 const scene=new THREE.Object3D();gltf.scenes[gltf.scene||0].nodes.forEach(i=>scene.add(nodes[i]));scene.updateMatrixWorld(true);
 const armature=scene.getObjectByName('Armature');return {armature,avatarHeight:1.78};
}
test('reach solver brings the actual sample palm to the opposite shoulder',()=>{
 const head=rig(),director=new MotionDirector(head);director.autonomous=false;
 director.reach('shoulder','right',1);
 assert.ok(director.reachError<.035,`error ${director.reachError}`);
});
test('all body skills preserve finite bone transforms and return the stage root',()=>{
 for(const skill of MOTION_SKILLS.filter(x=>x!=='custom')){
  const head=rig(),director=new MotionDirector(head);director.autonomous=false;
  director.plan({steps:[{skill,target:'belly',side:'right',duration:2,intensity:.7}]});
  for(let i=0;i<100;i++)director.update(40);
  head.armature.traverse(bone=>{assert.ok([...bone.quaternion.toArray(),...bone.position.toArray()].every(Number.isFinite),skill+' '+bone.name);});
  assert.ok(head.armature.position.distanceTo(director.origin)<.001,skill);
 }
});
test('autonomous movement occurs without a chat command and can be disabled',()=>{
 const director=new MotionDirector(rig());director.nextDecision=0;director.update(40);assert.ok(director.queue.length);
 director.stop();director.active=null;director.autonomous=false;director.nextDecision=0;director.update(40);assert.equal(director.queue.length,0);
 director.autonomous=true;director.engaged=true;director.nextDecision=0;director.update(40);assert.equal(director.queue.length,0);
 director.plan({steps:[{skill:'turn',duration:4}]},'persona');director.update(40);director.update(40);assert.notEqual(director.active.release,undefined);
});
test('free text can request a composed whole-body sequence',()=>{
 const plan=movementFromText('Dance a jig then touch your shoulder and bow');
 assert.ok(plan.steps.some(x=>x.skill==='reach'));assert.ok(plan.steps.some(x=>x.skill==='jig'));assert.ok(plan.steps.some(x=>x.skill==='bow'));
 assert.deepEqual(plan.steps.map(x=>x.skill),['jig','reach','bow']);
});
