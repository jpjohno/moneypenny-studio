'use strict';
// The production capture class, with deferred permission/audio activation. No
// real microphone, browser or transcription endpoint is used.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'..','workspace.js'),'utf8');
const start=source.indexOf('let localAudioContext=null;'),end=source.indexOf('\nfunction isVoiceStopCommand(',start);
assert.ok(start>0&&end>start);
const tick=()=>new Promise(setImmediate);
function stream(){const value={stopped:0};value.getTracks=()=>[{stop(){value.stopped++;}}];return value;}
function harness({deferResume=false}={}){
 const captures=[],resumes=[],connected=[];
 const context={navigator:{mediaDevices:{getUserMedia:()=>new Promise(resolve=>captures.push(resolve))}},$:()=>null,setTimeout:()=>1,clearTimeout(){},closeWakeMicrophone(){},console,AbortController,
  AudioContext:class{
   constructor(){this.destination={};this.state='running';}
   resume(){return deferResume?new Promise(resolve=>resumes.push(resolve)):Promise.resolve();}
   createMediaStreamSource(value){connected.push(value);return {connect(){},disconnect(){}};}
   createScriptProcessor(){return {connect(){},disconnect(){}};}
  }
 };
 vm.createContext(context);vm.runInContext(`let wakeMicStream=null,activeRecognition=null,activeUtterance=null,speechEchoUntil=0;${source.slice(start,end)};globalThis.captureTest={make:()=>new LocalRecognition(),get stream(){return wakeMicStream;},set active(value){activeRecognition=value;}};`,context);
 return {api:context.captureTest,captures,resumes,connected};
}
test('permission granted after Stop releases the late stream without starting audio capture',async()=>{
 const h=harness(),r=h.api.make(),audio=stream();const pending=r.start();r.abort();h.captures[0](audio);await pending;
 assert.equal(r.running,false);assert.equal(audio.stopped,1);assert.equal(h.api.stream,null);assert.deepEqual(h.connected,[]);
});
test('a late abandoned permission result cannot replace or stop the newer microphone',async()=>{
 const h=harness(),old=h.api.make(),current=h.api.make(),oldStream=stream(),currentStream=stream();
 const pendingOld=old.start();old.abort();h.api.active=current;const pendingCurrent=current.start();h.captures[1](currentStream);await pendingCurrent;
 h.captures[0](oldStream);await pendingOld;assert.equal(oldStream.stopped,1);assert.equal(currentStream.stopped,0);assert.equal(h.api.stream,currentStream);assert.deepEqual(h.connected,[currentStream]);current.abort();
});
test('an old suspended audio activation cannot stop a stream reused by the replacement recognizer',async()=>{
 const h=harness({deferResume:true}),old=h.api.make(),current=h.api.make(),audio=stream();
 h.api.active=old;const pendingOld=old.start();h.captures[0](audio);await tick();assert.equal(h.resumes.length,1);
 old.abort();h.api.active=current;const pendingCurrent=current.start();await tick();assert.equal(h.captures.length,1,'The replacement reuses the already granted stream');
 h.resumes[1]();await pendingCurrent;assert.deepEqual(h.connected,[audio]);h.resumes[0]();await pendingOld;
 assert.equal(audio.stopped,0,'A stale recognizer must not stop capture that its replacement is using');assert.equal(h.api.stream,audio);assert.equal(current.running,true);current.abort();
});
