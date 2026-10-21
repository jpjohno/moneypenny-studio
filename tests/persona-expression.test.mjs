import test from 'node:test';
import assert from 'node:assert/strict';
import {installWarmExpression,setPersonaMood} from '../static/persona-expression.js';
import {TalkingHead} from '../static/vendor/talkinghead/talkinghead.mjs';

function speechHead(){
 const head=Object.create(TalkingHead.prototype);
 const names=['mouthSmile','viseme_PP','viseme_aa','jawOpen','eyeBlinkLeft','eyeBlinkRight',
  'mouthRollUpper','mouthRollLower','mouthDimpleLeft','mouthPressLeft','browOuterUpLeft','cheekSquintLeft'];
 head.applied=new Float32Array(names.length);
 head.mtAvatar=Object.fromEntries(names.map((name,index)=>[name,{
  value:0,applied:0,baseline:0,base:null,fixed:null,realtime:null,system:null,systemd:null,newvalue:null,
  ref:null,v:0,maxv:5,acc:.01,limit:null,onchange:null,min:0,max:1,needsUpdate:false,ms:[head.applied],is:[index]
 }]));
 Object.assign(head,{studioNeutral:{},avatar:{},animClock:0,stateName:'idle',isSpeaking:false,
  mtBaselineDefault:0,mtBaselineExceptions:{},animQueue:[],audioPlaylist:[],speechQueue:[],
  mtRandomized:['mouthRollUpper','mouthRollLower','mouthDimpleLeft','mouthPressLeft','browOuterUpLeft','cheekSquintLeft'],
  animMoods:{neutral:{baseline:{},anims:[{name:'mouth',dt:[1000],vs:{mouthSmile:[.3]}}]}}});
 installWarmExpression(head);setPersonaMood(head,'neutral');
 return head;
}
function advance(head,ms){
 for(let elapsed=0;elapsed<ms;elapsed+=20)head.updateMorphTargets(Math.min(20,ms-elapsed));
}

test('warm expression keeps authored blink and speech ownership without changing neutral',()=>{
 const gaze=()=>.6;
 const neutral={baseline:{eyesLookDown:.1},speech:{deltaPitch:0},anims:[{name:'head'},{name:'mouth'},{name:'blink',vs:{eyeBlinkLeft:[1,0]}},{name:'eyes',idle:{alt:[{p:gaze}]}}]};
 const head={studioNeutral:{},animMoods:{neutral},setMood(value){this.selected=value;}};
 const original=JSON.stringify(neutral);assert.equal(installWarmExpression(head),true);
 assert.equal(JSON.stringify(neutral),original);assert.equal(head.animMoods.warm.baseline.mouthSmile,0);
 assert.deepEqual(head.animMoods.warm.anims.find(a=>a.name==='blink'),neutral.anims[2]);
 assert.equal(head.animMoods.warm.anims.find(a=>a.name==='eyes').idle.alt[0].p,gaze);
 assert.deepEqual(head.animMoods.warm.anims.find(a=>a.name==='mouth').vs,{});
 assert.equal(head.animMoods.warm.baseline.jawOpen,undefined);
 assert.equal(head.animMoods.warm.baseline.viseme_PP,undefined);
 setPersonaMood(head,'neutral');assert.equal(head.selected,'warm');
 setPersonaMood(head,'serious');assert.equal(head.selected,'serious');
});
test('actual TalkingHead morph application releases the resting smile during WAV speech',()=>{
 const head=speechHead();
 advance(head,4000);
 assert.ok(head.applied[0]>.23&&head.applied[0]<.3,'resting smile is restrained, rather than baseline plus animation');
 head.isSpeaking=true;
 // This is the Studio WAV lifecycle: stateName may still be idle. Audio-driven
 // phonemes, jaw and blink must reach the mesh without expression interference.
 head.mtAvatar.viseme_PP.realtime=.85;head.mtAvatar.viseme_PP.needsUpdate=true;
 head.mtAvatar.jawOpen.realtime=.07;head.mtAvatar.jawOpen.needsUpdate=true;
 head.mtAvatar.eyeBlinkLeft.realtime=1;head.mtAvatar.eyeBlinkLeft.needsUpdate=true;
 head.updateMorphTargets(20);
 assert.ok(head.applied[0]<.2,'smile starts releasing on the first speaking frame');
 advance(head,100);
 assert.ok(head.applied[0]<.01,'closed consonants no longer carry a held smile');
 assert.equal(head.stateName,'idle','does not mutate the speech engine state');
 assert.ok(Math.abs(head.applied[1]-.85)<1e-6);
 assert.ok(Math.abs(head.applied[3]-.07)<1e-6);
 assert.equal(head.applied[4],1);
 advance(head,200);assert.equal(head.applied[0],0);
});
test('short streamed phrase gaps stay neutral; Stop restores the resting expression gently',()=>{
 const head=speechHead();advance(head,4000);
 head.isSpeaking=true;advance(head,400);
 head.isSpeaking=false;advance(head,200);
 assert.equal(head.applied[0],0,'smile does not pulse between adjacent audio chunks');
 head.isSpeaking=true;advance(head,200);head.stopSpeaking();
 advance(head,200);assert.equal(head.applied[0],0,'audio and mouth can drain after Stop');
 advance(head,1000);assert.ok(head.applied[0]>.15&&head.applied[0]<.25);
 advance(head,3000);assert.ok(head.applied[0]>.24&&head.applied[0]<=.25);
});
test('expression installation is idempotent and leaves other moods and user controls alone',()=>{
 const head=speechHead(),update=head.updateMorphTargets;
 installWarmExpression(head);assert.equal(head.updateMorphTargets,update);
 setPersonaMood(head,'neutral');head.mtAvatar.mouthSmile.realtime=.65;
 head.mtAvatar.mouthSmile.needsUpdate=true;advance(head,1000);
 assert.ok(Math.abs(head.applied[0]-.65)<1e-6);
 head.mtAvatar.mouthSmile.realtime=null;
 head.mood=head.animMoods.neutral;head.mtAvatar.mouthSmile.newvalue=.4;
 head.mtAvatar.mouthSmile.needsUpdate=true;head.updateMorphTargets(20);
 assert.ok(Math.abs(head.applied[0]-.4)<1e-6);
 head.mood=head.animMoods.warm;head.studioNeutral=null;
 head.mtAvatar.mouthSmile.newvalue=.5;head.mtAvatar.mouthSmile.needsUpdate=true;
 head.updateMorphTargets(20);assert.equal(head.applied[0],.5,'a subsequently imported character is unaffected');
});
test('imported characters keep their selected expression',()=>{
 const head={animMoods:{neutral:{}},setMood(value){this.selected=value;}};
 assert.equal(installWarmExpression(head),false);setPersonaMood(head,'neutral');assert.equal(head.selected,'neutral');
});

