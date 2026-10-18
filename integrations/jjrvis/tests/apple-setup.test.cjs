/* Isolated capability and media lifecycle checks. No browser or hardware access. */
'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const sourcePath=path.join(__dirname,'../apple-setup.js');
const source=fs.readFileSync(sourcePath,'utf8');
// Exercise this browser script in either a CommonJS or ES-module parent repo.
const load=vm.runInThisContext('(function(module){'+source+'\n;return module.exports;})',{filename:sourcePath});
const {models,card,mediaController,labels,docs}=load({exports:{}});

test('opening module never requests permissions, starts sign-in or reads private content',()=>{
  let network=0,grants=0,created=0;
  const context={window:{fetch(){network++;throw new Error('Unexpected request');},navigator:{mediaDevices:{getUserMedia(){grants++;throw new Error('Unexpected grant');}}},document:{createElement(){created++;}}}};
  vm.runInNewContext(source,context);
  assert.equal(typeof context.window.JJAppleSetup.open,'function');
  assert.deepEqual({network,grants,created},{network:0,grants:0,created:0});
});

test('capability model reflects actual checks without turning iCloud Mail into general Apple access',()=>{
  const view=models({checked_at:'2026-10-18T00:00:00Z',accounts:[{provider:'icloud',state:'ready'}],capabilities:{mac_mail:{state:'ready',count:27},mac_messages:{state:'action_needed'},iphone_web_app:{state:'ready_to_pair',https_verified:true}}},{ai:{state:'ready',cloud:{credential_configured:true}}},{media:true,folder:false});
  assert.equal(view.internet[0][1],'ready');
  assert.equal(view.internet[1][1],'ready');
  assert.equal(view.mac[0][1],'ready');
  assert.match(view.mac[0][2],/27 locally stored/);
  assert.equal(view.mac[1][1],'action_needed');
  assert.equal(view.mac[2][1],'action_needed','Unsupported folder picker must not be called connected');
  assert.equal(view.icloud[0][1],'ready');
  for(const title of ['iCloud Drive','iCloud Photos','Apple Health','Apple Home'])assert.equal(view.icloud.find(row=>row[0]===title)[1],'not_connected');
  assert.equal(view.icloud.find(row=>row[0]==='Sign in with Apple')[1],'not_implemented');
  assert.equal(view.iphone.find(row=>row[0]==='Native iPhone controls')[1],'unsupported');
  assert.equal(view.ai[1][1],'configured_unverified','Saved cloud key is not proof of a live paid connection');
});

test('missing readiness stays unavailable and unsupported media does not claim permission',()=>{
  const view=models({}, {}, {media:false,folder:false});
  assert.equal(view.internet[0][1],'unavailable');
  assert.equal(view.ai[0][1],'unavailable');
  assert.equal(view.icloud[0][1],'unavailable');
  assert.deepEqual(view.media.map(row=>row[1]),['unsupported','unsupported']);
  assert.equal(view.iphone[0][1],'unavailable');
  const installed=models({}, {}, {standalone:true});
  assert.equal(installed.iphone[0][1],'ready','Only this device’s actual installed display mode counts');
});

test('iCloud provider failure is not mislabeled as missing sign-in and public search is offered only on request',()=>{
  for(const state of ['connected','ready'])assert.equal(models({accounts:[{provider:'icloud',state}]}).icloud[0][1],'ready');
  assert.equal(models({accounts:[{provider:'icloud',state:'unavailable'}]}).icloud[0][1],'unavailable');
  assert.equal(models({accounts:[{provider:'icloud',state:'action_needed',reason:'sign_in_needed'}]}).icloud[0][1],'sign_in_needed');
  const view=models();
  assert.equal(view.internet.find(row=>row[0]==='Public web search')[1],'available');
  assert.equal(view.internet.find(row=>row[0]==='Signed-in websites')[1],'not_connected');
  assert.equal(models({}, {ai:{provider:'openai',state:'configured_unverified'}}).ai[0][1],'not_connected');
});

