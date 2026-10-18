'use strict';
// Synthetic fixtures only. No browser, device, model, mail or network request.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const sourcePath=path.join(__dirname,'../daily-board.js');
const load=vm.runInThisContext('(function(module){'+fs.readFileSync(sourcePath,'utf8')+'\n;return module.exports;})',{filename:sourcePath});
const {mount,viewModel,renderBoard,createNewsCache,safeURL,when}=load({exports:{}});
const tick=()=>new Promise(setImmediate);
const deferred=()=>{let resolve;const promise=new Promise(done=>resolve=done);return {promise,resolve};};
const response={items:[{title:'Public fixture headline',url:'https://example.invalid/story',source:'Fixture publisher',published_at:'2026-10-18T12:00:00Z'}],sources:{'Fixture publisher':'connected'},checked_at:1792324800};

test('absent personal sources stay unknown and do not invent an empty calendar or connected accounts',()=>{
 const model=viewModel({}, {state:'deferred'}),html=renderBoard(model);
 assert.equal(model.tasksKnown,false);
 assert.ok(model.connectionRows.every(row=>row.state==='unknown'));
 assert.match(html,/Calendar has not been read on this board/);
 assert.match(html,/saved tasks will appear/);
 assert.doesNotMatch(html,/No appointments today|All accounts connected|£|guaranteed|profit/i);
});

test('only supplied open tasks and genuinely dated agenda are displayed, with dated priorities',()=>{
 const model=viewModel({brief:{checked_at:'2026-10-18T12:00:00Z',tasks:[{title:'Open fixture task',area:'Personal',done:false},{title:'Finished fixture',done:true}],source_read_status:{tasks:{state:'stale_cache',read_at:'2026-10-17T12:00:00Z'}},plan:{as_of:'2026-09-28',priorities:[{title:'Saved fixture priority',next:'Review its date'}]},calendar:{state:'connected',items:[{title:'Current fixture activity',due:'2026-10-19',timing:'Upcoming'},{title:'Historical fixture activity',timing:'Historical - review date'}]}}});
 const html=renderBoard(model);
 assert.equal(model.tasks.length,1);assert.equal(model.appointments.length,1);
 assert.match(html,/Earlier saved copy/);assert.match(html,/Open fixture task/);assert.match(html,/Current fixture activity/);
 assert.doesNotMatch(html,/Finished fixture|Historical fixture activity/);
 assert.match(html,/Saved priorities · 28 Sept? 2026/);
 assert.doesNotMatch(when('2026-10-19'),/00:00|01:00/,'A date-only activity must not acquire an invented time');
});

test('unavailable task fallback is not called a clear task list',()=>{
 const html=renderBoard(viewModel({brief:{tasks:[],source_read_status:{tasks:{state:'unavailable'}}}}));
 assert.match(html,/Saved tasks could not be read/);
 assert.doesNotMatch(html,/task list is clear/);
});

test('mail verification counts and Mac permission states stay separate from model availability',()=>{
 const model=viewModel({brief:{services:{services:[{id:'ollama',state:'online'}]}},connections:{apple:{summary:{verified_mailboxes:1,registered_mailboxes:5},capabilities:{mac_messages:{state:'action_needed'}}},system:{ai:{provider:'openai',state:'configured_unverified'}}}});
 assert.equal(model.connectionRows[0].detail,'1 of 5 inboxes verified');
 assert.equal(model.connectionRows[1].state,'setup');
 assert.equal(model.connectionRows[2].state,'unknown');
 assert.match(model.connectionRows[2].detail,/not tested/);
});

test('headline selection retains source dates, balances publishers and rejects unsafe links',()=>{
 const news={state:'available',data:{...response,items:[{title:'Unsafe fixture',url:'javascript:alert(1)',source:'Publisher'},{title:'<img src=x onerror=bad()>',url:'https://example.invalid/one',source:'<script>source</script>',published_at:'2026-10-18T12:00:00Z'},{title:'Second fixture',url:'https://example.invalid/two',source:'Publisher'},{title:'Third fixture',url:'https://example.invalid/three',source:'Publisher'},{title:'Fourth fixture',url:'https://example.invalid/four',source:'Publisher'}],sources:{'<script>source</script>':'cached_unavailable','Publisher':'connected'}}};
 const model=viewModel({},news),html=renderBoard(model);
 assert.equal(model.headlines.length,3);
 assert.match(html,/&lt;img/);assert.match(html,/&lt;script&gt;source/);assert.match(html,/Saved feed copy/);
 assert.doesNotMatch(html,/<img|<script|javascript:|Unsafe fixture|Fourth fixture/);
 assert.equal(safeURL('https://user:pass@example.invalid/private'),null);
 assert.equal(safeURL('http://example.invalid/story'),null);
});

