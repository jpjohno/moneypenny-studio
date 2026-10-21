import test from 'node:test';
import assert from 'node:assert/strict';
import {TalkingHead} from '../static/vendor/talkinghead/talkinghead.mjs';
import {OVR_VISEMES,parseSpeechTiming,attachSpeechTiming,speechTiming,TimedSpeechMouth} from '../static/speech-timing.js';

const encoder=new TextEncoder();
function chunk(tag,payload){
 const bytes=new Uint8Array(8+payload.length+(payload.length&1)),view=new DataView(bytes.buffer);
 bytes.set(encoder.encode(tag),0);view.setUint32(4,payload.length,true);bytes.set(payload,8);return bytes;
}
function wav(timing,{extra=[],duplicate=false,raw=null}={}){
 const chunks=[chunk('fmt ',new Uint8Array(16)),chunk('JUNK',new Uint8Array([1])),chunk('data',new Uint8Array(32)),...extra];
 if(timing!==null||raw!==null){const data=chunk('MPVS',encoder.encode(raw??JSON.stringify(timing)));chunks.push(data);if(duplicate)chunks.push(data);}
 const bytes=new Uint8Array(12+chunks.reduce((sum,value)=>sum+value.length,0)),view=new DataView(bytes.buffer);
 bytes.set(encoder.encode('RIFF'),0);view.setUint32(4,bytes.length-8,true);bytes.set(encoder.encode('WAVE'),8);
 let offset=12;for(const value of chunks){bytes.set(value,offset);offset+=value.length;}return bytes.buffer;
}
const timing=(name='viseme_aa',duration=1)=>({version:1,duration,cues:[[0,duration,name]]});
const decoded=(value=timing())=>attachSpeechTiming({duration:value.duration},parseSpeechTiming(wav(value)));
function head(){
 const applied=new Float32Array(OVR_VISEMES.length+1);
 const mtAvatar=Object.fromEntries([...OVR_VISEMES,'eyeBlinkLeft'].map((name,index)=>[name,{
  value:name==='eyeBlinkLeft'?1:0,applied:name==='eyeBlinkLeft'?1:0,baseline:0,base:null,fixed:null,realtime:null,system:null,systemd:null,newvalue:null,
  ref:null,v:0,maxv:5,acc:.01,limit:null,onchange:null,min:0,max:1,needsUpdate:false,ms:[applied],is:[index]
 }]));
 applied[OVR_VISEMES.length]=1;
 return {mtAvatar,applied,updateMorphTargets:TalkingHead.prototype.updateMorphTargets};
}
const value=(h,name)=>h.applied[OVR_VISEMES.indexOf(name)];
const near=(actual,expected)=>assert.ok(Math.abs(actual-expected)<1e-6,`${actual} differs from ${expected}`);

