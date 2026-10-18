'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../workspace.js'),'utf8');
const start=source.indexOf('async function streamAssistantAnswer('),end=source.indexOf('\nfunction setupAssistant(',start);
assert.ok(start>0&&end>start);
const encode=new TextEncoder();
function harness(){
 let stream,requests=0,locked=false;
 const context={TextDecoder,Uint8Array,DOMException,fetch:async()=>{requests++;return {ok:true,status:200,body:new ReadableStream({start(controller){stream=controller;}})};},lock(){locked=true;}};
 vm.createContext(context);vm.runInContext('let sessionEpoch=0;\n'+source.slice(start,end),context);
 return {context,get stream(){return stream;},get requests(){return requests;},get locked(){return locked;}};
}
test('answer text arrives before final metadata, including split UTF-8 bytes',async()=>{
 const h=harness(),parts=[];let completed=false;
 const result=h.context.streamAssistantAnswer({question:'Hello'},{onDelta:text=>parts.push(text)}).then(x=>{completed=true;return x;});
 await new Promise(setImmediate);
 const bytes=encode.encode(JSON.stringify({type:'delta',text:'Hello, James — '})+'\n');
 for(const byte of bytes)h.stream.enqueue(new Uint8Array([byte]));
 await new Promise(setImmediate);
 assert.equal(parts.join(''),'Hello, James — ');assert.equal(completed,false,'visible text is not delayed until completion');
 h.stream.enqueue(encode.encode(JSON.stringify({type:'final',data:{answer:'Hello, James — ready.',sources:[],model:'local'}})+'\n'));
 const final=await result;assert.equal(final.answer,'Hello, James — ready.');assert.equal(h.requests,1);
});
test('stream failures never masquerade as a completed answer or retry generation',async()=>{
 const h=harness();const reply=h.context.streamAssistantAnswer({question:'Explain a concept'});
 await new Promise(setImmediate);h.stream.enqueue(encode.encode('{"type":"delta","text":"A partial reply"}\n'));h.stream.close();
 await assert.rejects(reply,/interrupted before it completed/);assert.equal(h.requests,1);
});
test('cancellation prevents late chunks from entering the conversation',async()=>{
 const h=harness(),controller=new AbortController(),parts=[];
 const reply=h.context.streamAssistantAnswer({question:'Explain a concept'},{signal:controller.signal,onDelta:text=>parts.push(text)});
 await new Promise(setImmediate);controller.abort();h.stream.enqueue(encode.encode('{"type":"delta","text":"late"}\n'));
 await assert.rejects(reply,{name:'AbortError'});assert.equal(parts.length,0);
});
test('an expired or replaced workspace cannot receive private stream text',async()=>{
 const h=harness(),parts=[];const reply=h.context.streamAssistantAnswer({question:'Hello'},{onDelta:text=>parts.push(text)});
 await new Promise(setImmediate);vm.runInContext('sessionEpoch++;',h.context);
 h.stream.enqueue(encode.encode('{"type":"delta","text":"late"}\n'));
 await assert.rejects(reply,/Workspace session changed/);assert.equal(parts.length,0);
});
test('provider stream error is surfaced and the reader closes',async()=>{
 const h=harness();const reply=h.context.streamAssistantAnswer({question:'Hello'});
 await new Promise(setImmediate);h.stream.enqueue(encode.encode('{"type":"error","detail":"Local model unavailable"}\n'));
 await assert.rejects(reply,/Local model unavailable/);
});