test('one shared read is cached for60seconds across dashboard rerenders without polling',async()=>{
 let now=0,calls=0;const cache=createNewsCache({now:()=>now}),api=async(path,body,options)=>{calls++;assert.equal(path,'/v1/workspace/news-feeds');assert.equal(body,undefined);assert.ok(options.signal instanceof AbortSignal);return response;};
 await Promise.all([cache.read(api),cache.read(api)]);assert.equal(calls,1);
 now=59999;assert.equal((await cache.read(api)).cached,true);assert.equal(calls,1);
 now=60000;await cache.read(api);assert.equal(calls,2);
});

test('one disappearing board cannot abort another active consumer of the same read',async()=>{
 const cache=createNewsCache(),gate=deferred(),first=new AbortController(),second=new AbortController();let calls=0,upstream;
 const api=(_path,_body,options)=>{calls++;upstream=options.signal;return gate.promise;};
 const a=cache.read(api,{signal:first.signal}),b=cache.read(api,{signal:second.signal});await tick();first.abort();
 assert.equal((await a).state,'deferred');assert.equal(upstream.aborted,false);
 gate.resolve(response);assert.equal((await b).state,'available');assert.equal(calls,1);
});

test('eight-second deadline aborts and caches one failed read without a retry storm',async()=>{
 let timeout,calls=0,signal;const cache=createNewsCache({delay:(fn,ms)=>{assert.equal(ms,8000);timeout=fn;return 1;},cancel(){}});
 const api=(_path,_body,options)=>{calls++;signal=options.signal;return new Promise(()=>{});};
 const pending=cache.read(api);await tick();timeout();const failed=await pending;
 assert.equal(failed.state,'unavailable');assert.equal(signal.aborted,true);
 assert.equal((await cache.read(api)).state,'unavailable');assert.equal(calls,1);
});

function host({hidden=false,companion='workspace'}={}){
 const listeners=new Map(),events=new Map();
 const document={hidden,body:{dataset:{companion,companionHidden:'false'}},activeElement:null,addEventListener:(name,fn)=>listeners.set(name,fn),removeEventListener:name=>listeners.delete(name)};
 const target={ownerDocument:document,isConnected:true,hidden:false,innerHTML:'',classList:{add(){}},setAttribute(){},closest(){return null;},contains(){return false;},querySelector(){return null;},addEventListener:(name,fn)=>events.set(name,fn),removeEventListener:name=>events.delete(name),replaceChildren(){this.innerHTML='';}};
 return {target,document,listeners,events};
}

test('hidden and companion dashboards defer news until visible; updates reuse the single initial read',async()=>{
 for(const initial of [{hidden:true},{companion:'icon'}]){
  const h=host(initial);let calls=0;
  const board=mount(h.target,{api:async()=>{calls++;return response;}});
  await tick();assert.equal(calls,0);assert.match(h.target.innerHTML,/return to the dashboard/);
  h.document.hidden=false;h.document.body.dataset.companion='workspace';h.listeners.get('visibilitychange')();await tick();
  assert.equal(calls,1);assert.match(h.target.innerHTML,/Public fixture headline/);
  board.update({brief:{tasks:[]}});board.update({snapshot:{}});await tick();assert.equal(calls,1);
  board.destroy();assert.equal(h.listeners.size,0);assert.equal(h.events.size,0);assert.equal(h.target.innerHTML,'');
 }
});

test('destroying a board aborts its pending read and late results cannot repopulate it',async()=>{
 const h=host(),gate=deferred();let signal;
 const board=mount(h.target,{api:(_path,_body,options)=>{signal=options.signal;return gate.promise;}});
 await tick();board.destroy();assert.equal(signal.aborted,true);gate.resolve(response);await tick();
 board.update({brief:{tasks:[{title:'Must not reappear'}]}});assert.equal(h.target.innerHTML,'');
});
