import {studioURL} from './studio-paths.js';

export function pcmWav(samples,rate=16000){
  const buffer=new ArrayBuffer(44+samples.length*2),view=new DataView(buffer);
  const write=(offset,value)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
  write(0,'RIFF');view.setUint32(4,36+samples.length*2,true);write(8,'WAVE');write(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);write(36,'data');view.setUint32(40,samples.length*2,true);
  for(let i=0;i<samples.length;i++){const x=Math.max(-1,Math.min(1,samples[i]));view.setInt16(44+i*2,x*(x<0?32768:32767),true);}
  return buffer;
}

export function spokenText(raw){return raw.replace(/\*[^*]*\*/g,'').replace(/\*[^*]*$/,'').trimStart().replace(/^["“]|["”]$/g,'');}

export class SpeechSegmenter {
  constructor(onSegment){this.onSegment=onSegment;this.consumed=0;this.count=0;}
  update(raw,finished=false){
    const spoken=spokenText(raw);
    let remaining=spoken.slice(this.consumed);
    while(remaining.length){
      let end=0;
      const sentence=remaining.match(/^.*?[.!?](?:\s+|$)/s);
      if(sentence&&sentence[0].length<=2400&&sentence[0].trim().length>=8&&(finished||/\s$/.test(sentence[0])))end=sentence[0].length;
      const limit=this.count?170:80;
      if(!end&&remaining.length>limit){const prefix=remaining.slice(0,limit+25);const comma=prefix.lastIndexOf(', ');const boundary=prefix.lastIndexOf(' ');end=comma>25?comma+2:boundary>0?boundary:limit;}
      if(!end&&finished)end=remaining.length;
      if(!end)break;
      const part=remaining.slice(0,end).trim();this.consumed+=end;remaining=spoken.slice(this.consumed);
      if(part){this.count++;this.onSegment(part);}
    }
  }
}

export class SpeechPipeline {
  constructor(prepare,play){this.prepare=prepare;this.play=play;this.preparation=Promise.resolve();this.playback=Promise.resolve();this.error=null;this.count=0;}
  push(text){
    this.count++;
    const prepared=this.preparation.then(()=>{if(this.error)throw this.error;return this.prepare(text);});
    prepared.catch(()=>{});
    this.preparation=prepared.then(()=>{},error=>{this.error=error;});
    this.playback=this.playback.then(async()=>{const audio=await prepared;if(!this.error)await this.play(audio,text);}).catch(error=>{this.error=error;});
  }
  async done(){await this.playback;if(this.error)throw this.error;}
}

export class LiveSession {
  constructor({audioContext,onState,onStart,onEnd,onError,onLevel}){Object.assign(this,{audioContext,onState,onStart,onEnd,onError,onLevel});this.active=false;this.epoch=0;this.vad=null;this.stream=null;}
  async start(){
    if(this.active)return;
    this.active=true;const epoch=++this.epoch;
    // Request permission immediately on the user's click, before loading models.
    const streamPromise=navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
    this.onState('Opening microphone…');
    try{
      this.stream=await streamPromise;
      if(epoch!==this.epoch){this.stream.getTracks().forEach(t=>t.stop());return;}
      this.onState('Microphone on · preparing speech detection…');
      await this.audioContext.resume();
      this.vad=await window.vad.MicVAD.new({
        model:'v5',startOnLoad:false,audioContext:this.audioContext,
        baseAssetPath:studioURL('/vendor/vad/'),onnxWASMBasePath:studioURL('/vendor/onnx/'),
        ortConfig:ort=>{ort.env.wasm.numThreads=1;ort.env.logLevel='error';},
        positiveSpeechThreshold:.65,negativeSpeechThreshold:.35,minSpeechMs:128,redemptionMs:650,preSpeechPadMs:320,
        submitUserSpeechOnPause:true,
        getStream:async()=>this.stream,pauseStream:async()=>{},resumeStream:async()=>this.stream,
        onSpeechRealStart:()=>{
          if(!this.active)return;
          this.onStart();clearTimeout(this.limit);
          this.limit=setTimeout(async()=>{if(this.active){await this.vad.pause();if(this.active)await this.vad.start();}},28500);
        },
        onSpeechEnd:audio=>{clearTimeout(this.limit);if(this.active&&epoch===this.epoch)this.onEnd(pcmWav(audio));},
        onVADMisfire:()=>{if(this.active)this.onState('Listening');},
        onFrameProcessed:(probabilities,frame)=>{if(this.active)this.onLevel?.(probabilities.isSpeech,frame);},
      });
      if(epoch!==this.epoch){await this.vad.destroy();return;}
      await this.vad.start();this.onState('Listening · speak naturally');
      this.stream.getAudioTracks()[0].onended=()=>{if(this.active){this.stop();this.onError(new Error('The microphone disconnected. Start live conversation again.'));}};
    }catch(error){if(epoch===this.epoch){await this.stop();this.onError(error);}}
  }
  async stop(){
    this.active=false;this.epoch++;clearTimeout(this.limit);
    this.stream?.getTracks().forEach(t=>{t.onended=null;t.stop();});this.stream=null;
    const detector=this.vad;this.vad=null;
    if(detector)await detector.destroy().catch(()=>{});
  }
}

export function controlIntent(value){
  const text=value.trim().replace(/[.!?]+$/,'').toLowerCase();
  const numbers={one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10,fifteen:15,twenty:20,thirty:30};
  const time=text.match(/\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty)\s*(seconds?|minutes?|hours?)\b/);
  const delay=time?(Number(time[1])||numbers[time[1]])*(time[2].startsWith('hour')?3600:time[2].startsWith('min')?60:1):null;
  if(/\b(?:ask me|remind me|check back|come back|check in)\b/.test(text)&&delay)return {type:'reminder',delay,text:value};
  if(/\b(?:be quiet|stop talking|stop speaking|quiet for|stay quiet|silence|shut up)\b/.test(text)||/^(?:please )?stop$/.test(text))return {type:'quiet',delay};
  if(/^(?:please )?(?:resume|wake up|you can speak|start talking|carry on|talk to me)$/.test(text))return {type:'resume'};
  return null;
}
