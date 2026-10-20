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
export function connectSpeechSource(context,source,destination){
  const envelope=context.createGain(),now=context.currentTime,duration=source.buffer.duration;
  const fade=Math.min(.004,Math.max(0,duration)/2);
  envelope.gain.setValueAtTime(0,now);envelope.gain.linearRampToValueAtTime(1,now+fade);
  envelope.gain.setValueAtTime(1,now+Math.max(fade,duration-fade));envelope.gain.linearRampToValueAtTime(0,now+duration);
  source.connect(envelope);envelope.connect(destination);return envelope;
}
