import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {connectSpeechSource,fadeSpeechGain,openSpeechGate} from '../static/presence-audio.js';
import {TimedSpeechMouth,speechTiming,attachSpeechTiming} from '../static/speech-timing.js';
const studio=await readFile(new URL('../static/studio.js',import.meta.url),'utf8');
const stop=studio.slice(studio.indexOf('async function stopAll('),studio.indexOf('function performActions('));
const play=studio.slice(studio.indexOf('async function playPrepared('),studio.indexOf('async function playSpeech('));
function harness(){
 const sources=[],envelopes=[],cancellations=[];
 const gain=()=>({value:1,cancelAndHoldAtTime(){},linearRampToValueAtTime(){},setValueAtTime(){}});
 const context={currentTime:4,createGain(){const envelope={gain:gain(),connect(){},disconnect(){this.disconnected=true;}};envelopes.push(envelope);return envelope;},createBufferSource(){
  const source={connect(){},disconnect(){this.disconnected=true;},start(time){this.started=time;},stop(time){this.stopped=time;}};sources.push(source);return source;
 }};
 const elements=new Map(),element=id=>{if(!elements.has(id))elements.set(id,{dataset:{},classList:{remove(){}},querySelectorAll:()=>[],value:'neutral'});return elements.get(id);};
 const sandbox={connectSpeechSource,fadeSpeechGain,openSpeechGate,speechTiming,console,Uint8Array,clearTimeout,
  head:{audioCtx:context,mtAvatar:{viseme_aa:{value:0},viseme_PP:{value:0}},audioSpeechGainNode:{},isSpeaking:false,lookAtCamera(){context.currentTime+=.020;},stopSpeaking(){},stopGesture(){},setValue(){}},
  $:element,setState(){},setBusy(){},notify(){},api:async()=>{},performActions(){},setPersonaMood(){},
  recorder:{cancel(){}},analyser:{frequencyBinCount:16},cancelAnimationFrame:id=>cancellations.push(id),
  jarvisEmbed:true,proxiedPresence:true,document:{hidden:false},owner:'test',
 };
 sandbox.timedMouth=new TimedSpeechMouth(sandbox.head,context);
 vm.createContext(sandbox);
 vm.runInContext(`let generation=0,controller=null,motionLibrary=null,speechGate={gain:{value:0,cancelAndHoldAtTime(){},cancelScheduledValues(time){globalThis.openedAt=time;},setValueAtTime(){},linearRampToValueAtTime(){}}},speechDelay={delayTime:{value:.15}},speechStopAt=0,activeReply=null,recordingPending=false,currentSource=null,currentEnvelope=null,speechEnded=null,lips=null,visualizer=9,actionTimers=[],userSpeaking=false,avatarReady=true,turnStarted=0,firstVoiceAt=0,liveSession=null;${stop}\n${play}\nglobalThis.play=audio=>playPrepared(audio,generation);globalThis.stop=()=>stopAll();globalThis.state=()=>({currentSource,currentEnvelope,speechEnded,speaking:head.isSpeaking});`,sandbox);
 return {sandbox,sources,envelopes,context,cancellations};
}
test('real Studio playback starts its envelope with the PCM after slow gaze work',async()=>{
 const h=harness(),pending=h.sandbox.play({duration:.1}),source=h.sources[0];
 assert.equal(source.started,h.context.currentTime+.004);
 assert.equal(h.sandbox.openedAt,source.started+.15,'gate stays shut until the new voice reaches the output delay');
 source.onended();await pending;assert.equal(h.sandbox.state().speaking,false);
 assert.equal(h.envelopes[0].disconnected,true);
});
test('Stop drains old audio without letting stale completion clear a replacement',async()=>{
 const h=harness(),old=h.sandbox.play({duration:1}),source=h.sources[0],oldEnd=source.onended;
 await h.sandbox.stop();await old;
 assert.ok(source.stopped>h.context.currentTime,'stop is scheduled after the gain fade');
 assert.equal(source.disconnected,undefined,'remain connected until ended so fade is audible');
 const replacement=h.sandbox.play({duration:1}),next=h.sources[1];
 oldEnd();source.onended();
 assert.equal(h.sandbox.state().currentSource,next);
 assert.equal(h.sandbox.state().speaking,true);
 assert.equal(h.envelopes[1].disconnected,undefined);
 next.onended();await replacement;
 assert.equal(h.sandbox.state().speaking,false);assert.equal(h.sandbox.state().currentSource,null);
});
test('animation preview stops locally without waiting for a stalled voice service cancellation',async()=>{
 const h=harness(),busy=[];let completeRequest;
 h.sandbox.proxiedPresence=false;
 h.sandbox.api=()=>new Promise(resolve=>{completeRequest=resolve;});
 h.sandbox.setBusy=value=>busy.push(value);
 const speech=h.sandbox.play({duration:1});
 await vm.runInContext('stopAll(true,true,false)',h.sandbox);
 await speech;
 assert.equal(h.sandbox.state().speaking,false);
 assert.equal(h.sandbox.state().currentSource,null);
 assert.equal(busy.at(-1),false,'controls settle while the voice service request is pending');
 assert.equal(typeof completeRequest,'function','the old synthesis is still cancelled in the background');
 completeRequest();
});

test('actual playback retains delayed timed lips across phrase handoff and Stop cancels them',async()=>{
 const h=harness(),buffer=name=>attachSpeechTiming({duration:.5},{version:1,duration:.5,cues:[[0,.5,name]]});
 const first=h.sandbox.play(buffer('viseme_aa')),source=h.sources[0];
 h.context.currentTime=source.started+.5;source.onended();await first;
 const second=h.sandbox.play(buffer('viseme_PP')),next=h.sources[1];
 assert.equal(h.sandbox.timedMouth.queue.length,2,'previous output has not drained at source end');
 h.sandbox.timedMouth.update();assert.ok(h.sandbox.head.mtAvatar.viseme_aa.newvalue>.6);
 h.context.currentTime=next.started+.15+.1;h.sandbox.timedMouth.update();
 assert.ok(h.sandbox.head.mtAvatar.viseme_PP.newvalue>.7);assert.equal(h.sandbox.head.mtAvatar.viseme_aa.newvalue,0);
 await h.sandbox.stop();await second;
 assert.equal(h.sandbox.timedMouth.active,false);assert.equal(h.sandbox.head.mtAvatar.viseme_PP.newvalue,0);
 assert.equal(h.sandbox.head.studioSpeechActive,false);
});
