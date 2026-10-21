// Optional MPVS timing travels with the exact WAV that supplies the PCM. The
// browser never executes metadata and keeps no second copy of decoded audio.
export const OVR_VISEMES=Object.freeze(['viseme_aa','viseme_E','viseme_I','viseme_O','viseme_U','viseme_PP','viseme_SS','viseme_TH','viseme_DD','viseme_FF','viseme_kk','viseme_nn','viseme_RR','viseme_CH','viseme_sil']);
const indices=new Map(OVR_VISEMES.map((name,index)=>[name,index]));
const attachments=new WeakMap(),MAX_BYTES=512*1024,MAX_CUES=8192;
const attack=.020,release=.030;
const smooth=value=>{const t=Math.max(0,Math.min(1,value));return t*t*(3-2*t);};

function checkedTiming(value){
 if(!value||value.version!==1||typeof value.duration!=='number'||!Number.isFinite(value.duration)||value.duration<=0||value.duration>600||!Array.isArray(value.cues)||value.cues.length>MAX_CUES)return null;
 let previous=-1;const cues=[];
 for(const cue of value.cues){
  if(!Array.isArray(cue)||cue.length!==3)return null;
  const [start,end,name]=cue;
  if(typeof start!=='number'||typeof end!=='number'||!Number.isFinite(start)||!Number.isFinite(end)||start<0||end<start||start<previous||end>value.duration||!indices.has(name))return null;
  previous=start;cues.push(Object.freeze([start,end,name]));
 }
 return Object.freeze({version:1,duration:value.duration,cues:Object.freeze(cues)});
}

export function parseSpeechTiming(bytes){
 try{
  const view=bytes instanceof ArrayBuffer?new DataView(bytes):ArrayBuffer.isView(bytes)?new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength):null;
  if(!view||view.byteLength<12)return null;
  const tag=offset=>String.fromCharCode(view.getUint8(offset),view.getUint8(offset+1),view.getUint8(offset+2),view.getUint8(offset+3));
  if(tag(0)!=='RIFF'||tag(8)!=='WAVE')return null;
  const limit=view.getUint32(4,true)+8;if(limit>view.byteLength||limit<12)return null;
  let result=null,found=false,offset=12,chunks=0;
  while(offset<limit){
   if(++chunks>4096||offset+8>limit)return null;
   const name=tag(offset),length=view.getUint32(offset+4,true),start=offset+8,end=start+length;
   if(end>limit||end+(length&1)>limit)return null;
   if(name==='MPVS'){
    if(found||length>MAX_BYTES)return null;
    found=true;
    const text=new TextDecoder('utf-8',{fatal:true}).decode(new Uint8Array(view.buffer,view.byteOffset+start,length));
    result=checkedTiming(JSON.parse(text));if(!result)return null;
   }
   offset=end+(length&1);
  }
  return result;
 }catch{return null;}
}

export function attachSpeechTiming(buffer,timing){
 if(!buffer||typeof buffer!=='object')return buffer;
 const checked=checkedTiming(timing),duration=buffer.duration;
 if(!checked||typeof duration!=='number'||!Number.isFinite(duration)||duration<0||Math.abs(checked.duration-duration)>.05)attachments.delete(buffer);
 else attachments.set(buffer,checked);
 return buffer;
}
export function speechTiming(buffer){return buffer&&typeof buffer==='object'?attachments.get(buffer)||null:null;}

export class TimedSpeechMouth {
 constructor(head,context){
  this.head=head;this.context=context;this.queue=[];this.epoch=0;
  this.weights=new Float32Array(OVR_VISEMES.length);this.owned=false;
 }
 get active(){const now=this.context.currentTime;return this.queue.some(segment=>segment.epoch===this.epoch&&now<segment.end+release);}
 // Capture epoch before asynchronous preparation when needed; Stop invalidates
 // that optional fourth argument, so a late decode cannot resurrect old speech.
 schedule(buffer,startAt,outputDelay=0,epoch=this.epoch){
  const timing=speechTiming(buffer),now=this.context.currentTime,duration=buffer?.duration;
  if(epoch!==this.epoch||!timing||typeof startAt!=='number'||!Number.isFinite(startAt)||typeof outputDelay!=='number'||!Number.isFinite(outputDelay)||outputDelay<0||outputDelay>1||!(duration>0))return false;
  this.queue=this.queue.filter(segment=>segment.epoch===this.epoch&&now<segment.end+release);
  if(this.queue.length>=16||this.queue.reduce((sum,segment)=>sum+segment.timing.cues.length,0)+timing.cues.length>16384)return false;
  const start=startAt+outputDelay,end=start+duration;
  if(end+release<=now)return false;
  this.queue.push({timing,sourceStart:startAt,sourceEnd:startAt+duration,start,end,epoch,cursor:0});this.queue.sort((a,b)=>a.start-b.start);
  return true;
 }
 // Follow the DelayNode's current AudioParam value rather than the slider's
 // final target. Source times stay fixed so repeated ramps do not accumulate
 // drift, and increasing delay can revisit an earlier phoneme safely.
 syncOutputDelay(outputDelay){
  if(typeof outputDelay!=='number'||!Number.isFinite(outputDelay)||outputDelay<0||outputDelay>1)return false;
  for(const segment of this.queue){
   const start=segment.sourceStart+outputDelay;
   if(start>segment.start)segment.cursor=0;
   segment.start=start;segment.end=segment.sourceEnd+outputDelay;
  }
  return true;
 }
 write(){
  for(let index=0;index<OVR_VISEMES.length;index++){
   const channel=this.head?.mtAvatar?.[OVR_VISEMES[index]];
   if(channel){channel.newvalue=this.weights[index];channel.needsUpdate=true;}
  }
 }
 update(){
  const now=this.context.currentTime;
  this.queue=this.queue.filter(segment=>segment.epoch===this.epoch&&now<segment.end+release);
  this.weights.fill(0);
  for(const segment of this.queue){
   const time=now-segment.start;
   if(time< -attack||now>=segment.end+release)continue;
   const cues=segment.timing.cues;
   while(segment.cursor<cues.length&&cues[segment.cursor][1]+release<time)segment.cursor++;
   for(let cursor=segment.cursor;cursor<cues.length;cursor++){
    const [start,rawEnd,name]=cues[cursor],end=Math.min(rawEnd,segment.end-segment.start);
    if(start-attack>time)break;
    if(end<=start||end+release<time||name==='viseme_sil')continue;
    const weight=smooth((time-(start-attack))/attack)*smooth((end+release-time)/release);
    this.weights[indices.get(name)]+=weight;
   }
  }
  // Overlapping neighbouring phonemes blend; they cannot add multiple fully
  // open mouths together. PP/FF retain the existing authored 0.75 maximum.
  const total=this.weights.reduce((sum,value)=>sum+value,0),normalizer=Math.max(1,total);
  for(let index=0;index<this.weights.length;index++)this.weights[index]=this.weights[index]/normalizer*(OVR_VISEMES[index]==='viseme_PP'||OVR_VISEMES[index]==='viseme_FF'?.75:.65);
  const active=this.active;
  if(active||this.owned)this.write();this.owned=active;
  return active;
 }
 stop(){this.epoch++;this.queue=[];this.weights.fill(0);this.write();this.owned=false;return this.epoch;}
}
