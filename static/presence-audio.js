import {parseSpeechTiming,attachSpeechTiming,speechTiming} from './speech-timing.js';

// One broker-owned audio stream drives both this voice and its facial analysis.
export class PresenceAudio {
  constructor({stopAudio,decode,playAudio,drain=async()=>{},setBusy=()=>{},emit=()=>{}}){Object.assign(this,{stopAudio,decode,playAudio,drain,setBusy,emit});this.epoch=0;this.id=null;this.playing=false;this.lastSequence=-1;}
  cancel(){this.epoch++;this.id=null;this.playing=false;this.endRequested=false;}
  async finish(epoch){
    await this.drain();if(epoch!==this.epoch||this.id===null)return;
    const requestId=this.id,sequence=this.lastSequence;this.setBusy(false);this.cancel();
    this.emit('moneypenny-presence-idle',{requestId,sequence,final:true});
  }
  async end(message){if(message.requestId!==this.id)return;if(this.playing)this.endRequested=true;else await this.finish(this.epoch);}
  async play(message){
    const {requestId,sequence,audio}=message;
    if(typeof requestId!=='string'||!requestId||requestId.length>120||!Number.isInteger(sequence)||sequence<0||sequence>4096||!(audio instanceof ArrayBuffer)||audio.byteLength<44||audio.byteLength>6_000_044)return;
    if(!message.first&&(requestId!==this.id||this.playing||sequence<=this.lastSequence))return;
    if(message.first){
      this.cancel();this.id=requestId;const starting=this.epoch;
      await this.stopAudio();if(starting!==this.epoch)return;
    }
    const epoch=this.epoch;this.playing=true;this.setBusy(true);
    try{
      const decoded=await this.decode(audio);
      if(epoch!==this.epoch)return;
      await this.playAudio(decoded,{onStarted:()=>{if(epoch===this.epoch)this.emit('moneypenny-presence-speaking',{requestId,sequence});}});
      if(epoch!==this.epoch)return;
      this.playing=false;this.lastSequence=sequence;
      if(message.final||this.endRequested)await this.finish(epoch);
      else this.emit('moneypenny-presence-idle',{requestId,sequence,final:false});
    }catch(error){
      if(epoch!==this.epoch)return;
      this.setBusy(false);this.cancel();this.emit('moneypenny-presence-error',{requestId,sequence,message:String(error.message||'Audio playback unavailable.').slice(0,180)});
    }
  }
}

// Short edge ramps prevent discontinuities when independently prepared phrases meet.
export function connectSpeechSource(context,source,destination,startAt=context.currentTime){
  const envelope=context.createGain(),now=Math.max(context.currentTime,startAt),duration=source.buffer.duration;
  const fade=Math.min(.004,Math.max(0,duration)/2);
  envelope.gain.setValueAtTime(0,now);envelope.gain.linearRampToValueAtTime(1,now+fade);
  envelope.gain.setValueAtTime(1,now+Math.max(fade,duration-fade));envelope.gain.linearRampToValueAtTime(0,now+duration);
  source.connect(envelope);envelope.connect(destination);return envelope;
}

// Hold the instantaneous gain before changing it, including an interrupted ramp.
// Keep the source connected until its scheduled stop so the fade reaches output.
export function fadeSpeechGain(param,now,target,duration=.006){
  if(typeof param.cancelAndHoldAtTime==='function')param.cancelAndHoldAtTime(now);
  else {const held=param.value;param.cancelScheduledValues(now);param.setValueAtTime(held,now);}
  param.linearRampToValueAtTime(target,now+duration);
  return now+duration;
}

// The new source begins at zero after the old delayed source has drained.
// An explicit zero avoids sampling today's gain for a future output time on
// older Web Audio implementations without cancelAndHoldAtTime.
export function openSpeechGate(param,at){
  param.cancelScheduledValues(at);param.setValueAtTime(0,at);
  param.linearRampToValueAtTime(1,at+.004);
}

