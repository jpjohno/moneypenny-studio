/* Scene drawers reuse the real workspace views. Opening a drawer is explicit;
   it does not create accounts, grant permission or request an AI answer. */
(function(root){
 'use strict';
 function mount(hub,options={}){
  const doc=hub.ownerDocument;
  const scene=hub.querySelector('.presence-scene');
  const decoration=doc.createElement('div');decoration.className='scene-depth';decoration.setAttribute('aria-hidden','true');
  decoration.innerHTML='<div class="scene-grid"></div><i class="scene-orbit scene-orbit-one"></i><i class="scene-orbit scene-orbit-two"></i><i class="scene-orbit scene-orbit-three"></i><span class="scene-cross scene-cross-one">＋</span><span class="scene-cross scene-cross-two">＋</span>';
  scene.prepend(decoration);
  const rail=doc.createElement('nav');rail.className='scene-tools';rail.setAttribute('aria-label','Overview panels');
  const names={brief:['01','Your day','Tasks & headlines'],weather:['02','Weather & sky','Forecast & sunset'],devices:['03','Map & journeys','Explore & plan a route'],assets:['04','Your circle','People, pets & vehicles']};
  for(const [key,[number,label,note]] of Object.entries(names)){
   const button=doc.createElement('button');button.type='button';button.dataset.sceneOpen=key;button.setAttribute('aria-expanded','false');button.setAttribute('aria-controls','scene-panel-'+key);
   button.innerHTML='<small>'+number+'</small><span><b>'+label+'</b><em>'+note+'</em></span><i aria-hidden="true">↗</i>';rail.append(button);
  }
  scene.append(rail);
  const drawer=doc.createElement('section');drawer.className='scene-drawer';drawer.hidden=true;drawer.setAttribute('role','region');drawer.setAttribute('aria-labelledby','scene-drawer-title');
  drawer.innerHTML='<header><div><p>YOUR WORKSPACE</p><h3 id="scene-drawer-title"></h3></div><button type="button" class="scene-drawer-close" aria-label="Close overview panel">Close <span aria-hidden="true">×</span></button></header>';
  const panes=new Map(),mounted=new Set();let active='',dead=false;
  for(const key of Object.keys(names)){const pane=doc.createElement('div');pane.id='scene-panel-'+key;pane.className='scene-pane scene-pane-'+key;pane.hidden=true;drawer.append(pane);panes.set(key,pane);}
  scene.append(drawer);
  function close(focus=true){
   if(!active)return;
   const button=rail.querySelector('[data-scene-open="'+active+'"]');
   panes.get(active).hidden=true;button.setAttribute('aria-expanded','false');active='';drawer.hidden=true;hub.classList.remove('scene-panel-open');
   options.onChange?.('');if(focus&&button.isConnected)button.focus();
  }
  function open(key){
   if(dead||!panes.has(key))return;
   if(active===key){close();return;}
   close(false);active=key;const pane=panes.get(key);pane.hidden=false;
   drawer.querySelector('h3').textContent=names[key][1];drawer.hidden=false;hub.classList.add('scene-panel-open');
   rail.querySelector('[data-scene-open="'+key+'"]').setAttribute('aria-expanded','true');
   if(!mounted.has(key)){mounted.add(key);if(key==='assets')mountAssets(pane,options);else options.mount?.(key,pane);}
   options.onChange?.(key);drawer.querySelector('.scene-drawer-close').focus({preventScroll:true});
  }
  const click=event=>{const button=event.target.closest('[data-scene-open]');if(button&&rail.contains(button))open(button.dataset.sceneOpen);};
  const escape=event=>{if(event.key==='Escape'&&active&&!doc.querySelector('dialog[open]')){event.preventDefault();close();}};
  rail.addEventListener('click',click);drawer.querySelector('button').onclick=()=>close();doc.addEventListener('keydown',escape);
  return {open,close,state:()=>active,destroy(){dead=true;close(false);doc.removeEventListener('keydown',escape);rail.removeEventListener('click',click);drawer.remove();rail.remove();decoration.remove();}};
 }
 function mountAssets(pane,options){
  const doc=pane.ownerDocument;
  pane.innerHTML='<p>Profiles for your people, pets and vehicles. Saving a profile does not grant location access.</p><div data-assets-list></div><form data-assets-form><label>Name<input name="name" required maxlength="80" placeholder="Who or what would you like to add?"></label><label>Type<select name="kind"><option value="person">Person</option><option value="pet">Pet</option><option value="vehicle">Vehicle</option><option value="place">Place</option><option value="device">Device</option></select></label><button>Save profile</button></form><p role="status" data-assets-status></p>';
  const list=pane.querySelector('[data-assets-list]'),status=pane.querySelector('[data-assets-status]');
  function draw(data){list.replaceChildren();for(const item of data.assets||[]){
   const article=doc.createElement('article'),title=doc.createElement('h4'),text=doc.createElement('p');title.textContent=item.name;text.textContent=item.kind+' · '+item.note;article.append(title,text);
   const button=doc.createElement('button');button.type='button';button.textContent=item.connection==='bmw'?'Review BMW reports':'Connections & pairing';button.onclick=()=>options.navigate?.('home');article.append(button);list.append(article);
  }}
  options.api('/v1/workspace/assets').then(draw).catch(()=>{status.textContent='Profiles are unavailable. Retry after checking the workspace connection.';});
  pane.querySelector('form').onsubmit=async event=>{event.preventDefault();const form=event.currentTarget,button=form.querySelector('button');button.disabled=true;try{draw(await options.api('/v1/workspace/assets',{name:form.elements.name.value,kind:form.elements.kind.value}));form.reset();status.textContent='Profile saved. Tracking remains off until a supported source is paired.';}catch(error){status.textContent=error.message;}finally{button.disabled=false;}};
 }
 // Read-only source cards. Feed text is displayed as text, never as instructions.
 function briefingCards(kind,data={}){
  const time=value=>{const d=new Date(typeof value==='number'?value*1000:value);return Number.isFinite(d.getTime())?d.toLocaleString('en-GB'):'Time unavailable';};
  const fallback=detail=>[{kind,title:kind==='mail'?'Your inbox':kind==='markets'?'Your markets':'Your headlines',detail,source:'Connection status',unavailable:true,view:['mail','messages','whatsapp'].includes(kind)?'communications':kind==='markets'?'trading':'news'}];
  if(kind==='news'){
   const rows=Array.isArray(data.items)?data.items:[],seen=new Set();
   const selected=rows.filter(item=>{if(!item.title||seen.has(item.url))return false;seen.add(item.url);return true;});
   selected.sort((a,b)=>(b.category==='local')-(a.category==='local'));
   return selected.slice(0,5).map(item=>({kind,title:String(item.title),detail:String(item.summary||'Open the source for the full report.'),source:String(item.source||'Publisher')+' · '+time(item.published_at),view:'news',url:item.url,image:newsImage(item.image),regional:item.category==='local'})).concat(selected.length?[]:fallback('No connected headlines were returned. Open News & TV to check the feeds.'));
  }
  if(kind==='markets'){
   const rows=(Array.isArray(data.markets)?data.markets:[]).slice(0,3);
   return rows.length?rows.map(item=>({kind,title:String(item.name||item.symbol||'Market'),detail:Number.isFinite(Number(item.price))&&item.price!==null&&item.price!==''?'Observed '+Number(item.price).toLocaleString('en-GB',{maximumFractionDigits:6})+' '+String(item.currency||''):'No usable price supplied.',source:String(item.state||data.state||'unverified')+' · '+time(item.observed_at),view:'trading'})):fallback(data.detail||'The broker quote feed is unavailable. Open Markets to check its connection.');
  }
  if(['mail','messages','whatsapp'].includes(kind)){
   if(!['connected','available'].includes(data.state))return fallback(data.detail||'The inbox connection is unavailable. Open Communications to check access.');
   const rows=(Array.isArray(data.messages)?data.messages:[]).slice(0,8);
   return rows.length?rows.map(item=>({kind,title:String(item.subject||item.conversation_name||item.participant||'No subject'),detail:String(item.text||item.preview||item.body||'No stored text is available. Open the original app for attachments.'),source:String(item.sender||item.participant||item.account||'Junomo inbox')+' · '+time(item.received_at||item.date||data.checked_at),view:'communications',private:true,messageId:item.id,accountKey:item.accountKey||'',bodyPath:kind==='mail'?(item.accountKey?'/v1/workspace/native/mail/message?account='+encodeURIComponent(item.accountKey)+'&id='+encodeURIComponent(item.id):'/v1/workspace/mail/message?id='+encodeURIComponent(item.id)):'',scope:kind==='mail'?'Email preview':'Mac-synced text'})):fallback('No messages were returned by the connected Junomo inbox. Other inboxes have not been checked.');
  }
  return fallback('Source unavailable.');
 }
 function newsImage(value){try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password&&['ichef.bbci.co.uk','e3.365dm.com','i.guim.co.uk','s.france24.com','a57.foxnews.com','static.foxnews.com'].includes(url.hostname)?url.href:'';}catch{return '';}}
 function mountBriefing(hub,options={}){
  const doc=hub.ownerDocument,scene=hub.querySelector('.presence-scene');
  const launch=doc.createElement('button');launch.type='button';launch.className='scene-brief-launch';launch.textContent='✦ Brief me';launch.setAttribute('aria-expanded','false');
  const panel=doc.createElement('section');panel.className='scene-briefing';panel.hidden=true;panel.setAttribute('aria-label','Guided briefing');
  panel.innerHTML='<header><span>YOUR BRIEFING</span><button type="button" data-brief-close aria-label="Close briefing">×</button></header><nav aria-label="Briefing topics"><button type="button" data-brief-topic="news">News</button><button type="button" data-brief-topic="markets">Markets</button><button type="button" data-brief-topic="mail">Email</button><button type="button" data-brief-topic="messages">Messages</button><button type="button" data-brief-topic="whatsapp">WhatsApp</button></nav><div class="scene-brief-card" aria-live="polite" aria-atomic="true"></div><div class="scene-brief-controls"><button type="button" data-brief-pause>Pause cards</button><button type="button" data-brief-next>Next item →</button><button type="button" data-brief-next-topic>Next topic</button><button type="button" data-brief-more>More ↗</button></div><label class="scene-brief-narration"><input type="checkbox" data-brief-narration> Read card summaries aloud</label><small class="scene-brief-progress" role="status"></small>';
  scene.append(launch,panel);
  const topics=['news','markets','mail','messages','whatsapp'],paths={news:'/v1/workspace/news-feeds',markets:'/v1/workspace/trading',mail:'/v1/workspace/mail',messages:'/v1/workspace/native/messages',whatsapp:'/v1/workspace/native/whatsapp'},cache=new Map();
  let topic=0,index=0,cards=[],paused=false,timer=null,controller=null,epoch=0,dead=false,spoken=false,topicOnly=false;
  const body=panel.querySelector('.scene-brief-card'),progress=panel.querySelector('[role=status]'),pauseButton=panel.querySelector('[data-brief-pause]');
  function clear(){root.clearTimeout(timer);timer=null;}
  function pause(){paused=true;clear();pauseButton.textContent='Resume cards';}
  function visible(){return !dead&&!panel.hidden&&!doc.hidden&&!hub.closest('[hidden]')&&(doc.body.dataset.companion||'workspace')==='workspace';}
  function schedule(){clear();if(paused||!visible())return;timer=root.setTimeout(()=>{if(!visible()){pause();return;}if(options.voiceBusy?.()){schedule();return;}next();},9000);}
  function render(){
   if(!visible())return;const card=cards[index];if(!card)return;
   if(spoken){options.stopNarration?.();spoken=false;}
   body.classList.remove('brief-expanded');body.replaceChildren();const label=doc.createElement('small'),title=doc.createElement('h3'),detail=doc.createElement('p'),source=doc.createElement('small');
   label.textContent=card.regional?'REGIONAL NEWS':topics[topic].toUpperCase();title.textContent=card.title;detail.textContent=card.detail;source.textContent=card.source;if(card.image){const image=doc.createElement('img');image.className='scene-brief-image';image.src=card.image;image.alt='';image.decoding='async';image.referrerPolicy='no-referrer';image.onerror=()=>image.remove();body.append(image);}body.append(label,title,detail,source);options.onCard?.({kind:card.kind,unavailable:!!card.unavailable});
   for(const b of panel.querySelectorAll('[data-brief-topic]'))b.setAttribute('aria-pressed',String(b.dataset.briefTopic===topics[topic]));
   progress.textContent=(topic+1)+' / '+topics.length+' topics · '+(index+1)+' / '+cards.length+' items · '+(card.unavailable?'Needs attention':card.scope||'Connected source');
   body.classList.remove('brief-enter');void body.offsetWidth;body.classList.add('brief-enter');
   if(panel.querySelector('input').checked&&!card.unavailable&&!options.voiceBusy?.()){spoken=true;options.speak?.(card.title+'. '+card.detail.slice(0,320));}
   schedule();
  }
  async function readMail(signal){
   // A requested private briefing reads registered inboxes, never changes read flags.
   const results=await Promise.allSettled([options.api(paths.mail,undefined,{signal}),options.api('/v1/workspace/native/accounts',undefined,{signal})]);
   const live=results[0].status==='fulfilled'?results[0].value:{},accounts=results[1].status==='fulfilled'?results[1].value.accounts||[]:[];
   const local=await Promise.allSettled(accounts.slice(0,5).map(async account=>{
    const data=await options.api('/v1/workspace/native/mail?account='+encodeURIComponent(account.id),undefined,{signal});
    return (data.messages||[]).slice(0,4).map(item=>({...item,accountKey:account.id}));
   }));
   const rows=[...(live.messages||[]),...local.flatMap(result=>result.status==='fulfilled'?result.value:[])];
   const seen=new Set(),messages=rows.filter(item=>{const key=[item.subject,item.sender,item.received_at].join('|');if(seen.has(key))return false;seen.add(key);return true;}).sort((a,b)=>new Date(b.received_at)-new Date(a.received_at));
   return {state:messages.length||live.state==='connected'?'connected':'unavailable',messages,detail:'No registered inbox could be read. Check Connections and Mac access.'};
  }
  async function load(nextTopic){
   clear();controller?.abort();controller=new AbortController();const readController=controller,own=++epoch;topic=nextTopic;index=0;cards=[];body.textContent='Bringing the next item into view…';progress.textContent='Reading the connected source…';
   const kind=topics[topic],cached=cache.get(kind);if(cached){cards=cached;render();return;}
   const timeout=root.setTimeout(()=>readController.abort(),10000);
   try{const data=kind==='mail'?await readMail(readController.signal):await options.api(paths[kind],undefined,{signal:readController.signal});if(own!==epoch||dead)return;cards=briefingCards(kind,data);cache.set(kind,cards);}
   catch(error){if(own!==epoch||dead)return;cards=briefingCards(kind,{detail:error.message});}
   finally{root.clearTimeout(timeout);}
   if(own===epoch)render();
  }
  function finish(){pause();progress.textContent='You’re up to date with this briefing. What would you like to explore?';}
  function next(){if(index+1<cards.length){index++;render();}else if(!topicOnly&&topic<topics.length-1)load(topic+1);else finish();}
  function close(focus=true){clear();++epoch;controller?.abort();panel.hidden=true;launch.setAttribute('aria-expanded','false');hub.classList.remove('briefing-open');if(spoken){options.stopNarration?.();spoken=false;}if(focus)launch.focus({preventScroll:true});}
  function open(kind='news',read=false,onlyThisTopic=false){topicOnly=onlyThisTopic;options.onOpen?.();paused=false;pauseButton.textContent='Pause cards';panel.hidden=false;panel.querySelector('input').checked=read;hub.classList.add('briefing-open');launch.setAttribute('aria-expanded','true');load(Math.max(0,topics.indexOf(kind)));panel.querySelector('[data-brief-close]').focus({preventScroll:true});}
  launch.onclick=()=>{if(!panel.hidden)close();else open();};
  panel.querySelector('[data-brief-close]').onclick=()=>{options.onDismiss?.();close();};
  pauseButton.onclick=()=>{if(paused){paused=false;pauseButton.textContent='Pause cards';render();}else pause();};
  panel.querySelector('[data-brief-next]').onclick=next;
  panel.querySelector('[data-brief-next-topic]').onclick=()=>topic<topics.length-1?load(topic+1):finish();
  panel.querySelector('[data-brief-more]').onclick=async()=>{
   const card=cards[index];if(!card)return;pause();
   if(card.bodyPath){
    const own=epoch;const button=panel.querySelector('[data-brief-more]');button.disabled=true;
    try{const full=await options.api(card.bodyPath,undefined,{signal:controller?.signal});if(dead||panel.hidden||own!==epoch||cards[index]!==card)return;
     const text=full.body||full.text||full.preview;if(!text)throw new Error('No body');
     body.querySelector('p').textContent=String(text);body.classList.add('brief-expanded');progress.textContent='Full stored message · private · nothing marked read';
    }catch{if(own===epoch&&!panel.hidden)progress.textContent='Full message unavailable. Open Communications to check this inbox.';}
    finally{button.disabled=false;}return;
   }
   if(card.private){body.classList.add('brief-expanded');progress.textContent='Stored message text · private · nothing marked read';return;}
   if(card.kind==='news'&&card.url){try{const url=new URL(card.url);if(url.protocol==='https:'&&!url.username&&!url.password){root.open(url.href,'_blank','noopener,noreferrer');return;}}catch{}}
   close(false);options.navigate?.(card.view);
  };
  panel.querySelector('input').onchange=()=>{if(panel.querySelector('input').checked)render();else if(spoken){options.stopNarration?.();spoken=false;}};
  for(const button of panel.querySelectorAll('[data-brief-topic]'))button.onclick=()=>{topicOnly=false;load(topics.indexOf(button.dataset.briefTopic));};
  const activity=()=>{if(!visible())pause();else if(cards.length&&!body.querySelector('h3'))render();};const escape=e=>{if(e.key==='Escape'&&!panel.hidden&&!doc.querySelector('dialog[open]')){e.preventDefault();close();}};
  doc.addEventListener('visibilitychange',activity);root.addEventListener('jjrvis-companion-changed',activity);doc.addEventListener('keydown',escape);
  return {open,pause,close,destroy(){dead=true;close(false);doc.removeEventListener('visibilitychange',activity);root.removeEventListener('jjrvis-companion-changed',activity);doc.removeEventListener('keydown',escape);launch.remove();panel.remove();}};
 }
 root.JJSceneLayout={mount,mountBriefing};
 if(typeof module!=='undefined'&&module.exports)module.exports={briefingCards};
})(typeof window!=='undefined'?window:globalThis);
