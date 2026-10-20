import test from 'node:test';
import assert from 'node:assert/strict';
import {installWarmExpression,setPersonaMood} from '../static/persona-expression.js';
test('warm expression keeps authored blink and speech ownership without changing neutral',()=>{
 const gaze=()=>.6;
 const neutral={baseline:{eyesLookDown:.1},speech:{deltaPitch:0},anims:[{name:'head'},{name:'mouth'},{name:'blink',vs:{eyeBlinkLeft:[1,0]}},{name:'eyes',idle:{alt:[{p:gaze}]}}]};
 const head={studioNeutral:{},animMoods:{neutral},setMood(value){this.selected=value;}};
 const original=JSON.stringify(neutral);assert.equal(installWarmExpression(head),true);
 assert.equal(JSON.stringify(neutral),original);assert.equal(head.animMoods.warm.baseline.mouthSmile,.28);
 assert.deepEqual(head.animMoods.warm.anims.find(a=>a.name==='blink'),neutral.anims[2]);
 assert.equal(head.animMoods.warm.anims.find(a=>a.name==='eyes').idle.alt[0].p,gaze);
 assert.equal(head.animMoods.warm.anims.find(a=>a.name==='mouth').idle.vs.viseme_PP,undefined);
 assert.equal(head.animMoods.warm.baseline.jawOpen,undefined);
 assert.equal(head.animMoods.warm.baseline.viseme_PP,undefined);
 setPersonaMood(head,'neutral');assert.equal(head.selected,'warm');
 setPersonaMood(head,'serious');assert.equal(head.selected,'serious');
});
test('imported characters keep their selected expression',()=>{
 const head={animMoods:{neutral:{}},setMood(value){this.selected=value;}};
 assert.equal(installWarmExpression(head),false);setPersonaMood(head,'neutral');assert.equal(head.selected,'neutral');
});
