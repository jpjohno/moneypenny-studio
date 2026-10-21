import test from 'node:test';
import assert from 'node:assert/strict';
import {trimSpeechTail,connectSpeechSource} from '../static/presence-audio.js';
function buffer(seconds,channels=1,rate=24000){
 const samples=Array.from({length:channels},()=>new Float32Array(Math.round(seconds*rate)));
 return {sampleRate:rate,length:samples[0].length,numberOfChannels:channels,duration:samples[0].length/rate,getChannelData:channel=>samples[channel]};
}
function context(){return {currentTime:0,copies:0,createBuffer(channels,length,rate){this.copies++;return buffer(length/rate,channels,rate);}};}
function tone(audio,start,end,amplitude=.1,channel=0){
 const samples=audio.getChannelData(channel);
 for(let i=Math.round(start*audio.sampleRate);i<Math.round(end*audio.sampleRate);i++)samples[i]=amplitude*Math.sin(2*Math.PI*3100*i/audio.sampleRate);
}

test('only the confirmed trailing quiet is shortened, with active PCM and leading quiet unchanged',()=>{
 const input=buffer(1.4),ctx=context();tone(input,.05,1.1);
 const output=trimSpeechTail(ctx,input);
 assert.notEqual(output,input);assert.equal(output.sampleRate,input.sampleRate);
 assert.ok(output.duration>=1.18&&output.duration<=1.22);
 assert.deepEqual(output.getChannelData(0),input.getChannelData(0).subarray(0,output.length));
 assert.ok(input.length-output.length<=Math.floor(.35*input.sampleRate));
 assert.equal(ctx.copies,1);
});

test('quiet fricatives and short peaks in either channel remain with a full safety margin',()=>{
 const input=buffer(1.5,2),ctx=context();tone(input,.05,.9,.1,0);
 tone(input,.9,1.13,10**(-54/20)*Math.SQRT2,1);
 // A short peak would fall below a 20 ms RMS gate; preserve it in either channel.
 const peak=Math.round(1.16*input.sampleRate);input.getChannelData(1)[peak]=10**(-54/20);
 const output=trimSpeechTail(ctx,input);
 assert.ok(output.duration>=1.24,'at least 80 ms remains after the final quiet peak');
 for(let channel=0;channel<2;channel++)assert.deepEqual(output.getChannelData(channel),input.getChannelData(channel).subarray(0,output.length));
});

test('all-silent, uncertain, non-finite, short and already-tight clips return the same buffer',()=>{
 for(const input of [buffer(.5),buffer(.04),buffer(.5)]){
  const ctx=context();assert.equal(trimSpeechTail(ctx,input),input);
  assert.equal(ctx.copies,0);
 }
 const tight=buffer(.7);tone(tight,0,.66);assert.equal(trimSpeechTail(context(),tight),tight);
 const invalid=buffer(.5);invalid.getChannelData(0).fill(NaN);assert.equal(trimSpeechTail(context(),invalid),invalid);
 const veryLongQuiet=buffer(2);tone(veryLongQuiet,0,1);assert.equal(trimSpeechTail(context(),veryLongQuiet),veryLongQuiet,'no active window within the bounded search means leave it alone');
});

test('trimming is capped and adds no gain automation or duplicate edge fades',()=>{
 const input=buffer(1.5),ctx=context();tone(input,.1,1.07);
 ctx.createGain=()=>{assert.fail('tail trimming must not create another envelope');};
 const output=trimSpeechTail(ctx,input);assert.ok(input.duration-output.duration<=.35+1e-9);
 // Existing source lifecycle still owns exactly one attack/release envelope.
 const points=[],gain={gain:{setValueAtTime:(value,time)=>points.push([value,time]),linearRampToValueAtTime:(value,time)=>points.push([value,time])},connect(){}};
 connectSpeechSource({currentTime:0,createGain:()=>gain},{buffer:output,connect(){}},{});
 assert.equal(points.length,4);assert.equal(points.at(-1)[1],output.duration);
 assert.equal(points[0][0],0);assert.equal(points.at(-1)[0],0);
});