test('MPVS parsing walks padded WAV chunks and attaches checked metadata without changing PCM',()=>{
 const bytes=wav(timing()),copy=Buffer.from(bytes).toString('hex');
 const parsed=parseSpeechTiming(bytes);assert.deepEqual(parsed,timing());assert.equal(Object.isFrozen(parsed.cues[0]),true);
 const padded=new Uint8Array(bytes.byteLength+8);padded.set(new Uint8Array(bytes),4);
 assert.deepEqual(parseSpeechTiming(padded.subarray(4,4+bytes.byteLength)),timing());
 const audio={duration:1};assert.equal(attachSpeechTiming(audio,parsed),audio);assert.deepEqual(speechTiming(audio),timing());
 assert.equal(Buffer.from(bytes).toString('hex'),copy,'metadata parsing modified original audio bytes');
});
test('missing, corrupted, oversized and unsorted metadata safely selects the audio-analysis fallback',()=>{
 const invalid=[wav(null),wav(timing(),{raw:'{'}),wav(timing(),{duplicate:true}),wav(timing()).slice(0,-1),
  wav(timing(),{raw:' '.repeat(512*1024+1)}),
  wav({version:1,duration:1,cues:[[.5,.6,'viseme_PP'],[.1,.3,'viseme_aa']]}),
  wav({version:1,duration:1,cues:[[0,2,'viseme_aa']]}),
  wav({version:1,duration:0,cues:[]}),wav({version:1,duration:601,cues:[]}),
  wav({version:1,duration:1,cues:[[0,.5,'execute_code']]}),
  wav({version:1,duration:1,cues:Array(8193).fill([0,1,'viseme_aa'])}),
 ];
 for(const bytes of invalid)assert.equal(parseSpeechTiming(bytes),null);
 const audio=decoded();attachSpeechTiming(audio,{...timing(),duration:2});assert.equal(speechTiming(audio),null);
 const h=head(),context={currentTime:0},mouth=new TimedSpeechMouth(h,context);
 assert.equal(mouth.schedule(audio,0),false);assert.equal(mouth.update(),false);
 assert.equal(h.mtAvatar.viseme_aa.newvalue,null,'invalid metadata took ownership from HeadAudio');
});
test('timed PP/AA reach the actual morph updater on the delayed audio clock with bounded blending',()=>{
 const h=head(),context={currentTime:10},mouth=new TimedSpeechMouth(h,context);
 const audio=decoded({version:1,duration:.3,cues:[[0,.1,'viseme_PP'],[.1,.3,'viseme_aa']]});
 assert.equal(mouth.schedule(audio,10,.1),true);
 const update=now=>{context.currentTime=now;mouth.update();h.updateMorphTargets(16);};
 update(10.05);near(value(h,'viseme_PP'),0);
 update(10.12);near(value(h,'viseme_PP'),.75);near(value(h,'viseme_aa'),0);
 update(10.195);assert.ok(value(h,'viseme_PP')>0&&value(h,'viseme_aa')>0);
 assert.ok(h.applied.slice(0,OVR_VISEMES.length).reduce((sum,value)=>sum+value,0)<=.750001,'coarticulation added multiple full mouth shapes');
 update(10.25);near(value(h,'viseme_PP'),0);near(value(h,'viseme_aa'),.65);
 update(10.45);assert.equal(mouth.active,false);assert.ok(h.applied.slice(0,OVR_VISEMES.length).every(value=>value===0));
 assert.equal(h.applied.at(-1),1,'timed mouth altered blink');
});
test('adjacent PCM scheduling keeps the first delayed mouth performance until the next output arrives',()=>{
 const h=head(),context={currentTime:0},mouth=new TimedSpeechMouth(h,context);
 mouth.schedule(decoded(timing('viseme_PP')),0,.2);
 context.currentTime=1.004;mouth.schedule(decoded(timing('viseme_aa')),1.004,.2);
 context.currentTime=1.05;mouth.update();h.updateMorphTargets(16);
 near(value(h,'viseme_PP'),.75);near(value(h,'viseme_aa'),0);
 context.currentTime=1.25;mouth.update();h.updateMorphTargets(16);
 near(value(h,'viseme_PP'),0);near(value(h,'viseme_aa'),.65);
 assert.equal(mouth.active,true);
});
test('live output delay follows its actual ramp and can revisit earlier mouth cues without clock drift',()=>{
 const h=head(),context={currentTime:0},mouth=new TimedSpeechMouth(h,context);
 const audio=decoded({version:1,duration:.6,cues:[[0,.1,'viseme_PP'],[.1,.4,'viseme_aa'],[.4,.6,'viseme_FF']]});
 mouth.schedule(audio,0,.1);
 context.currentTime=.34;mouth.update();h.updateMorphTargets(16);
 near(value(h,'viseme_aa'),.65);assert.equal(mouth.queue[0].cursor,1);
 assert.equal(mouth.syncOutputDelay(.3),true);mouth.update();h.updateMorphTargets(16);
 near(value(h,'viseme_PP'),.75);near(value(h,'viseme_aa'),0);
 assert.equal(mouth.queue[0].cursor,0,'longer live delay skipped the earlier consonant');
 assert.equal(mouth.syncOutputDelay(.02),true);mouth.update();h.updateMorphTargets(16);
 near(value(h,'viseme_PP'),0);near(value(h,'viseme_aa'),.65);
 for(let i=0;i<100;i++){mouth.syncOutputDelay(.17);mouth.syncOutputDelay(.02);}
 near(mouth.queue[0].start,.02);near(mouth.queue[0].end,.62);
 const before=mouth.queue.map(({start,end,cursor})=>({start,end,cursor}));
 for(const invalid of [-.01,1.01,NaN,Infinity,'0.2',null])assert.equal(mouth.syncOutputDelay(invalid),false);
 assert.deepEqual(mouth.queue.map(({start,end,cursor})=>({start,end,cursor})),before);
 context.currentTime=.66;mouth.update();h.updateMorphTargets(16);
 assert.equal(mouth.active,false);assert.ok(h.applied.slice(0,OVR_VISEMES.length).every(value=>value===0));
});
test('live output delay aligns separately scheduled adjacent PCM against each original source time',()=>{
 const h=head(),context={currentTime:0},mouth=new TimedSpeechMouth(h,context);
 mouth.schedule(decoded(timing('viseme_PP')),0,.1);
 context.currentTime=.8;mouth.schedule(decoded(timing('viseme_aa')),.8,.25);
 mouth.syncOutputDelay(.3);
 assert.deepEqual(mouth.queue.map(({start,end})=>[start,end]),[[.3,1.3],[1.1,2.1]]);
 mouth.stop();assert.equal(mouth.syncOutputDelay(.1),true);assert.equal(mouth.active,false);
});
test('Stop clears actual mouth targets and rejects scheduling with a stale preparation epoch',()=>{
 const h=head(),context={currentTime:0},mouth=new TimedSpeechMouth(h,context),audio=decoded(),epoch=mouth.epoch;
 mouth.schedule(audio,0);context.currentTime=.2;mouth.update();h.updateMorphTargets(16);near(value(h,'viseme_aa'),.65);
 mouth.stop();h.updateMorphTargets(16);near(value(h,'viseme_aa'),0);assert.equal(mouth.active,false);
 assert.equal(mouth.schedule(audio,.2,0,epoch),false);
 assert.equal(mouth.schedule(audio,.2,0,mouth.epoch),true,'explicit replay with current ownership should remain usable');
});
test('empty cues keep valid silent PCM neutral rather than falling back to a stale classifier',()=>{
 const h=head(),context={currentTime:0},mouth=new TimedSpeechMouth(h,context),audio=decoded({version:1,duration:.5,cues:[]});
 assert.ok(speechTiming(audio));assert.equal(mouth.schedule(audio,0),true);
 context.currentTime=.25;assert.equal(mouth.update(),true);h.updateMorphTargets(16);
 assert.ok(h.applied.slice(0,OVR_VISEMES.length).every(value=>value===0));
 context.currentTime=.6;assert.equal(mouth.update(),false);
});
