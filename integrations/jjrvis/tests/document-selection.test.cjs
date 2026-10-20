'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../workspace.js'),'utf8');
const start=source.indexOf(' form.onsubmit=async e=>'),end=source.indexOf("\n if($('#assistant-speak'))",start);
function harness(){
 const nodes=new Map(),calls=[];
 const node=()=>({value:'Explain the selected document',checked:false,textContent:'',dataset:{},removeAttribute(){},setAttribute(){},replaceChildren(){},append(){},appendChild(){},after(){}});
 const ctx={document:{createElement:node},form:{},$:id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);},assistantFile:'fixture-selected-key',assistantHistory:[],assistantRequest:0,voiceReplyRequested:false,assistantController:null,streamingSpeech:null,commandBriefing:{pause(){}},mutedSpeechRequest:null,stopped:false,
  showAssistant:()=>true,stopVoice(){},voiceState(){},engineState(){},resumeWake(){},checkAssistantEngine(){},deviceIdentity:()=>({device_id:'fixture'}),
  setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,clearInterval(){},AbortController,Date,
  streamAssistantAnswer:async payload=>{calls.push(payload);throw Error('fixture interrupted');}};
 vm.createContext(ctx);vm.runInContext(source.slice(start,end),ctx);return {ctx,calls};
}
test('selected document survives a failed answer and stays attached to the next request',async()=>{
 const h=harness();await h.ctx.form.onsubmit({preventDefault(){}});assert.equal(h.ctx.assistantFile,'fixture-selected-key');
 await h.ctx.form.onsubmit({preventDefault(){}});assert.equal(h.calls.length,2);assert.ok(h.calls.every(x=>x.file_id==='fixture-selected-key'));
 assert.equal(h.ctx.$('#assistant-submit').disabled,false);
});
