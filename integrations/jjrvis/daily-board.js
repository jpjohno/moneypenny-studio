/* A read-only daily view. Supplied personal data stays on this mounted board. */
(function(root){
 'use strict';
 const NEWS_TTL=60000,NEWS_TIMEOUT=8000;
 const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
 const safeURL=value=>{try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password?url.href:null;}catch{return null;}};
 const stamp=value=>{if(value===null||value===undefined||value==='')return null;const date=new Date(typeof value==='number'?value*1000:value);return Number.isFinite(date.getTime())?date:null;};
 const when=value=>{const date=stamp(value);if(!date)return 'Time not supplied';return typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)?date.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):date.toLocaleString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});};
 const statusText={read_now:'Saved on this Mac',cached:'Saved on this Mac',stale_cache:'Earlier saved copy',unavailable:'Currently unavailable'};
 function createNewsCache({now=Date.now,delay=setTimeout,cancel=clearTimeout}={}){
  const entries=new WeakMap();
  async function read(api,{signal}={}){
   if(signal?.aborted)return {state:'deferred'};
   let entry=entries.get(api);
   if(entry?.result&&now()-entry.attempt<NEWS_TTL)return {...entry.result,cached:true};
   if(!entry?.pending||entry.controller.signal.aborted){
    entry={controller:new AbortController(),consumers:new Set(),pending:null,result:null,attempt:now()};entries.set(api,entry);
    const current=entry;
    current.pending=(async()=>{
     let timer;
     try{
      const deadline=new Promise((_,reject)=>{timer=delay(()=>{current.timedOut=true;current.controller.abort();reject(new Error('News deadline'));},NEWS_TIMEOUT);});
      const value=await Promise.race([Promise.resolve().then(()=>api('/v1/workspace/news-feeds',undefined,{signal:current.controller.signal})),deadline]);
      if(!value||!Array.isArray(value.items)||!value.sources||typeof value.sources!=='object'||Array.isArray(value.sources))throw new Error('Invalid news response');
      current.result={state:'available',data:value,receivedAt:now(),cached:false};
     }catch{
      if(current.controller.signal.aborted&&!current.timedOut)return {state:'deferred'};
      current.result={state:'unavailable',receivedAt:now(),cached:false};
     }finally{if(timer)cancel(timer);current.pending=null;}
     return current.result;
    })();
   }
   const token=Symbol('board');entry.consumers.add(token);
   const leave=()=>{entry.consumers.delete(token);if(!entry.consumers.size&&entry.pending)entry.controller.abort();};
   let abort;
   const cancelled=new Promise(resolve=>{abort=()=>{leave();resolve({state:'deferred'});};signal?.addEventListener('abort',abort,{once:true});});
   try{return await Promise.race([entry.pending,cancelled]);}
   finally{signal?.removeEventListener('abort',abort);leave();}
  }
  return {read};
 }
 const newsCache=createNewsCache();
 function viewModel({brief,snapshot,connections}={},news={state:'loading'}){
  const tasksRead=brief?.source_read_status?.tasks;
  const taskSource=Array.isArray(brief?.tasks)?brief.tasks:Array.isArray(snapshot?.tasks)?snapshot.tasks:null;
  const tasksKnown=taskSource!==null&&tasksRead?.state!=='unavailable';
  const tasks=(taskSource||[]).filter(item=>item&&item.done!==true&&typeof item.title==='string'&&item.title.trim()).slice(0,4);
  const calendar=brief?.calendar||snapshot?.calendar;
  const agenda=calendar&&Array.isArray(calendar.items)?calendar.items:calendar&&Array.isArray(calendar.events)?calendar.events:null;
  const appointments=(agenda||[]).filter(item=>item&&item.timing!=='Historical - review date'&&typeof item.title==='string').slice(0,2);
  const apple=connections?.apple||(connections?.accounts||connections?.capabilities?connections:null);
  const system=connections?.system||(connections?.ai?connections:null);
  const service=(brief?.services?.services||[]).find(item=>item.id==='ollama');
  const summary=apple?.summary;
  const validCounts=Number.isSafeInteger(summary?.verified_mailboxes)&&Number.isSafeInteger(summary?.registered_mailboxes)&&summary.verified_mailboxes>=0&&summary.registered_mailboxes>=summary.verified_mailboxes;
  const connectionRows=[];
  connectionRows.push({name:'Email accounts',state:validCounts&&summary.verified_mailboxes>0?'ready':apple?'setup':'unknown',detail:validCounts?`${summary.verified_mailboxes} of ${summary.registered_mailboxes} inboxes verified`:'Open connections for each account’s status'});
  const messages=apple?.capabilities?.mac_messages;
  connectionRows.push({name:'Mac Messages',state:messages?.state==='ready'?'ready':messages?'setup':'unknown',detail:messages?.state==='ready'?'Local access available · cloud sync not verified':messages?'Mac access needs setup':'Not checked on this board'});
  const ai=system?.ai;
  const assistantState=ai?(ai.state==='ready'?'ready':ai.state==='configured_unverified'?'unknown':'unavailable'):service?(service.state==='online'?'ready':'unavailable'):'unknown';
  connectionRows.push({name:'Assistant',state:assistantState,detail:ai?.state==='ready'?'Selected model available':ai?.state==='configured_unverified'?'Cloud service configured · not tested':!ai&&service?.state==='online'?'Local model service available':ai||service?'Connection needs attention':'Waiting for the workspace check'});
  const priorities=(brief?.plan?.priorities||[]).filter(item=>item&&typeof item.title==='string').slice(0,2);
  const rows=Array.isArray(news.data?.items)?news.data.items:[],seen=new Set(),counts=new Map(),headlines=[];
  const sorted=[...rows].sort((a,b)=>(stamp(b?.published_at)?.getTime()||0)-(stamp(a?.published_at)?.getTime()||0));
  for(const row of sorted){
   const url=safeURL(row?.url),source=String(row?.source||'Publisher');
   if(!url||typeof row?.title!=='string'||!row.title.trim()||seen.has(url)||(counts.get(source)||0)>=2)continue;
   seen.add(url);counts.set(source,(counts.get(source)||0)+1);
   headlines.push({...row,url,source,sourceState:String(news.data?.sources?.[source]||'unknown')});
   if(headlines.length===5)break;
  }
  return {tasks,tasksKnown,tasksRead,taskChecked:tasksRead?.read_at||brief?.checked_at,appointments,calendar,priorities,planChecked:brief?.plan?.as_of||brief?.source_read_status?.plan?.read_at,connectionRows,connectionChecked:apple?.checked_at||system?.checked_at||brief?.services?.checked_at,headlines,news,newsChecked:news.data?.checked_at};
 }
 function button(label,go){return `<button type="button" class="daily-board-button" data-daily-go="${go}" data-daily-focus="${go}">${label}<span aria-hidden="true">↗</span></button>`;}
 function renderBoard(model){
  const tasks=model.tasksKnown?(model.tasks.length?`<ul class="daily-board-tasks">${model.tasks.map(task=>`<li><span class="daily-task-mark" aria-hidden="true"></span><div><strong>${esc(task.title)}</strong><small>${esc(task.area||'Saved task')}</small></div></li>`).join('')}</ul>`:'<p class="daily-board-empty">Your saved task list is clear. Add a next step whenever you’re ready.</p>'):`<p class="daily-board-empty">${model.tasksRead?.state==='unavailable'?'Saved tasks could not be read. Open your plan to check them.':'Your saved tasks will appear when the workspace briefing arrives.'}</p>`;
  const agenda=model.appointments.length?model.appointments.map(item=>`<li><strong>${esc(item.title)}</strong><small>${esc(item.timing||'Recorded date')} · ${esc(when(item.due||item.at||item.start))}</small></li>`).join(''):null;
  const news=model.headlines.length?`<ol class="daily-board-headlines">${model.headlines.map((item,index)=>`<li><span class="daily-news-index" aria-hidden="true">${String(index+1).padStart(2,'0')}</span><div><a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a><p class="daily-news-meta">${esc(item.source)} · <time>${esc(when(item.published_at))}</time>${item.sourceState.startsWith('cached')?' · Saved feed copy':''}${item.sourceState.startsWith('unavailable')?' · Feed refresh unavailable':''}</p></div></li>`).join('')}</ol>`:`<p class="daily-board-empty">${model.news.state==='loading'?'Bringing your headlines together…':model.news.state==='deferred'?'Headlines will load when you return to the dashboard.':model.news.state==='unavailable'?'Headlines could not be read just now. Open News & TV when you want to try again.':'No usable headlines were returned by the connected feeds.'}</p>`;
  const sourceStates=Object.values(model.news.data?.sources||{}),sourceCount=sourceStates.filter(state=>state==='connected').length;
  const feedNote=model.newsChecked?`Feeds checked ${when(model.newsChecked)}${sourceCount?' · '+sourceCount+' publisher feeds available':''}`:model.news.state==='loading'?'One read from the existing news feeds':'No current feed check available';
  return `<header class="daily-board-heading"><div><p class="daily-board-eyebrow">A LITTLE CLARITY</p><h2>Your day, in view.</h2></div><p>What’s next. What matters. What’s connected.</p></header><div class="daily-board-grid"><article class="daily-board-card daily-board-today"><div class="daily-board-card-heading"><h3>Up next</h3><span class="daily-board-source">${esc(statusText[model.tasksRead?.state]||'Your saved tasks')}</span></div>${tasks}<p class="daily-board-stamp">${model.taskChecked?'Last read '+esc(when(model.taskChecked)):'Task check pending'}</p><div class="daily-board-agenda"><h4>Your agenda</h4>${agenda?`<ul>${agenda}</ul>`:`<p>${model.calendar?.state==='unavailable'?'The calendar connection is unavailable.':model.calendar?'No currently dated items were supplied.':'Calendar has not been read on this board.'}</p>`}</div><div class="daily-board-actions">${button('Open your plan','plan')}${button('Open agenda','junomo')}</div></article><article class="daily-board-card daily-board-news"><div class="daily-board-card-heading"><h3>In the headlines</h3><span class="daily-board-source">Publisher reports</span></div>${news}<p class="daily-board-stamp" role="status">${esc(feedNote)}</p>${button('Open News & TV','news')}</article><article class="daily-board-card daily-board-connections"><div class="daily-board-card-heading"><div><h3>Your workspace</h3><p class="daily-board-stamp">${model.connectionChecked?'Checked '+esc(when(model.connectionChecked)):'Waiting for connection details'}</p></div>${button('Connections','connections')}</div><ul class="daily-board-connection-list">${model.connectionRows.map(row=>`<li><span class="daily-connection-dot" data-state="${esc(row.state)}" aria-hidden="true"></span><div><strong>${esc(row.name)}</strong><small>${esc(row.detail)}</small></div><span class="daily-connection-state">${esc({ready:'Available',setup:'Setup needed',unknown:'Not checked',unavailable:'Unavailable'}[row.state])}</span></li>`).join('')}</ul>${model.priorities.length?`<details class="daily-board-priorities"><summary>Saved priorities${model.planChecked?' · '+esc(when(model.planChecked)):''}</summary><ul>${model.priorities.map(item=>`<li><strong>${esc(item.title)}</strong>${item.next?`<p>${esc(item.next)}</p>`:''}</li>`).join('')}</ul></details>`:''}</article></div>`;
 }
 async function defaultApi(path,_body,{signal}={}){const response=await root.fetch(path,{credentials:'same-origin',cache:'no-store',signal});if(!response.ok)throw new Error('News unavailable');return response.json();}
 function mount(target,options={}){
  const document=target.ownerDocument||root.document,api=options.api||defaultApi;
  let values={brief:options.brief,snapshot:options.snapshot,connections:options.connections},news={state:'loading'},destroyed=false,attempted=false,reading=false,controller=null;
  target.classList.add('jj-daily-board');target.setAttribute('aria-label','Your daily workspace');
  function visible(){const mode=document.body?.dataset?.companion;return !destroyed&&target.isConnected!==false&&!target.hidden&&!document.hidden&&!target.closest?.('[hidden]')&&(!mode||mode==='workspace')&&document.body?.dataset?.companionHidden!=='true';}
  function render(){if(destroyed)return;const focus=target.contains(document.activeElement)&&document.activeElement?.dataset?.dailyFocus;target.innerHTML=renderBoard(viewModel(values,news));if(['plan','news','junomo','connections'].includes(focus))target.querySelector(`[data-daily-focus="${focus}"]`)?.focus({preventScroll:true});}
  async function loadNews(){
   if(!visible()){if(!reading&&!attempted){news={state:'deferred'};render();}return;}
   if(attempted||reading)return;
   reading=true;controller=new AbortController();const current=controller;news={state:'loading'};render();
   try{const result=await newsCache.read(api,{signal:current.signal});if(destroyed||current.signal.aborted)return;if(result.state!=='deferred'){attempted=true;news=result;render();}}
   finally{reading=false;if(!attempted&&visible())loadNews();}
  }
  function activity(){if(!visible())controller?.abort();else loadNews();}
  function click(event){const item=event.target.closest?.('[data-daily-go]');if(!item||!target.contains(item))return;const go=item.dataset.dailyGo;if(go==='connections'&&root.JJAppleSetup?.open)root.JJAppleSetup.open({api});else if(['plan','news','junomo','connections'].includes(go))options.navigate?.(go);}
  target.addEventListener('click',click);document.addEventListener('visibilitychange',activity);root.addEventListener?.('jjrvis-companion-changed',activity);
  render();loadNews();
  return {update(next={}){if(destroyed)return;for(const key of ['brief','snapshot','connections'])if(key in next)values[key]=next[key];render();loadNews();},destroy(){if(destroyed)return;destroyed=true;controller?.abort();values={};news={state:'deferred'};target.removeEventListener('click',click);document.removeEventListener('visibilitychange',activity);root.removeEventListener?.('jjrvis-companion-changed',activity);target.replaceChildren();}};
 }
 root.JJDailyBoard={mount};
 if(typeof module!=='undefined'&&module.exports)module.exports={mount,viewModel,renderBoard,createNewsCache,safeURL,when};
})(typeof window!=='undefined'?window:globalThis);
