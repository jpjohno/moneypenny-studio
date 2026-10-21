import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {SpeechFrameClock} from '../static/presence-audio.js';

const source=await readFile(new URL('../static/studio.js',import.meta.url),'utf8');
const callback=source.slice(source.indexOf('    let previousMotionClock='),source.indexOf('    liveSession=new LiveSession'));
function harness(libraryPlaying=false){
 const calls={motion:[],library:[],rig:[],lips:[],breathing:[],correctives:[]};
 const audio={currentTime:0},head={animClock:0,opt:{},isSpeaking:false};
 const stage={dataset:{}},sandbox={head,speechClock:new SpeechFrameClock(audio),renderFrames:0,
  $:()=>stage,stageActivity:{update(){}},busy:false,userSpeaking:false,
  lips:{update:dt=>calls.lips.push(dt)},
  motion:{active:null,queue:[],autonomous:true,update:dt=>calls.motion.push(dt)},
  motionLibrary:{playing:libraryPlaying,currentSource:'instruction',update:dt=>calls.library.push(dt)},
  rig:{targets:new Map(),resetBody(){},breathe:dt=>calls.breathing.push(dt),update:dt=>calls.rig.push(dt)},
  poseCorrectives:{update:dt=>calls.correctives.push(dt)},seatSupport:{update(){}},rigView:{visible:false},
 };
 vm.createContext(sandbox);vm.runInContext(callback,sandbox);
 const frame=(elapsed,clamped=1000/15)=>{head.animClock+=elapsed;audio.currentTime+=elapsed/1000;head.opt.update(clamped);};
 return {calls,frame,audio,head};
}
test('the real Studio callback preserves a second of motion at 5 fps despite vendor pose clamping',()=>{
 for(const library of [false,true]){
  const h=harness(library);for(let i=0;i<5;i++)h.frame(200);
  const sum=values=>values.reduce((a,b)=>a+b,0);
  assert.ok(Math.abs(sum(library?h.calls.library:h.calls.motion)-(library?1:1000))<1e-8);
  assert.ok(Math.abs(sum(h.calls.rig)-1)<1e-8);
  assert.ok(h.calls.lips.every(value=>value===100),'mouth interpolation follows current audio instead of a capped pose delta');
 }
});
test('hidden animation clocks do not make body movement catch up when the audio clock kept running',()=>{
 const h=harness();h.frame(40);h.audio.currentTime+=30;
 h.frame(40);
 assert.deepEqual(h.calls.motion,[40,40]);
 assert.deepEqual(h.calls.lips,[40,100]);
});