test('held vendor lip randomization releases during PCM speech without altering PP or blink',()=>{
 const head=speechHead(),original=head.mtRandomized,roll=head.mtAvatar.mouthRollUpper;
 // Reproduce the actual vendor randomizer's held base using the real morph
 // updater: it can settle at a random value with needsUpdate then false.
 roll.base=.4;roll.needsUpdate=true;advance(head,1000);
 assert.equal(roll.value,.4);assert.equal(roll.needsUpdate,false);
 head.isSpeaking=true;head.mtAvatar.viseme_PP.realtime=.75;head.mtAvatar.viseme_PP.needsUpdate=true;
 head.mtAvatar.eyeBlinkLeft.realtime=1;head.mtAvatar.eyeBlinkLeft.needsUpdate=true;
 head.updateMorphTargets(20);
 assert.equal(head.mtRandomized.includes('mouthRollUpper'),false);
 assert.equal(head.mtRandomized.includes('browOuterUpLeft'),true);
 assert.equal(head.mtRandomized.includes('cheekSquintLeft'),true);
 advance(head,100);assert.ok(roll.applied<.014,'random roll still distorts the consonant after release');
 assert.equal(head.applied[1],.75);assert.equal(head.applied[4],1);
 head.isSpeaking=false;advance(head,200);
 assert.notEqual(head.mtRandomized,original,'short gaps must not reintroduce random lips');
 advance(head,200);assert.equal(head.mtRandomized,original,'restore the original idle picker after speech drains');
});

test('external speech preserves named expression tracks and fixed/realtime mouth controls',()=>{
 const head=speechHead();head.isSpeaking=true;
 const roll=head.mtAvatar.mouthRollUpper,lower=head.mtAvatar.mouthRollLower,press=head.mtAvatar.mouthPressLeft;
 roll.fixed=.4;roll.needsUpdate=true;lower.realtime=.3;lower.needsUpdate=true;
 press.newvalue=.2;press.needsUpdate=true;
 head.updateMorphTargets(20);
 assert.equal(roll.fixed,.4);assert.ok(roll.applied>.35,'fixed control was blocked');
 assert.ok(Math.abs(lower.applied-.3)<1e-6);
 assert.ok(Math.abs(press.applied-.2)<1e-6,'a queued purposeful expression lost ownership');
 const original=head.mtRandomized;head.studioNeutral=null;head.updateMorphTargets(20);
 assert.notEqual(head.mtRandomized,original,'importing a character restores the picker immediately');
 assert.equal(head.mtRandomized.includes('mouthRollUpper'),true);
});

test('timed output keeps random lips and resting smile released after the input source ends',()=>{
 const head=speechHead(),original=head.mtRandomized;
 head.isSpeaking=true;advance(head,200);
 head.isSpeaking=false;head.studioSpeechActive=true;advance(head,800);
 assert.equal(head.applied[0],0,'resting smile returned before delayed speech finished');
 assert.equal(head.mtRandomized.includes('mouthRollUpper'),false);
 head.studioSpeechActive=false;advance(head,200);assert.notEqual(head.mtRandomized,original);
 advance(head,200);assert.equal(head.mtRandomized,original);assert.ok(head.applied[0]<.1);
});


test('adjacent speech phrases keep the actual TalkingHead mood animation queue continuous',()=>{
 const head=speechHead();
 const queued=[...head.animQueue],mood=head.mood;
 assert.ok(queued.length>0);assert.equal(setPersonaMood(head,'neutral'),false);
 assert.equal(head.mood,mood);assert.deepEqual(head.animQueue,queued);
 for(let i=0;i<queued.length;i++)assert.equal(head.animQueue[i],queued[i],'existing timed tracks retain their identity and progress');
 // A replaced mood definition is a real change even if its name is retained.
 head.animMoods.warm={...head.animMoods.warm,baseline:{...head.animMoods.warm.baseline,cheekSquintLeft:.05}};
 assert.equal(setPersonaMood(head,'neutral'),true);assert.notEqual(head.mood,mood);
 assert.notEqual(head.animQueue[0],queued[0]);
});
