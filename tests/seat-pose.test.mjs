import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {rig} from './rig-fixture.mjs';
import {RigController} from '../static/rig.js';
import {MotionDirector,movementFromText} from '../static/motion.js';
import {SeatSupport} from '../static/seat-support.js';
const point=bone=>bone.getWorldPosition(new THREE.Vector3());

test('either foot reaches the support while the standing foot stays planted',()=>{
  for(const side of ['left','right']){
    const r=new RigController(rig()),step=r.supportedStep(side);
    const chains=['Left','Right'].map(s=>[r.bones[s+'UpLeg'],r.bones[s+'Leg'],r.bones[s+'Foot']]);
    const lengths=chains.map(([a,b,c])=>[point(a).distanceTo(point(b)),point(b).distanceTo(point(c))]);
    r.poseSkill('supported_step',1,side);r.root.updateMatrixWorld(true);
    assert.ok(point(r.bones[step.raised]).distanceTo(r.world(step.target))<.002);
    assert.ok(point(r.bones[step.standing]).distanceTo(r.world(r.neutral[step.standing]))<.002);
    chains.forEach(([a,b,c],i)=>{
      assert.ok(Math.abs(point(a).distanceTo(point(b))-lengths[i][0])<1e-5);
      assert.ok(Math.abs(point(b).distanceTo(point(c))-lengths[i][1])<1e-5);
    });
    assert.ok(Math.abs(point(r.bones.Hips).x-r.world(r.neutral[step.standing]).x)<.06);
  }
});

test('support appears only for the step and Stop lowers the foot back to rest',()=>{
  const head=rig(),r=new RigController(head),motion=new MotionDirector(head,()=>{},r);
  const scene=new THREE.Scene(),seat=new SeatSupport(scene,r);motion.autonomous=false;
  motion.plan({steps:[{skill:'supported_step',side:'left',duration:8,intensity:1}]});
  for(let i=0;i<100;i++){r.resetBody();motion.update(20);r.update(.02);seat.update(motion);}
  assert.equal(seat.group.visible,true);
  assert.ok(point(r.bones.LeftFoot).y>r.world(r.neutral.LeftFoot).y+.3);
  assert.ok(Math.abs(point(r.bones.RightFoot).y-r.world(r.neutral.RightFoot).y)<.002);
  motion.stop();
  for(let i=0;i<150;i++){r.resetBody(!!motion.active);motion.update(20);r.update(.02);seat.update(motion);}
  assert.equal(motion.active,null);assert.equal(seat.group.visible,false);
  for(const name of ['LeftFoot','RightFoot'])assert.ok(point(r.bones[name]).distanceTo(r.world(r.neutral[name]))<.002);
  seat.dispose();assert.equal(scene.children.length,0);
});

test('seat requests preserve side and negation; no intimate action is inferred',()=>{
  for(const text of ['One leg on the toilet seat','Put your left foot on the seat']){
    const plan=movementFromText(text);assert.equal(plan.steps.length,1);assert.equal(plan.steps[0].skill,'supported_step');
  }
  assert.equal(movementFromText('Put your left foot on the seat').steps[0].side,'left');
  assert.equal(movementFromText("Don't put your foot on the seat"),null);
  assert.equal(movementFromText('Insert a tampon'),null);
});
