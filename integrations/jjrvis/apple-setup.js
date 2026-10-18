/* Owner connections centre. No credentials, permissions or device activation on opening. */
(function (root) {
  'use strict';
  const sections=[['internet','Internet'],['mac','This Mac'],['iphone','iPhone & devices'],['mail','Email accounts'],['icloud','iCloud & photos'],['media','Camera & microphone'],['ai','AI services']];
  const labels={ready:'Connected',connected:'Connected',ready_to_pair:'Ready to pair',action_needed:'Setup needed',sign_in_needed:'Sign-in needed',available:'Available on request',not_connected:'Not connected',not_implemented:'Not supported here',unsupported:'Not supported here',unavailable:'Unavailable',check_needed:'Check needed',configured_unverified:'Configured · unchecked',credential_required:'Sign-in needed',model_missing:'Model needed'};
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const amount=value=>Number.isSafeInteger(value)&&value>=0?value.toLocaleString('en-GB'):null;
  const docs={install:'https://support.apple.com/guide/iphone/iph42ab2f3a7/ios',password:'https://support.apple.com/en-gb/102654',drive:'https://www.icloud.com/iclouddrive/',photos:'https://www.icloud.com/photos/'};
  function card(title,state,detail,action){return `<article class="apple-capability" data-capability-state="${esc(state)}"><div class="apple-card-top"><h3>${esc(title)}</h3><span class="apple-state" data-state="${esc(state)}">${esc(labels[state]||'Not checked')}</span></div><p>${esc(detail)}</p>${action?`<button type="button" class="secondary" data-apple-action="${esc(action.id)}">${esc(action.label)}</button>`:''}</article>`;}
  function models(data={},connections={},browser={}){
    const c=data.capabilities||{}, mail=c.mac_mail||{}, messages=c.mac_messages||{}, phone=c.iphone_web_app||{}, ai=connections.ai||{}, cloud=ai.cloud||{};
    const iCloud=(data.accounts||[]).find(account=>account.provider==='icloud');
    const iCloudState=['ready','connected'].includes(iCloud?.state)?'ready':iCloud?.reason==='sign_in_needed'?'sign_in_needed':iCloud?.state||(data.checked_at?'not_connected':'unavailable');
    return {
      internet:[['Your JJRVIS workspace',data.checked_at?'ready':'unavailable',data.checked_at?'This browser has reached your private workspace.':'The workspace connection has not been checked.'],['Private internet link',phone.https_verified?'ready':phone.state||'unavailable',phone.https_verified?'The secure web app address is reachable. Your Mac must stay awake and connected.':'The secure web app address could not be verified.'],['Public web search','available','Ask JJRVIS to search online for current public pages. Results are checked when you search; this overview does not run a search.',{id:'search',label:'Search & usage'}],['Signed-in websites','not_connected','Public search does not sign into your other websites. Supported accounts connect separately through their provider.']],
      mac:[['Apple Mail on this Mac',mail.state||'unavailable',amount(mail.count)!==null?`${amount(mail.count)} locally stored mail records are readable. This does not prove current cloud sync.`:mail.detail||'Local mail access has not been verified.'],['Messages on this Mac',messages.state||'unavailable',amount(messages.count)!==null?`${amount(messages.count)} locally stored messages are readable. Nothing is sent or marked read.`:messages.detail||'Open Messages and check macOS access.'],['Other folders',browser.folder?'available':'action_needed',browser.folder?'Select a folder for this browser visit. Persistent file indexing needs a separate connection.':'Folder selection is not supported by this browser here. You can open iCloud Drive and choose files to share.',{id:browser.folder?'folder':'drive',label:browser.folder?'Choose a folder':'Open iCloud Drive'}]],
      iphone:[['JJRVIS on your iPhone',browser.standalone?'ready':phone.state||'unavailable',browser.standalone?'JJRVIS is open in an installed app window on this device.':phone.detail||'Pair from your Mac, then add JJRVIS to the Home Screen in Safari.',{id:'pair',label:'Pair a device'}],['Native iPhone controls','unsupported','This web app does not have general control of your phone, calls, other apps or background sensors.']],
      icloud:[['iCloud Mail',iCloudState,iCloudState==='ready'?'Your iCloud inbox access is verified. Drive, Photos and other Apple services connect separately.':'Connect iCloud Mail separately using an Apple app-specific password. This does not connect your other iCloud services.',{id:'mail',label:iCloudState==='ready'?'Manage iCloud Mail':'Connect iCloud Mail'}],['iCloud Drive','not_connected','An iCloud Mail connection does not grant Drive access. You can open Drive or select a local folder for this visit.',{id:'drive',label:'Open iCloud Drive'}],['iCloud Photos',c.icloud_photos?.state||'not_connected','JJRVIS is not connected to your photo library. Open Photos to choose what you want to share.',{id:'photos',label:'Open iCloud Photos'}],['Apple Health',c.apple_health?.state||'not_connected','Health data is not connected to this workspace.'],['Apple Home',c.homekit?.state||'not_connected','No HomeKit connection is enabled here. Your separate home integrations keep their own status.'],['Sign in with Apple',c.apple_account_sign_in?.state||'not_implemented','JJRVIS does not request your main Apple Account password. Mail sign-in and device pairing are separate.']],
      media:[['Microphone',browser.media?'available':'unsupported','Check this browser’s microphone when you choose. The check does not record or send audio.',{id:'mic',label:'Check microphone'}],['Camera',browser.media?'available':'unsupported','Preview this device’s camera only when you choose. The preview stays in this browser.',{id:'camera',label:'Preview camera'}]],
      ai:[['Local assistant',ai.provider==='openai'?'not_connected':ai.state||'unavailable',ai.provider==='openai'?'Your selected assistant uses a cloud provider. Choose a local assistant in Voice & AI settings.':ai.state==='ready'?'The selected local model is installed. This check does not generate a reply.':'The selected local assistant could not be verified.',{id:'ai',label:'Voice & AI settings'}],['Cloud AI services',cloud.credential_configured?'configured_unverified':'credential_required',cloud.credential_configured?'A provider key is saved. This check makes no paid request; cloud replies use your selected AI settings.':'No configured cloud provider key was found. Local answers can work separately.',{id:'ai',label:'Manage AI services'}]]
    };
  }
  function mediaController(mediaDevices,update,preview,{delay=setTimeout,cancel=clearTimeout}={}){
    let stream=null,timer=null,generation=0;
    function stop(announce=true){generation++;if(timer)cancel(timer);timer=null;stream?.getTracks().forEach(track=>track.stop());stream=null;if(preview)preview.srcObject=null;if(announce)update('Camera and microphone checks are off.');}
    async function start(kind){
      stop(false);const request=++generation;
      if(!mediaDevices?.getUserMedia){update('This browser cannot request device access here. Use Safari over HTTPS or the local Mac workspace.');return;}
      update(kind==='camera'?'Waiting for your camera permission…':'Waiting for your microphone permission…');
      try{
        const next=await mediaDevices.getUserMedia({audio:kind==='mic',video:kind==='camera'});
        if(request!==generation){next.getTracks().forEach(track=>track.stop());return;}
        stream=next;if(preview&&kind==='camera'){preview.srcObject=next;preview.play()?.catch(()=>{});}
        update(kind==='camera'?'Camera preview is on. It stops automatically after 15 seconds.':'Microphone access works. Nothing is recorded; the check stops after 15 seconds.');
        timer=delay(()=>stop(),15000);
      }catch(error){if(request===generation)update(error?.name==='NotAllowedError'?'Access was not allowed. You can change this website’s permissions in your browser settings.':'The device could not be opened. Check whether another app is using it.');}
    }
    return {start,stop};
  }

  let dialog=null,options={},opener=null,active='internet',revision=0,mailMount=null,media=null;
  let data={},connections={},sessions=[],loadError='';
  const doc=()=>root.document;
  const one=selector=>dialog.querySelector(selector);
  function status(message){const target=one('[data-apple-status]');if(target)target.textContent=message;}
  async function api(path,body){
    if(options.api)return options.api(path,body);
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
    try{
      const response=await root.fetch(path,{credentials:'same-origin',cache:'no-store',signal:controller.signal,...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
      const result=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(response.status===401?'Connect this browser to JJRVIS first.':typeof result.detail==='string'?result.detail:'This connection could not be checked.');
      return result;
    }finally{clearTimeout(timer);}
  }
  function browserState(){return {media:!!root.navigator?.mediaDevices?.getUserMedia,folder:!!root.showDirectoryPicker,standalone:!!root.navigator?.standalone||!!root.matchMedia?.('(display-mode: standalone)').matches};}
  function select(id){
    active=sections.some(([key])=>key===id)?id:'internet';
    dialog.querySelectorAll('[data-apple-tab]').forEach(button=>{const selected=button.dataset.appleTab===active;button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;});
    dialog.querySelectorAll('[data-apple-pane]').forEach(pane=>pane.hidden=pane.dataset.applePane!==active);
    if(active==='mail')mountMail();
  }
  function external(url){root.open(url,'_blank','noopener,noreferrer');}
  function settings(section){close();if(options.settings)options.settings(section);else root.dispatchEvent(new CustomEvent('jjrvis-open-settings',{detail:{section}}));}
  async function chooseFolder(){
    if(!root.showDirectoryPicker){status('This browser does not support folder access here. Open iCloud Drive, or add files through the existing JJRVIS file workflow.');return;}
    try{const selected=await root.showDirectoryPicker({mode:'read'});status(`Selected “${selected.name}” for this visit. No files were uploaded or indexed; a folder connection still needs setup.`);}
    catch(error){if(error.name!=='AbortError')status('The folder could not be opened. No files were shared.');}
  }
  function act(id){
    if(id==='pair'){close();if(options.pair)options.pair();else doc().querySelector('#pair-phone')?.click();}
    else if(id==='mail')select('mail');
    else if(id==='ai')settings('voice');
    else if(id==='search')settings('usage');
    else if(id==='folder')chooseFolder();
    else if(id==='drive')external(docs.drive);
    else if(id==='photos')external(docs.photos);
    else if(id==='mic'||id==='camera'){select('media');media.start(id);}
  }
  function render(){
    const view=models(data,connections,browserState());
    for(const [id] of sections){if(id==='mail')continue;const target=one(`[data-apple-cards="${id}"]`);target.innerHTML=(view[id]||[]).map(args=>card(...args)).join('');}
    const summary=data.summary||{};
    one('[data-apple-summary]').textContent=data.checked_at?`${summary.verified_mailboxes||0} of ${summary.registered_mailboxes||0} mailboxes verified. Each connection below has its own access.`:'Connections are checked separately. Sign-in never grants access to every Apple service.';
    const accounts=Array.isArray(data.accounts)?data.accounts:[];
    one('[data-apple-mail-summary]').innerHTML=accounts.map(account=>card(account.masked_address||'Saved mailbox',account.reason==='sign_in_needed'?'sign_in_needed':account.state,account.inbox_count!==null&&amount(account.inbox_count)!==null?`${amount(account.inbox_count)} inbox items${amount(account.unread_count)!==null?` · ${amount(account.unread_count)} unread`:''}. Read-only provider check.`:account.detail||'Open this account to finish setup.')).join('');
    one('[data-apple-sessions]').innerHTML=sessions.length?sessions.map(session=>`<div class="apple-device"><div><strong>${esc(session.label||'Paired browser')}</strong><small>${session.current?'This browser':'Owner browser session'} · expires ${esc(new Date(session.expires_at*1000).toLocaleDateString('en-GB'))}</small></div><button type="button" class="secondary" data-apple-revoke="${esc(session.id)}" ${session.current?'disabled':''}>${session.current?'Current device':'Remove access'}</button></div>`).join(''):'<p>No paired browsers could be verified.</p>';
    one('[data-apple-error]').textContent=loadError;
    one('[data-apple-error]').hidden=!loadError;
    dialog.querySelectorAll('[data-apple-action]').forEach(button=>button.onclick=()=>act(button.dataset.appleAction));
    dialog.querySelectorAll('[data-apple-revoke]').forEach(button=>button.onclick=async()=>{button.disabled=true;try{await api('/v1/workspace/sessions/revoke',{session_id:button.dataset.appleRevoke});status('Device access removed.');await refresh();}catch(error){status(error.message||'Access could not be removed.');button.disabled=false;}});
    select(active);
  }
  async function mountMail(){
    if(mailMount||!root.JJMailAccounts?.mount)return;
    mailMount={destroy(){}};
    const current=revision;
    let mounted;
    try{mounted=await root.JJMailAccounts.mount(one('[data-apple-mail-mount]'),{api,onOpen:account=>{close();if(options.openAccount)options.openAccount(account.id);else settings('accounts');},notify:status});}
    catch{mailMount=null;status('Mail sign-in could not be opened. Refresh your connections and try again.');return;}
    if(current!==revision||!dialog.open){mounted?.destroy();return;}
    mailMount=mounted;
  }
  async function refresh(){
    const current=revision;status('Checking your connections…');
    one('[data-apple-refresh]').disabled=true;
    const results=await Promise.allSettled([api('/v1/workspace/apple-connections'),api('/v1/workspace/connections'),api('/v1/workspace/sessions')]);
    if(current!==revision||!dialog.open)return;
    data=results[0].status==='fulfilled'?results[0].value:{};
    connections=results[1].status==='fulfilled'?results[1].value:{};
    sessions=results[2].status==='fulfilled'?results[2].value.devices||[]:[];
    loadError=results[0].status==='rejected'?(results[0].reason.message||'Connections could not be loaded.'):'';
    render();one('[data-apple-refresh]').disabled=false;
    status(loadError?'Some connections need attention.':`Checked ${new Date().toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})}. Saved provider checks refresh within two minutes.`);
  }
  function mount(){
    if(dialog)return;
    dialog=doc().createElement('dialog');dialog.className='jj-apple-setup';dialog.setAttribute('aria-labelledby','apple-setup-title');
    dialog.innerHTML=`<header class="apple-setup-head"><div><p class="eyebrow">YOUR PRIVATE WORKSPACE</p><h2 id="apple-setup-title">Your connections</h2><p data-apple-summary>Everything in one place. Choose what JJRVIS can use.</p></div><button type="button" class="secondary" data-apple-close aria-label="Close connections">Close ×</button></header><div class="apple-setup-layout"><nav class="apple-setup-nav" role="tablist" aria-label="Connection categories">${sections.map(([id,title])=>`<button type="button" role="tab" id="apple-tab-${id}" data-apple-tab="${id}" aria-controls="apple-pane-${id}">${esc(title)}</button>`).join('')}</nav><div class="apple-setup-body"><p data-apple-error class="apple-setup-error" role="alert" hidden></p>${sections.map(([id,title])=>`<section id="apple-pane-${id}" data-apple-pane="${id}" role="tabpanel" aria-labelledby="apple-tab-${id}" hidden><h2>${esc(title)}</h2>${id==='mail'?'<p>Connect each provider separately. Your main account password stays with its provider.</p><div class="apple-card-grid" data-apple-mail-summary></div><div data-apple-mail-mount></div>':`<div class="apple-card-grid" data-apple-cards="${id}"></div>`}${id==='iphone'?`<div class="apple-install"><h3>Add JJRVIS to your iPhone</h3><ol><li>Pair this device from your signed-in Mac workspace.</li><li>Open JJRVIS in Safari and choose Share → Add to Home Screen.</li><li>Enable Open as Web App if offered, then tap Add.</li></ol><a href="${docs.install}" target="_blank" rel="noopener noreferrer">Apple’s installation guide ↗</a></div><h3 class="apple-subheading">Devices with owner access</h3><p>Remove access for a browser you no longer use. A browser session does not prove an iPhone is installed or online.</p><div data-apple-sessions></div>`:''}${id==='media'?'<div class="apple-media-check"><video data-apple-video muted playsinline aria-label="Local camera preview"></video><button type="button" class="secondary" data-apple-stop>Stop device checks</button><p>No audio or video is uploaded by these checks. Access is requested separately on each device.</p></div>':''}${id==='icloud'?`<p class="apple-explanation"><a href="${docs.password}" target="_blank" rel="noopener noreferrer">Apple’s app-specific password guide ↗</a>. iCloud Mail uses an app-specific password and two-factor authentication. It does not grant access to Photos, Drive, Health or your Home.</p>`:''}</section>`).join('')}</div></div><footer class="apple-setup-foot"><p role="status" aria-live="polite" data-apple-status></p><button type="button" class="secondary" data-apple-refresh>Refresh connections</button></footer>`;
    doc().body.append(dialog);
    media=mediaController(root.navigator?.mediaDevices,status,one('[data-apple-video]'));
    one('[data-apple-close]').onclick=close;one('[data-apple-refresh]').onclick=refresh;one('[data-apple-stop]').onclick=()=>media.stop();
    dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
    dialog.addEventListener('close',()=>{revision++;media.stop(false);mailMount?.destroy();mailMount=null;data={};connections={};sessions=[];loadError='';one('[data-apple-mail-mount]').replaceChildren();opener?.isConnected&&opener.focus();});
    dialog.querySelectorAll('[data-apple-tab]').forEach(button=>{button.onclick=()=>select(button.dataset.appleTab);button.onkeydown=event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key))return;event.preventDefault();const tabs=[...dialog.querySelectorAll('[data-apple-tab]')],index=tabs.indexOf(button),next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(['ArrowDown','ArrowRight'].includes(event.key)?1:-1)+tabs.length)%tabs.length;tabs[next].click();tabs[next].focus();};});
    root.addEventListener('jjrvis-mail-accounts-changed',()=>{if(dialog.open)refresh();});
  }
  function open(nextOptions={},section='internet'){
    if(typeof nextOptions==='string'){section=nextOptions;nextOptions={};}
    options={...options,...nextOptions};mount();active=section;
    if(!dialog.open){opener=doc().activeElement;revision++;dialog.showModal();}
    render();refresh();one('[data-apple-close]').focus();
  }
  function close(){if(dialog?.open)dialog.close();}
  const apiObject={open,close};
  root.JJAppleSetup=apiObject;
  if(typeof module!=='undefined'&&module.exports)module.exports={models,card,mediaController,labels,docs};
})(typeof window!=='undefined'?window:globalThis);