const visemeLifecycles=new WeakSet();
// HeadAudio's bundled event handler treats numeric index 0 as false, although
// index 0 is the open AA vowel. Keep all of its callbacks and analysis intact,
// then apply a checked index so AA can replace the previous consonant too.
export function installSpeechVisemeLifecycle(processor){
  if(!processor?.port||typeof processor.port.onmessage!=='function'||typeof processor.resetAll!=='function'||!Array.isArray(processor.visemeNames))return false;
  if(visemeLifecycles.has(processor))return true;
  visemeLifecycles.add(processor);
  const receive=processor.port.onmessage,reset=processor.resetAll;
  processor.port.onmessage=function(event){
    receive.call(this,event);
    const data=event?.data,index=data?.viseme;
    if(data?.event==='viseme'&&Number.isInteger(index)&&index>=0&&index<processor.visemeNames.length){
      processor.visemeActive=processor.visemeNames[index]==='viseme_sil'?-1:index;
    }
  };
  // The worker reset clears its analysis buffers, but does not send an ended
  // event or clear the main-thread active vowel. Release it locally as well;
  // HeadAudio's normal interpolation closes the mouth instead of holding it.
  processor.resetAll=function(){this.visemeActive=-1;return reset.call(this);};
  return true;
}

// Lip interpolation follows the PCM clock, independently of the character's
// capped animation/physics dt. One update catches up only to the latest mouth
// target, never replays missed phonemes or advances more than 100 ms.
export class SpeechFrameClock {
  constructor(context){this.context=context;this.reset();}
  reset(){const now=this.context?.currentTime;this.last=Number.isFinite(now)?now:null;}
  tick(){
    const now=this.context?.currentTime;
    if(!Number.isFinite(now)){this.last=null;return 0;}
    const elapsed=this.last===null?0:(now-this.last)*1000;
    this.last=now;
    return Math.min(100,Math.max(0,elapsed));
  }
}

// Generated passages often carry a few hundred milliseconds of digital quiet
// after the words. Shorten only a confirmed tail: never leading audio, never
// more than 350 ms, and leave at least 80 ms after the last active 20 ms window.
// A peak guard preserves short quiet consonants that an RMS-only gate can miss.
export function trimSpeechTail(context,buffer){
  const rate=buffer?.sampleRate,length=buffer?.length,channels=buffer?.numberOfChannels;
  if(!Number.isFinite(rate)||rate<=0||!Number.isInteger(length)||length<=0||!Number.isInteger(channels)||channels<=0||typeof context?.createBuffer!=='function')return buffer;
  const window=Math.max(1,Math.ceil(rate*.02)),margin=Math.ceil(rate*.08),maximum=Math.floor(rate*.35),threshold=10**(-55/20);
  if(length<=margin+window)return buffer;
  const samples=Array.from({length:channels},(_,channel)=>buffer.getChannelData(channel));
  const earliest=Math.max(0,length-maximum-margin-window);
  let activeEnd=null;
  for(let end=length;end>earliest;){
    const start=Math.max(earliest,end-window),count=end-start;
    let active=false;
    for(const data of samples){
      let sum=0,peak=0;
      for(let i=start;i<end;i++){
        const value=data[i];if(!Number.isFinite(value))return buffer;
        sum+=value*value;peak=Math.max(peak,Math.abs(value));
      }
      if(Math.sqrt(sum/count)>threshold||peak>threshold){active=true;break;}
    }
    if(active){activeEnd=end;break;}end=start;
  }
  // Do not manufacture a meaningful duration for an all-quiet or uncertain clip.
  if(activeEnd===null)return buffer;
  const end=Math.min(length,Math.max(activeEnd+margin,length-maximum));
  if(length-end<window)return buffer;
  const trimmed=context.createBuffer(channels,end,rate);
  for(let channel=0;channel<channels;channel++)trimmed.getChannelData(channel).set(samples[channel].subarray(0,end));
  return trimmed;
}

// Read optional phoneme timing before decodeAudioData can detach the WAV bytes.
// Validate against the original PCM duration, then clip only a confirmed quiet
// tail. Old or malformed metadata leaves the existing audio analysis available.
export async function decodeSpeechBuffer(context,bytes){
  const timing=parseSpeechTiming(bytes);
  const decoded=attachSpeechTiming(await context.decodeAudioData(bytes),timing);
  const checked=speechTiming(decoded),trimmed=trimSpeechTail(context,decoded);
  if(!checked||trimmed===decoded)return trimmed;
  const duration=trimmed.duration;
  return attachSpeechTiming(trimmed,{version:1,duration,cues:checked.cues
    .filter(([start])=>start<duration)
    .map(([start,end,name])=>[start,Math.min(end,duration),name])});
}
