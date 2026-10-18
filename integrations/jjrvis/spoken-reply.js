/* One cancellable speech queue. Only the caller can opt a response into early speech. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.JJSpokenReply=api;})(typeof window==='undefined'?this:window,()=>{
 'use strict';
 function boundary(text,first,final){
  const limit=first?48:145;
  const head=text.slice(0,limit+1);
  const sentence=[...head.matchAll(/[.!?](?:[”"']?)(?=\s|$)/g)].find(m=>m.index>=10&&(final||m.index+m[0].length<text.length||!/[0-9]/.test(text[m.index-1])));
  if(sentence)return sentence.index+sentence[0].length;
  if(final&&text.length<=limit)return text.length;
  if(text.length<=limit)return 0;
  const clause=[...head.matchAll(/[,;:](?=\s)/g)].map(m=>m.index+1).filter(n=>n>=28);
  const space=head.lastIndexOf(' ');return clause.at(-1)||(space>0?space:limit);
 }
 function create({prepare,play,finish=()=>{},onError=()=>{},onFirst=()=>{},onDone=()=>{}}){
  const controller=new AbortController(),queue=[];
  let accepted='',buffer='',first=true,closed=false,running=false,ended=false,prepared=null,firstPlayed=false,phase='idle';
  let resolveDone;const done=new Promise(resolve=>resolveDone=resolve);
  const prepareOne=part=>Promise.resolve().then(()=>{if(controller.signal.aborted)throw new DOMException('Stopped','AbortError');return prepare(part,controller.signal);}).then(value=>({value}),error=>({error}));
  // The local voice engine accepts one generation at a time. A later phrase
  // may be prepared while audio plays, never while another prepare is pending.
  const prefetch=()=>{if(phase==='playing'&&queue.length&&!prepared&&!controller.signal.aborted)prepared={part:queue[0],promise:prepareOne(queue[0])};};
  async function pump(){
   if(running||ended)return;running=true;
   try{
    while(queue.length&&!controller.signal.aborted){
     phase='preparing';
     const part=queue.shift(),task=prepared?.part===part?prepared.promise:prepareOne(part);prepared=null;
     const result=await task;
     if(controller.signal.aborted)return;
     if(result.error)throw result.error;
     phase='playing';prefetch();
     await play(result.value,{first:!firstPlayed,signal:controller.signal,onStarted(){if(!firstPlayed){firstPlayed=true;onFirst();}}});
     phase='idle';
    }
    if(closed&&!controller.signal.aborted){await finish();if(controller.signal.aborted||ended)return;ended=true;onDone();resolveDone({state:'complete'});}
   }catch(error){if(!controller.signal.aborted){ended=true;controller.abort();onError(error);resolveDone({state:'error',error});}}
   finally{running=false;phase='idle';}
  }
  function update(text,final=false){
   if(ended||closed||controller.signal.aborted)return;
   text=String(text||'');if(text.length>24000){cancel();throw new Error('Reply is too long for speech.');}
   if(!text.startsWith(accepted)){cancel();throw new Error('Spoken reply changed while it was being prepared.');}
   buffer+=text.slice(accepted.length);accepted=text;
   while(buffer.trim()){
    buffer=buffer.trimStart();const end=boundary(buffer,first,final);if(!end)break;
    const part=buffer.slice(0,end).trim();buffer=buffer.slice(end);if(part){queue.push(part);first=false;}
   }
   if(final){closed=true;if(buffer.trim()){queue.push(buffer.trim());buffer='';}}
   prefetch();
   pump();
  }
  function cancel(){if(ended)return;ended=true;controller.abort();queue.length=0;buffer='';resolveDone({state:'cancelled'});}
  return {update,cancel,done,signal:controller.signal,get started(){return firstPlayed;}};
 }
 return {create,boundary};
});
