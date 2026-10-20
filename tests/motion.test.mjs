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

test('ordinary presentations alternate hands and retain a restrained intensity',()=>{
 const director=new MotionDirector(rig()),random=Math.random;
 try{
  Math.random=()=>.3;director.activity=.45;director.persona='Composed assistant';
  director.autonomousChoice();const first=director.queue[0];
  assert.equal(first.skill,'present');assert.ok(first.intensity<.25);
  director.autonomousChoice();assert.equal(director.queue[0].skill,'idle');
  director.autonomousChoice();assert.equal(director.queue[0].skill,'present');assert.notEqual(director.queue[0].side,first.side);
 }finally{Math.random=random;}
});

test('presentation intensity changes actual hand travel rather than only metadata',async()=>{
 const {RigController,authoredNeutral}=await import('../static/rig.js');
 const distance=intensity=>{
  const head=rig();head.studioNeutral=authoredNeutral(head.armature);const r=new RigController(head),director=new MotionDirector(head,()=>{},r);director.autonomous=false;
  const start=r.bones.LeftHand.getWorldPosition(head.armature.position.clone());
  director.plan({steps:[{skill:'present',side:'left',duration:4,intensity}]},'persona');
  for(let i=0;i<30;i++){r.resetBody();director.update(40);r.update(.04);}
  return r.bones.LeftHand.getWorldPosition(start.clone()).distanceTo(start);
 };
 const small=distance(.2),large=distance(.8);
 assert.ok(small>.005,'small presentation never moved');assert.ok(small<large*.4,`intensity ignored: ${small} versus ${large}`);
});
