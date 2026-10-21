/* Read-only clock and device HUD, plus progressive navigation disclosures. */
(function(root){
 'use strict';
 const navInstances=new WeakMap();
 let nextId=0;
 const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
 const epoch=value=>{if(value===null||value===undefined||value==='')return null;const n=typeof value==='number'||typeof value==='string'&&/^\d+(?:\.\d+)?$/.test(value.trim())?Number(value)*1000:Date.parse(value);return Number.isFinite(n)?n:null;};
 function clockText(now=new Date(),timeZone){
  const date=now instanceof Date?now:new Date(now),zone=timeZone?{timeZone}:{};
  if(!Number.isFinite(date.getTime()))return {local:'--:--:--',utc:'--:--:--',date:'Time unavailable',zone:'LOCAL'};
  const format=options=>new Intl.DateTimeFormat('en-GB',options).format(date);
  return {local:format({...zone,hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}),utc:format({timeZone:'UTC',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}),date:format({...zone,weekday:'long',day:'numeric',month:'long'}),zone:(timeZone||Intl.DateTimeFormat().resolvedOptions().timeZone||'Local time').replace(/_/g,' ')};
 }
 function viewModel(values={},now=Date.now()){
  const connections=values.connections?.system||values.connections;
  const system=values.system||{};
  const rows=Array.isArray(values.devices)?values.devices:Array.isArray(values.devices?.devices)?values.devices.devices:null;
  const devices=(rows||[]).filter(item=>item&&typeof item==='object').map(item=>{
   const seen=epoch(item.last_seen),age=seen===null?null:Math.max(0,(now-seen)/1000);
   const live=item.online===true&&(age===null||age<180);
   const state=live?'ready':item.online===false||age!==null&&age>=180?'offline':'unknown';
   const minutes=age===null?null:Math.floor(age/60);
   const detail=live?'Reporting now':state==='offline'?(minutes===null?'Not currently reporting':minutes<1?'Last report just now':minutes<60?`Last report ${minutes} min ago`:minutes<1440?`Last report ${Math.floor(minutes/60)} hr ago`:`Last report ${Math.floor(minutes/1440)} days ago`):'Heartbeat not checked';
   return {name:String(item.name||'Unnamed device'),kind:['Mac','iPhone','iPad','browser'].includes(item.kind)?item.kind:'Device',state,detail,lastSeen:seen};
  }).sort((a,b)=>(b.state==='ready')-(a.state==='ready')||((b.lastSeen??0)-(a.lastSeen??0)));
  const ai=connections?.ai,voice=system.voice;
  const services=[];
  if(ai){
   const ready=ai.state==='ready';
   services.push({name:'Assistant model',state:ready?'ready':ai.state==='configured_unverified'?'unknown':'unavailable',detail:ready?'Selected model available':ai.state==='configured_unverified'?'Configured · not tested':ai.state==='model_missing'?'Selected model is not installed':ai.state==='credential_required'?'Sign-in needed':'Connection unavailable'});
  }else services.push({name:'Assistant model',state:'unknown',detail:'Awaiting connection check'});
  if(voice)services.push({name:'Voice engine',state:voice.state==='ready'?'ready':voice.state==='unavailable'?'unavailable':'unknown',detail:voice.state==='ready'?'Speech engine available':voice.state==='unavailable'?'Speech engine unavailable':'Not checked'});
  else if(connections?.moneypenny)services.push({name:'Moneypenny',state:connections.moneypenny.state==='ready'?'ready':'unavailable',detail:connections.moneypenny.state==='ready'?'Character renderer available':'Character connection unavailable'});
  return {devices:devices.slice(0,3),registered:rows===null?null:devices.length,reporting:rows===null?null:devices.filter(item=>item.state==='ready').length,services,checked:connections?.checked_at||null};
 }
 function renderDevices(model){
  const summary=model.registered===null?'Waiting for device reports':model.registered===0?'No devices have reported':`${model.reporting} reporting · ${model.registered} registered`;
  return `<div class="command-devices-heading"><h3>Your devices</h3><span>${esc(summary)}</span></div>${model.devices.length?`<ul class="command-device-list">${model.devices.map((device,index)=>`<li><button type="button" class="command-device" data-command-action="home" data-command-focus="device-${index}"><span class="command-device-icon" data-kind="${esc(device.kind)}" aria-hidden="true"></span><span class="command-device-copy"><strong>${esc(device.name)}</strong><small>${esc(device.kind)} · ${esc(device.detail)}</small></span><span class="command-state-dot" data-state="${device.state}" aria-hidden="true"></span></button></li>`).join('')}</ul>`:`<p class="command-device-empty">${model.registered===0?'Pair a device to bring its status into view.':'Device status appears after the workspace check.'}</p>`}${model.registered>3?`<p class="command-device-more">${model.registered-3} more in Home & devices</p>`:''}<ul class="command-service-list">${model.services.map(service=>`<li><span class="command-state-dot" data-state="${service.state}" aria-hidden="true"></span><span><strong>${esc(service.name)}</strong><small>${esc(service.detail)}</small></span></li>`).join('')}</ul>`;
 }
 function mount(target,options={}){
  if(!target)throw new TypeError('A command deck host is required');
  const document=target.ownerDocument||root.document;
  let values={connections:typeof options.connections==='function'?null:options.connections,system:options.system,devices:options.devices},destroyed=false,timer=null,inView=true,lastDevices='';
  target.classList.add('command-deck');
  target.innerHTML='<section class="command-status-panel" aria-label="Time and devices"><header class="command-panel-heading"><span class="command-panel-label">YOUR COMMAND CENTRE</span><span class="command-panel-mark" aria-hidden="true">◈</span></header><div class="command-clock"><p class="command-clock-label">LOCAL TIME</p><time class="command-local-time" data-command-clock="local" aria-label="Local time"></time><p class="command-local-date" data-command-clock="date"></p><div class="command-world-time"><span data-command-clock="zone"></span><span><time data-command-clock="utc" aria-label="UTC time"></time> UTC</span></div></div><div class="command-device-body"></div><footer class="command-panel-actions"><button type="button" data-command-action="connections">Connections <span aria-hidden="true">↗</span></button><button type="button" data-command-action="pair">Pair device <span aria-hidden="true">+</span></button></footer></section>';
  const clockNodes={};for(const key of ['local','date','zone','utc'])clockNodes[key]=target.querySelector(`[data-command-clock="${key}"]`);
  const body=target.querySelector('.command-device-body');
  function visible(){const mode=document.body?.dataset?.companion;return !destroyed&&inView&&!document.hidden&&target.isConnected!==false&&!target.hidden&&!target.closest?.('[hidden]')&&(!mode||mode==='workspace')&&document.body?.dataset?.companionHidden!=='true';}
  function render(now){
   const model=viewModel(values,now),next=renderDevices(model);if(next===lastDevices)return;
   const focus=body.contains(document.activeElement)?document.activeElement?.dataset?.commandFocus:null;
   lastDevices=next;body.innerHTML=next;
   if(focus&&/^device-[0-2]$/.test(focus))body.querySelector(`[data-command-focus="${focus}"]`)?.focus({preventScroll:true});
  }
  function tick(){if(!visible())return;const now=new Date(),text=clockText(now);for(const key of Object.keys(clockNodes))if(clockNodes[key])clockNodes[key].textContent=text[key];clockNodes.local?.setAttribute('datetime',now.toISOString());clockNodes.utc?.setAttribute('datetime',now.toISOString());render(now.getTime());}
  function activity(){if(visible()){tick();if(timer===null)timer=root.setInterval(tick,1000);}else if(timer!==null){root.clearInterval(timer);timer=null;}}
  function click(event){const button=event.target.closest?.('[data-command-action]');if(!button||!target.contains(button))return;if(button.dataset.commandAction==='pair'&&typeof options.pair==='function')options.pair();else if(button.dataset.commandAction==='connections'){if(typeof options.connections==='function')options.connections();else options.navigate?.('connections');}else options.navigate?.('home');}
  target.addEventListener('click',click);document.addEventListener('visibilitychange',activity);root.addEventListener?.('jjrvis-companion-changed',activity);
  const observer=typeof root.IntersectionObserver==='function'?new root.IntersectionObserver(entries=>{inView=entries.some(entry=>entry.isIntersecting);activity();}):null;observer?.observe(target);
  render(Date.now());activity();
  return {update(next={}){if(destroyed)return;for(const key of ['system','devices','connections'])if(key in next)values[key]=next[key];render(Date.now());activity();},destroy(){if(destroyed)return;destroyed=true;if(timer!==null)root.clearInterval(timer);timer=null;observer?.disconnect();document.removeEventListener('visibilitychange',activity);root.removeEventListener?.('jjrvis-companion-changed',activity);target.removeEventListener('click',click);values={};target.replaceChildren();target.classList.remove('command-deck');}};
 }
 function init(options={}){
  const document=options.nav?.ownerDocument||root.document,nav=options.nav||document.querySelector('nav[aria-label="Workspace navigation"]');
  if(!nav)return {destroy(){},update(){}};
  if(navInstances.has(nav))return navInstances.get(nav);
  const originalNodes=Array.from(nav.childNodes),buttons=Array.from(nav.querySelectorAll('button[data-view]'));
  if(!buttons.length)return {destroy(){},update(){}};
  const originalCurrent=new Map(buttons.map(button=>[button,button.getAttribute('aria-current')])),hadClass=nav.classList.contains('command-nav');
  const groups=[],home=buttons.find(button=>button.dataset.view==='overview'),id=++nextId;
  const hadHomeClass=home?.classList.contains('command-nav-home');
  const categories=[{label:'Work',views:['communications','junomo','trading','plan']},{label:'Connected',views:['home','rooms','jarvis','connections']},{label:'Explore',views:['news','music','research','library']}];
  const known=new Set(['overview',...categories.flatMap(group=>group.views)]);categories[2].views.push(...buttons.filter(button=>!known.has(button.dataset.view)).map(button=>button.dataset.view));
  nav.replaceChildren();nav.classList.add('command-nav');if(home){home.classList.add('command-nav-home');nav.append(home);}
  for(const category of categories){
   const children=category.views.flatMap(view=>buttons.filter(button=>button.dataset.view===view));if(!children.length)continue;
   const details=document.createElement('details'),summary=document.createElement('summary'),panel=document.createElement('div'),label=document.createElement('span'),arrow=document.createElement('span');
   details.className='command-nav-group';summary.className='command-nav-trigger';panel.className='command-nav-popover';panel.id=`command-nav-${id}-${groups.length}`;
   label.textContent=category.label;arrow.className='command-nav-chevron';arrow.textContent='⌄';arrow.setAttribute('aria-hidden','true');summary.append(label,arrow);summary.setAttribute('aria-controls',panel.id);summary.setAttribute('aria-expanded','false');panel.append(...children);details.append(summary,panel);nav.append(details);groups.push({details,summary,panel,buttons:children});
  }
  function expanded(group,value){if(group.details.open!==value)group.details.open=value;group.summary.setAttribute('aria-expanded',String(value));}
  function close(except){for(const group of groups)if(group!==except)expanded(group,false);}
  function sync(){for(const button of buttons){if(button.classList.contains('active'))button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');}for(const group of groups){const active=group.buttons.some(button=>button.classList.contains('active'));if(group.summary.classList.contains('command-nav-current')!==active)group.summary.classList.toggle('command-nav-current',active);group.summary.setAttribute('aria-expanded',String(group.details.open));}}
  function groupFor(node){return groups.find(group=>group.details.contains(node));}
  function click(event){const group=groupFor(event.target);if(!group){close();return;}if(group.summary.contains(event.target))close(group);else if(event.target.closest?.('button[data-view]')){close();sync();}}
  function keydown(event){
   const group=groupFor(event.target);if(!group)return;const onSummary=group.summary.contains(event.target),index=group.buttons.indexOf(document.activeElement);
   if(event.key==='Escape'&&group.details.open){event.preventDefault();expanded(group,false);group.summary.focus();}
   else if((event.key==='ArrowDown'||event.key==='ArrowUp')&&(onSummary||index>=0)){event.preventDefault();close(group);expanded(group,true);const next=onSummary?(event.key==='ArrowDown'?0:group.buttons.length-1):(index+(event.key==='ArrowDown'?1:-1)+group.buttons.length)%group.buttons.length;group.buttons[next]?.focus();}
   else if((event.key==='Home'||event.key==='End')&&index>=0){event.preventDefault();group.buttons[event.key==='Home'?0:group.buttons.length-1]?.focus();}
  }
  function outside(event){if(!nav.contains(event.target))close();}
  function focusout(event){if(!event.relatedTarget)return;const group=groupFor(event.target);if(group&&!group.details.contains(event.relatedTarget))expanded(group,false);if(!nav.contains(event.relatedTarget))close();}
  const toggles=groups.map(group=>{const handler=()=>{if(group.details.open)close(group);group.summary.setAttribute('aria-expanded',String(group.details.open));};group.details.addEventListener('toggle',handler);return [group.details,handler];});
  nav.addEventListener('click',click);nav.addEventListener('keydown',keydown);nav.addEventListener('focusout',focusout);document.addEventListener('pointerdown',outside);
  const observer=typeof root.MutationObserver==='function'?new root.MutationObserver(sync):null;observer?.observe(nav,{subtree:true,attributes:true,attributeFilter:['class']});sync();
  let destroyed=false;
  const handle={update:sync,destroy(){if(destroyed)return;destroyed=true;observer?.disconnect();nav.removeEventListener('click',click);nav.removeEventListener('keydown',keydown);nav.removeEventListener('focusout',focusout);document.removeEventListener('pointerdown',outside);for(const [node,handler]of toggles)node.removeEventListener('toggle',handler);nav.replaceChildren(...originalNodes);if(!hadClass)nav.classList.remove('command-nav');if(!hadHomeClass)home?.classList.remove('command-nav-home');for(const [button,current]of originalCurrent)if(current===null)button.removeAttribute('aria-current');else button.setAttribute('aria-current',current);navInstances.delete(nav);}};
  navInstances.set(nav,handle);return handle;
 }
 root.JJCommandDeck={mount,init};
 if(typeof module!=='undefined'&&module.exports)module.exports={mount,init,viewModel,clockText,renderDevices};
})(typeof window!=='undefined'?window:globalThis);
