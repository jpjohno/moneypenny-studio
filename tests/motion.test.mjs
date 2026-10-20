import test from 'node:test';
import assert from 'node:assert/strict';
import { rig } from './rig-fixture.mjs';
import { MotionDirector, MOTION_SKILLS, movementFromText } from '../static/motion.js';
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

test('reset placement restores a completed turn and clears pending motion',()=>{
 const head=rig(),director=new MotionDirector(head);director.autonomous=false;
 director.plan({steps:[{skill:'turn',duration:2,intensity:1}]});
 for(let i=0;i<60;i++)director.update(40);
 assert.ok(Math.abs(director.heading)>1);
 director.resetPlacement();director.update(40);
 assert.equal(director.heading,0);assert.equal(director.currentHeading,0);
 assert.equal(director.active,null);assert.equal(director.queue.length,0);
 assert.ok(head.armature.quaternion.angleTo(director.rootRotation)<1e-6);
 assert.ok(head.armature.position.distanceTo(director.origin)<1e-6);
});

test('ordinary autonomy chooses restrained motion and avoids repeated large gestures',()=>{
 const director=new MotionDirector(rig()),random=Math.random;
 try{
  Math.random=()=>.99;director.activity=.45;director.persona='Composed assistant';
  director.autonomousChoice();assert.equal(director.queue[0].skill,'turn');assert.ok(director.queue[0].intensity<.25);
  director.autonomousChoice();assert.equal(director.queue[0].skill,'idle');
 }finally{Math.random=random;}
});
