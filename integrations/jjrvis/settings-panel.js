/* Device display preferences stay on this browser; shared AI choices use the broker. */
(function () {
  'use strict';
  const panels = {mail:'Inbox',calendar:'Zoho agenda',day:'Next actions',markets:'Broker markets',devices:'Device network',whatsapp:'WhatsApp',messages:'iMessage',calls:'Calls',news:'Market TV & news',library:'Files & knowledge',search:'Web search'};
  const defaultPanels = ['mail','markets','devices','day','calls','messages','whatsapp','news','calendar'];
  const key = 'jjrvis-display-v1';
  const palettes = [
    {id:'sky',name:'Sky',description:'Clear light blue',background:'#eaf4fc',ink:'#19364a',accent:'#246b91'},
    {id:'pearl',name:'Pearl',description:'Warm and light',background:'#f5f0e8',ink:'#40382d',accent:'#7b5f3d'},
    {id:'sage',name:'Sage',description:'Soft green',background:'#edf4ed',ink:'#294338',accent:'#396b51'},
    {id:'lavender',name:'Lavender',description:'Quiet violet',background:'#f1eef8',ink:'#3d3554',accent:'#69538f'},
    {id:'midnight',name:'Midnight',description:'Deep blue',background:'#091723',ink:'#e4f0f7',accent:'#7bc8e1'},
  ];
  const defaults = {appearance:'midnight',density:'comfortable',text:'standard',presence:'together',startView:'workspace',motion:true,startup:false,volume:0.85};
  const reducedMotion=window.matchMedia?.('(prefers-reduced-motion: reduce)');
  function read() {try {
    const saved=JSON.parse(localStorage.getItem(key)||'{}');
    if(!saved||typeof saved!=='object'||Array.isArray(saved))return {...defaults};
    let appearance=saved.appearance;
    if(appearance==='sky'&&saved.appearanceChosen!==true)appearance='midnight';
    if(appearance==='slate')appearance='midnight';
    if(!palettes.some(palette=>palette.id===appearance))appearance='midnight';
    return {...defaults,...saved,appearance,startView:saved.startView==='companion'?'companion':'workspace',startup:saved.startupChosen===true?!!saved.startup:false,presence:['moneypenny','jarvis','together'].includes(saved.presence)?saved.presence:defaults.presence,motion:saved.motionChosen===true?!!saved.motion:true};
  } catch {return {...defaults};}}
  function apply(p) {
    document.documentElement.dataset.appearance = palettes.some(palette=>palette.id===p.appearance)?p.appearance:'sky';
    document.documentElement.dataset.appearanceTone = p.appearance==='midnight'?'dark':'light';
    document.documentElement.dataset.presenceMode = ['moneypenny','jarvis','together'].includes(p.presence)?p.presence:'together';
    document.documentElement.dataset.density = p.density==='compact'?'compact':'comfortable';
    document.documentElement.dataset.textSize = p.text==='large'?'large':'standard';
    document.documentElement.classList.toggle('jj-reduced-motion',!p.motion||!!reducedMotion?.matches);
  }
  function announce(p){window.dispatchEvent(new CustomEvent('jjrvis-display-changed',{detail:{...p,effectiveMotion:!!p.motion&&!reducedMotion?.matches}}));}
  function save(p) {localStorage.setItem(key,JSON.stringify(p));localStorage.setItem('jjrvis-motion',p.motion&&!reducedMotion?.matches?'running':'paused');apply(p);announce(p);}
  apply(read());
  reducedMotion?.addEventListener?.('change',()=>{const p=read();apply(p);announce(p);});
  let activeDialog;
  window.JJSettings = {
    preferences:read,
    setPresence(value){if(!['moneypenny','jarvis','together'].includes(value))return false;save({...read(),presence:value});return true;},
    setAppearance(value){if(!palettes.some(palette=>palette.id===value))return false;save({...read(),appearance:value,appearanceChosen:true});return true;},
    open(options={},section='appearance') {
      if(activeDialog?.open){activeDialog.querySelector(`[data-section="${section}"]`)?.click();return;}
      const opener=document.activeElement;
      const dialog=document.createElement('dialog');activeDialog=dialog;dialog.className='jj-settings';dialog.setAttribute('aria-labelledby','settings-title');
      dialog.innerHTML=`<header class="settings-head"><div><p class="eyebrow">MAKE IT YOURS</p><h2 id="settings-title">Settings</h2></div><button type="button" class="secondary" data-close-settings aria-label="Close settings">Close ×</button></header><div class="settings-layout"><div class="settings-tabs" role="tablist" aria-label="Settings sections">${[['appearance','Appearance'],['panels','Your overview'],['voice','Voice & AI'],['accounts','Accounts & passwords'],['usage','Search & usage']].map(([id,label])=>`<button type="button" role="tab" id="settings-tab-${id}" aria-controls="settings-${id}" data-section="${id}">${label}</button>`).join('')}</div><div class="settings-body">${['appearance','panels','voice','accounts','usage'].map(id=>`<section role="tabpanel" id="settings-${id}" aria-labelledby="settings-tab-${id}" data-settings-pane="${id}" hidden></section>`).join('')}</div></div>`;
      document.body.append(dialog);
      const pane=id=>dialog.querySelector(`[data-settings-pane="${id}"]`);
      const p=read();
      pane('appearance').innerHTML=`<h3>Your display</h3><p>A place that feels like you. Every colour and assistant is available to everyone.</p><div class="settings-palettes" role="group" aria-label="Colour palette previews">${palettes.map(palette=>`<button type="button" class="settings-palette" data-palette="${palette.id}" aria-pressed="${p.appearance===palette.id}"><span class="palette-preview" aria-hidden="true"><i></i><i></i><i></i></span><strong>${palette.name}</strong><small>${palette.description}</small></button>`).join('')}</div><div class="settings-fields"><label>Colour palette<select data-display="appearance">${palettes.map(palette=>`<option value="${palette.id}">${palette.name} · ${palette.description}</option>`).join('')}</select></label><label>On your home screen<select data-display="presence"><option value="together">Moneypenny and Jarvis together</option><option value="moneypenny">Moneypenny</option><option value="jarvis">Jarvis · orb and world</option></select></label><label>When JJRVIS opens<select data-display="startView"><option value="workspace">Show the dashboard</option><option value="companion">Show the full companion</option></select></label><label>Spacing<select data-display="density"><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></label><label>Text size<select data-display="text"><option value="standard">Standard</option><option value="large">Larger</option></select></label><label class="settings-check"><input type="checkbox" data-display="motion"> Animate the globe and interface</label><p class="settings-motion-note">Your device’s reduced motion setting is also respected.</p><label class="settings-check"><input type="checkbox" data-display="startup"> Show the introduction when opening JJRVIS</label></div><p class="settings-saved" role="status">Changes apply immediately and are saved for this browser.</p>`;
      const updatePalettes=appearance=>pane('appearance').querySelectorAll('[data-palette]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.palette===appearance)));
      const changed=()=>pane('appearance').querySelector('[role="status"]').textContent='Saved on this browser.';
      pane('appearance').querySelectorAll('[data-display]').forEach(el=>{el.type==='checkbox'?el.checked=!!p[el.dataset.display]:el.value=p[el.dataset.display];el.onchange=()=>{const next=read();next[el.dataset.display]=el.type==='checkbox'?el.checked:el.value;if(el.dataset.display==='motion')next.motionChosen=true;if(el.dataset.display==='startup')next.startupChosen=true;if(el.dataset.display==='appearance'){next.appearanceChosen=true;updatePalettes(next.appearance);}save(next);changed();};});
      pane('appearance').querySelectorAll('[data-palette]').forEach(button=>button.onclick=()=>{const next={...read(),appearance:button.dataset.palette,appearanceChosen:true};save(next);pane('appearance').querySelector('[data-display="appearance"]').value=next.appearance;updatePalettes(next.appearance);changed();});
      let saved;try{saved=JSON.parse(localStorage.getItem('jjrvis-desk-v2'));}catch{}
      const selected=new Set(saved&&typeof saved==='object'?Object.keys(saved):defaultPanels);
      pane('panels').innerHTML=`<h3>Choose your overview panels</h3><p>Keep the information you use within reach. You can still open every workspace from the navigation.</p><div class="settings-panel-choices">${Object.entries(panels).map(([id,label])=>`<label class="settings-check"><input type="checkbox" data-panel="${id}" ${selected.has(id)?'checked':''}>${label}</label>`).join('')}</div><button type="button" data-save-panels>Apply panels</button><p role="status"></p>`;
      pane('panels').querySelector('[data-save-panels]').onclick=()=>{let old={};try{old=JSON.parse(localStorage.getItem('jjrvis-desk-v2')||'{}')}catch{}const chosen={};pane('panels').querySelectorAll('[data-panel]:checked').forEach(el=>chosen[el.dataset.panel]=old[el.dataset.panel]||{});localStorage.setItem('jjrvis-desk-v2',JSON.stringify(chosen));options.onPanels?.();pane('panels').querySelector('[role="status"]').textContent='Overview updated.';};
      pane('voice').innerHTML='<div data-ai-preferences></div><label class="settings-volume">Speaking volume <input type="range" min="0" max="100" step="5" data-volume><output></output></label><p>This controls JJRVIS speech on this browser. Your Mac volume also applies.</p>';
      options.mountVoice?.(pane('voice').querySelector('[data-ai-preferences]'));
      const volume=pane('voice').querySelector('[data-volume]');volume.value=Math.round(p.volume*100);const showVolume=()=>pane('voice').querySelector('output').textContent=volume.value+'%';showVolume();volume.oninput=()=>{save({...read(),volume:Number(volume.value)/100});showVolume();};
      pane('accounts').innerHTML='<h3>Your accounts</h3><div data-account-settings></div><h3 class="settings-subheading">Paired devices</h3><p>Each installed browser has its own private session. Rename this device or remove one you no longer use.</p><div data-session-devices><p>Checking paired devices…</p></div><h3 class="settings-subheading">Passwords & security</h3><p>Change your account password securely with its provider. This does not store your main account passwords in JJRVIS.</p><div class="settings-links"><a href="https://myaccount.google.com/security" target="_blank" rel="noopener noreferrer">Google account security ↗</a><a href="https://account.apple.com/" target="_blank" rel="noopener noreferrer">Apple account & app passwords ↗</a><a href="https://mysignins.microsoft.com/security-info" target="_blank" rel="noopener noreferrer">Microsoft work account security ↗</a><a href="https://account.microsoft.com/security" target="_blank" rel="noopener noreferrer">Microsoft personal account security ↗</a><a href="https://accounts.zoho.com/home#security" target="_blank" rel="noopener noreferrer">Zoho account security ↗</a></div><button class="secondary" type="button" data-lock-settings>Lock this JJRVIS session</button>';
      const deviceList=pane('accounts').querySelector('[data-session-devices]');
      const loadDevices=async()=>{try{const data=await options.api('/v1/workspace/sessions');deviceList.replaceChildren();if(!data.devices.length){deviceList.textContent='No paired browser sessions are active.';return;}data.devices.forEach(device=>{const row=document.createElement('div');row.className='settings-device';const field=document.createElement('input');field.value=device.label;field.maxLength=80;field.setAttribute('aria-label','Device name');const note=document.createElement('small');note.textContent=(device.current?'This device · ':'')+'Last used '+new Date(device.last_seen_at*1000).toLocaleString('en-GB');const action=document.createElement('button');action.type='button';action.className='secondary';action.textContent=device.current?'Rename':'Remove';action.onclick=async()=>{action.disabled=true;try{if(device.current)await options.api('/v1/workspace/sessions/name',{name:field.value});else await options.api('/v1/workspace/sessions/revoke',{session_id:device.id});await loadDevices();}catch(error){note.textContent=error.message;}finally{action.disabled=false;}};row.append(field,note,action);deviceList.append(row);});}catch(error){deviceList.textContent=error.message;}};
      loadDevices();
      if(window.JJMailAccounts)window.JJMailAccounts.mount(pane('accounts').querySelector('[data-account-settings]'),{api:options.api,onOpen:account=>{dialog.close();options.openAccount?.(account.id);}}).then(handle=>{if(!dialog.isConnected)handle.destroy();else dialog.addEventListener('close',()=>handle.destroy(),{once:true});});else pane('accounts').querySelector('[data-account-settings]').innerHTML='<p>Open Communications to choose a mailbox and check its connection.</p><button type="button" data-open-accounts>Open Communications</button>';
      pane('accounts').querySelector('[data-open-accounts]')?.addEventListener('click',()=>{dialog.close();options.navigate?.('communications');});
      pane('accounts').querySelector('[data-lock-settings]').onclick=()=>{dialog.close();options.lock?.();};
      pane('usage').innerHTML='<h3>Search, models & usage</h3><p>Use Google, Bing, DuckDuckGo and ChatGPT, or ask JJRVIS to search the web. The Research workspace includes the usage recorded by this app and links to your provider account totals.</p><button type="button" data-open-research>Open Search & usage</button><p>Higher answer quality changes the selected model. Provider budgets and account limits are managed in the provider’s own dashboard.</p>';
      pane('usage').querySelector('button').onclick=()=>{dialog.close();options.navigate?.('research');};
      const select=id=>{dialog.querySelectorAll('[data-section]').forEach(b=>{b.setAttribute('aria-selected',String(b.dataset.section===id));b.tabIndex=b.dataset.section===id?0:-1;});dialog.querySelectorAll('[data-settings-pane]').forEach(el=>el.hidden=el.dataset.settingsPane!==id);};
      dialog.querySelectorAll('[data-section]').forEach(b=>{b.onclick=()=>select(b.dataset.section);b.onkeydown=e=>{if(!['ArrowRight','ArrowLeft','ArrowUp','ArrowDown','Home','End'].includes(e.key))return;e.preventDefault();const tabs=[...dialog.querySelectorAll('[data-section]')],i=tabs.indexOf(b),next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(['ArrowRight','ArrowDown'].includes(e.key)?1:-1)+tabs.length)%tabs.length;tabs[next].click();tabs[next].focus();};});
      dialog.querySelector('[data-close-settings]').onclick=()=>dialog.close();
      dialog.addEventListener('close',()=>{dialog.querySelectorAll('audio').forEach(a=>{a.pause();if(a.src.startsWith('blob:'))URL.revokeObjectURL(a.src);});dialog.remove();opener?.isConnected&&opener.focus();});
      select(section);dialog.showModal();
    }
  };
})();