test('capability rendering escapes account names, state and arbitrary service text',()=>{
  const result=card('<img src=x onerror=attack()>','unsupported','<script>bad()</script>',{id:'" onclick="attack()',label:'<button>bad</button>'});
  assert.ok(result.includes('Not supported here'));
  assert.ok(result.includes('&lt;img'));
  assert.ok(!result.includes('<img'));
  assert.ok(!result.includes('<script>'));
  assert.ok(!result.includes('data-apple-action="" onclick='));
  assert.ok(result.includes('&quot; onclick=&quot;'));
  assert.equal(card('No native access','unsupported','Not implemented').includes('data-apple-action'),false);
});

test('official Apple guides are linked directly and no provider sign-in secret appears in links',()=>{
  assert.equal(new URL(docs.install).hostname,'support.apple.com');
  assert.equal(new URL(docs.password).hostname,'support.apple.com');
  Object.values(docs).forEach(url=>{assert.equal(new URL(url).protocol,'https:');assert.equal(new URL(url).search,'');});
  assert.equal(labels.available,'Available on request');
  assert.equal(labels.not_connected,'Not connected');
});

test('microphone test starts only when explicitly called and stops its own tracks',async()=>{
  const requests=[],updates=[],tracks=[{stops:0,stop(){this.stops++;}}],timers=[];
  const controller=mediaController({getUserMedia:async constraints=>{requests.push(constraints);return {getTracks:()=>tracks};}},message=>updates.push(message),null,{delay:(fn,ms)=>{timers.push({fn,ms});return 1;},cancel(){}});
  assert.equal(requests.length,0);
  await controller.start('mic');
  assert.deepEqual(requests,[{audio:true,video:false}]);
  assert.match(updates.at(-1),/Nothing is recorded/);
  assert.equal(timers[0].ms,15000);
  controller.stop();
  assert.equal(tracks[0].stops,1);
  assert.match(updates.at(-1),/checks are off/);
});

test('camera preview is local and automatically releases tracks',async()=>{
  const calls=[],track={stops:0,stop(){this.stops++;}},preview={srcObject:null,play(){calls.push('play');return Promise.resolve();}};
  let timeout;
  const stream={getTracks:()=>[track]};
  const controller=mediaController({getUserMedia:async constraints=>{assert.deepEqual(constraints,{audio:false,video:true});return stream;}},()=>{},preview,{delay:fn=>{timeout=fn;return 1;},cancel(){}});
  await controller.start('camera');
  assert.equal(preview.srcObject,stream);
  assert.deepEqual(calls,['play']);
  timeout();
  assert.equal(track.stops,1);
  assert.equal(preview.srcObject,null);
});

test('closing while browser permission is pending cannot turn the camera on later',async()=>{
  let resolve;const updates=[],track={stops:0,stop(){this.stops++;}},preview={srcObject:null,play(){assert.fail('Closed preview must not play');}};
  const controller=mediaController({getUserMedia:()=>new Promise(done=>resolve=done)},message=>updates.push(message),preview);
  const pending=controller.start('camera');
  controller.stop(false);
  resolve({getTracks:()=>[track]});
  await pending;
  assert.equal(track.stops,1);
  assert.equal(preview.srcObject,null);
  assert.ok(!updates.some(message=>message.includes('preview is on')));
});

test('permission refusal and missing APIs report setup limits without falling back to recording',async()=>{
  const updates=[];
  const denied=mediaController({getUserMedia:async()=>{const error=new Error();error.name='NotAllowedError';throw error;}},message=>updates.push(message),null);
  await denied.start('mic');
  assert.match(updates.at(-1),/not allowed/);
  const unavailable=mediaController(null,message=>updates.push(message),null);
  await unavailable.start('camera');
  assert.match(updates.at(-1),/cannot request device access/);
});
