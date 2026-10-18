import test from 'node:test';
import assert from 'node:assert/strict';
import { SpeechSegmenter,SpeechPipeline,controlIntent,pcmWav } from '../static/live.js';

test('speech is available before the model finishes, without stage directions',()=>{
  const parts=[];const segmenter=new SpeechSegmenter(x=>parts.push(x));
  segmenter.update('*smiles');assert.deepEqual(parts,[]);
  segmenter.update('*smiles* Hello, James. ');assert.deepEqual(parts,['Hello, James.']);
  segmenter.update('*smiles* Hello, James. How can I help',false);assert.equal(parts.length,1);
  segmenter.update('*smiles* Hello, James. How can I help you?',true);assert.deepEqual(parts,['Hello, James.','How can I help you?']);
});
test('long first phrases flush without waiting for a complete answer',()=>{
  const parts=[],s=new SpeechSegmenter(x=>parts.push(x));
  s.update('A longer explanation can still begin speaking before the full answer arrives because the first phrase is ready to say');
  assert.equal(parts.length,1);
});
test('preparation prefetches the next clip while the first one plays',async()=>{
  const events=[];let release;const blocked=new Promise(resolve=>release=resolve);
  const pipeline=new SpeechPipeline(async text=>{events.push('prepare '+text);return text;},async text=>{events.push('play '+text);if(text==='first')await blocked;});
  pipeline.push('first');pipeline.push('second');
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(events.includes('prepare second'));assert.ok(!events.includes('play second'));
  release();await pipeline.done();assert.equal(events.at(-1),'play second');
});
test('a cancelled preparation never starts playback',async()=>{
  let played=false;const pipeline=new SpeechPipeline(async()=>{throw new DOMException('Stopped','AbortError');},async()=>{played=true;});
  pipeline.push('old');await assert.rejects(pipeline.done());assert.equal(played,false);
});
test('quiet and timed follow-ups are local controls',()=>{
  assert.deepEqual(controlIntent('Be quiet for ten minutes'),{type:'quiet',delay:600});
  assert.equal(controlIntent('Ask me in ten minutes if I have finished').delay,600);
  assert.equal(controlIntent('Ask me in ten minutes if I have finished').type,'reminder');
  assert.equal(controlIntent('resume').type,'resume');assert.equal(controlIntent('What time is it?'),null);
});
test('microphone segments are encoded as bounded mono PCM',()=>{
  const wav=pcmWav(new Float32Array([-1,0,1]));const data=new DataView(wav);
  assert.equal(data.getUint32(24,true),16000);assert.equal(data.getInt16(44,true),-32768);assert.equal(data.getInt16(48,true),32767);
});
