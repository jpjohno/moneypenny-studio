import test from 'node:test';
import assert from 'node:assert/strict';
import {renderProfile,StageActivity} from '../static/render-budget.js';

test('retina rendering caps real pixel area and embedded passes without losing active frame rate',()=>{
 const desktop=renderProfile({pixelRatio:2,embedded:true});
 assert.equal(desktop.pixelRatio,1.25);assert.equal(desktop.pixelRatioScale,.625);
 assert.equal(desktop.activeFPS,30);assert.equal(desktop.idleFPS,15);assert.equal(desktop.shadows,false);
 const mobile=renderProfile({pixelRatio:3,narrow:true});
 assert.equal(mobile.pixelRatio,1);assert.equal(mobile.activeFPS,24);assert.equal(mobile.idleFPS,12);
 assert.ok((desktop.pixelRatio/2)**2<.4,'Desktop retina canvas draws under40% of its previous pixels');
});
test('offscreen, parent-hidden and background stages stop only graphics and resume once',()=>{
 let starts=0,suspends=0,cancels=0;
 const head={opt:{},armature:{},isRunning:true,_raf:7,audioCtx:{suspend(){suspends++;}},stop(){throw new Error('Stopping TalkingHead would also suspend voice');},start(){starts++;this.isRunning=true;this._raf=8;}};
 const activity=new StageActivity(head,renderProfile({embedded:true}),{cancelFrame(){cancels++;}});
 activity.update({inView:false});activity.update({inView:false});
 assert.equal(head.isRunning,false);assert.equal(cancels,1);assert.equal(suspends,0);
 activity.update({inView:true,parentVisible:false});assert.equal(starts,0);
 activity.update({parentVisible:true});assert.equal(starts,1);
 activity.update({active:true});assert.equal(head.animFrameDur,1000/30);assert.equal(starts,1);
 activity.update({documentVisible:false});assert.equal(head.isRunning,false);assert.equal(suspends,0);
 activity.update({documentVisible:true});assert.equal(starts,2);
});
test('the default frame canceller retains the browser global receiver',()=>{
 const previous=globalThis.cancelAnimationFrame;let cancelled=null;
 globalThis.cancelAnimationFrame=function(frame){assert.equal(this,globalThis);cancelled=frame;};
 try{
  const head={opt:{},armature:{},isRunning:true,_raf:42};
  const activity=new StageActivity(head,renderProfile());activity.update({parentVisible:false});
  assert.equal(cancelled,42);assert.equal(head.isRunning,false);
 }finally{globalThis.cancelAnimationFrame=previous;}
});

test('camera interaction stays at active cadence independently of speech and idle motion',()=>{
 const head={opt:{},armature:{},isRunning:true};
 const activity=new StageActivity(head,renderProfile());
 assert.equal(activity.status().fps,15);
 activity.update({interacting:true});activity.update({active:false});
 assert.equal(activity.status().fps,30);
 activity.update({interacting:false});assert.equal(activity.status().fps,15);
});
