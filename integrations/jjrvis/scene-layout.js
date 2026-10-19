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
  const names={brief:['01','Your day','Tasks & headlines'],weather:['02','Weather & sky','Forecast & sunset'],devices:['03','Device map','Reported connections']};
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
   if(!mounted.has(key)){mounted.add(key);options.mount?.(key,pane);}
   options.onChange?.(key);drawer.querySelector('.scene-drawer-close').focus({preventScroll:true});
  }
  const click=event=>{const button=event.target.closest('[data-scene-open]');if(button&&rail.contains(button))open(button.dataset.sceneOpen);};
  const escape=event=>{if(event.key==='Escape'&&active&&!doc.querySelector('dialog[open]')){event.preventDefault();close();}};
  rail.addEventListener('click',click);drawer.querySelector('button').onclick=()=>close();doc.addEventListener('keydown',escape);
  return {open,close,state:()=>active,destroy(){dead=true;close(false);doc.removeEventListener('keydown',escape);rail.removeEventListener('click',click);drawer.remove();rail.remove();decoration.remove();}};
 }
 root.JJSceneLayout={mount};
})(typeof window!=='undefined'?window:globalThis);
