/* A view of the existing assistant. This module never creates another avatar,
   starts a microphone, or moves the mounted presence iframe. */
(()=>{
 'use strict';
 const key='jjrvis-companion-position-v1',size={width:88,height:94};
 let configuration={},mode='workspace',hidden=false,lastFocus=null,drag=null,suppressClick=false;
 const inertBefore=new Map();
 const toolbar=document.createElement('div');toolbar.className='jj-companion-toolbar';toolbar.hidden=true;toolbar.setAttribute('role','toolbar');toolbar.setAttribute('aria-label','Companion controls');
 toolbar.innerHTML='<span class="jj-companion-title">Moneypenny <small>Same assistant. Your space.</small></span><div><button type="button" data-companion-action="exit">Dashboard</button><button type="button" data-companion-action="shrink">Small icon</button><button type="button" data-companion-action="hide" title="Hide the character; your conversation stays open">Hide</button><button type="button" data-companion-action="stop">Stop speaking</button><button type="button" data-companion-action="connections" hidden>Connected apps</button><button type="button" data-companion-action="popup" title="Open a separate browser window. Your system controls which window stays in front.">Small window ↗</button></div>';
 const icon=document.createElement('button');icon.type='button';icon.className='jj-companion-icon';icon.hidden=true;icon.innerHTML='<span aria-hidden="true">M<span>✦</span></span><b>Moneypenny</b>';icon.setAttribute('aria-label','Open Moneypenny. Drag to move, or use arrow keys. Escape returns to the dashboard.');icon.setAttribute('aria-controls','assistant-panel');
 const restore=document.createElement('button');restore.type='button';restore.className='jj-companion-restore';restore.hidden=true;restore.textContent='✦ Bring back Moneypenny';
 const status=document.createElement('p');status.className='jj-companion-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 document.body.append(toolbar,icon,restore,status);
 const viewport=()=>({width:window.visualViewport?.width||window.innerWidth,height:window.visualViewport?.height||window.innerHeight});
 const clamp=value=>{const view=viewport();return {x:Math.max(8,Math.min(view.width-size.width-8,Number(value?.x)||8)),y:Math.max(8,Math.min(view.height-size.height-8,Number(value?.y)||8))};};
 let position;try{const saved=JSON.parse(localStorage.getItem(key));if(Number.isFinite(saved?.x)&&Number.isFinite(saved?.y))position=clamp(saved);}catch{}
 if(!position){const view=viewport();position=clamp({x:view.width-size.width-18,y:view.height-size.height-18});}
 function place(value,persist=false){position=clamp(value);icon.style.left=position.x+'px';icon.style.top=position.y+'px';if(persist)try{localStorage.setItem(key,JSON.stringify(position));}catch{}return {...position};}
 function setInert(open){
  if(open){for(const element of document.querySelectorAll('body > aside, main > :not(#content), #content > :not(.presence-hub), body > .assistant-launch')){if(!inertBefore.has(element))inertBefore.set(element,element.inert);element.inert=true;}}
  else{for(const [element,previous] of inertBefore)element.inert=previous;inertBefore.clear();}
 }
 function change(next,isHidden=false){
  mode=next;hidden=isHidden;document.body.dataset.companion=mode;document.body.dataset.companionHidden=String(hidden);
  toolbar.hidden=mode!=='open';icon.hidden=mode!=='icon';restore.hidden=!hidden;setInert(mode==='open');place(position);
  configuration.postToPresence?.({type:'jjrvis-presence-visibility',visible:!document.hidden&&mode!=='icon'&&!hidden});
  window.dispatchEvent(new CustomEvent('jjrvis-companion-changed',{detail:{mode,hidden}}));
 }
 function enter(){
  if(typeof configuration.showAssistant!=='function')return false;
  if(configuration.showAssistant()===false)return false;
  if(!document.querySelector('.presence-hub')&&configuration.navigate)configuration.navigate('overview');
  if(!document.querySelector('.presence-hub'))return false;
  if(mode==='workspace'&&!hidden&&!document.activeElement?.closest('.jj-companion-toolbar,.jj-companion-icon,.jj-companion-restore'))lastFocus=document.activeElement;
  change('open');status.textContent='Moneypenny companion opened. Escape returns to the dashboard.';
  (document.querySelector('#assistant-input')||toolbar.querySelector('button')).focus({preventScroll:true});return true;
 }
 function exit(){change('workspace');status.textContent='Dashboard restored.';if(lastFocus?.isConnected&&!lastFocus.closest('.jj-companion-toolbar'))lastFocus.focus({preventScroll:true});return true;}
 function shrink(){change('icon');status.textContent='Moneypenny is in the movable icon. Her graphics are paused.';icon.focus({preventScroll:true});return true;}
 function hide(){change('workspace',true);status.textContent='Moneypenny hidden. Use Bring back Moneypenny to restore her.';restore.focus({preventScroll:true});return true;}
 function stop(){try{return Promise.resolve(configuration.stopSpeaking?.()).catch(()=>{status.textContent='Could not stop playback. Use the conversation Stop button.';});}catch{status.textContent='Could not stop playback. Use the conversation Stop button.';return Promise.resolve();}}
 function openPopup(){
  const view=viewport(),width=Math.min(420,view.width),height=Math.min(650,view.height),left=Math.max(0,(window.screen?.availWidth||view.width)-width-24),top=Math.max(0,(window.screen?.availHeight||view.height)-height-48);
  const popup=window.open('/workspace?companion=1','jjrvis-companion',`popup=yes,width=${Math.round(width)},height=${Math.round(height)},left=${Math.round(left)},top=${Math.round(top)},resizable=yes,scrollbars=yes`);
  status.textContent=popup?'Companion opened in a separate browser window.':'Your browser blocked the window. Allow pop-ups for JJRVIS or use this companion here.';return !!popup;
 }
 function configure(options={}){configuration={...configuration,...options};toolbar.querySelector('[data-companion-action="connections"]').hidden=!configuration.connections&&!configuration.navigate;return window.JJCompanion;}
 const actions={enter,exit,shrink,hide,stop,popup:openPopup,connections:()=>{exit();if(configuration.connections)configuration.connections();else configuration.navigate?.('connections');}};
 toolbar.addEventListener('click',event=>{const button=event.target.closest('[data-companion-action]');if(button)actions[button.dataset.companionAction]?.();});
 icon.addEventListener('click',()=>{if(suppressClick){suppressClick=false;return;}enter();});restore.addEventListener('click',enter);
 icon.addEventListener('pointerdown',event=>{if(event.button!==0)return;drag={id:event.pointerId,x:event.clientX,y:event.clientY,start:{...position},moved:false};suppressClick=false;icon.setPointerCapture(event.pointerId);});
 icon.addEventListener('pointermove',event=>{if(!drag||event.pointerId!==drag.id)return;const x=event.clientX-drag.x,y=event.clientY-drag.y;if(Math.hypot(x,y)>6)drag.moved=true;if(drag.moved)place({x:drag.start.x+x,y:drag.start.y+y});});
 icon.addEventListener('pointerup',event=>{if(!drag||event.pointerId!==drag.id)return;suppressClick=drag.moved;drag=null;place(position,true);});
 icon.addEventListener('pointercancel',()=>{drag=null;suppressClick=false;});
 icon.addEventListener('keydown',event=>{const delta={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];if(!delta)return;event.preventDefault();const step=event.shiftKey?24:10;place({x:position.x+delta[0]*step,y:position.y+delta[1]*step},true);});
 document.addEventListener('keydown',event=>{if(event.defaultPrevented||event.key!=='Escape'||mode==='workspace'||document.querySelector('dialog[open]'))return;event.preventDefault();exit();});
 window.addEventListener('resize',()=>place(position));window.visualViewport?.addEventListener('resize',()=>place(position));
 window.JJCompanion=Object.freeze({configure,enter,exit,shrink,hide,stop,openPopup,toggle:()=>mode==='open'?exit():enter(),state:()=>({mode,hidden,position:{...position}})});
 change('workspace');
})();
