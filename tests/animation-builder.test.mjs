import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {AnimationDraft,AnimationBuilder,validateAnimationSequence,saveAnimationSequence} from '../static/animation-builder.js';
import {MotionLibrary} from '../static/motion-library.js';
import {MotionDirector} from '../static/motion.js';
import {RigController,authoredNeutral} from '../static/rig.js';
import {rig} from './rig-fixture.mjs';

function harness(){
 const head=rig();head.studioNeutral=authoredNeutral(head.armature);
 const controller=new RigController(head),states=[],director=new MotionDirector(head,value=>states.push(value),controller);
 director.autonomous=false;
 const library=new MotionLibrary(head,controller,value=>states.push(value));
 library.onSequence=(plan,source)=>director.plan(plan,source)?director:null;
 const update=seconds=>{for(let t=0;t<seconds;t+=.02){controller.resetBody(true);library.update(.02);controller.update(.02);}};
 return {head,controller,director,library,states,update};
}
const sample=()=>({version:1,kind:'sequence',name:'Greeting',steps:[{skill:'wave',duration:2,side:'left'},{skill:'bow',duration:2}]});

test('a draft can add, reorder, edit and reopen its actual saved step order',()=>{
 const draft=new AnimationDraft();draft.add('wave',4).add('bow',3).add('idle',2);
 assert.equal(draft.move(1,-1),true);draft.update(1,{duration:5,side:'left'});draft.remove(2);
 const reopened=new AnimationDraft().replace(JSON.parse(JSON.stringify(draft.data())));
 assert.deepEqual(reopened.steps.map(step=>step.skill),['bow','wave']);
 assert.equal(reopened.steps[1].side,'left');assert.equal(reopened.duration,8);
 reopened.update(0,{duration:1});assert.equal(draft.steps[0].duration,3,'reopening must not share the editor array');
});
test('sequence files are bounded movement data and reject unsupported instructions',()=>{
 const normalized=validateAnimationSequence({...sample(),steps:[{skill:'wave',duration:100,intensity:-2,execute:'ignored'}]});
 assert.deepEqual(normalized.steps,[{skill:'wave',duration:20,intensity:.1,side:'right'}]);
 for(const steps of [[],Array(9).fill({skill:'wave'}),[{skill:'execute_python'}],[{skill:'custom',frames:[]}],[{skill:'wave',duration:true}],[{skill:'wave',intensity:NaN}]]){
  assert.throws(()=>validateAnimationSequence({...sample(),steps}));
 }
});
test('saving sends the exact reopenable sequence to the existing motion asset API',async()=>{
 let stored;
 const record=await saveAnimationSequence(sample(),async(url,options)=>{
  assert.equal(url,'/api/motion/library');assert.equal(options.method,'POST');
  assert.equal(options.headers['X-Studio-Client'],'moneypenny');
  assert.equal(options.body.get('name'),'Greeting');const file=options.body.get('file');
  assert.equal(file.name,'greeting.sequence.json');stored=JSON.parse(await file.text());
  return {ok:true,json:async()=>({id:'saved',format:'sequence'})};
 });
 assert.equal(record.id,'saved');assert.deepEqual(new AnimationDraft().replace(stored).data(),validateAnimationSequence(sample()));
});
test('a freshly reopened library sequence decodes as movement data rather than a baked clip',async()=>{
 const h=harness(),original=globalThis.fetch;
 try{
  globalThis.fetch=async url=>{assert.equal(url,'/api/motion/assets/saved');return {ok:true,json:async()=>sample()};};
  h.library.items=[{id:'saved',format:'sequence',url:'/api/motion/assets/saved'}];
  const entries=await h.library.load('saved');
  assert.equal(entries[0].clip.name,'Greeting');assert.equal(entries[0].clip.duration,4);
  assert.deepEqual(entries[0].sequence,validateAnimationSequence(sample()));
  await h.library.play('saved');h.update(.8);assert.equal(h.director.active.skill,'wave');
 }finally{globalThis.fetch=original;}
});
test('sequence replay advances the existing repaired wave and bow on the real body rig',async()=>{
 const h=harness(),data=validateAnimationSequence(sample());
 h.library.items=[{id:'saved',format:'sequence'}];h.library.cache.set('saved',[{sequence:data,clip:{name:data.name,duration:4},mapping:{}}]);
 const start=h.controller.bones.LeftHand.getWorldPosition(new THREE.Vector3());
 await h.library.play('saved');assert.equal(h.library.canPause,false);
 h.update(.8);const raised=h.controller.bones.LeftHand.getWorldPosition(new THREE.Vector3());
 assert.ok(raised.y-start.y>.1,'saved wave did not raise the actual hand');
 assert.equal(h.director.active.skill,'wave');assert.equal(h.director.active.side,'left');
 assert.equal(h.director.plan({steps:[{skill:'stretch',duration:4}]},'conversation'),false,'late conversation replaced authored animation');
 h.update(2);assert.equal(h.director.active.skill,'bow');
 assert.ok(h.controller.bones.Spine.quaternion.angleTo(h.controller.rest.Spine.q)>.1,'second step did not bend the actual spine');
 h.update(2);assert.equal(h.library.playing,false);assert.equal(h.library.canPause,true);
 assert.ok(h.states.some(state=>state==='Animation complete'));
});
test('Stop clears remaining sequence steps and a late asset load cannot restart it',async()=>{
 const h=harness();h.library.playSequence(sample(),'animation-builder');h.update(.6);h.library.stop();
 assert.equal(h.director.queue.length,0);assert.notEqual(h.director.active.release,undefined);
 // The normal Studio loop resumes the director's smooth release after Stop.
 for(let i=0;i<40;i++){h.controller.resetBody(true);h.director.update(20);h.controller.update(.02);}
 assert.equal(h.director.active,null);assert.equal(h.library.playing,false);
 let release;h.library.load=()=>new Promise(resolve=>{release=resolve;});
 const pending=h.library.play('late');h.library.stop();release([{sequence:sample()}]);
 assert.equal(await pending,null);assert.equal(h.director.queue.length,0);
});
test('stopping while Preview waits for voice shutdown prevents that preview from starting',async()=>{
 let release,played=0;
 const view={epoch:0,draft:new AnimationDraft().replace(sample()),$:()=>({value:'Greeting'}),say(){},api:{
  stopConversation:()=>new Promise(resolve=>{release=resolve;}),getLibrary:()=>({stop(){},playSequence(){played++;}}),getRig:()=>({clear(){}}),frame(){}
 }};
 const pending=AnimationBuilder.prototype.preview.call(view);AnimationBuilder.prototype.stop.call(view);release();
 assert.equal(await pending,false);assert.equal(played,0);
});
