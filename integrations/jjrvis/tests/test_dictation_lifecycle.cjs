'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('workspace.js','utf8');
const context={AbortController,Int16Array,setTimeout,clearTimeout,$:()=>null,closeWakeMicrophone(){}};
let resolveRequest;
context.fetch=()=>new Promise(resolve=>{resolveRequest=resolve;});
vm.createContext(context);vm.runInContext(source.slice(source.indexOf('class LocalRecognition {'),source.indexOf('\nfunction isVoiceStopCommand'))+'\nglobalThis.Recognition=LocalRecognition;',context);
(async()=>{
 const r=new context.Recognition();r.running=true;r.parts=[new Int16Array([12,13])];r.samples=2;
 let words='',ended=false;r.onresult=e=>{words=e.results[0][0].transcript;};r.onend=()=>{ended=true;};
 const pending=r.flush();r.finishRequested=true;const stopping=r.stop();
 assert.equal(ended,false,'Finish waits for transcription already in flight');
 resolveRequest({ok:true,json:async()=>({text:'the complete question'})});await pending;await stopping;
 assert.equal(words,'the complete question');assert.equal(ended,true);
 const cancelled=new context.Recognition();cancelled.running=true;cancelled.parts=[new Int16Array([12])];cancelled.samples=1;
 cancelled.onresult=()=>assert.fail('Cancelled recognition must not append late text');
 const inflight=cancelled.flush();cancelled.abort();resolveRequest({ok:true,json:async()=>({text:'late'})});await inflight;
 console.log('Dictation lifecycle: Finish retains pending words; cancelled results are ignored.');
})().catch(e=>{console.error(e);process.exitCode=1;});
