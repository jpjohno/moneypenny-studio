import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {rig} from './rig-fixture.mjs';
import {RigController} from '../static/rig.js';
import {MotionDirector,movementFromText} from '../static/motion.js';
import {actionOnly,movementAcknowledgement,wardrobeCommand} from '../static/action-commands.js';
const point=b=>b.getWorldPosition(new THREE.Vector3());

test('bend over reaches the real rig with feet planted and a forward torso',()=>{
  const head=rig(),r=new RigController(head),director=new MotionDirector(head,()=>{},r);director.autonomous=false;
  const plan=movementFromText('Bend over');assert.equal(plan.steps[0].skill,'bend_forward');assert.equal(actionOnly('Can you bend over?'),true);
  assert.match(movementAcknowledgement(plan),/bend forward/);
  director.plan(plan);
  for(let i=0;i<120;i++){r.resetBody();director.update(20);r.update(.02);}
  for(const name of ['LeftFoot','RightFoot'])assert.ok(point(r.bones[name]).distanceTo(r.world(r.neutral[name]))<.003,name);
  const torso=point(r.bones.Head).sub(point(r.bones.Hips));assert.ok(torso.z>.35,`torso forward=${torso.z}`);
  head.armature.traverse(b=>assert.ok([...b.quaternion.toArray(),...b.position.toArray()].every(Number.isFinite)));
  director.stop();
  for(let i=0;i<150;i++){r.resetBody(!!director.active);director.update(20);r.update(.02);}
  for(const name of ['LeftFoot','RightFoot'])assert.ok(point(r.bones[name]).distanceTo(r.world(r.neutral[name]))<.003);
  assert.ok(point(r.bones.Head).sub(point(r.bones.Hips)).z<.15);
});

test('late conversation gestures and persona plans cannot replace a direct instruction',()=>{
  const director=new MotionDirector(rig());director.plan(movementFromText('Bend over'));
  assert.equal(director.plan({steps:[{skill:'dance'}]},'conversation'),false);
  director.update(20);assert.equal(director.active.skill,'bend_forward');
  assert.equal(director.plan({steps:[{skill:'turn'}]},'persona'),false);
  assert.equal(director.plan({steps:[{skill:'bow'}]},'instruction'),true);
  assert.equal(director.queue[0].skill,'bow');
});

test('turn around keeps the new direction through a subsequent bend and upright recovery',()=>{
  const head=rig(),r=new RigController(head),director=new MotionDirector(head,()=>{},r);director.autonomous=false;
  const plan=movementFromText('Turn around and bend over');assert.deepEqual(plan.steps.map(step=>step.skill),['turn','bend_forward']);director.plan(plan);
  for(let i=0;i<480;i++){r.resetBody(!!director.active||!!director.queue.length);director.update(20);r.update(.02);}
  assert.equal(director.active.skill,'bend_forward');
  assert.ok(Math.abs(director.heading-Math.PI)<.01);
  assert.ok(point(r.bones.Head).sub(point(r.bones.Hips)).z<-.35);
  for(const name of ['LeftFoot','RightFoot']){
    const expected=r.neutral[name].clone().applyAxisAngle(new THREE.Vector3(0,1,0),Math.PI);
    assert.ok(point(r.bones[name]).distanceTo(r.world(expected))<.004);
  }
  for(let i=0;i<400;i++){r.resetBody(!!director.active||!!director.queue.length);director.update(20);r.update(.02);}
  assert.equal(director.active,null);assert.ok(Math.abs(director.currentHeading-Math.PI)<.01);
  assert.ok(Math.abs(point(r.bones.Head).sub(point(r.bones.Hips)).z)<.15);
});

test('clothing commands select only actual presets and preserve mixed questions',()=>{
  assert.deepEqual(wardrobeCommand('Put on trainers'),{footwear:'trainers'});
  assert.deepEqual(wardrobeCommand('Change into the evening dress'),{outfit:'dress'});
  assert.deepEqual(wardrobeCommand('Remove your outer layers'),{outfit:'base'});
  assert.equal(wardrobeCommand('Put on some music'),null);
  assert.equal(wardrobeCommand("Don't wear the dress"),null);
  assert.equal(actionOnly('Bend over and explain how balance works'),false);
  assert.equal(movementFromText("Don't bend over"),null);
});
