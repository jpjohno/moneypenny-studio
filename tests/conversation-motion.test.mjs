import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {rig as sampleRig} from './rig-fixture.mjs';
import {authoredNeutral,RigController} from '../static/rig.js';
import {MotionDirector,queueConversationGesture} from '../static/motion.js';

function authored(){
  const head=sampleRig();head.studioNeutral=authoredNeutral(head.armature);
  const rig=new RigController(head),director=new MotionDirector(head,()=>{},rig);
  director.autonomous=false;
  return {head,rig,director};
}
const position=bone=>bone.getWorldPosition(new THREE.Vector3());

test('a speaking presentation survives the actual authored reset and director frame order',()=>{
  const {head,rig,director}=authored(),start=position(rig.bones.LeftHand);
  const feet=['LeftFoot','RightFoot'].map(name=>position(rig.bones[name]));
  assert.equal(queueConversationGesture(director,{gesture:'side'},.7),true);
  for(let frame=0;frame<30;frame++){
    // TalkingHead's earlier body pass cannot own this authored arm. The later
    // local director must restore its intended presentation after resetBody.
    rig.bones.LeftArm.quaternion.setFromEuler(new THREE.Euler(.8,0,.5));
    rig.resetBody(!!director.active||!!director.queue.length);
    rig.breathe(.04,true);director.engaged=true;director.update(40);rig.update(.04);
  }
  assert.ok(position(rig.bones.LeftHand).distanceTo(start)>.01,'speaking arm stayed frozen');
  ['LeftFoot','RightFoot'].forEach((name,i)=>assert.ok(position(rig.bones[name]).distanceTo(feet[i])<1e-6,'presentation moved a planted foot'));
  assert.ok(head.armature.position.distanceTo(director.origin)<1e-6);
});

test('conversation preserves an explicit wave, both active and queued',()=>{
  for(const active of [false,true]){
    const {director}=authored();director.plan({steps:[{skill:'wave',duration:4}]},'instruction');
    if(active)director.update(40);
    const before=director.active||director.queue[0];
    assert.equal(queueConversationGesture(director,{gesture:'side'},.8),false);
    assert.equal(director.active||director.queue[0],before);
    assert.equal(before.skill,'wave');
  }
});

test('new speech phrases keep the existing gesture and later presentations alternate sides',()=>{
  const {director}=authored();
  queueConversationGesture(director,{gesture:'ok'},1);director.update(40);
  const first=director.active;
  assert.equal(first.skill,'present');assert.ok(first.intensity<=.34);
  assert.equal(queueConversationGesture(director,{gesture:'side'},1),true);
  assert.equal(director.active,first);assert.equal(director.queue.length,0);
  for(let i=0;i<85;i++)director.update(40);
  assert.equal(director.active,null);
  assert.equal(queueConversationGesture(director,{},.7),true);
  assert.notEqual(director.queue[0].side,first.side);
});

test('imported avatars retain their caller fallback and low movement remains quiet',()=>{
  const imported=new MotionDirector(sampleRig());
  assert.equal(queueConversationGesture(imported,{gesture:'side'},1),false);
  assert.equal(imported.queue.length,0);
  const {director}=authored();
  for(const amount of [0,.2,NaN,Infinity])assert.equal(queueConversationGesture(director,{gesture:'side'},amount),false);
  assert.equal(queueConversationGesture(director,{},.4),false);
  assert.equal(director.queue.length,0);
});
